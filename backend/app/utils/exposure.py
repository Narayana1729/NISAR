"""Real-World Spatial Exposure Analysis Engine.

Computes geographic intersection between detected surface change masks and mapped
infrastructure, settlement, road, agricultural, or protected-area vector assets.

Strictly distinguishes measured spatial exposure from unverified structural damage
or economic loss.
"""
from __future__ import annotations

import json
from typing import Any

import numpy as np
from rasterio.crs import CRS
from rasterio.features import rasterize
from rasterio.warp import transform_geom

from app.database.models import DatasetModel
from app.schemas.results import ExposureInfo, MetricItem
from app.services.pipeline import PipelineContext
from app.utils.raster import RasterData, fmt, mask_area_m2, write_class_png


def evaluate_spatial_exposure(
    ctx: PipelineContext,
    role: str,
    change_mask: np.ndarray,
    base_raw: RasterData,
    pixel_areas_m2: np.ndarray,
    area_unit: str = "ha",
) -> ExposureInfo:
    """Intersect a detected-change boolean mask against a georeferenced exposure_assets GeoJSON."""
    if not ctx.has(role):
        return ExposureInfo()

    ds: DatasetModel = ctx.datasets[role]
    gj_path = ctx.path_of(role)
    try:
        gj = json.loads(gj_path.read_text())
    except Exception as exc:
        return ExposureInfo(
            status="not_evaluated",
            asset_dataset_id=ds.id,
            asset_dataset_name=ds.name,
            notes=f"Could not parse exposure GeoJSON: {exc}",
        )

    features = [f for f in gj.get("features", []) if f.get("geometry")]
    if not features:
        return ExposureInfo(
            status="not_evaluated",
            asset_dataset_id=ds.id,
            asset_dataset_name=ds.name,
            notes="Exposure GeoJSON contains no valid geometry features.",
        )

    src_crs = CRS.from_epsg(4326)
    dst_crs = base_raw.crs
    shape = (base_raw.height, base_raw.width)
    res_m = abs(float(base_raw.transform.a))
    scale = 1_000_000.0 if area_unit == "km²" else 10_000.0

    # 0 = none, 1 = unexposed asset footprint, 2 = exposed asset intersecting change
    exposure_canvas = np.zeros(shape, dtype="uint8")
    breakdown: list[dict[str, Any]] = []

    exposed_feature_count = 0
    total_in_aoi_count = 0
    total_exposed_area_m2 = 0.0
    total_exposed_road_km = 0.0

    for idx, feat in enumerate(features):
        props = feat.get("properties") or {}
        asset_name = str(props.get("name") or props.get("id") or f"Asset #{idx + 1}")
        asset_class = str(props.get("asset_class") or props.get("type") or props.get("category") or "infrastructure").lower()
        geom = feat["geometry"]
        gtype = geom.get("type", "Polygon")

        try:
            proj_geom = transform_geom(src_crs, dst_crs, geom) if dst_crs.to_epsg() != 4326 else geom
            feat_mask = rasterize(
                [(proj_geom, 1)],
                out_shape=shape,
                transform=base_raw.transform,
                fill=0,
                all_touched=True,
                dtype="uint8",
            ).astype(bool)
        except Exception:
            continue

        if not np.any(feat_mask):
            continue

        total_in_aoi_count += 1
        intersect_mask = feat_mask & change_mask.astype(bool)
        intersect_px = int(np.sum(intersect_mask))
        is_exposed = intersect_px > 0

        exposure_canvas[feat_mask & (exposure_canvas == 0)] = 1
        if is_exposed:
            exposure_canvas[intersect_mask] = 2
            exposed_feature_count += 1

        if gtype in ("LineString", "MultiLineString") or "road" in asset_class or "highway" in asset_class:
            # Estimate intersected corridor length in km from pixel count along rasterized line
            exposed_km = (intersect_px * res_m) / 1000.0
            total_km = (int(np.sum(feat_mask)) * res_m) / 1000.0
            total_exposed_road_km += exposed_km
            qty_str = f"{exposed_km:.2f} / {total_km:.2f}"
            qty_unit = "km corridor"
        else:
            exposed_m2 = mask_area_m2(intersect_mask, pixel_areas_m2)
            total_m2 = mask_area_m2(feat_mask, pixel_areas_m2)
            total_exposed_area_m2 += exposed_m2
            qty_str = f"{exposed_m2 / scale:.2f} / {total_m2 / scale:.2f}"
            qty_unit = area_unit

        breakdown.append({
            "asset_name": asset_name,
            "asset_class": asset_class,
            "geometry_type": gtype,
            "exposed": is_exposed,
            "intersected_pixels": intersect_px,
            "exposure_measurement": qty_str,
            "unit": qty_unit,
            "measurement_basis": "Measured spatial intersection in " + str(dst_crs),
        })

    if np.any(exposure_canvas > 0):
        exp_png = "exposure_overlay.png"
        palette = {
            0: (0, 0, 0, 0),
            1: (168, 85, 247, 175),   # Purple: Mapped asset outside change zone
            2: (250, 204, 21, 245),   # High-visibility Gold: Asset intersecting detected change
        }
        write_class_png(ctx.out(exp_png), exposure_canvas, palette)
        ctx.add_layer(
            "exposure_overlay",
            "Asset Exposure Overlay",
            "preview",
            exp_png,
            "Gold = Exposed asset intersecting change, Purple = Unexposed mapped asset",
        )

    metrics = [
        MetricItem(
            label="Exposed Mapped Assets",
            value=f"{exposed_feature_count} / {total_in_aoi_count}",
            unit="features",
            description="Assets within study area spatially intersecting detected change.",
        ),
        MetricItem(
            label="Exposed Polygon Footprint",
            value=fmt(total_exposed_area_m2 / scale, 2),
            unit=area_unit,
            description="Measured polygon asset area intersecting detected change.",
        ),
    ]
    if total_exposed_road_km > 0:
        metrics.append(
            MetricItem(
                label="Exposed Linear Corridors",
                value=fmt(total_exposed_road_km, 2),
                unit="km",
                description="Estimated length of linear road/infrastructure segments intersecting change.",
            )
        )

    return ExposureInfo(
        status="evaluated",
        asset_dataset_id=ds.id,
        asset_dataset_name=ds.name,
        asset_source=ds.source or "Registered Georeferenced Vector Layer",
        asset_is_synthetic=bool(ds.is_synthetic),
        metrics=metrics,
        asset_breakdown=breakdown,
        notes=(
            f"Spatial intersection computed in {dst_crs} at {res_m:.1f}m grid resolution against '{ds.name}'."
            + (" Note: Supporting asset layer is a synthetic demonstration fixture." if ds.is_synthetic else "")
        ),
        limitations=[
            "Spatial intersection measures geographic co-location between SAR-detected surface change and mapped asset footprints.",
            "It does NOT establish structural damage, building collapse, casualties, or financial loss without ground inspection.",
            "Rasterized corridor lengths depend on pixel resolution and line orientation.",
        ],
    )
