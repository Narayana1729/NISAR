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

@pytest.fixture
def synthetic_flood_datasets(tmp_path):
    """Generates synthetic test GeoTIFF rasters for unit testing the flood pipeline slice."""
    data_dir = Path("data/raw/domain1")
    data_dir.mkdir(parents=True, exist_ok=True)

    base_file = data_dir / "test_flood_base.tif"
    event_file = data_dir / "test_flood_event.tif"

    # 20x20 grid, 10m pixels
    transform = Affine(10.0, 0.0, 500000.0, 0.0, -10.0, 4000000.0)
    crs = CRS.from_epsg(32632)

    # Baseline: dry land (around -10 dB = 0.1 power)
    base_arr = np.full((20, 20), 0.1, dtype="float32")
    # Add a permanent river channel in row 0: (power 0.005 = -23 dB)
    base_arr[0, :] = 0.005
    ref_d = RasterData(array=base_arr, transform=transform, crs=crs, width=20, height=20)
    write_geotiff(base_file, base_arr, ref_d, dtype="float32", nodata=-9999.0)

    # Event: Flood occurs in central block rows 5:15, cols 5:15 (drops to 0.005 = -23 dB)
    event_arr = base_arr.copy()
    event_arr[5:15, 5:15] = 0.005
    write_geotiff(event_file, event_arr, ref_d, dtype="float32", nodata=-9999.0)

    # Register in DB
    db = SessionLocal()
    ds_base = DatasetModel(
        id="ds-test-base-flood",
        name="Synthetic Pre-Flood Baseline",
        domain="domain1",
        product_type="sar_backscatter",
        value_scale="power",
        relative_path="raw/domain1/test_flood_base.tif",
        format="GeoTIFF",
        crs="EPSG:32632",
        is_synthetic=True
    )
    ds_event = DatasetModel(
        id="ds-test-event-flood",
        name="Synthetic Post-Flood Crisis",
        domain="domain1",
        product_type="sar_backscatter",
        value_scale="power",
        relative_path="raw/domain1/test_flood_event.tif",
        format="GeoTIFF",
        crs="EPSG:32632",
        is_synthetic=True
    )
    db.merge(ds_base)
    db.merge(ds_event)
    db.commit()
    db.close()

    return "ds-test-base-flood", "ds-test-event-flood"

def test_flood_pipeline_execution(synthetic_flood_datasets):
    base_id, event_id = synthetic_flood_datasets

    payload = {
        "inputs": {
            "baseline": base_id,
            "event": event_id
        },
        "parameters": {
            "threshold_mode": "bounded_otsu",
            "min_drop_db": 3.0,
            "filter_window": 3,
            "min_cluster_pixels": 2
        }
    }

    response = client.post("/api/domains/domain1/process", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["domain"] == "domain1"
    assert data["status"] == "completed"
    assert data["is_synthetic_input"] is True

    # Check that warnings flag synthetic data
    assert any("SYNTHETIC" in w for w in data["warnings"])

    # Check that flood extent metric is present and positive
    flood_metric = next((m for m in data["summary_metrics"] if m["label"] == "New Flood Inundation"), None)
    assert flood_metric is not None
    assert float(flood_metric["value"]) > 0.0

    # Check that preview and raster layers are returned
    layer_keys = [l["key"] for l in data["layers"]]
    assert "classification_geotiff" in layer_keys
    assert "baseline_preview" in layer_keys
    assert "event_preview" in layer_keys
    assert "flood_overlay" in layer_keys

    # Check four-level explanation presence
    exp = data["explanation"]
    assert len(exp["level1_visual"]) > 10
    assert len(exp["level2_method"]) > 10
    assert len(exp["level3_evidence"]) > 10
    assert len(exp["level4_uncertainty"]) > 10

def test_flood_pipeline_missing_inputs():
    response = client.post("/api/domains/domain1/process", json={"inputs": {}})
    assert response.status_code == 422
    assert "Missing required input" in response.json()["detail"]
