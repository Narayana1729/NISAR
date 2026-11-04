import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_domain1_real_data_workflow():
    """Phase 1: Full end-to-end integration test of the Domain 1 workflow with real Sentinel-1 RTC data."""
    # 1. Frontend queries available datasets
    ds_res = client.get("/api/datasets?domain=domain1")
    assert ds_res.status_code == 200
    datasets = ds_res.json()
    assert len(datasets) >= 2

    # Locate real Sentinel-1 acquisitions
    real_base = next((d for d in datasets if not d["is_synthetic"] and "Pre-Flood" in d["name"]), None)
    real_event = next((d for d in datasets if not d["is_synthetic"] and "Post-Flood" in d["name"]), None)
    assert real_base is not None
    assert real_event is not None

    # 2. Frontend submits processing request with parameters
    payload = {
        "inputs": {
            "baseline": real_base["id"],
            "event": real_event["id"]
        },
        "parameters": {
            "threshold_mode": "bounded_otsu",
            "min_drop_db": 3.0,
            "filter_window": 5,
            "min_cluster_pixels": 8
        }
    }
    proc_res = client.post("/api/domains/domain1/process", json=payload)
    assert proc_res.status_code == 200
    data = proc_res.json()

    # 3. Verify standardized domain response fields
    assert data["domain"] == "domain1"
    assert data["status"] == "completed"
    assert data["is_synthetic_input"] is False
    assert len(data["summary_metrics"]) >= 3
    assert len(data["layers"]) >= 3
    assert "flood_overlay" in [l["key"] for l in data["layers"]]

    # 4. Verify outputs are accessible over HTTP
    run_id = data["run_id"]
    overlay_layer = next(l for l in data["layers"] if l["key"] == "flood_overlay")
    img_res = client.get(overlay_layer["url"])
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/png"
    assert len(img_res.content) > 1000

    # 5. Verify exportable JSON investigation report
    export_res = client.get(f"/api/explorer/runs/{run_id}/export")
    assert export_res.status_code == 200
    report = export_res.json()
    assert report["run_id"] == run_id
    assert "Floods" in report["report_title"]
    assert len(report["investigation_summary"]) >= 3

def test_file_safety_path_traversal():
    """Phase 2: Verify protection against path traversal in dataset registration."""
    bad_payload = {
        "name": "Malicious Traversal Attempt",
        "domain": "domain1",
        "product_type": "sar_backscatter",
        "relative_path": "../../etc/passwd"
    }
    res = client.post("/api/datasets/register", json=bad_payload)
    assert res.status_code == 422
    assert "relative_path must point inside" in res.json()["detail"]

def test_file_safety_nonexistent_dataset_input():
    """Phase 2: Verify clear error on non-existent dataset IDs."""
    payload = {
        "inputs": {
            "baseline": "00000000-0000-0000-0000-000000000000",
            "event": "11111111-1111-1111-1111-111111111111"
        }
    }
    res = client.post("/api/domains/domain1/process", json=payload)
    assert res.status_code == 422
    assert "was not found" in res.json()["detail"]

def test_earth_event_explorer_api_and_context():
    """Phase 5: Verify event catalog loads, includes real metadata and links to analytical domains."""
    res = client.get("/api/explorer/events")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 4

    thessaly_evt = next((e for e in events if e["id"] == "event-thessaly-storm-daniel-2023"), None)
    assert thessaly_evt is not None
    assert thessaly_evt["status"] == "data_available"
    assert "domain1" in thessaly_evt["domains_involved"]
    assert "baseline" in thessaly_evt["dataset_ids"]["domain1"]

def test_common_domain_interface_and_lifecycle():
    """Verify that all 5 domain pipelines implement DomainInterface with the 6 standard lifecycle stages."""
    from app.services.pipeline import DomainInterface
    from app.domains.domain1.processor import FloodsPipeline
    from app.domains.domain2.processor import ForestsPipeline
    from app.domains.domain3.processor import EarthquakesPipeline
    from app.domains.domain4.processor import AgriculturePipeline
    from app.domains.domain5.processor import GlaciersPipeline

    pipelines = [
        FloodsPipeline(),
        ForestsPipeline(),
        EarthquakesPipeline(),
        AgriculturePipeline(),
        GlaciersPipeline(),
    ]

    for p in pipelines:
        # Adheres to DomainInterface
        assert isinstance(p, DomainInterface)

        # Stage 1: get_info() returns valid metadata contract
        info = p.get_info()
        assert "domain" in info
        assert "analysis" in info
        assert "inputs" in info
        assert "parameters" in info
        assert len(info["inputs"]) >= 2

        # Lifecycle methods are callable
        assert callable(getattr(p, "validate_inputs", None))
        assert callable(getattr(p, "preprocess", None))
        assert callable(getattr(p, "analyze", None))
        assert callable(getattr(p, "generate_outputs", None))
        assert callable(getattr(p, "validate_results", None))
