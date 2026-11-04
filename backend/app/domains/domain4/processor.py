"""Domain 4: Land Movement & Urban Change Pipeline Implementation

Implements:
- Input validation: Precomputed InSAR Line-of-Sight (LOS) displacement or velocity GeoTIFF (e.g. ASF HyP3).
- Optional InSAR interferometric coherence mask (0..1).
- Optional independent reference displacement raster (GNSS/leveling/reference InSAR) for RMSE/MAE/Bias validation.
- Optional exposure assets (urban buildings, highways, canals, levees) for spatial exposure intersection.
- Coherence quality thresholding to mask noisy decorrelated pixels.
- Subsidence bowl hotspot clustering and area quantification.
- Diverging color ramp rendering (red=subsidence, white=stable, blue=uplift).
- Multi-tier scientific explainability detailing satellite Line-of-Sight geometry.
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
    SEQUENTIAL,
    align_to,
    box_mean,
    build_inspector_grid,
    common_stretch,
    fmt,
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
from app.utils.validation import evaluate_binary_classification, evaluate_continuous_field


class LandMovementPipeline(DomainPipeline):
    domain = "domain4"
    analysis_name = "InSAR Ground Deformation & Subsidence Hotspot Analysis"
    summary = (
        "Maps millimeter-scale ground displacement and subsidence hotspots from pre-computed unwrapped "
        "interferometric SAR (InSAR) products, with coherence quality filtering, reference validation, and asset exposure."
    )
    implementation_status = "implemented"
    deferred_features = [
        "Raw Single Look Complex (SLC) interferogram generation and phase unwrapping from scratch",
        "Dual-track 3D vector decomposition (requires ascending + descending tracks)",
    ]

    inputs = [
        InputSpec(
            role="displacement",
            label="InSAR Displacement / Velocity Raster",
            product_types=["insar_displacement"],
            required=True,
            description="Calibrated Line-of-Sight (LOS) deformation rate (e.g. mm/year or cumulative displacement in mm).",
        ),
        InputSpec(
            role="coherence",
            label="InSAR Coherence Raster (Optional)",
            product_types=["insar_coherence"],
            required=False,
            description="Interferometric coherence (0.0 to 1.0). Used to mask decorrelated, unreliable phase measurements.",
        ),
        InputSpec(
            role="reference_displacement",
            label="Reference Displacement / Cross-Pair Interferogram (Optional Validation)",
            product_types=["reference_displacement", "insar_displacement"],
            required=False,
            description="Reference deformation field, cross-pair interferogram, or interpolated GNSS reference (mm or mm/yr) for RMSE/MAE/Bias comparison.",
        ),
        InputSpec(
            role="exposure_assets",
            label="Urban Infrastructure & Assets (Optional GeoJSON)",
            product_types=["exposure_assets"],
            required=False,
            description="Georeferenced buildings, highways, canals, or critical infrastructure (GeoJSON) for exposure intersection.",
        ),
    ]

    params = [
        ParamSpec(
            name="min_coherence",
            label="Minimum Coherence Threshold",
            type="number",
            default=0.35,
            min=0.0,
            max=0.95,
            description="Pixels with interferometric coherence below this threshold are masked as unreliable.",
        ),
        ParamSpec(
            name="subsidence_threshold_mm",
            label="Subsidence Hotspot Threshold (mm or mm/yr)",
            type="number",
            default=-15.0,
            min=-500.0,
            max=-1.0,
            description="Displacement threshold defining significant ground subsidence (negative is movement away from sensor).",
        ),
        ParamSpec(
            name="color_stretch_mm",
            label="Color Stretch Range (+/- mm)",
            type="number",
            default=40.0,
            min=5.0,
            max=500.0,
            description="Symmetric color ramp limits (-stretch to +stretch).",
        ),
    ]

    def run(self, ctx: PipelineContext) -> dict:
        notes: list[str] = []
        warnings: list[str] = []

        disp_ds = ctx.datasets["displacement"]
        disp_unit = (disp_ds.units or "mm/yr").strip()
        disp_source = disp_ds.source or "Pre-computed Unwrapped InSAR Product"
        notes.append(f"InSAR product source: {disp_source} (units: {disp_unit}).")

        disp_raw = read_band(ctx.path_of("displacement"), max_pixels=max_pixels())
        disp_arr = disp_raw.array.copy()

        valid_mask = np.isfinite(disp_arr) & (disp_arr > -9000.0)
        if not np.any(valid_mask):
            raise PipelineInputError("Displacement raster contains no valid finite data.")
        disp_arr[~valid_mask] = np.nan

        coh_arr_for_inspector = np.full_like(disp_arr, np.nan)
        low_coh_mask = np.zeros_like(valid_mask)
        if ctx.has("coherence"):
            coh_raw = read_band(ctx.path_of("coherence"), max_pixels=max_pixels())
            coh_aligned, _ = align_to(disp_raw, coh_raw, Resampling.bilinear)
            coh_arr_for_inspector = coh_aligned.array
            min_coh = ctx.params["min_coherence"]
            low_coh_mask = (coh_aligned.array < min_coh) | ~np.isfinite(coh_aligned.array)
            disp_arr[low_coh_mask] = np.nan
            valid_mask = np.isfinite(disp_arr)
            masked_count = int(np.sum(low_coh_mask))
            notes.append(f"Filtered {masked_count} low-coherence pixels (coherence < {min_coh:.2f}).")

            coh_png = "coherence_preview.png"
            write_ramp_png(ctx.out(coh_png), coh_aligned.array, 0.0, 1.0, SEQUENTIAL)
            ctx.add_layer("baseline_preview", "Interferometric Coherence (0–1)", "preview", coh_png, "Phase quality (yellow = high coherence, dark = decorrelated)")
        else:
            warnings.append("No coherence layer provided; all non-nan displacement pixels were retained.")

        sub_thr = ctx.params["subsidence_threshold_mm"]
        is_subsiding = (disp_arr <= sub_thr) & valid_mask
        cleaned_hotspots = remove_small_clusters(is_subsiding, min_pixels=4)

        valid_vals = disp_arr[valid_mask]
        peak_subsidence = float(np.nanmin(valid_vals)) if len(valid_vals) > 0 else 0.0
        peak_uplift = float(np.nanmax(valid_vals)) if len(valid_vals) > 0 else 0.0
        mean_disp = float(np.nanmean(valid_vals)) if len(valid_vals) > 0 else 0.0

        pixel_areas = pixel_area_m2(disp_raw.transform, disp_raw.crs, disp_raw.height)
        bowl_area_m2 = mask_area_m2(cleaned_hotspots, pixel_areas)
        bowl_km2 = bowl_area_m2 / 1_000_000.0

        out_tif = "insar_filtered_displacement.tif"
        write_geotiff(ctx.out(out_tif), disp_arr, disp_raw, dtype="float32", nodata=-9999.0)
        ctx.add_layer("displacement_geotiff", "InSAR Displacement GeoTIFF", "raster", out_tif, "Line-of-Sight ground deformation (mm)")

        stretch = ctx.params["color_stretch_mm"]
        disp_png = "insar_velocity_heatmap.png"
        write_ramp_png(ctx.out(disp_png), disp_arr, -stretch, stretch, DIVERGING)
        ctx.add_layer("displacement_preview", "Deformation Heatmap", "preview", disp_png, f"Red = subsidence (<={sub_thr:.0f} mm), Blue = uplift")

        hotspot_class = np.zeros(disp_raw.array.shape, dtype="uint8")
        hotspot_class[cleaned_hotspots] = 1
        hotspot_png = "subsidence_hotspots.png"
        write_class_png(
            ctx.out(hotspot_png),
            hotspot_class,
            {
                0: (0, 0, 0, 0),
                1: (239, 68, 68, 225),
            },
        )
        ctx.add_layer("change_overlay", "Subsidence Hotspot Overlay", "preview", hotspot_png, f"Red = Subsidence Hotspot (≤ {sub_thr:.0f} {disp_unit})")

        validation_info = evaluate_continuous_field(
            ctx=ctx,
            ref_role="reference_displacement",
            measured_arr=disp_arr,
            base_raw=disp_raw,
            valid_mask=valid_mask,
            unit=disp_unit,
        )

        exposure_info = evaluate_spatial_exposure(
            ctx=ctx,
            role="exposure_assets",
            change_mask=cleaned_hotspots,
            base_raw=disp_raw,
            pixel_areas_m2=pixel_areas,
            area_unit="km²",
        )

        metrics = [
            {"label": "Peak Subsidence", "value": fmt(peak_subsidence, 1), "unit": disp_unit, "description": "Maximum movement away from sensor along Line of Sight."},
            {"label": "Subsidence Hotspot Area", "value": fmt(bowl_km2, 2), "unit": "km²", "description": f"Area with LOS deformation <= {sub_thr:.0f} {disp_unit}."},
            {"label": "Mean Deformation", "value": fmt(mean_disp, 1), "unit": disp_unit, "description": "Average Line-of-Sight deformation across AOI."},
            {"label": "Peak Uplift", "value": fmt(peak_uplift, 1), "unit": disp_unit, "description": "Maximum motion toward sensor detected."},
        ]

        explanation = {
            "level1_visual": (
                "The visualization displays ground surface movement along the satellite radar Line of Sight (LOS). "
                "Warm red tones indicate ground movement away from the satellite (subsidence or normal-fault hanging-wall drop), white represents stable terrain, "
                "and blue denotes movement toward the satellite."
            ),
            "level2_method": (
                f"Pre-computed unwrapped InSAR displacement products ({disp_source}, units: {disp_unit}) "
                f"were filtered for phase reliability (coherence >= {ctx.params['min_coherence']:.2f}) and segmented for hotspots <= {sub_thr:.1f} {disp_unit}."
            ),
            "level3_evidence": (
                f"Peak LOS subsidence reached {peak_subsidence:.1f} {disp_unit} across a contiguous hotspot area of {bowl_km2:.2f} km²."
            ),
            "level4_uncertainty": (
                "Single-track InSAR measures 1D projection along the radar Line of Sight (LOS); it does NOT automatically isolate vertical sinking "
                "from horizontal tectonic motion without combining ascending and descending orbits. Conventional interferometry cannot be performed on "
                "amplitude-only GRD data and is vulnerable to tropospheric water vapor delay."
            ),
        }

        caveats = [
            f"Product source: {disp_source} (pre-computed unwrapped InSAR product in {disp_unit}, not raw SLC interferometry computed on the fly).",
            "Displacement is measured along the 1D satellite Line of Sight (LOS), not pure vertical movement.",
            "When compared against a cross-pair interferogram from the same track/frame that shares an acquisition epoch (e.g. LiCSAR 18-day S1B–S1A vs. 12-day S1A–S1A sharing 2021-03-09), the comparison is a partially independent cross-interferogram consistency check rather than an independent non-InSAR ground-truth validation.",
            "Conventional InSAR requires Single Look Complex (SLC) phase products (e.g. COMET-LiCSAR, ASF HyP3) and cannot be computed from GRD amplitude rasters.",
            "Tropospheric water vapor and ionospheric delays can introduce centimeter-scale long-wavelength phase ramps.",
        ]

        inspector = build_inspector_grid(
            disp_raw,
            {
                "los_displacement": disp_arr,
                "coherence": coh_arr_for_inspector,
                "hotspot_flag": cleaned_hotspots.astype("float32"),
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
                "peak_subsidence_mm": peak_subsidence,
                "peak_uplift_mm": peak_uplift,
                "subsidence_bowl_km2": bowl_km2,
                "displacement_unit": disp_unit,
                "legend": [
                    {"color": "#dc2626", "label": f"Subsidence Hotspot (≤ {sub_thr:.0f} {disp_unit})", "unit": f"{disp_unit} LOS"},
                    {"color": "#f8fafc", "label": f"Stable Ground (~0 {disp_unit})", "unit": f"{disp_unit} LOS"},
                    {"color": "#2563eb", "label": f"Surface Uplift / Motion Toward Sensor (+{stretch:.0f} {disp_unit})", "unit": f"{disp_unit} LOS"},
                ],
                "inspector": inspector,
            },
        }


class AgriculturePipeline(DomainPipeline):
    domain = "domain4"
    analysis_name = "Agriculture & Soil Conditions Radar Analysis"
    summary = (
        "Analyses agricultural surface changes and suitable radar-derived indicators "
        "(crop canopy growth/harvesting, soil roughness, and moisture change proxies) "
        "from repeat-pass SAR backscatter observations."
    )
    implementation_status = "demonstration"
    deferred_features = [
        "Multi-frequency L+C band polarimetric Radar Vegetation Index (RVI) inversion",
        "Calibrated volumetric soil moisture inversion (e.g. Dubois/IEM model)",
    ]

    inputs = [
        InputSpec(
            role="baseline",
            label="Baseline Agricultural SAR (VV/VH)",
            product_types=["sar_backscatter"],
            required=True,
            description="Pre-change or early-season SAR backscatter raster representing baseline crop/soil condition.",
        ),
        InputSpec(
            role="monitoring",
            label="Monitoring SAR (VV/VH)",
            product_types=["sar_backscatter"],
            required=True,
            description="Repeat-pass SAR backscatter raster to evaluate crop growth, harvesting, or soil moisture shifts.",
        ),
        InputSpec(
            role="crop_mask",
            label="Agricultural Boundary / Crop Mask (Optional)",
            product_types=["forest_mask", "reference_water"],
            required=False,
            description="Crop field boundary or agricultural mask to restrict analysis to cultivated areas.",
        ),
        InputSpec(
            role="reference_condition",
            label="Reference Surface / Soil Condition (Optional Validation)",
            product_types=["reference_disturbance", "reference_flood"],
            required=False,
            description="Independent reference crop status or surface condition mask for validation.",
        ),
        InputSpec(
            role="exposure_assets",
            label="Agricultural Assets & Infrastructure (Optional GeoJSON)",
            product_types=["exposure_assets"],
            required=False,
            description="Georeferenced field parcels, irrigation canals, or agricultural facilities (GeoJSON).",
        ),
    ]

    params = [
        ParamSpec(
            name="delta_threshold_db",
            label="Backscatter Change Threshold (dB)",
            type="number",
            default=-2.0,
            min=-12.0,
            max=-0.5,
            description="Relative backscatter drop (dB) threshold defining surface disturbance, harvest, or tillage.",
        ),
        ParamSpec(
            name="filter_window",
            label="Speckle Filter Window",
            type="number",
            default=3,
            min=1,
            max=15,
            description="Boxcar kernel size (pixels) for spatial speckle reduction.",
        ),
        ParamSpec(
            name="min_cluster_pixels",
            label="Min Cluster Size (pixels)",
            type="number",
            default=4,
            min=1,
            max=100,
            description="Minimum contiguous pixel cluster size to filter out isolated speckle noise.",
        ),
        ParamSpec(
            name="soil_indicator_sensitivity",
            label="Soil Condition Sensitivity Multiplier",
            type="number",
            default=1.0,
            min=0.1,
            max=5.0,
            description="Calibration multiplier for relative soil moisture and surface roughness indicator index.",
        ),
    ]

    def run(self, ctx: PipelineContext) -> dict:
        notes: list[str] = []
        warnings: list[str] = []

        base_ds = ctx.datasets["baseline"]
        event_ds = ctx.datasets.get("monitoring") or ctx.datasets.get("event")
        if not event_ds:
            raise PipelineInputError("Agriculture pipeline requires 'monitoring' (or 'event') SAR input.")

        thr_db = float(ctx.params.get("delta_threshold_db", -2.0))
        filter_w = int(ctx.params.get("filter_window", 3))
        min_cluster = int(ctx.params.get("min_cluster_pixels", 4))
        soil_mult = float(ctx.params.get("soil_indicator_sensitivity", 1.0))

        base_raw = read_band(ctx.path_of("baseline"), max_pixels=max_pixels())
        event_role = "monitoring" if ctx.has("monitoring") else "event"
        event_raw = read_band(ctx.path_of(event_role), max_pixels=max_pixels())

        event_aligned, _ = align_to(base_raw, event_raw, Resampling.bilinear)

        base_p = to_power(base_raw.array, base_ds.value_scale)
        event_p = to_power(event_aligned.array, event_ds.value_scale)

        valid_mask = np.isfinite(base_p) & (base_p > 0) & np.isfinite(event_p) & (event_p > 0)
        if not np.any(valid_mask):
            raise PipelineInputError("SAR inputs contain no overlapping valid positive backscatter pixels.")

        if filter_w > 1:
            base_p = box_mean(base_p, filter_w)
            event_p = box_mean(event_p, filter_w)
            notes.append(f"Applied {filter_w}x{filter_w} spatial speckle filtering.")

        base_db = power_to_db(base_p)
        event_db = power_to_db(event_p)

        # Delta backscatter: Event - Baseline (dB)
        delta_db = event_db - base_db
        delta_db[~valid_mask] = np.nan

        # Significant agricultural surface drop (e.g. harvest, tillage, or biomass removal)
        raw_change = (delta_db <= thr_db) & valid_mask

        # Mask non-agricultural pixels if crop_mask provided
        if ctx.has("crop_mask"):
            cmask_raw = read_band(ctx.path_of("crop_mask"), max_pixels=max_pixels())
            cmask_aligned, _ = align_to(base_raw, cmask_raw, Resampling.nearest)
            raw_change &= (cmask_aligned.array > 0)
            notes.append("Filtered surface changes by agricultural crop boundary mask.")

        if min_cluster > 1:
            cleaned_change = remove_small_clusters(raw_change, min_cluster)
        else:
            cleaned_change = raw_change

        pixel_areas = pixel_area_m2(base_raw.transform, base_raw.crs, base_raw.height)
        total_eval_ha = mask_area_m2(valid_mask, pixel_areas) / 10_000.0
        change_ha = mask_area_m2(cleaned_change, pixel_areas) / 10_000.0
        change_km2 = change_ha / 100.0

        mean_delta = float(np.nanmean(delta_db[valid_mask])) if np.any(valid_mask) else 0.0
        soil_proxy_index = float(np.nanmedian(delta_db[valid_mask]) * soil_mult) if np.any(valid_mask) else 0.0

        # Export deliverables
        out_tif = "agricultural_surface_change.tif"
        write_geotiff(ctx.out(out_tif), cleaned_change.astype("uint8"), base_raw, dtype="uint8", nodata=255)
        ctx.add_layer("change_mask", "Agricultural Surface Change Mask", "raster", out_tif)

        delta_tif = "delta_backscatter_db.tif"
        write_geotiff(ctx.out(delta_tif), delta_db, base_raw, dtype="float32", nodata=-9999.0)
        ctx.add_layer("delta_db", "Backscatter Difference (Delta dB)", "raster", delta_tif)

        overlay_png = "change_overlay.png"
        write_class_png(ctx.out(overlay_png), cleaned_change, {1: (217, 119, 6, 180)})
        ctx.add_layer("change_overlay", "Surface Change Extent Overlay", "preview", overlay_png, description=f"Surface Dynamic (Delta <= {thr_db:.1f} dB)")

        delta_png = "delta_map.png"
        write_ramp_png(ctx.out(delta_png), delta_db, -6.0, 6.0, DIVERGING)
        ctx.add_layer("delta_map", "Delta Backscatter Dynamic Map", "preview", delta_png, description="Radar Dynamic: Red=Drop (Harvest/Soil), Blue=Increase (Growth/Moisture)")

        b_min, b_max = common_stretch(base_db[valid_mask])
        base_png = "baseline_preview.png"
        write_grayscale_png(ctx.out(base_png), base_db, b_min, b_max)
        ctx.add_layer("baseline_preview", "Baseline SAR Preview", "preview", base_png)

        e_min, e_max = common_stretch(event_db[valid_mask])
        event_png = "monitoring_preview.png"
        write_grayscale_png(ctx.out(event_png), event_db, e_min, e_max)
        ctx.add_layer("monitoring_preview", "Monitoring SAR Preview", "preview", event_png)

        # Validation
        validation_info = None
        if ctx.has("reference_condition"):
            ref_raw = read_band(ctx.path_of("reference_condition"), max_pixels=max_pixels())
            ref_aligned, _ = align_to(base_raw, ref_raw, Resampling.nearest)
            validation_info = evaluate_binary_classification(
                ctx=ctx,
                ref_role="reference_condition",
                predicted_mask=cleaned_change,
                ref_arr=ref_aligned.array,
                valid_mask=valid_mask,
                pixel_areas_m2=pixel_areas,
            )

        # Exposure
        exposure_info = None
        if ctx.has("exposure_assets"):
            exposure_info = evaluate_spatial_exposure(
                ctx=ctx,
                role="exposure_assets",
                change_mask=cleaned_change,
                base_raw=base_raw,
                pixel_areas_m2=pixel_areas,
                area_unit="ha",
            )

        metrics = [
            {"label": "Agricultural Area Evaluated", "value": fmt(total_eval_ha, 1), "unit": "ha", "description": "Total valid agricultural footprint analyzed."},
            {"label": "Surface Change Area", "value": fmt(change_ha, 2), "unit": "ha", "description": f"Area exhibiting backscatter change <= {thr_db:.1f} dB."},
            {"label": "Change Area (km²)", "value": fmt(change_km2, 2), "unit": "km²", "description": "Total surface dynamic extent in square kilometers."},
            {"label": "Mean Backscatter Delta", "value": fmt(mean_delta, 2), "unit": "dB", "description": "Average backscatter shift across evaluated parcels."},
            {"label": "Radar Soil/Crop Index", "value": fmt(soil_proxy_index, 2), "unit": "index", "description": "Relative surface roughness and moisture dynamic proxy."},
        ]

        explanation = {
            "level1_visual": (
                "The orange overlay highlights agricultural zones experiencing significant microwave backscatter changes "
                f"exceeding {abs(thr_db):.1f} dB, corresponding to crop harvesting, biomass shift, or surface soil condition changes."
            ),
            "level2_method": (
                f"Multi-temporal repeat-pass SAR backscatter was calibrated to power, smoothed with a {filter_w}x{filter_w} speckle filter, "
                f"and thresholded at Delta <= {thr_db:.1f} dB. Clusters smaller than {min_cluster} pixels were pruned to suppress speckle noise."
            ),
            "level3_evidence": (
                f"Detected {change_ha:.2f} hectares ({change_km2:.2f} km²) of significant surface dynamic across {total_eval_ha:.1f} ha evaluated, "
                f"with an average backscatter delta of {mean_delta:.2f} dB."
            ),
            "level4_uncertainty": (
                "SAR backscatter over agricultural fields is influenced simultaneously by soil moisture (dielectric constant), "
                "surface roughness (tillage direction), and vegetative canopy structure (volume scattering). Single-polarization observations "
                "cannot decouple soil moisture increases from surface roughening without multi-frequency (L+C band) or dual-polarization decomposition."
            ),
        }

        caveats = [
            "SAR backscatter responds to both dielectric permittivity (soil moisture) and geometric surface roughness (furrow orientation and plowing).",
            "Dense mature crop canopies attenuate microwave signals, causing C-band saturation over fully developed crops.",
            "Precipitation events immediately prior to satellite acquisition can cause widespread dielectric surges not related to irrigation.",
            "Radar indicators provide comparative indicators across repeat passes rather than absolute volumetric soil moisture without ground-probe calibration.",
        ]

        inspector = build_inspector_grid(
            base_raw,
            {
                "baseline_db": base_db,
                "monitoring_db": event_db,
                "delta_db": delta_db,
                "change_flag": cleaned_change.astype("float32"),
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
                "change_ha": change_ha,
                "change_km2": change_km2,
                "mean_delta_db": mean_delta,
                "soil_proxy_index": soil_proxy_index,
                "legend": [
                    {"color": "#d97706", "label": f"Surface Dynamic / Harvest (≤ {thr_db:.1f} dB)", "unit": "dB"},
                    {"color": "#3b82f6", "label": "Moisture Surge / Biomass Increase (> 0 dB)", "unit": "dB"},
                    {"color": "#64748b", "label": "Stable Agricultural Canopy", "unit": "~0 dB"},
                ],
                "inspector": inspector,
            },
        }
