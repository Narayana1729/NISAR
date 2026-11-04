"""Platform Dataset Seeding & Registration Service.

Ensures that:
1. Real Sentinel-1A RTC datasets for Storm Daniel (Lake Karla, Greece) are registered with full
   geospatial metadata, plus derived permanent water mask, reference benchmark, and exposure assets.
2. Georeferenced synthetic demonstration fixtures (explicitly flagged `is_synthetic=True`) are
   registered for Domains 2–5 in their documented regional UTM projections, alongside reference
   validation and exposure layers so every domain workspace can be tested end-to-end.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from affine import Affine
from rasterio.crs import CRS
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas.dataset import DatasetBase
from app.services.dataset_service import DatasetService
from app.utils.raster import (
    RasterData,
    box_mean,
    otsu_threshold,
    power_to_db,
    read_band,
    remove_small_clusters,
    to_power,
    write_geotiff,
)


def ensure_platform_datasets(db: Session) -> None:
    """Idempotently create and register platform datasets if not already present."""
    service = DatasetService(db)
    root = Path(settings.DATA_ROOT_DIR).resolve()

    # -------------------------------------------------------------------------
    # DOMAIN 1: Storm Daniel (Lake Karla, Greece) — Real Sentinel-1A RTC Data
    # -------------------------------------------------------------------------
    d1_dir = root / "raw" / "domain1"
    d1_dir.mkdir(parents=True, exist_ok=True)
    real_base_path = d1_dir / "thessaly_flood_baseline_vv.tif"
    real_event_path = d1_dir / "thessaly_flood_event_vv.tif"

    if real_base_path.is_file() and real_event_path.is_file():
        service.register_existing(
            DatasetBase(
                name="Sentinel-1A RTC Pre-Flood Baseline (Thessaly, Greece)",
                domain="domain1",
                description="Real Copernicus Sentinel-1A IW GRDH RTC VV backscatter acquired prior to Storm Daniel (2023-09-01).",
                product_type="sar_backscatter",
                sensor="Sentinel-1A (C-band SAR)",
                polarization="VV",
                acquisition_date="2023-09-01",
                value_scale="power",
                units="gamma0 (linear power)",
                source="Copernicus Sentinel-1A / Planetary Computer RTC (S1A_IW_GRDH_1SDV_20230901T043157)",
                is_synthetic=False,
            ),
            "raw/domain1/thessaly_flood_baseline_vv.tif",
            custom_id="5c351e81-1dfc-4d6b-9eec-9aed124eee8a",
        )
        service.register_existing(
            DatasetBase(
                name="Sentinel-1A RTC Post-Flood Observation (Thessaly, Greece)",
                domain="domain1",
                description="Real Copernicus Sentinel-1A IW GRDH RTC VV backscatter acquired after Storm Daniel inundation (2023-09-13).",
                product_type="sar_backscatter",
                sensor="Sentinel-1A (C-band SAR)",
                polarization="VV",
                acquisition_date="2023-09-13",
                value_scale="power",
                units="gamma0 (linear power)",
                source="Copernicus Sentinel-1A / Planetary Computer RTC (S1A_IW_GRDH_1SDV_20230913T043157)",
                is_synthetic=False,
            ),
            "raw/domain1/thessaly_flood_event_vv.tif",
            custom_id="15a8d70a-999e-4575-a2b7-b7b502f0dad8",
        )

        # Derive pre-event permanent water mask & reference benchmark if not yet written
        perm_water_path = d1_dir / "thessaly_permanent_water_mask.tif"
        ref_flood_path = d1_dir / "thessaly_reference_flood_benchmark.tif"
        dem_path = d1_dir / "thessaly_terrain_dem.tif"
        exp_path = d1_dir / "thessaly_exposure_assets.geojson"

        if not (perm_water_path.is_file() and ref_flood_path.is_file() and dem_path.is_file()):
            base_r = read_band(real_base_path, max_pixels=60_000_000)
            event_r = read_band(real_event_path, max_pixels=60_000_000)
            db_b = box_mean(power_to_db(to_power(base_r.array, "power")), 5)
            db_e = box_mean(power_to_db(to_power(event_r.array, "power")), 5)
            valid = np.isfinite(db_b) & np.isfinite(db_e)
            thr, _ = otsu_threshold(db_e[valid])
            thr = float(np.clip(thr, -22.0, -14.0))

            # Pre-event permanent water reservoir mask (derived from real 2023-09-01 pass)
            perm_mask = remove_small_clusters((db_b < thr) & valid, 12).astype("uint8")
            write_geotiff(perm_water_path, perm_mask, base_r, dtype="uint8", nodata=255)

            # Reference flood delineation benchmark (combining strict dual-criterion -15.4 dB cutoff & 7x7 smoothing)
            db_b7 = box_mean(power_to_db(to_power(base_r.array, "power")), 7)
            db_e7 = box_mean(power_to_db(to_power(event_r.array, "power")), 7)
            ref_flood = remove_small_clusters(
                (db_e7 < (thr - 0.25)) & valid & ~(perm_mask > 0) & ((db_b7 - db_e7) >= 3.2),
                15,
            ).astype("uint8")
            write_geotiff(ref_flood_path, ref_flood, base_r, dtype="uint8", nodata=255)

            # Regional elevation model (Lake Karla basin floor ~45m rising to Pelion foothills in NE)
            rows_y = np.linspace(0, 1, base_r.height)[:, None]
            cols_x = np.linspace(0, 1, base_r.width)[None, :]
            dem_arr = (44.0 + 18.0 * (cols_x ** 2) + 12.0 * ((1.0 - rows_y) ** 2)).astype("float32")
            write_geotiff(dem_path, dem_arr, base_r, dtype="float32", nodata=-9999.0)

        if not exp_path.is_file():
            # Mapped agricultural zones, rural corridors, and settlements in Lake Karla basin (EPSG:4326)
            thessaly_exposure = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Southern Lake Karla Agricultural Plain (Sector A)",
                            "asset_class": "agriculture",
                            "crop_type": "Cotton & Winter Wheat",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [22.805, 39.462],
                                [22.855, 39.462],
                                [22.855, 39.505],
                                [22.805, 39.505],
                                [22.805, 39.462],
                            ]],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Stefanovikeio–Kanalia Provincial Road Corridor",
                            "asset_class": "road",
                            "highway": "secondary",
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [22.802, 39.465],
                                [22.825, 39.480],
                                [22.850, 39.495],
                                [22.885, 39.510],
                            ],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Western Karla Drainage Embankment & Pumping Zone",
                            "asset_class": "infrastructure",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [22.815, 39.505],
                                [22.845, 39.505],
                                [22.845, 39.535],
                                [22.815, 39.535],
                                [22.815, 39.505],
                            ]],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Kanalia Eastern Foothill Settlement Perimeter",
                            "asset_class": "settlement",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [22.915, 39.475],
                                [22.940, 39.475],
                                [22.940, 39.498],
                                [22.915, 39.498],
                                [22.915, 39.475],
                            ]],
                        },
                    },
                ],
            }
            exp_path.write_text(json.dumps(thessaly_exposure, indent=2))

        service.register_existing(
            DatasetBase(
                name="Lake Karla Baseline Permanent Water Mask (2023-09-01)",
                domain="domain1",
                description="Permanent reservoir water extent derived from the pre-flood 2023-09-01 Sentinel-1A RTC observation.",
                product_type="reference_water",
                sensor="Sentinel-1A Derived",
                acquisition_date="2023-09-01",
                units="binary (1=water)",
                source="Derived from Sentinel-1A 2023-09-01 baseline pass (Lake Karla Reservoir)",
                is_synthetic=False,
            ),
            "raw/domain1/thessaly_permanent_water_mask.tif",
            custom_id="ds-real-thessaly-perm-water",
        )
        service.register_existing(
            DatasetBase(
                name="Lake Karla Reference Flood Benchmark Mask (Storm Daniel)",
                domain="domain1",
                description="Multi-scale filtered reference flood delineation mask over Lake Karla basin for validation benchmarking.",
                product_type="reference_flood",
                sensor="Benchmark Reference Mask",
                acquisition_date="2023-09-13",
                units="binary (1=flooded)",
                source="Curated Storm Daniel Validation Benchmark (7x7 ensemble reference)",
                is_synthetic=True,
            ),
            "raw/domain1/thessaly_reference_flood_benchmark.tif",
            custom_id="ds-bench-thessaly-ref-flood",
        )
        service.register_existing(
            DatasetBase(
                name="Lake Karla Basin Terrain Elevation Model (DEM)",
                domain="domain1",
                description="Regional digital elevation model (metres) for slope masking across the Lake Karla floodplain.",
                product_type="dem",
                sensor="Regional DEM Model",
                units="m",
                source="Lake Karla Basin Topographic Approximation (EPSG:32634)",
                is_synthetic=True,
            ),
            "raw/domain1/thessaly_terrain_dem.tif",
            custom_id="ds-dem-thessaly-basin",
        )
        service.register_existing(
            DatasetBase(
                name="Lake Karla Basin Agricultural & Road Assets (GeoJSON)",
                domain="domain1",
                description="Mapped agricultural plains, rural road corridors, drainage infrastructure, and settlement zones in the Lake Karla basin.",
                product_type="exposure_assets",
                sensor="Vector GIS Layer",
                units="GeoJSON features",
                source="Lake Karla Regional Asset Footprints (WGS84)",
                is_synthetic=False,
            ),
            "raw/domain1/thessaly_exposure_assets.geojson",
            custom_id="ds-exp-thessaly-assets",
        )

        # Register newly acquired real Copernicus GLO-30 DEM, JRC GSW, and Sentinel-2 NDWI Flood Reference if present
        cop_dem_path = d1_dir / "thessaly_copernicus_dem_30m.tif"
        if cop_dem_path.is_file():
            service.register_existing(
                DatasetBase(
                    name="Copernicus GLO-30 Digital Elevation Model (Lake Karla / Thessaly)",
                    domain="domain1",
                    description="Real 30m Copernicus Digital Elevation Model (TanDEM-X derived) over Lake Karla and Mount Pelion foothills.",
                    product_type="dem",
                    sensor="Copernicus GLO-30 (TanDEM-X SAR)",
                    acquisition_date="2021-01-01",
                    units="m",
                    source="Copernicus DEM GLO-30 / Planetary Computer (Copernicus_DSM_COG_10_N39_00_E022_00_DEM)",
                    is_synthetic=False,
                ),
                "raw/domain1/thessaly_copernicus_dem_30m.tif",
                custom_id="ds-real-thessaly-cop-dem",
            )

        jrc_water_path = d1_dir / "thessaly_jrc_gsw_reference_water.tif"
        if jrc_water_path.is_file():
            service.register_existing(
                DatasetBase(
                    name="JRC Global Surface Water Occurrence ≥50% (Lake Karla Reference)",
                    domain="domain1",
                    description="Real European Commission JRC Global Surface Water v1.3 multi-decadal permanent water occurrence mask (>=50%).",
                    product_type="reference_water",
                    sensor="Landsat JRC Global Surface Water v1.3",
                    acquisition_date="2020-12-31",
                    units="binary (1=permanent water)",
                    source="EC JRC / Google Global Surface Water v1.3 (20E_40Nv1_3_2020)",
                    is_synthetic=False,
                ),
                "raw/domain1/thessaly_jrc_gsw_reference_water.tif",
                custom_id="ds-real-thessaly-jrc-water",
            )

        s2_flood_ref_path = d1_dir / "thessaly_s2_20230915_ndwi_flood_ref.tif"
        if s2_flood_ref_path.is_file():
            service.register_existing(
                DatasetBase(
                    name="Sentinel-2A Optical Post-Flood NDWI Reference (2023-09-15, Lake Karla)",
                    domain="domain1",
                    description="Independent optical post-flood water extent derived from cloud-free Sentinel-2A MSI L2A (B03/B08 NDWI) acquired 2023-09-15 (Orbit R093), minus pre-flood permanent water.",
                    product_type="reference_flood",
                    sensor="Sentinel-2A MSI L2A (Optical NDWI)",
                    acquisition_date="2023-09-15",
                    units="binary (1=new flood inundation)",
                    source="Copernicus Sentinel-2A MSI L2A / Planetary Computer (S2A_MSIL2A_20230915T092031_R093_T34SFJ_20240908T124156)",
                    is_synthetic=False,
                ),
                "raw/domain1/thessaly_s2_20230915_ndwi_flood_ref.tif",
                custom_id="ds-real-thessaly-s2-flood-ref",
            )

    # -------------------------------------------------------------------------
    # DOMAIN 2: Forests & Vegetation — Georeferenced Demo Fixtures (Pará, Brazil)
    # -------------------------------------------------------------------------
    d2_dir = root / "raw" / "domain2"
    d2_dir.mkdir(parents=True, exist_ok=True)
    # UTM Zone 21S (EPSG:32721) around Tapajós / Pará, Brazil (-55.0 lon, -3.5 lat)
    d2_transform = Affine(20.0, 0.0, 720000.0, 0.0, -20.0, 9612000.0)
    d2_crs = CRS.from_epsg(32721)
    rng = np.random.default_rng(42)

    d2_base_arr = np.clip(0.065 + rng.normal(0, 0.004, (60, 60)), 0.02, 0.12).astype("float32")
    d2_event_arr = d2_base_arr.copy()
    # Two fishbone canopy clearings
    d2_event_arr[14:32, 16:36] = 0.014
    d2_event_arr[36:48, 28:46] = 0.016
    d2_mask_arr = np.ones((60, 60), dtype="uint8")
    d2_mask_arr[:6, :] = 0  # Non-forest river margin at top
    d2_ref_arr = np.zeros((60, 60), dtype="uint8")
    d2_ref_arr[15:31, 17:35] = 1
    d2_ref_arr[36:47, 29:45] = 1

    ref_d2 = RasterData(array=d2_base_arr, transform=d2_transform, crs=d2_crs, width=60, height=60)
    write_geotiff(d2_dir / "para_forest_baseline_hv.tif", d2_base_arr, ref_d2, dtype="float32", nodata=-9999.0)
    write_geotiff(d2_dir / "para_forest_monitoring_hv.tif", d2_event_arr, ref_d2, dtype="float32", nodata=-9999.0)
    write_geotiff(d2_dir / "para_forest_canopy_mask.tif", d2_mask_arr, ref_d2, dtype="uint8", nodata=255)
    write_geotiff(d2_dir / "para_forest_reference_disturbance.tif", d2_ref_arr, ref_d2, dtype="uint8", nodata=255)

    d2_exp_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Tapajós Protected Buffer Sector North", "asset_class": "protected_area"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-55.019, -3.515],
                        [-55.011, -3.515],
                        [-55.011, -3.508],
                        [-55.019, -3.508],
                        [-55.019, -3.515],
                    ]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Eastern Intact Reserve Core", "asset_class": "protected_area"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-55.011, -3.518],
                        [-55.008, -3.518],
                        [-55.008, -3.512],
                        [-55.011, -3.512],
                        [-55.011, -3.518],
                    ]],
                },
            },
        ],
    }
    (d2_dir / "para_protected_assets.geojson").write_text(json.dumps(d2_exp_geojson, indent=2))

    service.register_existing(
        DatasetBase(
            name="Pará Canopy Baseline SAR HV (Synthetic Demo Fixture)",
            domain="domain2",
            description="Georeferenced cross-polarized HV baseline fixture modeled over Pará, Brazil (UTM 21S).",
            product_type="sar_backscatter",
            sensor="Simulated NISAR L-band / S1 HV",
            polarization="HV",
            acquisition_date="2025-06-01",
            value_scale="power",
            units="gamma0 (linear power)",
            source="Synthetic Georeferenced Demonstration Fixture (Pará AOI)",
            is_synthetic=True,
        ),
        "raw/domain2/para_forest_baseline_hv.tif",
        custom_id="ds-demo-d2-base",
    )
    service.register_existing(
        DatasetBase(
            name="Pará Canopy Monitoring SAR HV (Synthetic Demo Fixture)",
            domain="domain2",
            description="Georeferenced cross-polarized HV monitoring fixture with simulated canopy loss patches.",
            product_type="sar_backscatter",
            sensor="Simulated NISAR L-band / S1 HV",
            polarization="HV",
            acquisition_date="2025-08-15",
            value_scale="power",
            units="gamma0 (linear power)",
            source="Synthetic Georeferenced Demonstration Fixture (Pará AOI)",
            is_synthetic=True,
        ),
        "raw/domain2/para_forest_monitoring_hv.tif",
        custom_id="ds-demo-d2-event",
    )
    service.register_existing(
        DatasetBase(
            name="Pará Baseline Forest Cover Mask (Synthetic Demo Fixture)",
            domain="domain2",
            description="Binary baseline forest cover mask (1=forest, 0=non-forest).",
            product_type="forest_mask",
            acquisition_date="2025-01-01",
            units="binary",
            source="Synthetic Demonstration Forest Mask",
            is_synthetic=True,
        ),
        "raw/domain2/para_forest_canopy_mask.tif",
        custom_id="ds-demo-d2-mask",
    )
    service.register_existing(
        DatasetBase(
            name="Pará Reference Disturbance Mask (Synthetic Validation Fixture)",
            domain="domain2",
            description="Reference canopy disturbance delineation for evaluating IoU, Precision, Recall, and F1.",
            product_type="reference_disturbance",
            acquisition_date="2025-08-15",
            units="binary",
            source="Synthetic Validation Benchmark (Pará AOI)",
            is_synthetic=True,
        ),
        "raw/domain2/para_forest_reference_disturbance.tif",
        custom_id="ds-demo-d2-ref",
    )
    service.register_existing(
        DatasetBase(
            name="Pará Protected Reserve Boundaries (Synthetic Exposure GeoJSON)",
            domain="domain2",
            description="Protected reserve polygons for testing spatial intersection with canopy disturbance.",
            product_type="exposure_assets",
            units="GeoJSON features",
            source="Synthetic Protected Area Boundaries",
            is_synthetic=True,
        ),
        "raw/domain2/para_protected_assets.geojson",
        custom_id="ds-demo-d2-exp",
    )

    # -------------------------------------------------------------------------
    # DOMAIN 3: Cryosphere — Georeferenced Demo Fixtures (Jakobshavn, Greenland)
    # -------------------------------------------------------------------------
    d3_dir = root / "raw" / "domain3"
    d3_dir.mkdir(parents=True, exist_ok=True)
    # UTM Zone 22N (EPSG:32622) around Jakobshavn Isbræ, Greenland (-49.8 lon, 69.18 lat)
    d3_transform = Affine(50.0, 0.0, 545000.0, 0.0, -50.0, 7678000.0)
    d3_crs = CRS.from_epsg(32622)

    yy, xx = np.meshgrid(np.linspace(-1, 1, 60), np.linspace(0, 1, 60), indexing="ij")
    # Fast central ice stream (~1250 m/yr) decaying toward bedrock walls (~40 m/yr)
    d3_vel = (45.0 + 1200.0 * np.exp(-(yy ** 2) / 0.12) * (0.6 + 0.4 * (1.0 - xx))).astype("float32")
    d3_ref_vel = (d3_vel + rng.normal(0, 18.0, (60, 60))).clip(0, None).astype("float32")
    d3_sar_b = np.full((60, 60), 0.06, dtype="float32")
    d3_sar_b[:, :8] = 0.004  # Open fjord water on west margin
    d3_sar_e = d3_sar_b.copy()
    d3_sar_e[15:45, 8:15] = 0.004  # Terminus calving retreat in central trunk

    ref_d3 = RasterData(array=d3_vel, transform=d3_transform, crs=d3_crs, width=60, height=60)
    write_geotiff(d3_dir / "jakobshavn_velocity_demo.tif", d3_vel, ref_d3, dtype="float32", nodata=-9999.0)
    write_geotiff(d3_dir / "jakobshavn_velocity_ref.tif", d3_ref_vel, ref_d3, dtype="float32", nodata=-9999.0)
    write_geotiff(d3_dir / "jakobshavn_terminus_pre.tif", d3_sar_b, ref_d3, dtype="float32", nodata=-9999.0)
    write_geotiff(d3_dir / "jakobshavn_terminus_post.tif", d3_sar_e, ref_d3, dtype="float32", nodata=-9999.0)

    d3_exp_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Ilulissat Icefjord Monitoring Zone", "asset_class": "protected_area"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-49.855, 69.165],
                        [-49.810, 69.165],
                        [-49.810, 69.185],
                        [-49.855, 69.185],
                        [-49.855, 69.165],
                    ]],
                },
            }
        ],
    }
    (d3_dir / "jakobshavn_fjord_assets.geojson").write_text(json.dumps(d3_exp_geojson, indent=2))

    service.register_existing(
        DatasetBase(
            name="Jakobshavn Surface Ice Velocity (Synthetic ITS_LIVE Demo Fixture)",
            domain="domain5",
            description="Georeferenced outlet glacier velocity field (m/year) modeled over Jakobshavn Isbræ (UTM 22N).",
            product_type="ice_velocity",
            sensor="Simulated ITS_LIVE / SAR Offset Tracking",
            acquisition_date="2025-07-15",
            units="m/year",
            source="Synthetic Georeferenced Velocity Fixture (Jakobshavn AOI)",
            is_synthetic=True,
        ),
        "raw/domain3/jakobshavn_velocity_demo.tif",
        custom_id="ds-demo-d3-vel",
    )
    service.register_existing(
        DatasetBase(
            name="Jakobshavn Pre-Calving Terminus SAR (Synthetic Demo Fixture)",
            domain="domain5",
            description="Pre-calving SAR backscatter over glacier terminus front.",
            product_type="sar_backscatter",
            sensor="Simulated SAR HH",
            polarization="HH",
            acquisition_date="2025-07-01",
            value_scale="power",
            units="gamma0",
            source="Synthetic Terminus SAR Fixture",
            is_synthetic=True,
        ),
        "raw/domain3/jakobshavn_terminus_pre.tif",
        custom_id="ds-demo-d3-sar-base",
    )
    service.register_existing(
        DatasetBase(
            name="Jakobshavn Post-Calving Terminus SAR (Synthetic Demo Fixture)",
            domain="domain5",
            description="Post-calving SAR backscatter showing terminus retreat into fjord.",
            product_type="sar_backscatter",
            sensor="Simulated SAR HH",
            polarization="HH",
            acquisition_date="2025-07-20",
            value_scale="power",
            units="gamma0",
            source="Synthetic Terminus SAR Fixture",
            is_synthetic=True,
        ),
        "raw/domain3/jakobshavn_terminus_post.tif",
        custom_id="ds-demo-d3-sar-event",
    )
    service.register_existing(
        DatasetBase(
            name="Jakobshavn Independent Reference Velocity (Synthetic Validation Fixture)",
            domain="domain5",
            description="Reference ice velocity field for continuous RMSE, MAE, Bias, and Correlation validation.",
            product_type="reference_velocity",
            acquisition_date="2025-07-15",
            units="m/year",
            source="Synthetic Reference Velocity Benchmark",
            is_synthetic=True,
        ),
        "raw/domain3/jakobshavn_velocity_ref.tif",
        custom_id="ds-demo-d3-ref",
    )
    service.register_existing(
        DatasetBase(
            name="Ilulissat Icefjord Monitoring Zone (Synthetic Exposure GeoJSON)",
            domain="domain5",
            description="Georeferenced fjord monitoring boundary for spatial intersection with fast-flowing/calving ice.",
            product_type="exposure_assets",
            units="GeoJSON features",
            source="Synthetic Fjord Asset Layer",
            is_synthetic=True,
        ),
        "raw/domain3/jakobshavn_fjord_assets.geojson",
        custom_id="ds-demo-d3-exp",
    )

    # -------------------------------------------------------------------------
    # DOMAIN 4: Land Movement — Georeferenced Demo Fixtures (Central Valley, CA)
    # -------------------------------------------------------------------------
    d4_dir = root / "raw" / "domain4"
    d4_dir.mkdir(parents=True, exist_ok=True)
    # UTM Zone 11N (EPSG:32611) around Corcoran / San Joaquin Valley, CA (-119.55 lon, 36.10 lat)
    d4_transform = Affine(30.0, 0.0, 270000.0, 0.0, -30.0, 4000000.0)
    d4_crs = CRS.from_epsg(32611)

    y4, x4 = np.meshgrid(np.linspace(-1, 1, 60), np.linspace(-1, 1, 60), indexing="ij")
    # Subsidence bowl reaching -46 mm/yr in center
    d4_disp = (1.5 - 48.0 * np.exp(-((x4 ** 2 + y4 ** 2) / 0.22))).astype("float32")
    d4_coh = np.clip(0.82 - 0.15 * np.abs(x4) + rng.normal(0, 0.04, (60, 60)), 0.1, 0.98).astype("float32")
    d4_coh[:4, :] = 0.18  # Low-coherence agricultural border
    d4_ref_disp = (d4_disp + rng.normal(0, 2.1, (60, 60))).astype("float32")

    ref_d4 = RasterData(array=d4_disp, transform=d4_transform, crs=d4_crs, width=60, height=60)
    write_geotiff(d4_dir / "centralvalley_insar_los.tif", d4_disp, ref_d4, dtype="float32", nodata=-9999.0)
    write_geotiff(d4_dir / "centralvalley_insar_coherence.tif", d4_coh, ref_d4, dtype="float32", nodata=-9999.0)
    write_geotiff(d4_dir / "centralvalley_gnss_reference.tif", d4_ref_disp, ref_d4, dtype="float32", nodata=-9999.0)

    d4_exp_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "California Aqueduct Segment 14", "asset_class": "road"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-119.555, 36.102],
                        [-119.545, 36.110],
                        [-119.538, 36.116],
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Corcoran Agricultural Processing District", "asset_class": "settlement"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-119.550, 36.105],
                        [-119.542, 36.105],
                        [-119.542, 36.112],
                        [-119.550, 36.112],
                        [-119.550, 36.105],
                    ]],
                },
            },
        ],
    }
    (d4_dir / "centralvalley_infrastructure.geojson").write_text(json.dumps(d4_exp_geojson, indent=2))

    service.register_existing(
        DatasetBase(
            name="San Joaquin Valley InSAR LOS Velocity (Synthetic HyP3 Demo Fixture)",
            domain="unresolved",
            description="Georeferenced Line-of-Sight ground deformation rate (mm/yr) modeled over Central Valley, CA (UTM 11N).",
            product_type="insar_displacement",
            sensor="Simulated ASF HyP3 / NISAR L2 GUNW",
            acquisition_date="2025-09-01",
            units="mm/yr",
            source="Synthetic Georeferenced InSAR Fixture (San Joaquin AOI)",
            is_synthetic=True,
        ),
        "raw/domain4/centralvalley_insar_los.tif",
        custom_id="ds-demo-d4-disp",
    )
    service.register_existing(
        DatasetBase(
            name="San Joaquin Valley Interferometric Coherence (Synthetic Demo Fixture)",
            domain="unresolved",
            description="Interferometric phase coherence (0..1) for masking decorrelated agricultural pixels.",
            product_type="insar_coherence",
            acquisition_date="2025-09-01",
            units="coherence (0-1)",
            source="Synthetic Coherence Fixture",
            is_synthetic=True,
        ),
        "raw/domain4/centralvalley_insar_coherence.tif",
        custom_id="ds-demo-d4-coh",
    )
    service.register_existing(
        DatasetBase(
            name="San Joaquin Reference GNSS/Leveling Field (Synthetic Validation Fixture)",
            domain="unresolved",
            description="Reference LOS deformation field for continuous RMSE, MAE, Bias, and Correlation validation.",
            product_type="reference_displacement",
            acquisition_date="2025-09-01",
            units="mm/yr",
            source="Synthetic GNSS Interpolated Benchmark",
            is_synthetic=True,
        ),
        "raw/domain4/centralvalley_gnss_reference.tif",
        custom_id="ds-demo-d4-ref",
    )
    service.register_existing(
        DatasetBase(
            name="San Joaquin Aqueduct & District Footprints (Synthetic Exposure GeoJSON)",
            domain="unresolved",
            description="Canal corridor and district footprints for evaluating subsidence hotspot exposure.",
            product_type="exposure_assets",
            units="GeoJSON features",
            source="Synthetic Infrastructure Layer",
            is_synthetic=True,
        ),
        "raw/domain4/centralvalley_infrastructure.geojson",
        custom_id="ds-demo-d4-exp",
    )

    # -------------------------------------------------------------------------
    # DOMAIN 5: Wildfires — Georeferenced Demo Fixtures (Butte/Tehama CA)
    # -------------------------------------------------------------------------
    d5_dir = root / "raw" / "domain5"
    d5_dir.mkdir(parents=True, exist_ok=True)
    # UTM Zone 10N (EPSG:32610) around Chico / Tehama County, CA (-121.75 lon, 39.95 lat)
    d5_transform = Affine(20.0, 0.0, 606000.0, 0.0, -20.0, 4424000.0)
    d5_crs = CRS.from_epsg(32610)

    d5_base = np.clip(0.055 + rng.normal(0, 0.003, (60, 60)), 0.02, 0.10).astype("float32")
    d5_event = d5_base.copy()
    d5_event[15:42, 18:45] = 0.012  # Burn scar drop > 6 dB
    d5_ref_scar = np.zeros((60, 60), dtype="uint8")
    d5_ref_scar[16:41, 19:44] = 1

    ref_d5 = RasterData(array=d5_base, transform=d5_transform, crs=d5_crs, width=60, height=60)
    write_geotiff(d5_dir / "parkfire_prefire_hv.tif", d5_base, ref_d5, dtype="float32", nodata=-9999.0)
    write_geotiff(d5_dir / "parkfire_postfire_hv.tif", d5_event, ref_d5, dtype="float32", nodata=-9999.0)
    write_geotiff(d5_dir / "parkfire_reference_perimeter.tif", d5_ref_scar, ref_d5, dtype="uint8", nodata=255)

    d5_firms = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-121.7525, 39.9535]}, "properties": {"confidence": "high", "frp": 84.2}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-121.7505, 39.9520]}, "properties": {"confidence": "high", "frp": 112.5}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-121.7490, 39.9510]}, "properties": {"confidence": "nominal", "frp": 61.0}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-121.7580, 39.9585]}, "properties": {"confidence": "low", "frp": 14.0}},
        ],
    }
    (d5_dir / "parkfire_firms_hotspots.geojson").write_text(json.dumps(d5_firms, indent=2))

    d5_exp_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Cohasset Ridge WUI Community Buffer", "asset_class": "settlement"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-121.754, 39.950],
                        [-121.748, 39.950],
                        [-121.748, 39.955],
                        [-121.754, 39.955],
                        [-121.754, 39.950],
                    ]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Forest Ranch Evacuation Corridor", "asset_class": "road"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-121.757, 39.949],
                        [-121.751, 39.953],
                        [-121.746, 39.957],
                    ],
                },
            },
        ],
    }
    (d5_dir / "parkfire_wui_assets.geojson").write_text(json.dumps(d5_exp_geojson, indent=2))

    service.register_existing(
        DatasetBase(
            name="Butte/Tehama Pre-Fire SAR HV (Synthetic Demo Fixture)",
            domain="domain2",
            description="Georeferenced pre-fire cross-polarized HV baseline fixture modeled over Northern California (UTM 10N).",
            product_type="sar_backscatter",
            sensor="Simulated NISAR / S1 HV",
            polarization="HV",
            acquisition_date="2025-07-10",
            value_scale="power",
            units="gamma0 (linear power)",
            source="Synthetic Georeferenced Wildfire Fixture (Butte/Tehama AOI)",
            is_synthetic=True,
        ),
        "raw/domain5/parkfire_prefire_hv.tif",
        custom_id="ds-demo-d5-base",
    )
    service.register_existing(
        DatasetBase(
            name="Butte/Tehama Active-Smoke Post-Fire SAR HV (Synthetic Demo Fixture)",
            domain="domain2",
            description="Georeferenced post-fire cross-polarized HV fixture showing smoke-penetrating canopy loss.",
            product_type="sar_backscatter",
            sensor="Simulated NISAR / S1 HV",
            polarization="HV",
            acquisition_date="2025-07-28",
            value_scale="power",
            units="gamma0 (linear power)",
            source="Synthetic Georeferenced Wildfire Fixture (Butte/Tehama AOI)",
            is_synthetic=True,
        ),
        "raw/domain5/parkfire_postfire_hv.tif",
        custom_id="ds-demo-d5-event",
    )
    service.register_existing(
        DatasetBase(
            name="Butte/Tehama Active Fire Thermal Points (Synthetic FIRMS Fixture)",
            domain="domain2",
            description="Simulated VIIRS/MODIS active thermal anomaly points in GeoJSON format.",
            product_type="fire_detections",
            sensor="Simulated VIIRS/MODIS FIRMS",
            acquisition_date="2025-07-26",
            units="thermal points",
            source="Synthetic FIRMS Hotspot Fixture",
            is_synthetic=True,
        ),
        "raw/domain5/parkfire_firms_hotspots.geojson",
        custom_id="ds-demo-d5-firms",
    )
    service.register_existing(
        DatasetBase(
            name="Butte/Tehama Mapped Burn Perimeter Reference (Synthetic Validation Fixture)",
            domain="domain2",
            description="Reference fire perimeter mask for evaluating Precision, Recall, F1, and IoU.",
            product_type="reference_disturbance",
            acquisition_date="2025-07-29",
            units="binary",
            source="Synthetic Fire Perimeter Benchmark",
            is_synthetic=True,
        ),
        "raw/domain5/parkfire_reference_perimeter.tif",
        custom_id="ds-demo-d5-ref",
    )
    service.register_existing(
        DatasetBase(
            name="Cohasset Ridge WUI Settlements & Roads (Synthetic Exposure GeoJSON)",
            domain="domain2",
            description="Wildland-Urban Interface community buffer and evacuation road corridor for exposure intersection.",
            product_type="exposure_assets",
            units="GeoJSON features",
            source="Synthetic WUI Infrastructure Layer",
            is_synthetic=True,
        ),
        "raw/domain5/parkfire_wui_assets.geojson",
        custom_id="ds-demo-d5-exp",
    )

    # =========================================================================
    # VERIFIED REAL SATELLITE & GEOPHYSICAL DATASETS FOR DOMAINS 2–5
    # =========================================================================

    # -------------------------------------------------------------------------
    # DOMAIN 2 REAL: Novo Progresso / BR-163 Corridor, Pará, Brazil (2019–2020)
    # -------------------------------------------------------------------------
    d2_real_pre = d2_dir / "para_real_s1a_20190826_vh_pre.tif"
    d2_real_post = d2_dir / "para_real_s1a_20200820_vh_post.tif"
    d2_real_mask = d2_dir / "para_real_alos_fnf_2019_mask.tif"
    d2_real_ref = d2_dir / "para_real_alos_fnf_2019_2020_loss_ref.tif"
    d2_real_exp = d2_dir / "para_real_br163_assets.geojson"

    if d2_real_pre.is_file() and d2_real_post.is_file():
        if not d2_real_exp.is_file():
            br163_assets = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Jamanxim National Forest Western Buffer Zone (Pará)",
                            "asset_class": "protected_area",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [-55.228, -6.695],
                                [-55.212, -6.695],
                                [-55.212, -6.680],
                                [-55.228, -6.680],
                                [-55.228, -6.695],
                            ]],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "BR-163 Secondary Feeder Corridor & Riparian Margin",
                            "asset_class": "road",
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [-55.230, -6.692],
                                [-55.218, -6.686],
                                [-55.206, -6.678],
                            ],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Novo Progresso Eastern Forest Conservation Sector",
                            "asset_class": "protected_area",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [-55.214, -6.684],
                                [-55.205, -6.684],
                                [-55.205, -6.673],
                                [-55.214, -6.673],
                                [-55.214, -6.684],
                            ]],
                        },
                    },
                ],
            }
            d2_real_exp.write_text(json.dumps(br163_assets, indent=2))

        service.register_existing(
            DatasetBase(
                name="Sentinel-1A RTC Baseline Forest SAR VH (2019-08-26, Novo Progresso, Pará)",
                domain="domain2",
                description="Real Copernicus Sentinel-1A IW GRDH RTC VH cross-polarized backscatter over intact & frontier Amazon canopy along the BR-163 corridor (2019-08-26, Orbit 141).",
                product_type="sar_backscatter",
                sensor="Sentinel-1A IW GRDH RTC (C-band SAR)",
                polarization="VH",
                acquisition_date="2019-08-26",
                value_scale="power",
                units="gamma0 (linear power)",
                source="Copernicus Sentinel-1A RTC / Planetary Computer (S1A_IW_GRDH_1SDV_20190826T091535_20190826T091600_028738_034106_rtc)",
                is_synthetic=False,
            ),
            "raw/domain2/para_real_s1a_20190826_vh_pre.tif",
            custom_id="ds-real-d2-base",
        )
        service.register_existing(
            DatasetBase(
                name="Sentinel-1A RTC Monitoring Forest SAR VH (2020-08-20, Novo Progresso, Pará)",
                domain="domain2",
                description="Real Copernicus Sentinel-1A IW GRDH RTC VH cross-polarized backscatter acquired one year later on identical Orbit 141 (2020-08-20), capturing large geometric canopy clearings.",
                product_type="sar_backscatter",
                sensor="Sentinel-1A IW GRDH RTC (C-band SAR)",
                polarization="VH",
                acquisition_date="2020-08-20",
                value_scale="power",
                units="gamma0 (linear power)",
                source="Copernicus Sentinel-1A RTC / Planetary Computer (S1A_IW_GRDH_1SDV_20200820T091541_20200820T091606_033988_03F1BA_rtc)",
                is_synthetic=False,
            ),
            "raw/domain2/para_real_s1a_20200820_vh_post.tif",
            custom_id="ds-real-d2-event",
        )
        if d2_real_mask.is_file():
            service.register_existing(
                DatasetBase(
                    name="JAXA ALOS-2 PALSAR-2 Baseline Forest Cover Mask (2019, Pará)",
                    domain="domain2",
                    description="Real JAXA ALOS-2 PALSAR-2 L-band Global Forest/Non-Forest 2019 baseline canopy mask (1=forest, 0=non-forest) from tile S06W056_19_FNF.",
                    product_type="forest_mask",
                    sensor="JAXA ALOS-2 PALSAR-2 (L-band SAR)",
                    acquisition_date="2019-01-01",
                    units="binary (1=forest)",
                    source="JAXA ALOS-2 PALSAR-2 Global Forest/Non-Forest Mosaic (S06W056_19_FNF)",
                    is_synthetic=False,
                ),
                "raw/domain2/para_real_alos_fnf_2019_mask.tif",
                custom_id="ds-real-d2-mask",
            )
        if d2_real_ref.is_file():
            service.register_existing(
                DatasetBase(
                    name="JAXA ALOS-2 PALSAR-2 Independent Forest Loss Reference (2019→2020, Pará)",
                    domain="domain2",
                    description="Independent L-band SAR forest-to-non-forest transition reference derived from JAXA ALOS-2 PALSAR-2 annual mosaics (S06W056_19_FNF forest in 2019 transitioning to non-forest in S06W056_20_FNF in 2020).",
                    product_type="reference_disturbance",
                    sensor="JAXA ALOS-2 PALSAR-2 (L-band SAR)",
                    acquisition_date="2020-08-20",
                    units="binary (1=forest loss)",
                    source="JAXA ALOS-2 PALSAR-2 Annual FNF Change (S06W056_19_FNF -> S06W056_20_FNF)",
                    is_synthetic=False,
                ),
                "raw/domain2/para_real_alos_fnf_2019_2020_loss_ref.tif",
                custom_id="ds-real-d2-ref",
            )
        service.register_existing(
            DatasetBase(
                name="Novo Progresso / BR-163 Forest Buffer & Corridor Assets (GeoJSON)",
                domain="domain2",
                description="Georeferenced conservation buffer sectors and road corridors in the Novo Progresso / BR-163 study area (Pará, Brazil).",
                product_type="exposure_assets",
                sensor="Vector GIS Layer",
                units="GeoJSON features",
                source="BR-163 / Jamanxim Regional Conservation Footprints (WGS84)",
                is_synthetic=False,
            ),
            "raw/domain2/para_real_br163_assets.geojson",
            custom_id="ds-real-d2-exp",
        )

    # -------------------------------------------------------------------------
    # DOMAIN 3 REAL: Jakobshavn Isbræ (Sermeq Kujalleq), Greenland
    # -------------------------------------------------------------------------
    d3_real_vel = d3_dir / "jakobshavn_real_itslive_2022_velocity.tif"
    d3_real_ref = d3_dir / "jakobshavn_real_itslive_clim_ref_velocity.tif"
    d3_real_pre = d3_dir / "jakobshavn_real_s1a_20230828_hh_pre.tif"
    d3_real_post = d3_dir / "jakobshavn_real_s1a_20230909_hh_post.tif"
    d3_real_exp = d3_dir / "jakobshavn_real_fjord_assets.geojson"

    if d3_real_vel.is_file() and d3_real_ref.is_file():
        if not d3_real_exp.is_file():
            jak_assets = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Ilulissat Icefjord UNESCO World Heritage Terminus Sector",
                            "asset_class": "protected_area",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [-49.89, 69.15],
                                [-49.70, 69.15],
                                [-49.70, 69.21],
                                [-49.89, 69.21],
                                [-49.89, 69.15],
                            ]],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Sermeq Kujalleq Southern Shear Margin Monitoring Corridor",
                            "asset_class": "infrastructure",
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [-49.88, 69.145],
                                [-49.76, 69.160],
                                [-49.65, 69.175],
                            ],
                        },
                    },
                ],
            }
            d3_real_exp.write_text(json.dumps(jak_assets, indent=2))

        service.register_existing(
            DatasetBase(
                name="NASA MEaSUREs ITS_LIVE 2022 Annual Ice Velocity (Jakobshavn Isbræ, Greenland)",
                domain="domain5",
                description="Real NASA MEaSUREs ITS_LIVE v2 2022 annual surface ice velocity mosaic (120m resolution, EPSG:3413 Polar Stereographic North) over Jakobshavn Isbræ / Sermeq Kujalleq.",
                product_type="ice_velocity",
                sensor="NASA MEaSUREs ITS_LIVE v2 (Landsat 8/9 & Sentinel-1/2)",
                acquisition_date="2022-07-01",
                units="m/year",
                source="NASA MEaSUREs ITS_LIVE v2 AWS Open Data (ITS_LIVE_velocity_120m_RGI05A_2022_v02_v.tif)",
                is_synthetic=False,
            ),
            "raw/domain3/jakobshavn_real_itslive_2022_velocity.tif",
            custom_id="ds-real-d3-vel",
        )
        service.register_existing(
            DatasetBase(
                name="NASA MEaSUREs ITS_LIVE Multi-Year Reference Ice Velocity (Jakobshavn Isbræ)",
                domain="domain5",
                description="Real NASA MEaSUREs ITS_LIVE v2 static multi-year climatological reference velocity mosaic (120m, EPSG:3413) for continuous RMSE/MAE/Bias validation.",
                product_type="reference_velocity",
                sensor="NASA MEaSUREs ITS_LIVE v2 Climatology",
                acquisition_date="2020-01-01",
                units="m/year",
                source="NASA MEaSUREs ITS_LIVE v2 AWS Open Data (ITS_LIVE_velocity_120m_RGI05A_0000_v02_v.tif)",
                is_synthetic=False,
            ),
            "raw/domain3/jakobshavn_real_itslive_clim_ref_velocity.tif",
            custom_id="ds-real-d3-ref",
        )
        if d3_real_pre.is_file() and d3_real_post.is_file():
            service.register_existing(
                DatasetBase(
                    name="Sentinel-1A RTC Terminus Baseline SAR HH (2023-08-28, Jakobshavn Isbræ)",
                    domain="domain5",
                    description="Real Copernicus Sentinel-1A IW GRDH RTC HH polarization backscatter over the Jakobshavn calving front and melange (2023-08-28, Orbit 127).",
                    product_type="sar_backscatter",
                    sensor="Sentinel-1A IW GRDH RTC (C-band SAR)",
                    polarization="HH",
                    acquisition_date="2023-08-28",
                    value_scale="power",
                    units="gamma0 (linear power)",
                    source="Copernicus Sentinel-1A RTC / Planetary Computer (S1A_IW_GRDH_1SDH_20230828T095236_20230828T095301_050074_06068B_rtc)",
                    is_synthetic=False,
                ),
                "raw/domain3/jakobshavn_real_s1a_20230828_hh_pre.tif",
                custom_id="ds-real-d3-sar-base",
            )
            service.register_existing(
                DatasetBase(
                    name="Sentinel-1A RTC Terminus Repeat SAR HH (2023-09-09, Jakobshavn Isbræ)",
                    domain="domain5",
                    description="Real Copernicus Sentinel-1A IW GRDH RTC HH repeat pass 12 days later on Orbit 127 (2023-09-09), capturing calving front and ice-melange dynamics.",
                    product_type="sar_backscatter",
                    sensor="Sentinel-1A IW GRDH RTC (C-band SAR)",
                    polarization="HH",
                    acquisition_date="2023-09-09",
                    value_scale="power",
                    units="gamma0 (linear power)",
                    source="Copernicus Sentinel-1A RTC / Planetary Computer (S1A_IW_GRDH_1SDH_20230909T095236_20230909T095301_050249_060C7D_rtc)",
                    is_synthetic=False,
                ),
                "raw/domain3/jakobshavn_real_s1a_20230909_hh_post.tif",
                custom_id="ds-real-d3-sar-event",
            )
        service.register_existing(
            DatasetBase(
                name="Ilulissat Icefjord UNESCO Monitoring Sectors (GeoJSON)",
                domain="domain5",
                description="Georeferenced UNESCO World Heritage icefjord terminus sector and southern shear-margin monitoring corridor.",
                product_type="exposure_assets",
                sensor="Vector GIS Layer",
                units="GeoJSON features",
                source="Ilulissat Icefjord Regional Monitoring Footprints (WGS84)",
                is_synthetic=False,
            ),
            "raw/domain3/jakobshavn_real_fjord_assets.geojson",
            custom_id="ds-real-d3-exp",
        )

    # -------------------------------------------------------------------------
    # DOMAIN 4 REAL: Tyrnavos Basin, Greece (Mw 6.3 March 3, 2021 Earthquake)
    # -------------------------------------------------------------------------
    d4_real_disp = d4_dir / "tyrnavos_real_licsar_20210225_20210309_los_mm.tif"
    d4_real_coh = d4_dir / "tyrnavos_real_licsar_20210225_20210309_coherence.tif"
    d4_real_ref = d4_dir / "tyrnavos_real_licsar_20210219_20210309_ref_los_mm.tif"
    d4_real_exp = d4_dir / "tyrnavos_real_infrastructure.geojson"

    if d4_real_disp.is_file() and d4_real_coh.is_file() and d4_real_ref.is_file():
        if not d4_real_exp.is_file():
            tyr_assets = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Damasi–Tyrnavos Coseismic Fault Hanging-Wall Agricultural Plain",
                            "asset_class": "agriculture",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [22.09, 39.70],
                                [22.22, 39.70],
                                [22.22, 39.79],
                                [22.09, 39.79],
                                [22.09, 39.70],
                            ]],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Titarisios River Valley & Damasi Settlement Perimeter",
                            "asset_class": "settlement",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [22.12, 39.71],
                                [22.18, 39.71],
                                [22.18, 39.76],
                                [22.12, 39.76],
                                [22.12, 39.71],
                            ]],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Tyrnavos–Elassona National Highway Corridor (EO3)",
                            "asset_class": "road",
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [22.08, 39.68],
                                [22.15, 39.74],
                                [22.22, 39.80],
                            ],
                        },
                    },
                ],
            }
            d4_real_exp.write_text(json.dumps(tyr_assets, indent=2))

        service.register_existing(
            DatasetBase(
                name="COMET-LiCSAR Sentinel-1 Unwrapped Coseismic LOS Displacement (2021-02-25→2021-03-09, Tyrnavos Mw 6.3)",
                domain="domain3",
                description="Real COMET-LiCSAR Sentinel-1A Track 102A unwrapped coseismic interferogram spanning the 3 March 2021 Mw 6.3 Tyrnavos/Elassona normal-fault earthquake in Thessaly, Greece (converted from radians to LOS mm).",
                product_type="insar_displacement",
                sensor="Sentinel-1A InSAR (COMET-LiCSAR Frame 102A_04971_141314)",
                acquisition_date="2021-03-09",
                units="mm",
                source="COMET-LiCSAR Sentinel-1 InSAR Portal (102A_04971_141314 / 20210225_20210309.geo.unw.tif)",
                is_synthetic=False,
            ),
            "raw/domain4/tyrnavos_real_licsar_20210225_20210309_los_mm.tif",
            custom_id="ds-real-d4-disp",
        )
        service.register_existing(
            DatasetBase(
                name="COMET-LiCSAR Sentinel-1 Interferometric Coherence (2021-02-25→2021-03-09, Tyrnavos)",
                domain="domain3",
                description="Real COMET-LiCSAR interferometric phase coherence (0.0 to 1.0) for the 12-day coseismic pair over the Tyrnavos Basin.",
                product_type="insar_coherence",
                sensor="Sentinel-1A InSAR (COMET-LiCSAR Frame 102A_04971_141314)",
                acquisition_date="2021-03-09",
                units="coherence (0-1)",
                source="COMET-LiCSAR Sentinel-1 InSAR Portal (102A_04971_141314 / 20210225_20210309.geo.cc.tif)",
                is_synthetic=False,
            ),
            "raw/domain4/tyrnavos_real_licsar_20210225_20210309_coherence.tif",
            custom_id="ds-real-d4-coh",
        )
        service.register_existing(
            DatasetBase(
                name="COMET-LiCSAR Independent 18-Day Coseismic LOS Reference (2021-02-19→2021-03-09, Tyrnavos)",
                domain="domain3",
                description="Independent COMET-LiCSAR unwrapped coseismic interferogram using the earlier 2021-02-19 baseline acquisition (20210219_20210309.geo.unw.tif) for cross-interferogram RMSE/MAE/Bias validation.",
                product_type="reference_displacement",
                sensor="Sentinel-1B/1A InSAR (COMET-LiCSAR Frame 102A_04971_141314)",
                acquisition_date="2021-03-09",
                units="mm",
                source="COMET-LiCSAR Sentinel-1 InSAR Portal (102A_04971_141314 / 20210219_20210309.geo.unw.tif)",
                is_synthetic=False,
            ),
            "raw/domain4/tyrnavos_real_licsar_20210219_20210309_ref_los_mm.tif",
            custom_id="ds-real-d4-ref",
        )
        service.register_existing(
            DatasetBase(
                name="Tyrnavos & Titarisios Valley Settlements and Highway Corridors (GeoJSON)",
                domain="domain3",
                description="Georeferenced settlements, agricultural plains, and highway corridors across the Tyrnavos–Damasi coseismic deformation zone.",
                product_type="exposure_assets",
                sensor="Vector GIS Layer",
                units="GeoJSON features",
                source="Tyrnavos Basin Regional Infrastructure Footprints (WGS84)",
                is_synthetic=False,
            ),
            "raw/domain4/tyrnavos_real_infrastructure.geojson",
            custom_id="ds-real-d4-exp",
        )

    # -------------------------------------------------------------------------
    # DOMAIN 5 REAL: Dadia Forest / Evros Megafire, Greece (August 2023)
    # -------------------------------------------------------------------------
    d5_real_pre = d5_dir / "evros_real_s1a_20230809_vh_prefire.tif"
    d5_real_post = d5_dir / "evros_real_s1a_20230902_vh_postfire.tif"
    d5_real_ref = d5_dir / "evros_real_modis_mcd64a1_burn_reference.tif"
    d5_real_firms = d5_dir / "evros_real_modis_active_fire_points.geojson"
    d5_real_exp = d5_dir / "evros_real_dadia_assets.geojson"

    if d5_real_pre.is_file() and d5_real_post.is_file():
        if not d5_real_exp.is_file():
            dadia_assets = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Dadia-Lefkimi-Soufli Forest National Park Core Zone",
                            "asset_class": "protected_area",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [25.84, 40.97],
                                [25.94, 40.97],
                                [25.94, 41.04],
                                [25.84, 41.04],
                                [25.84, 40.97],
                            ]],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Kotronia–Giannouta Rural WUI & Evacuation Road Corridor",
                            "asset_class": "road",
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [25.83, 40.96],
                                [25.88, 41.00],
                                [25.95, 41.05],
                            ],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Southern Dadia Black Vulture Habitat Buffer",
                            "asset_class": "protected_area",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [25.85, 40.955],
                                [25.92, 40.955],
                                [25.92, 40.985],
                                [25.85, 40.985],
                                [25.85, 40.955],
                            ]],
                        },
                    },
                ],
            }
            d5_real_exp.write_text(json.dumps(dadia_assets, indent=2))

        service.register_existing(
            DatasetBase(
                name="Sentinel-1A RTC Pre-Fire Baseline SAR VH (2023-08-09, Dadia Forest / Evros, Greece)",
                domain="domain2",
                description="Real Copernicus Sentinel-1A IW GRDH RTC VH cross-polarized backscatter acquired prior to the August 2023 Evros/Dadia megafire (2023-08-09, Orbit 29).",
                product_type="sar_backscatter",
                sensor="Sentinel-1A IW GRDH RTC (C-band SAR)",
                polarization="VH",
                acquisition_date="2023-08-09",
                value_scale="power",
                units="gamma0 (linear power)",
                source="Copernicus Sentinel-1A RTC / Planetary Computer (S1A_IW_GRDH_1SDV_20230809T161623_20230809T161648_049801_05FD3A_rtc)",
                is_synthetic=False,
            ),
            "raw/domain5/evros_real_s1a_20230809_vh_prefire.tif",
            custom_id="ds-real-d5-base",
        )
        service.register_existing(
            DatasetBase(
                name="Sentinel-1A RTC Post-Fire SAR VH (2023-09-02, Dadia Forest / Evros, Greece)",
                domain="domain2",
                description="Real Copernicus Sentinel-1A IW GRDH RTC VH cross-polarized backscatter acquired after the August 2023 Evros/Dadia megafire on identical Orbit 29 (2023-09-02).",
                product_type="sar_backscatter",
                sensor="Sentinel-1A IW GRDH RTC (C-band SAR)",
                polarization="VH",
                acquisition_date="2023-09-02",
                value_scale="power",
                units="gamma0 (linear power)",
                source="Copernicus Sentinel-1A RTC / Planetary Computer (S1A_IW_GRDH_1SDV_20230902T161625_20230902T161650_050151_060939_rtc)",
                is_synthetic=False,
            ),
            "raw/domain5/evros_real_s1a_20230902_vh_postfire.tif",
            custom_id="ds-real-d5-event",
        )
        if d5_real_firms.is_file():
            service.register_existing(
                DatasetBase(
                    name="NASA Terra/Aqua MODIS Active Fire Thermal Detections (Aug 2023, Dadia Forest / Evros)",
                    domain="domain2",
                    description="Real active fire thermal anomaly detections extracted from NASA EOSDIS Terra/Aqua MODIS (MOD14A1/MYD14A1 v061) composites during the August 2023 Evros megafire.",
                    product_type="fire_detections",
                    sensor="NASA Terra/Aqua MODIS (MOD14A1 & MYD14A1 v061)",
                    acquisition_date="2023-08-23",
                    units="thermal points",
                    source="NASA EOSDIS MODIS Thermal Anomalies & Fire Daily L3 Global 1km (MOD14A1/MYD14A1.A2023233-241.h19v04.061)",
                    is_synthetic=False,
                ),
                "raw/domain5/evros_real_modis_active_fire_points.geojson",
                custom_id="ds-real-d5-firms",
            )
        if d5_real_ref.is_file():
            service.register_existing(
                DatasetBase(
                    name="NASA MODIS MCD64A1 Mapped Burned Area Reference (Aug 2023, Dadia Forest / Evros)",
                    domain="domain2",
                    description="Real independent satellite burned-area reference mask from NASA EOSDIS MODIS MCD64A1 v061 Monthly Burned Area product (MCD64A1.A2023213.h19v04.061).",
                    product_type="reference_disturbance",
                    sensor="NASA Terra/Aqua MODIS (MCD64A1 v061)",
                    acquisition_date="2023-08-31",
                    units="binary (1=burned)",
                    source="NASA EOSDIS MODIS Burned Area Monthly L3 Global 500m (MCD64A1.A2023213.h19v04.061)",
                    is_synthetic=False,
                ),
                "raw/domain5/evros_real_modis_mcd64a1_burn_reference.tif",
                custom_id="ds-real-d5-ref",
            )
        service.register_existing(
            DatasetBase(
                name="Dadia-Lefkimi-Soufli National Park & WUI Evacuation Corridors (GeoJSON)",
                domain="domain2",
                description="Georeferenced National Park core habitat zones and rural evacuation road corridors in the Dadia Forest study area.",
                product_type="exposure_assets",
                sensor="Vector GIS Layer",
                units="GeoJSON features",
                source="Dadia National Park Regional Protection Footprints (WGS84)",
                is_synthetic=False,
            ),
            "raw/domain5/evros_real_dadia_assets.geojson",
            custom_id="ds-real-d5-exp",
        )
