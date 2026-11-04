"""Domain 5: Wildfires & Land Disturbance Pipeline Implementation

Implements:
- Input validation: Baseline and post-fire cross-polarized (HV/VH) SAR rasters.
- Optional NASA FIRMS active thermal fire points (GeoJSON).
- Optional independent burn-perimeter/disturbance reference mask for IoU/F1/Precision/Recall validation.
- Optional WUI settlements, roads, and infrastructure GeoJSON for spatial exposure analysis.
- Radar structural disturbance mapping through smoke plumes (Delta HV drop).
- Spatial intersection between radar disturbance polygons and thermal detections.
- Multi-tier scientific explainability separating radar canopy loss from optical char or fire causation.
"""
from __future__ import annotations

import json
import numpy as np
from rasterio.enums import Resampling

from app.services.pipeline import (
    DomainPipeline,
    InputSpec,
    ParamSpec,
    PipelineContext,
    PipelineInputError,
    max_pixels,
)
from app.utils.exposure import evaluate_spatial_exposure
from app.utils.raster import (
    DIVERGING,
    align_to,
    box_mean,
    build_inspector_grid,
    common_stretch,
    fmt,
    lonlat_to_pixel,
    mask_area_m2,
    pixel_area_m2,
    power_to_db,
    read_band,
    remove_small_clusters,
    to_power,
    write_class_png,
    write_geotiff,
    write_grayscale_png,
    write_ramp_png,
)
from app.utils.validation import evaluate_binary_classification


class WildfiresPipeline(DomainPipeline):
    domain = "domain5"
    analysis_name = "Wildfire Burn Scar & Radar Disturbance Analysis"
    summary = (
        "Maps smoke-penetrating forest canopy disturbance and potential structural burn scars using SAR backscatter "
        "changes, corroborated with independent NASA FIRMS active thermal hotspot evidence and reference perimeters."
    )
    implementation_status = "implemented"
    deferred_features = [
        "Post-fire hydrological debris flow runoff simulation",
        "Multispectral dNBR optical calibration",
    ]

    inputs = [
        InputSpec(
            role="baseline",
            label="Pre-Fire Baseline SAR (HV/VH)",
            product_types=["sar_backscatter"],
            required=True,
            description="Pre-fire cross-polarized SAR raster representing intact forest canopy.",
        ),
        InputSpec(
            role="event",
            label="Post-Fire SAR (HV/VH)",
            product_types=["sar_backscatter"],
            required=True,
            description="Post-fire or active-fire SAR raster acquired through smoke.",
        ),
        InputSpec(
            role="fire_detections",
            label="Active Fire Thermal Detections (Optional GeoJSON)",
            product_types=["fire_detections"],
            required=False,
            description="NASA FIRMS (VIIRS/MODIS) thermal anomaly points in GeoJSON format.",
        ),
        InputSpec(
            role="reference_disturbance",
            label="Independent Mapped Burn Perimeter (Optional Validation)",
            product_types=["reference_disturbance"],
            required=False,
            description="Independent mapped fire perimeter or dNBR burn-severity raster (1=burned) for validation.",
        ),
        InputSpec(
            role="exposure_assets",
            label="WUI Settlements & Infrastructure (Optional GeoJSON)",
            product_types=["exposure_assets"],
            required=False,
            description="Georeferenced WUI communities, evacuation roads, or utility lines (GeoJSON) for exposure intersection.",
        ),
    ]

    params = [
        ParamSpec(
            name="burn_drop_db",
            label="Burn Scar Drop Threshold (dB)",
            type="number",
            default=3.2,
            min=1.0,
            max=10.0,
            description="Minimum drop in cross-polarized backscatter to classify structural canopy disturbance.",
        ),
        ParamSpec(
            name="filter_window",
            label="Speckle Filter Window",
            type="integer",
            default=5,
            min=3,
            max=15,
            description="Boxcar spatial filter size.",
        ),
        ParamSpec(
            name="min_cluster_pixels",
            label="Minimum Scar Size (pixels)",
            type="integer",
            default=5,
            min=1,
            max=100,
            description="Sieve threshold for removing isolated speckle artifacts.",
        ),
    ]

    def run(self, ctx: PipelineContext) -> dict:
        import time

        notes: list[str] = []
        warnings: list[str] = []
        t_seg_start = time.perf_counter()

        base_ds = ctx.datasets["baseline"]
        event_ds = ctx.datasets["event"]
        pol_label = (base_ds.polarization or event_ds.polarization or "HV/VH").upper()
        notes.append(f"Evaluated cross-polarized channel: {pol_label} ({base_ds.sensor or 'SAR'}).")

        if (
            base_ds.acquisition_date
            and event_ds.acquisition_date
            and base_ds.acquisition_date > event_ds.acquisition_date
        ):
            warnings.append(
                f"Chronological order warning: Pre-fire baseline ({base_ds.acquisition_date}) is later than "
                f"Post-fire event ({event_ds.acquisition_date}). Verify pre/post role assignment."
            )

        base_raw = read_band(ctx.path_of("baseline"), max_pixels=max_pixels())
        event_raw = read_band(ctx.path_of("event"), max_pixels=max_pixels())

        event_aligned, was_resampled = align_to(base_raw, event_raw, Resampling.bilinear)
        if was_resampled:
            notes.append("Event raster resampled to match baseline georeferencing.")

        p_b = to_power(base_raw.array, base_ds.value_scale or "power")
        p_e = to_power(event_aligned.array, event_ds.value_scale or "power")
        db_b = power_to_db(p_b)
        db_e = power_to_db(p_e)

        t_seg_start = time.perf_counter()
        f_win = ctx.params["filter_window"]
        db_b_filt = box_mean(db_b, f_win)
        db_e_filt = box_mean(db_e, f_win)

        valid_mask = np.isfinite(db_b_filt) & np.isfinite(db_e_filt)
        if not np.any(valid_mask):
            raise PipelineInputError("No overlapping valid pixels between pre-fire and post-fire acquisitions.")

        delta_hv = db_b_filt - db_e_filt
        burn_thr = ctx.params["burn_drop_db"]
        raw_scar = (delta_hv >= burn_thr) & valid_mask

        min_cluster = ctx.params["min_cluster_pixels"]
        confirmed_scar = remove_small_clusters(raw_scar, min_cluster)
        adaptive_runtime_ms = round((time.perf_counter() - t_seg_start) * 1000.0, 2)

        # Thermal hotspot corroboration
        thermal_total = 0
        thermal_inside = 0
        if ctx.has("fire_detections"):
            gj_path = ctx.path_of("fire_detections")
            gj = json.loads(gj_path.read_text())
            points = [f for f in gj.get("features", []) if (f.get("geometry") or {}).get("type") == "Point"]
            thermal_total = len(points)
            if points:
                lons = np.array([p["geometry"]["coordinates"][0] for p in points])
                lats = np.array([p["geometry"]["coordinates"][1] for p in points])
                rows, cols = lonlat_to_pixel(base_raw, lons, lats)

                in_bounds = (rows >= 0) & (rows < base_raw.height) & (cols >= 0) & (cols < base_raw.width)
                valid_r = rows[in_bounds]
                valid_c = cols[in_bounds]
                hits = confirmed_scar[valid_r, valid_c]
                thermal_inside = int(np.sum(hits))
                notes.append(f"Intersected {thermal_total} FIRMS thermal points; {thermal_inside} coincided with radar disturbance.")
        else:
            warnings.append("No active-fire thermal dataset (e.g. NASA FIRMS) supplied; disturbance is uncorroborated by thermal sensors.")

        classified = np.zeros(base_raw.array.shape, dtype="uint8")
        classified[confirmed_scar] = 1

        pixel_areas = pixel_area_m2(base_raw.transform, base_raw.crs, base_raw.height)
        scar_m2 = mask_area_m2(confirmed_scar, pixel_areas)
        scar_ha = scar_m2 / 10_000.0

        out_tif = "burn_scar_classified.tif"
        write_geotiff(ctx.out(out_tif), classified, base_raw, dtype="uint8", nodata=0)
        ctx.add_layer("burn_geotiff", "Burn Scar GeoTIFF", "raster", out_tif, "1 = SAR-inferred structural canopy disturbance")

        vmin, vmax = common_stretch(db_b[valid_mask], db_e[valid_mask])
        base_png = "prefire_preview.png"
        event_png = "postfire_preview.png"
        write_grayscale_png(ctx.out(base_png), db_b, vmin, vmax)
        write_grayscale_png(ctx.out(event_png), db_e, vmin, vmax)
        ctx.add_layer("baseline_preview", f"Pre-Fire Baseline SAR ({pol_label})", "preview", base_png)
        ctx.add_layer("event_preview", f"Post-Fire SAR ({pol_label}, Smoke-Penetrating)", "preview", event_png)

        delta_png = "burn_change_map.png"
        write_ramp_png(ctx.out(delta_png), -delta_hv, -6.0, 6.0, DIVERGING)
        ctx.add_layer("change_preview", f"Backscatter Change Map (Δ{pol_label})", "preview", delta_png, "Red/Blue = Cross-pol volume scattering change (dB)")

        class_png = "burn_overlay.png"
        palette = {
            0: (0, 0, 0, 0),
            1: (220, 38, 38, 220),
        }
        write_class_png(ctx.out(class_png), classified, palette)
        ctx.add_layer("burn_overlay", "Burn Disturbance Overlay", "preview", class_png, "Red = radar-detected structural canopy disturbance")

        # Validation & Exposure
        static_baseline = ((db_b - db_e) >= 3.0) & valid_mask
        validation_info = evaluate_binary_classification(
            ctx=ctx,
            ref_role="reference_disturbance",
            predicted_mask=confirmed_scar,
            base_raw=base_raw,
            valid_mask=valid_mask,
            pixel_areas_m2=pixel_areas,
            area_unit="ha",
            feature_arrays={
                "static_signal": db_b - db_e,
                "static_cutoff": 3.0,
                "static_baseline_mask": static_baseline,
                "primary_signal": delta_hv,
                "secondary_signal": -db_e_filt,
                "adaptive_runtime_ms": adaptive_runtime_ms,
            },
            positive_class_label="SAR-Inferred Burn Disturbance",
        )

        exposure_info = evaluate_spatial_exposure(
            ctx=ctx,
            role="exposure_assets",
            change_mask=confirmed_scar,
            base_raw=base_raw,
            pixel_areas_m2=pixel_areas,
            area_unit="ha",
        )

        metrics = [
            {"label": "Burn Scar Extent", "value": fmt(scar_ha, 1), "unit": "ha", "description": "Area exhibiting structural canopy disturbance."},
            {"label": "Corroborated Thermal Points", "value": f"{thermal_inside} / {thermal_total}", "unit": "pts", "description": "Active FIRMS thermal detections intersecting radar disturbance."},
            {"label": "Burn Drop Threshold", "value": f"{burn_thr:.1f}", "unit": "dB", "description": f"Cross-pol ({pol_label}) volume scattering cutoff."},
        ]

        explanation = {
            "level1_visual": (
                f"The viewer shows pre-fire and post-fire cross-polarized ({pol_label}) radar backscatter. "
                "Because microwave pulses penetrate thick wildfire smoke, surface structural changes can be imaged during the crisis. "
                "The red overlay outlines areas where the canopy lost structural volume scattering."
            ),
            "level2_method": (
                f"Cross-polarized backscatter difference (Δ{pol_label} >= {burn_thr:.1f} dB) was computed after {f_win}x{f_win} "
                f"speckle filtering. Spatial sieving removed isolated noise clusters smaller than {min_cluster} pixels. "
                f"Where available, NASA FIRMS/MODIS active fire hotspots (corroborating thermal evidence) and mapped fire perimeters were intersected."
            ),
            "level3_evidence": (
                f"Detected {scar_ha:.1f} hectares of SAR-inferred canopy disturbance in {pol_label}. "
                + (
                    f"{thermal_inside} of {thermal_total} independent NASA FIRMS/MODIS active-fire thermal detections fell within the radar disturbance boundary (corroborating active combustion)."
                    if thermal_total > 0
                    else "No independent thermal hotspot file was provided for this run."
                )
            ),
            "level4_uncertainty": (
                "SAR measures physical loss of vegetation volume (leaves/branches), which is distinct from optical char/ash (dNBR) "
                "and active thermal emission (FIRMS/MODIS, which are corroborating hotspot observations rather than final burn-perimeter ground truth). "
                "When validated against coarse-resolution burned-area products (e.g., ~500m NASA MODIS MCD64A1 resampled onto a ~30m SAR grid), "
                "coarse reference blocks encompass both severe crown burns and low-intensity surface burns/unburned islands, elevating apparent precision "
                "while depressing recall."
            ),
        }

        caveats = [
            "Active-fire thermal detections (MODIS/VIIRS FIRMS) are corroborating thermal observations, NOT ground truth for the final burn perimeter.",
            "Coarse-to-fine scale difference: NASA MODIS MCD64A1 (~500m native Sinusoidal grid) maps ~21.5 ha blocks, encompassing unburned canopy islands and low-intensity surface fires that do not cause a >=2.0 dB C-band VH volume drop at ~30m resolution.",
            "SAR change alone does not prove wildfire causation without thermal or optical corroboration.",
            f"Low-severity understory burns that leave upper tree crowns intact may not produce a strong {pol_label} drop.",
        ]

        inspector = build_inspector_grid(
            base_raw,
            {
                "prefire_db": db_b_filt,
                "postfire_db": db_e_filt,
                "delta_db": delta_hv,
                "classification": classified.astype("float32"),
            },
        )

        return {
            "metrics": metrics,
            "explanation": explanation,
            "caveats": caveats,
            "warnings": warnings,
            "processing_notes": notes,
            "validation": validation_info,
            "exposure": exposure_info,
            "domain_data": {
                "scar_ha": scar_ha,
                "thermal_inside": thermal_inside,
                "thermal_total": thermal_total,
                "polarization": pol_label,
                "legend": [
                    {"color": "#dc2626", "label": "SAR-Inferred Burn Disturbance", "unit": f"Δ{pol_label} ≥ {burn_thr:.1f} dB"},
                    {"color": "#f59e0b", "label": "Corroborated Thermal Detections", "unit": f"{thermal_inside}/{thermal_total} pts"},
                ],
                "inspector": inspector,
            },
        }


from app.domains.domain3.processor import CryospherePipeline


class GlaciersPipeline(CryospherePipeline):
    domain = "domain5"
    analysis_name = "Glaciers & Snow/Ice Dynamics Analysis"
    summary = (
        "Investigates glacier movement, flow velocity fields, terminus retreat, and ice-related surface conditions "
        "from repeat-pass SAR and validated ice velocity products (e.g. NASA ITS_LIVE)."
    )
