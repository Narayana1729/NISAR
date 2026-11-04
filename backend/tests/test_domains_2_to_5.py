import json
import pytest
import numpy as np
from pathlib import Path
from affine import Affine
from rasterio.crs import CRS
from fastapi.testclient import TestClient

from app.main import app
from app.utils.raster import RasterData, write_geotiff
from app.database.connection import SessionLocal
from app.database.models import DatasetModel

client = TestClient(app)


@pytest.fixture(scope="module")
def staged_domains_2_to_5_data():
    """Generates synthetic and georeferenced test datasets for Domains 2 through 5."""
    db = SessionLocal()
    transform = Affine(10.0, 0.0, 500000.0, 0.0, -10.0, 4000000.0)
    crs = CRS.from_epsg(32632)

    # Clean existing test datasets if any
    test_ids = [
        "ds-test-d2-base", "ds-test-d2-event", "ds-test-d2-mask",
        "ds-test-d3-vel", "ds-test-d3-sar-base", "ds-test-d3-sar-event",
        "ds-test-d4-disp", "ds-test-d4-coh",
        "ds-test-d5-base", "ds-test-d5-event", "ds-test-d5-firms",
    ]
    db.query(DatasetModel).filter(DatasetModel.id.in_(test_ids)).delete(synchronize_session=False)
    db.commit()

    # --- Domain 2: Forests ---
    d2_dir = Path("data/raw/domain2")
    d2_dir.mkdir(parents=True, exist_ok=True)

    # Baseline forest: high HV volume backscatter (-12 dB ~ 0.063 power)
    base_arr = np.full((30, 30), 0.063, dtype="float32")
    ref_d2 = RasterData(array=base_arr, transform=transform, crs=crs, width=30, height=30)
    write_geotiff(d2_dir / "test_forest_base.tif", base_arr, ref_d2, dtype="float32", nodata=-9999.0)

    # Event forest: 10x10 clearing in center drops to -18 dB ~ 0.0158 power (drop > 5.5 dB)
    event_arr = base_arr.copy()
    event_arr[10:20, 10:20] = 0.0158
    write_geotiff(d2_dir / "test_forest_event.tif", event_arr, ref_d2, dtype="float32", nodata=-9999.0)

    # Forest mask: 1 across most, 0 in first 5 rows
    mask_arr = np.ones((30, 30), dtype="uint8")
    mask_arr[:5, :] = 0
    write_geotiff(d2_dir / "test_forest_mask.tif", mask_arr, ref_d2, dtype="uint8", nodata=0)

    db.add_all([
        DatasetModel(
            id="ds-test-d2-base",
            name="Test Forest Baseline HV",
            domain="domain2",
            product_type="sar_backscatter",
            polarization="HV",
            value_scale="power",
            relative_path="raw/domain2/test_forest_base.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
        DatasetModel(
            id="ds-test-d2-event",
            name="Test Forest Monitoring HV",
            domain="domain2",
            product_type="sar_backscatter",
            polarization="HV",
            value_scale="power",
            relative_path="raw/domain2/test_forest_event.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
        DatasetModel(
            id="ds-test-d2-mask",
            name="Test Forest Reference Mask",
            domain="domain2",
            product_type="forest_mask",
            relative_path="raw/domain2/test_forest_mask.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
    ])

    # --- Domain 3: Cryosphere ---
    d3_dir = Path("data/raw/domain3")
    d3_dir.mkdir(parents=True, exist_ok=True)

    # Ice velocity: slow flow (50 m/yr) with fast central outlet stream (600 m/yr)
    vel_arr = np.full((30, 30), 50.0, dtype="float32")
    vel_arr[:, 12:18] = 600.0  # Fast ice stream
    ref_d3 = RasterData(array=vel_arr, transform=transform, crs=crs, width=30, height=30)
    write_geotiff(d3_dir / "test_ice_velocity.tif", vel_arr, ref_d3, dtype="float32", nodata=-9999.0)

    # Terminus SAR pair
    base_sar = np.full((30, 30), 0.05, dtype="float32")
    event_sar = base_sar.copy()
    event_sar[25:, :] = 0.005  # Calving retreat / water drop
    write_geotiff(d3_dir / "test_terminus_base.tif", base_sar, ref_d3, dtype="float32", nodata=-9999.0)
    write_geotiff(d3_dir / "test_terminus_event.tif", event_sar, ref_d3, dtype="float32", nodata=-9999.0)

    db.add_all([
        DatasetModel(
            id="ds-test-d3-vel",
            name="Test Ice Velocity ITS_LIVE",
            domain="domain5",
            product_type="ice_velocity",
            units="m/year",
            relative_path="raw/domain3/test_ice_velocity.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
        DatasetModel(
            id="ds-test-d3-sar-base",
            name="Test Terminus Pre-Calving SAR",
            domain="domain5",
            product_type="sar_backscatter",
            relative_path="raw/domain3/test_terminus_base.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
        DatasetModel(
            id="ds-test-d3-sar-event",
            name="Test Terminus Post-Calving SAR",
            domain="domain5",
            product_type="sar_backscatter",
            relative_path="raw/domain3/test_terminus_event.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
    ])

    # --- Domain 4: Land Movement ---
    d4_dir = Path("data/raw/domain4")
    d4_dir.mkdir(parents=True, exist_ok=True)

    # Displacement raster: stable (+1 mm/yr) with a subsidence bowl (-35 mm/yr) in center
    disp_arr = np.full((30, 30), 1.0, dtype="float32")
    disp_arr[10:20, 10:20] = -35.0  # Subsiding bowl
    ref_d4 = RasterData(array=disp_arr, transform=transform, crs=crs, width=30, height=30)
    write_geotiff(d4_dir / "test_insar_disp.tif", disp_arr, ref_d4, dtype="float32", nodata=-9999.0)

    # Coherence raster: high (0.85) everywhere except outer edge (0.15)
    coh_arr = np.full((30, 30), 0.85, dtype="float32")
    coh_arr[0, :] = 0.15
    write_geotiff(d4_dir / "test_insar_coh.tif", coh_arr, ref_d4, dtype="float32", nodata=-9999.0)

    db.add_all([
        DatasetModel(
            id="ds-test-d4-disp",
            name="Test InSAR Displacement LOS",
            domain="domain3",
            product_type="insar_displacement",
            units="mm/yr",
            relative_path="raw/domain4/test_insar_disp.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
        DatasetModel(
            id="ds-test-d4-coh",
            name="Test InSAR Coherence Mask",
            domain="domain3",
            product_type="insar_coherence",
            relative_path="raw/domain4/test_insar_coh.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
    ])

    # --- Domain 5: Wildfires ---
    d5_dir = Path("data/raw/domain5")
    d5_dir.mkdir(parents=True, exist_ok=True)

    # Pre-fire: intact canopy HV (-13 dB ~ 0.05 power)
    fire_base = np.full((30, 30), 0.05, dtype="float32")
    ref_d5 = RasterData(array=fire_base, transform=transform, crs=crs, width=30, height=30)
    write_geotiff(d5_dir / "test_fire_base.tif", fire_base, ref_d5, dtype="float32", nodata=-9999.0)

    # Post-fire: burn scar in rows 10:20, cols 10:20 (-19 dB ~ 0.0125 power, drop > 6 dB)
    fire_event = fire_base.copy()
    fire_event[10:20, 10:20] = 0.0125
    write_geotiff(d5_dir / "test_fire_event.tif", fire_event, ref_d5, dtype="float32", nodata=-9999.0)

    # FIRMS GeoJSON points inside the scar: pixel (15, 15) in EPSG:32632 is:
    # x = 500000 + 15 * 10 = 500150
    # y = 4000000 - 15 * 10 = 3999850
    # In WGS84 (lon, lat) around UTM zone 32N: approx lon 9.0019, lat 36.1437
    # Note: lonlat_to_pixel transforms from lon, lat into dataset CRS.
    firms_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [9.0019, 36.1437]
                },
                "properties": {
                    "confidence": "high",
                    "brightness": 345.2,
                    "instrument": "VIIRS"
                }
            }
        ]
    }
    firms_path = d5_dir / "test_firms.geojson"
    firms_path.write_text(json.dumps(firms_geojson))

    db.add_all([
        DatasetModel(
            id="ds-test-d5-base",
            name="Test Wildfire Pre-Fire HV",
            domain="domain2",
            product_type="sar_backscatter",
            polarization="HV",
            value_scale="power",
            relative_path="raw/domain5/test_fire_base.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
        DatasetModel(
            id="ds-test-d5-event",
            name="Test Wildfire Post-Fire HV",
            domain="domain2",
            product_type="sar_backscatter",
            polarization="HV",
            value_scale="power",
            relative_path="raw/domain5/test_fire_event.tif",
            format="GeoTIFF",
            crs="EPSG:32632",
            is_synthetic=True,
        ),
        DatasetModel(
            id="ds-test-d5-firms",
            name="Test NASA FIRMS Thermal Hotspots",
            domain="domain2",
            product_type="fire_detections",
            relative_path="raw/domain5/test_firms.geojson",
            format="GeoJSON",
            is_synthetic=True,
        ),
    ])

    db.commit()
    db.close()
    yield


def test_domain2_forests_pipeline(staged_domains_2_to_5_data):
    """Domain 2: Verify forest disturbance calculation and optional forest mask integration."""
    payload = {
        "inputs": {
            "baseline": "ds-test-d2-base",
            "event": "ds-test-d2-event",
            "forest_mask": "ds-test-d2-mask",
        },
        "parameters": {
            "min_drop_db": 3.0,
            "filter_window": 3,
            "min_cluster_pixels": 4,
        }
    }
    res = client.post("/api/domains/domain2/process", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["domain"] == "domain2"
    assert data["status"] == "completed"
    assert data["is_synthetic_input"] is True

    # 10x10 pixels disturbed = 100 pixels * 100 m² = 10,000 m² = 1.0 hectare
    disturbed_metric = next((m for m in data["summary_metrics"] if m["label"] == "Potential Disturbance"), None)
    assert disturbed_metric is not None
    assert float(disturbed_metric["value"]) == pytest.approx(1.0, rel=0.1)

    # Check that disturbance overlay layer exists and is valid PNG
    overlay = next(l for l in data["layers"] if l["key"] == "disturbance_overlay")
    img_res = client.get(overlay["url"])
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/png"


def test_domain5_cryosphere_pipeline(staged_domains_2_to_5_data):
    """Domain 5: Verify ice velocity heatmap and terminus comparison generation."""
    payload = {
        "inputs": {
            "velocity": "ds-test-d3-vel",
            "baseline_sar": "ds-test-d3-sar-base",
            "event_sar": "ds-test-d3-sar-event",
        },
        "parameters": {
            "v_max_display": 1000.0,
            "fast_ice_threshold": 300.0,
        }
    }
    res = client.post("/api/domains/domain5/process", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["domain"] == "domain5"
    assert data["status"] == "completed"

    peak_vel = next((m for m in data["summary_metrics"] if m["label"] == "Peak Flow Velocity"), None)
    assert peak_vel is not None
    assert float(peak_vel["value"]) == 600.0

    # Fast ice percentage: 6 cols out of 30 = 20.0%
    fast_pct = next((m for m in data["summary_metrics"] if m["label"] == "Fast Streaming Zone"), None)
    assert fast_pct is not None
    assert float(fast_pct["value"]) == pytest.approx(20.0, rel=0.05)

    # Check velocity heatmap layer
    vel_preview = next(l for l in data["layers"] if l["key"] == "velocity_preview")
    img_res = client.get(vel_preview["url"])
    assert img_res.status_code == 200


def test_domain3_land_movement_pipeline(staged_domains_2_to_5_data):
    """Domain 3: Verify InSAR displacement filtering, coherence masking, and subsidence bowl calculation."""
    payload = {
        "inputs": {
            "displacement": "ds-test-d4-disp",
            "coherence": "ds-test-d4-coh",
        },
        "parameters": {
            "min_coherence": 0.4,
            "subsidence_threshold_mm": -15.0,
            "color_stretch_mm": 50.0,
        }
    }
    res = client.post("/api/domains/domain3/process", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["domain"] == "domain3"
    assert data["status"] == "completed"

    peak_sub = next((m for m in data["summary_metrics"] if m["label"] == "Peak Subsidence"), None)
    assert peak_sub is not None
    assert float(peak_sub["value"]) == -35.0

    # Subsidence bowl area: 10x10 pixels = 10,000 m² = 0.01 km²
    bowl_metric = next((m for m in data["summary_metrics"] if m["label"] == "Subsidence Hotspot Area"), None)
    assert bowl_metric is not None
    assert float(bowl_metric["value"]) == pytest.approx(0.01, rel=0.1)

    disp_preview = next(l for l in data["layers"] if l["key"] == "displacement_preview")
    img_res = client.get(disp_preview["url"])
    assert img_res.status_code == 200


def test_domain2_wildfires_pipeline(staged_domains_2_to_5_data):
    """Domain 2: Verify wildfire disturbance detection and NASA FIRMS thermal point intersection."""
    payload = {
        "inputs": {
            "baseline": "ds-test-d5-base",
            "event": "ds-test-d5-event",
            "fire_detections": "ds-test-d5-firms",
        },
        "parameters": {
            "min_drop_db": 3.0,
            "filter_window": 3,
            "min_cluster_pixels": 4,
        }
    }
    res = client.post("/api/domains/domain2/process", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["domain"] == "domain2"
    assert data["status"] == "completed"

    scar_metric = next((m for m in data["summary_metrics"] if m["label"] == "Potential Disturbance"), None)
    assert scar_metric is not None
    # 10x10 pixels = 10,000 m² = 1.0 ha
    assert float(scar_metric["value"]) == pytest.approx(1.0, rel=0.1)

    # Check disturbance overlay
    scar_overlay = next(l for l in data["layers"] if l["key"] == "disturbance_overlay")
    img_res = client.get(scar_overlay["url"])
    assert img_res.status_code == 200
