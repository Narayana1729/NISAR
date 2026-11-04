"""Domain 1: Floods & Water Dynamics Pipeline Implementation

Implements:
- Input validation: Requires baseline and event SAR backscatter rasters.
- Optional reference water mask (JRC Global Surface Water or historical baseline).
- Optional DEM for slope masking.
- Optional independent flood reference map for Precision/Recall/F1/IoU validation & Error Explorer.
- Optional georeferenced exposure assets (roads, settlements, agriculture) for spatial exposure analysis.
- Bounded Otsu histogram thresholding + relative backscatter drop (Delta dB).
- Multi-looking / boxcar spatial filtering and morphological sieve filtering.
- Accurate georeferenced area calculation (planar or ellipsoidal).
- Export of GeoTIFF deliverables and RGBA preview layers for BeforeAfterViewer.
- Comprehensive 4-level scientific explainability and uncertainty caveats.
"""
from __future__ import annotations

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
    mask_area_m2,
    otsu_threshold,
    pixel_area_m2,
    power_to_db,
    read_band,
    remove_small_clusters,
    slope_degrees,
    to_power,
    write_class_png,
    write_geotiff,
    write_grayscale_png,
    write_ramp_png,
)
from app.utils.validation import evaluate_binary_classification


class FloodsPipeline(DomainPipeline):
    domain = "domain1"
    analysis_name = "Floods & Wetlands Inundation Analysis"
    summary = (
        "Detects changes in inundation, flooded areas, and wetland extent by identifying characteristic drops in SAR "
        "microwave specular backscatter relative to a baseline acquisition, with optional terrain slope filtering, "
        "permanent-water masking, reference validation, and asset exposure analysis."
    )
    implementation_status = "implemented"
    deferred_features = [
        "Sub-canopy polarimetric L-band double-bounce decomposition",
        "Hydrodynamic floodwater depth estimation",
    ]

    inputs = [
        InputSpec(
            role="baseline",
            label="Pre-Event Baseline SAR",
            product_types=["sar_backscatter"],
            required=True,
            description="Calibrated pre-flood SAR backscatter raster (e.g. dry season or pre-event pass).",
        ),
        InputSpec(
            role="event",
            label="Post-Event / Crisis SAR",
            product_types=["sar_backscatter"],
            required=True,
            description="Calibrated crisis SAR backscatter raster acquired during or immediately following flood.",
        ),
        InputSpec(
            role="reference_water",
            label="Permanent Reference Water Mask (Optional)",
            product_types=["reference_water"],
            required=False,
            description="Binary mask of permanent lakes/rivers (1=water). If omitted, baseline water is used.",
        ),
        InputSpec(
            role="dem",
            label="Digital Elevation Model (Optional)",
            product_types=["dem"],
            required=False,
            description="DEM used to compute terrain slopes and mask out hillside radar shadows.",
        ),
        InputSpec(
            role="reference_flood",
            label="Independent Reference Flood Map (Optional Validation)",
            product_types=["reference_flood"],
            required=False,
            description="Independent flood extent raster (1=flooded) for computing IoU, Precision, Recall, F1, and Error Explorer.",
        ),
        InputSpec(
            role="exposure_assets",
            label="Exposure Assets Layer (Optional GeoJSON)",
            product_types=["exposure_assets"],
            required=False,
            description="Georeferenced roads, settlements, or agricultural zones (GeoJSON) to evaluate flood exposure.",
        ),
    ]

    params = [
        ParamSpec(
            name="threshold_mode",
            label="Threshold Mode",
            type="select",
            default="bounded_otsu",
            options=["bounded_otsu", "fixed_threshold"],
            description="Method for segmenting water backscatter on the event raster.",
        ),
        ParamSpec(
            name="fixed_threshold_db",
            label="Fixed Threshold (dB)",
            type="number",
            default=-16.0,
            min=-30.0,
            max=-5.0,
            description="Used if threshold_mode is 'fixed_threshold'.",
        ),
        ParamSpec(
            name="min_drop_db",
            label="Minimum Drop vs Baseline (dB)",
            type="number",
            default=3.0,
            min=0.5,
            max=15.0,
            description="Required backscatter drop relative to baseline to flag new flooding (avoids permanent smooth ground).",
        ),
        ParamSpec(
            name="filter_window",
            label="Speckle Filter Window",
            type="integer",
            default=5,
            min=3,
            max=15,
            description="Odd boxcar window size for spatial smoothing before thresholding.",
        ),
        ParamSpec(
            name="min_cluster_pixels",
            label="Minimum Cluster Size (pixels)",
            type="integer",
            default=5,
            min=1,
            max=100,
            description="Filters out isolated speckle noise smaller than this pixel count.",
        ),
        ParamSpec(
            name="max_slope_deg",
            label="Max Terrain Slope (degrees)",
            type="number",
            default=5.0,
            min=1.0,
            max=25.0,
            description="Masks water detections on slopes steeper than this value (if DEM is provided).",
        ),
    ]

    def run(self, ctx: PipelineContext) -> dict:
        import time

        notes: list[str] = []
        warnings: list[str] = []
        t_seg_start = time.perf_counter()

        # 1. Read baseline and event rasters
        base_ds = ctx.datasets["baseline"]
        event_ds = ctx.datasets["event"]
        if (
            base_ds.acquisition_date
            and event_ds.acquisition_date
            and base_ds.acquisition_date > event_ds.acquisition_date
        ):
            warnings.append(
                f"Chronological order warning: Baseline acquisition ({base_ds.acquisition_date}) is later than "
                f"Event acquisition ({event_ds.acquisition_date}). Verify pre/post role assignment."
            )
        base_raw = read_band(ctx.path_of("baseline"), max_pixels=max_pixels())
        event_raw = read_band(ctx.path_of("event"), max_pixels=max_pixels())

        # Alignment: Resample event to baseline if grid differs
        event_aligned, was_resampled = align_to(base_raw, event_raw, Resampling.bilinear)
        if was_resampled:
            notes.append("Event raster was resampled to match baseline georeferencing and resolution.")

        # Ensure valid backscatter scale
        scale_base = base_ds.value_scale or "power"
        scale_event = event_ds.value_scale or "power"
        p_base = to_power(base_raw.array, scale_base)
        p_event = to_power(event_aligned.array, scale_event)

        # Convert to dB
        db_base = power_to_db(p_base)
        db_event = power_to_db(p_event)

        # 2. Filter speckle (start timing in-memory segmentation pipeline)
        t_seg_start = time.perf_counter()
        f_win = ctx.params["filter_window"]
        db_base_filt = box_mean(db_base, f_win)
        db_event_filt = box_mean(db_event, f_win)

        # 3. Water segmentation
        valid_mask = np.isfinite(db_base_filt) & np.isfinite(db_event_filt)
        if not np.any(valid_mask):
            raise PipelineInputError("No overlapping valid pixels between baseline and event acquisitions.")

        thr_mode = ctx.params["threshold_mode"]
        if thr_mode == "bounded_otsu":
            raw_thr, _ = otsu_threshold(db_event_filt[valid_mask])
            thr_val = float(np.clip(raw_thr, -22.0, -14.0))
            if thr_val != raw_thr:
                warnings.append(
                    f"Otsu threshold ({raw_thr:.1f} dB) was outside safe water range; clamped to {thr_val:.1f} dB."
                )
        else:
            thr_val = float(ctx.params["fixed_threshold_db"])

        water_event_raw = (db_event_filt < thr_val) & valid_mask
        water_base_raw = (db_base_filt < thr_val) & valid_mask

        # Detect relative drop
        min_drop = ctx.params["min_drop_db"]
        delta_db = db_base_filt - db_event_filt  # positive when event became darker
        significant_drop = delta_db >= min_drop

        # 4. Optional DEM Slope masking
        slope_masked_count = 0
        steep_mask = np.zeros_like(valid_mask)
        if ctx.has("dem"):
            dem_raw = read_band(ctx.path_of("dem"), max_pixels=max_pixels())
            dem_aligned, _ = align_to(base_raw, dem_raw, Resampling.bilinear)
            slopes = slope_degrees(dem_aligned)
            steep_mask = (slopes > ctx.params["max_slope_deg"]) & np.isfinite(slopes)
            slope_masked_count = int(np.sum(water_event_raw & steep_mask))
            water_event_raw = water_event_raw & ~steep_mask
            notes.append(f"Slope mask applied (slope <= {ctx.params['max_slope_deg']} deg); excluded {slope_masked_count} pixels.")

        # 5. Clean spatial noise (sieve)
        min_cluster = ctx.params["min_cluster_pixels"]
        water_event = remove_small_clusters(water_event_raw, min_cluster)
        water_base = remove_small_clusters(water_base_raw, min_cluster)

        # Inundation categorization
        # 0 = dry/unclassified, 1 = permanent/baseline water, 2 = anomalous flood water
        classified = np.zeros(base_raw.array.shape, dtype="uint8")

        if ctx.has("reference_water"):
            ref_raw = read_band(ctx.path_of("reference_water"), max_pixels=max_pixels())
            ref_aligned, _ = align_to(base_raw, ref_raw, Resampling.nearest)
            perm_water = (ref_aligned.array > 0.5) & valid_mask
            anomalous_flood = water_event & ~perm_water & significant_drop
            classified[perm_water] = 1
            classified[anomalous_flood] = 2
            notes.append(f"Subtracted permanent reference water mask ('{ctx.datasets['reference_water'].name}').")
        else:
            perm_water = water_base
            anomalous_flood = water_event & ~perm_water & significant_drop
            classified[perm_water] = 1
            classified[anomalous_flood] = 2
            warnings.append("No independent reference water layer supplied; baseline SAR water was used as permanent reference.")

        adaptive_runtime_ms = round((time.perf_counter() - t_seg_start) * 1000.0, 2)

        # 6. Compute Areas
        pixel_areas = pixel_area_m2(base_raw.transform, base_raw.crs, base_raw.height)
        flood_area_m2 = mask_area_m2(anomalous_flood, pixel_areas)
        perm_area_m2 = mask_area_m2(classified == 1, pixel_areas)
        total_water_m2 = mask_area_m2(classified > 0, pixel_areas)

        flood_km2 = flood_area_m2 / 1_000_000.0
        perm_km2 = perm_area_m2 / 1_000_000.0
        total_km2 = total_water_m2 / 1_000_000.0

        # 7. Write Deliverable Files
        out_tif_name = "flood_classification.tif"
        write_geotiff(ctx.out(out_tif_name), classified, base_raw, dtype="uint8", nodata=0)
        ctx.add_layer("classification_geotiff", "Inundation GeoTIFF", "raster", out_tif_name, "0=dry, 1=permanent water, 2=potential flood")

        vmin, vmax = common_stretch(db_base[valid_mask], db_event[valid_mask])
        base_png = "baseline_preview.png"
        event_png = "event_preview.png"
        write_grayscale_png(ctx.out(base_png), db_base, vmin, vmax)
        write_grayscale_png(ctx.out(event_png), db_event, vmin, vmax)
        ctx.add_layer("baseline_preview", "Pre-Event Baseline SAR", "preview", base_png)
        ctx.add_layer("event_preview", "Post-Event SAR", "preview", event_png)

        # Backscatter Change (Delta dB) Preview
        delta_png = "backscatter_change.png"
        write_ramp_png(ctx.out(delta_png), -(delta_db), -8.0, 8.0, DIVERGING)
        ctx.add_layer("change_preview", "Backscatter Change Map (ΔdB)", "preview", delta_png, "Blue = Backscatter drop (specular water), Red = Backscatter increase")

        # Classification Color Overlay
        class_png = "flood_overlay.png"
        palette = {
            0: (0, 0, 0, 0),
            1: (30, 64, 175, 200),    # navy: permanent water
            2: (6, 182, 212, 235),    # cyan: potential flood inundation
        }
        write_class_png(ctx.out(class_png), classified, palette)
        ctx.add_layer("flood_overlay", "Classified Flood Overlay", "preview", class_png, "Permanent water (navy) & detected potential inundation (cyan)")

        # 8. Optional Reference Validation & Error Explorer
        domain_constraint = ~perm_water & ~steep_mask
        static_baseline_mask = (db_event <= -16.0) & domain_constraint & valid_mask
        validation_info = evaluate_binary_classification(
            ctx=ctx,
            ref_role="reference_flood",
            predicted_mask=anomalous_flood,
            base_raw=base_raw,
            valid_mask=valid_mask,
            pixel_areas_m2=pixel_areas,
            area_unit="km²",
            low_quality_mask=steep_mask,
            feature_arrays={
                "domain_constraint_mask": domain_constraint,
                "static_signal": -db_event,
                "static_cutoff": 16.0,
                "static_baseline_mask": static_baseline_mask,
                "primary_signal": delta_db,
                "secondary_signal": -db_event_filt,
                "adaptive_runtime_ms": adaptive_runtime_ms,
            },
            positive_class_label="New Flood Inundation (excluding permanent water)",
        )

        # 9. Optional Spatial Exposure Analysis
        exposure_info = evaluate_spatial_exposure(
            ctx=ctx,
            role="exposure_assets",
            change_mask=anomalous_flood,
            base_raw=base_raw,
            pixel_areas_m2=pixel_areas,
            area_unit="km²",
        )

        # 10. Assemble Metrics & Explanations
        metrics = [
            {"label": "New Flood Inundation", "value": fmt(flood_km2, 2), "unit": "km²", "description": "Detected potential temporary surface water (excluding permanent water)."},
            {"label": "Permanent Water Extent", "value": fmt(perm_km2, 2), "unit": "km²", "description": "Baseline/reference open water."},
            {"label": "Total Surface Water", "value": fmt(total_km2, 2), "unit": "km²", "description": "Combined water surface extent."},
            {"label": "Water Threshold", "value": f"{thr_val:.1f}", "unit": "dB", "description": "Backscatter cutoff for specular surface."},
        ]
        if validation_info.status == "compared_to_reference" and validation_info.metrics:
            iou_m = next((m for m in validation_info.metrics if "IoU" in m.label), None)
            if iou_m:
                metrics.append({"label": "Reference Overlap (IoU)", "value": iou_m.value, "unit": "%", "description": "Agreement against independent reference flood map."})

        explanation = {
            "level1_visual": (
                "The viewer shows pre-event baseline radar reflectance alongside the crisis observation. Calm standing "
                "water acts as a specular reflector, scattering microwave energy away from the radar sensor and appearing dark. "
                "The cyan overlay highlights detected potential inundation where radar reflectance dropped significantly below baseline."
            ),
            "level2_method": (
                f"Calibrated SAR backscatter was converted to decibels and smoothed with a {f_win}x{f_win} boxcar filter. "
                f"Open water was segmented using {thr_mode} at {thr_val:.1f} dB with a required relative drop of >= {min_drop:.1f} dB "
                f"versus baseline. Isolated clusters < {min_cluster} pixels were sieved."
            ),
            "level3_evidence": (
                f"Detected potential new inundation covers {flood_km2:.2f} km² alongside {perm_km2:.2f} km² of permanent water. "
                f"Pixel values in newly inundated zones exhibited a backscatter drop >= {min_drop:.1f} dB below baseline."
            ),
            "level4_uncertainty": (
                "Detected specular backscatter drop indicates potential surface water inundation, not confirmed hydrological flooding "
                "until cross-checked with terrain and ground observations. High surface winds (>15 knots) can roughen water surfaces "
                "and cause under-detection, while dense urban/vegetated canopies can obscure underlying standing water."
            ),
        }

        caveats = [
            "Detected potential inundation is inferred from radar specular backscatter drop and should be distinguished from confirmed ground-verified flooding.",
            "Radar backscatter detects surface water presence, not water column depth.",
            "Smooth bare soil or paved surfaces can produce low backscatter similar to standing water.",
            "High surface winds or emergent vegetation double-bounce may cause flooded areas to be missed.",
        ]

        inspector = build_inspector_grid(
            base_raw,
            {
                "baseline_db": db_base_filt,
                "event_db": db_event_filt,
                "delta_db": delta_db,
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
                "threshold_db": thr_val,
                "min_drop_db": min_drop,
                "flood_km2": flood_km2,
                "permanent_water_km2": perm_km2,
                "slope_masked_pixels": slope_masked_count,
                "legend": [
                    {"color": "#06b6d4", "label": "Detected Potential Inundation (Class 2)", "unit": f"< {thr_val:.1f} dB & ΔdB ≥ {min_drop:.1f} dB"},
                    {"color": "#1e40af", "label": "Permanent / Baseline Water (Class 1)", "unit": "Reference Water"},
                ],
                "inspector": inspector,
            },
        }
