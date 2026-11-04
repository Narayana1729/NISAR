"""Domain 3: Ice, Glaciers & Cryosphere Pipeline Implementation

Implements:
- Input validation: Glacier SAR observations or precomputed ice velocity magnitude raster (e.g. NASA ITS_LIVE).
- Optional pre/post calving pair for terminus retreat edge and area analysis.
- Optional independent velocity reference raster for continuous RMSE/MAE/Bias/Correlation validation.
- Optional exposure assets (fjord infrastructure, coastal stations, shipping corridors) for exposure analysis.
- Terminus shift detection and flow speed velocity visualization with calibrated color scales.
- Multi-tier scientific explainability separating ice surface speed from volumetric ice mass loss.
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
from app.utils.validation import evaluate_continuous_field


class CryospherePipeline(DomainPipeline):
    domain = "domain3"
    analysis_name = "Ice Dynamics & Glacier Surface Velocity Visualization"
    summary = (
        "Maps glacier terminus position changes and visualizes calibrated surface flow velocity magnitude "
        "fields from repeat-pass SAR and validated ice velocity products (e.g. NASA ITS_LIVE)."
    )
    implementation_status = "implemented"
    deferred_features = [
        "Raw sub-pixel normalized cross-correlation feature tracking engine",
        "Grounding line double-differential InSAR tidal flexure analysis",
    ]

    inputs = [
        InputSpec(
            role="velocity",
            label="Ice Velocity Raster",
            product_types=["ice_velocity"],
            required=True,
            description="Calibrated surface flow velocity magnitude raster (e.g. meters/year from ITS_LIVE or SAR tracking).",
        ),
        InputSpec(
            role="baseline_sar",
            label="Baseline SAR Terminus (Optional)",
            product_types=["sar_backscatter"],
            required=False,
            description="Pre-calving SAR observation for terminus margin inspection.",
        ),
        InputSpec(
            role="event_sar",
            label="Post-Calving SAR (Optional)",
            product_types=["sar_backscatter"],
            required=False,
            description="Post-calving SAR observation for terminus margin inspection.",
        ),
        InputSpec(
            role="reference_velocity",
            label="Reference / Climatological Velocity (Optional Comparison)",
            product_types=["reference_velocity", "ice_velocity"],
            required=False,
            description="Reference glacier velocity field or multi-year climatology (m/year) for RMSE, MAE, Bias, and Correlation evaluation.",
        ),
        InputSpec(
            role="exposure_assets",
            label="Glacier Boundary / Infrastructure Assets (Optional GeoJSON)",
            product_types=["exposure_assets"],
            required=False,
            description="Georeferenced glacier inventory boundaries, research stations, or fjord corridors (GeoJSON).",
        ),
    ]

    params = [
        ParamSpec(
            name="v_max_display",
            label="Max Display Velocity (m/yr)",
            type="number",
            default=1500.0,
            min=10.0,
            max=10000.0,
            description="Upper cutoff for velocity color ramp stretching.",
        ),
        ParamSpec(
            name="fast_ice_threshold",
            label="Fast Flow Threshold (m/yr)",
            type="number",
            default=300.0,
            min=10.0,
            max=5000.0,
            description="Threshold defining rapidly streaming outlet glaciers.",
        ),
    ]

    def run(self, ctx: PipelineContext) -> dict:
        notes: list[str] = []
        warnings: list[str] = []

        vel_ds = ctx.datasets["velocity"]
        vel_units = vel_ds.units or "m/year"
        vel_source_label = vel_ds.source or "External Pre-Computed Velocity Product (NASA ITS_LIVE / SAR Tracking)"
        notes.append(f"Velocity source: {vel_source_label} (units: {vel_units}).")

        vel_raw = read_band(ctx.path_of("velocity"), max_pixels=max_pixels())
        vel_arr = vel_raw.array.copy()
        valid_mask = np.isfinite(vel_arr) & (vel_arr >= 0) & (vel_arr < 50_000.0)
        if not np.any(valid_mask):
            raise PipelineInputError("Velocity raster contains no valid non-negative values.")
        vel_arr[~valid_mask] = np.nan

        v_max = ctx.params["v_max_display"]
        fast_thr = ctx.params["fast_ice_threshold"]

        mean_vel = float(np.nanmean(vel_arr[valid_mask]))
        max_vel = float(np.nanmax(vel_arr[valid_mask]))
        fast_mask = (vel_arr >= fast_thr) & valid_mask
        fast_pixels = int(np.sum(fast_mask))
        fast_pct = (fast_pixels / int(np.sum(valid_mask))) * 100.0

        pixel_areas = pixel_area_m2(vel_raw.transform, vel_raw.crs, vel_raw.height)
        fast_km2 = mask_area_m2(fast_mask, pixel_areas) / 1_000_000.0

        out_tif = "ice_velocity_clipped.tif"
        write_geotiff(ctx.out(out_tif), vel_arr, vel_raw, dtype="float32", nodata=-9999.0)
        ctx.add_layer("velocity_geotiff", "Velocity GeoTIFF", "raster", out_tif, "Surface ice velocity (m/year)")

        vel_png = "velocity_heatmap.png"
        write_ramp_png(ctx.out(vel_png), vel_arr, 0.0, v_max, SEQUENTIAL)
        ctx.add_layer("velocity_preview", "Velocity Flow Heatmap", "preview", vel_png, "Flow speed (purple=slow, yellow=fast streaming)")

        terminus_change_km2 = 0.0
        change_mask_for_exposure = fast_mask

        # Optional Terminus SAR overlays & calving margin comparison
        if ctx.has("baseline_sar") and ctx.has("event_sar"):
            base_sar_ds = ctx.datasets["baseline_sar"]
            event_sar_ds = ctx.datasets["event_sar"]
            if (
                base_sar_ds.acquisition_date
                and event_sar_ds.acquisition_date
                and base_sar_ds.acquisition_date > event_sar_ds.acquisition_date
            ):
                warnings.append(
                    f"Chronological order warning: Baseline Terminus SAR ({base_sar_ds.acquisition_date}) is later than "
                    f"Post-Calving Terminus SAR ({event_sar_ds.acquisition_date}). Verify pre/post role assignment."
                )
            base_sar = read_band(ctx.path_of("baseline_sar"), max_pixels=max_pixels())
            event_sar = read_band(ctx.path_of("event_sar"), max_pixels=max_pixels())
            base_sar_al, _ = align_to(vel_raw, base_sar, Resampling.bilinear)
            event_sar_al, _ = align_to(vel_raw, event_sar, Resampling.bilinear)

            p_b = to_power(base_sar_al.array, ctx.datasets["baseline_sar"].value_scale or "power")
            p_e = to_power(event_sar_al.array, ctx.datasets["event_sar"].value_scale or "power")
            db_b = power_to_db(p_b)
            db_e = power_to_db(p_e)

            val_sar = np.isfinite(db_b) & np.isfinite(db_e)
            if np.any(val_sar):
                vmin, vmax = common_stretch(db_b[val_sar], db_e[val_sar])
                b_png = "terminus_baseline.png"
                e_png = "terminus_event.png"
                write_grayscale_png(ctx.out(b_png), db_b, vmin, vmax)
                write_grayscale_png(ctx.out(e_png), db_e, vmin, vmax)
                ctx.add_layer("terminus_baseline", "Baseline Terminus SAR", "preview", b_png)
                ctx.add_layer("terminus_event", "Post-Calving Terminus SAR", "preview", e_png)

                # Calving front retreat detection (where bright glacier ice dropped > 4 dB to dark open fjord water)
                calving_drop = (box_mean(db_b, 3) - box_mean(db_e, 3)) >= 4.0
                calving_clean = remove_small_clusters(calving_drop & val_sar, 4)
                terminus_change_km2 = mask_area_m2(calving_clean, pixel_areas) / 1_000_000.0
                change_mask_for_exposure = fast_mask | calving_clean

                term_class = np.zeros(vel_raw.array.shape, dtype="uint8")
                term_class[fast_mask] = 1
                term_class[calving_clean] = 2
                term_png = "terminus_overlay.png"
                write_class_png(
                    ctx.out(term_png),
                    term_class,
                    {
                        0: (0, 0, 0, 0),
                        1: (56, 189, 248, 160),   # Sky blue: Fast streaming zone
                        2: (244, 63, 94, 230),    # Rose: Terminus calving retreat margin
                    },
                )
                ctx.add_layer("change_overlay", "Terminus Calving & Fast Flow Overlay", "preview", term_png, "Rose = Calving retreat, Cyan = Fast ice stream")
                notes.append("Generated comparative terminus SAR layers and calving front retreat overlay.")

        validation_info = evaluate_continuous_field(
            ctx=ctx,
            ref_role="reference_velocity",
            measured_arr=vel_arr,
            base_raw=vel_raw,
            valid_mask=valid_mask,
            unit="m/year",
        )

        exposure_info = evaluate_spatial_exposure(
            ctx=ctx,
            role="exposure_assets",
            change_mask=change_mask_for_exposure,
            base_raw=vel_raw,
            pixel_areas_m2=pixel_areas,
            area_unit="km²",
        )

        metrics = [
            {"label": "Peak Flow Velocity", "value": fmt(max_vel, 0), "unit": "m/year", "description": "Maximum surface flow speed recorded."},
            {"label": "Mean Ice Speed", "value": fmt(mean_vel, 0), "unit": "m/year", "description": "Average ice speed across valid domain."},
            {"label": "Fast Streaming Zone", "value": fmt(fast_pct, 1), "unit": "%", "description": f"Percentage of glacier area moving >= {fast_thr:.0f} m/yr."},
            {"label": "Fast Ice Area", "value": fmt(fast_km2, 2), "unit": "km²", "description": f"Physical area moving >= {fast_thr:.0f} m/yr."},
        ]
        if terminus_change_km2 > 0:
            metrics.append({"label": "Terminus Retreat Zone", "value": fmt(terminus_change_km2, 2), "unit": "km²", "description": "Area of terminus backscatter transition between SAR passes."})

        explanation = {
            "level1_visual": (
                "The visualization maps glacier surface flow speed in meters per year. Warm yellow and orange hues indicate "
                "rapidly discharging ice streams and calving margins, while deep purple shows stagnant ice or bedrock margins."
            ),
            "level2_method": (
                f"Surface velocity fields are ingested from {vel_source_label} ({vel_units}). "
                f"Display values are stretched linearly from 0 to {v_max:.0f} m/yr, and fast-streaming outlet trunks are segmented at >= {fast_thr:.0f} m/yr."
            ),
            "level3_evidence": (
                f"Peak surface flow speed reached {max_vel:.0f} m/year, with {fast_pct:.1f}% ({fast_km2:.2f} km²) of the observed domain "
                f"exceeding the fast-streaming threshold of {fast_thr:.0f} m/year."
            ),
            "level4_uncertainty": (
                "Displayed velocity represents horizontal surface speed from external/pre-computed offset tracking and does not "
                "directly measure ice thickness or basal volumetric mass balance without radar altimetry/gravimetry. "
                "When an annual ITS_LIVE velocity mosaic is compared against the multi-year ITS_LIVE static climatology, the metrics "
                "quantify interannual velocity anomaly relative to the multi-decadal baseline rather than error against an independent sensor."
            ),
        }

        caveats = [
            f"Velocity product source: {vel_source_label} (external pre-computed product, not raw offset tracking computed on the fly).",
            "Comparing an annual velocity mosaic against a multi-year climatological reference from the same processing suite measures interannual flow anomaly, not independent ground-truth error.",
            "Surface flow velocity does not equal volumetric mass loss without ice thickness constraints.",
            "Summer surface meltwater lowers SAR backscatter without implying structural ice shelf collapse.",
        ]

        inspector = build_inspector_grid(
            vel_raw,
            {
                "velocity_m_yr": vel_arr,
                "fast_stream_flag": fast_mask.astype("float32"),
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
                "max_velocity_m_yr": max_vel,
                "mean_velocity_m_yr": mean_vel,
                "fast_streaming_pct": fast_pct,
                "fast_streaming_km2": fast_km2,
                "terminus_change_km2": terminus_change_km2,
                "velocity_origin": "external_product",
                "legend": [
                    {"color": "#fde047", "label": f"Fast Streaming Ice (≥ {fast_thr:.0f} m/yr)", "unit": "m/year"},
                    {"color": "#a855f7", "label": "Intermediate Glacier Flow", "unit": "m/year"},
                    {"color": "#1e1b4b", "label": "Stagnant Ice / Bedrock Margin", "unit": "~0 m/year"},
                ],
                "inspector": inspector,
            },
        }


from app.domains.domain4.processor import LandMovementPipeline


class EarthquakesPipeline(LandMovementPipeline):
    domain = "domain3"
    analysis_name = "Earthquakes & InSAR Ground Deformation Analysis"
    summary = (
        "Investigates surface displacement and land subsidence from InSAR observations with "
        "coherence quality filtering, reference validation, and infrastructure exposure."
    )
