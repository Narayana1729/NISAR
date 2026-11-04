"""test_scientific_dataset_ownership.py

Comprehensive test suite verifying corrected scientific dataset ownership,
API domain filtering, cross-domain isolation, physical file preservation,
and domain input compatibility across NISAR Domains 1-5.
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.connection import get_db
from app.database.models import DatasetModel
from app.services.dataset_service import DatasetService
from app.services.pipeline import PipelineInputError
from app.services.processing_service import ProcessingService
from app.schemas.results import ProcessingRequest
from app.domains.domain4.processor import AgriculturePipeline

client = TestClient(app)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def test_1_manifest_and_sqlite_id_consistency():
    """Verify that datasets.json and SQLite backend/nisar.db contain the exact same 60 IDs."""
    manifest_path = ROOT_DIR / "data" / "manifests" / "datasets.json"
    assert manifest_path.is_file(), "Manifest datasets.json must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    manifest_datasets = manifest_data.get("datasets", [])
    assert len(manifest_datasets) == 60, f"Expected 60 datasets in manifest, found {len(manifest_datasets)}"

    manifest_ids = {d["id"]: d for d in manifest_datasets}
    assert len(manifest_ids) == 60, "Manifest must not contain duplicate IDs"

    db: Session = next(get_db())
    db_records = db.query(DatasetModel).all()
    assert len(db_records) == 60, f"Expected 60 records in SQLite, found {len(db_records)}"

    db_ids = {r.id: r for r in db_records}
    assert set(manifest_ids.keys()) == set(db_ids.keys()), "Manifest and SQLite IDs must match 1-to-1"

    # Check domain alignment between manifest and DB
    for ds_id, m_item in manifest_ids.items():
        db_item = db_ids[ds_id]
        assert m_item["domain"] == db_item.domain, (
            f"Domain mismatch for {ds_id}: manifest={m_item['domain']}, db={db_item.domain}"
        )


def test_2_correct_logical_domain_counts():
    """Verify exact counts per domain in manifest and SQLite:

    D1: 11
    D2: 26
    D3: 6
    D4: 0
    D5: 13
    unresolved: 4
    Total: 60
    """
    manifest_path = ROOT_DIR / "data" / "manifests" / "datasets.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    from collections import Counter
    m_counts = Counter(d["domain"] for d in manifest_data["datasets"])

    assert m_counts["domain1"] == 11, f"Expected 11 D1 datasets, got {m_counts['domain1']}"
    assert m_counts["domain2"] == 26, f"Expected 26 D2 datasets, got {m_counts['domain2']}"
    assert m_counts["domain3"] == 6, f"Expected 6 D3 datasets, got {m_counts['domain3']}"
    assert m_counts["domain4"] == 0, f"Expected 0 D4 datasets, got {m_counts['domain4']}"
    assert m_counts["domain5"] == 13, f"Expected 13 D5 datasets, got {m_counts['domain5']}"
    assert m_counts["unresolved"] == 4, f"Expected 4 unresolved datasets, got {m_counts['unresolved']}"

    db: Session = next(get_db())
    db_records = db.query(DatasetModel).all()
    db_counts = Counter(r.domain for r in db_records)

    assert db_counts["domain1"] == 11
    assert db_counts["domain2"] == 26
    assert db_counts["domain3"] == 6
    assert db_counts["domain4"] == 0
    assert db_counts["domain5"] == 13
    assert db_counts["unresolved"] == 4


def test_3_api_filtering_for_all_domains():
    """Verify /api/datasets?domain=X returns the exact logical domain datasets."""
    expected_counts = {
        "domain1": 11,
        "domain2": 26,
        "domain3": 6,
        "domain4": 0,
        "domain5": 13,
        "unresolved": 4,
    }

    for dom, expected in expected_counts.items():
        res = client.get(f"/api/datasets?domain={dom}")
        assert res.status_code == 200
        items = res.json()
        assert len(items) == expected, f"API query for {dom} returned {len(items)}, expected {expected}"
        for item in items:
            assert item["domain"] == dom

    # Without filter, all 60 are returned
    res_all = client.get("/api/datasets")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 60


def test_4_no_cross_domain_contamination():
    """Verify strictly zero contamination across domains."""
    res_d1 = client.get("/api/datasets?domain=domain1").json()
    res_d2 = client.get("/api/datasets?domain=domain2").json()
    res_d3 = client.get("/api/datasets?domain=domain3").json()
    res_d4 = client.get("/api/datasets?domain=domain4").json()
    res_d5 = client.get("/api/datasets?domain=domain5").json()

    d1_ids = {d["id"] for d in res_d1}
    d2_ids = {d["id"] for d in res_d2}
    d3_ids = {d["id"] for d in res_d3}
    d4_ids = {d["id"] for d in res_d4}
    d5_ids = {d["id"] for d in res_d5}

    # All sets must be completely disjoint
    assert len(d4_ids) == 0, "D4 must have 0 datasets"
    assert d1_ids.isdisjoint(d2_ids)
    assert d1_ids.isdisjoint(d3_ids)
    assert d1_ids.isdisjoint(d5_ids)
    assert d2_ids.isdisjoint(d3_ids)
    assert d2_ids.isdisjoint(d5_ids)
    assert d3_ids.isdisjoint(d5_ids)

    # Jakobshavn datasets must NOT appear in D1, D2, D3, or D4
    jakobshavn_ids = {
        "ds-demo-d3-exp", "ds-demo-d3-ref", "ds-demo-d3-sar-base", "ds-demo-d3-sar-event", "ds-demo-d3-vel",
        "ds-real-d3-exp", "ds-real-d3-ref", "ds-real-d3-sar-base", "ds-real-d3-sar-event", "ds-real-d3-vel",
        "ds-test-d3-sar-base", "ds-test-d3-sar-event", "ds-test-d3-vel"
    }
    assert jakobshavn_ids.issubset(d5_ids)
    assert jakobshavn_ids.isdisjoint(d1_ids)
    assert jakobshavn_ids.isdisjoint(d2_ids)
    assert jakobshavn_ids.isdisjoint(d3_ids)

    # Central Valley datasets must NOT appear in any domain (only in 'unresolved')
    cv_ids = {"ds-demo-d4-coh", "ds-demo-d4-disp", "ds-demo-d4-exp", "ds-demo-d4-ref"}
    for dom_set in (d1_ids, d2_ids, d3_ids, d4_ids, d5_ids):
        assert cv_ids.isdisjoint(dom_set)


def test_5_physical_file_paths_on_disk_preserved():
    """Verify that all 60 datasets point to existing, valid physical files on disk.

    Zero files moved, renamed, or deleted.
    """
    manifest_path = ROOT_DIR / "data" / "manifests" / "datasets.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    for item in manifest_data["datasets"]:
        did = item["id"]
        rel_path = item["relative_path"]
        abs_path = ROOT_DIR / "data" / rel_path
        assert abs_path.is_file(), f"Dataset {did} file missing at {abs_path}"
        assert abs_path.stat().st_size > 0, f"Dataset {did} file is empty at {abs_path}"


def test_6_domain2_retrieves_wildfire_and_forest_datasets():
    """Verify D2 retrieves both Pará deforestation datasets and wildfire disturbance datasets."""
    res = client.get("/api/datasets?domain=domain2")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 26

    ids = {d["id"] for d in items}

    # Pará deforestation datasets (13 total)
    assert "ds-real-d2-base" in ids
    assert "ds-real-d2-event" in ids
    assert "ds-real-d2-mask" in ids
    assert "ds-demo-d2-base" in ids

    # Dadia/Evros wildfire datasets (5 real)
    assert "ds-real-d5-base" in ids
    assert "ds-real-d5-event" in ids
    assert "ds-real-d5-firms" in ids
    assert "ds-real-d5-ref" in ids
    assert "ds-real-d5-exp" in ids

    # Park Fire wildfire datasets (5 demo + 3 test)
    assert "ds-demo-d5-base" in ids
    assert "ds-demo-d5-event" in ids
    assert "ds-demo-d5-firms" in ids
    assert "ds-test-d5-base" in ids

    # Verify product types present in D2
    ptypes = {d["product_type"] for d in items}
    assert "sar_backscatter" in ptypes
    assert "forest_mask" in ptypes
    assert "fire_detections" in ptypes
    assert "reference_disturbance" in ptypes
    assert "exposure_assets" in ptypes


def test_7_domain5_retrieves_jakobshavn_glacier_datasets():
    """Verify D5 retrieves all 13 Jakobshavn glacier velocity and terminus datasets."""
    res = client.get("/api/datasets?domain=domain5")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 13

    ids = {d["id"] for d in items}
    expected_jakobshavn = {
        "ds-real-d3-vel",
        "ds-real-d3-ref",
        "ds-real-d3-sar-base",
        "ds-real-d3-sar-event",
        "ds-real-d3-exp",
        "ds-demo-d3-vel",
        "ds-demo-d3-ref",
        "ds-demo-d3-sar-base",
        "ds-demo-d3-sar-event",
        "ds-demo-d3-exp",
        "ds-test-d3-vel",
        "ds-test-d3-sar-base",
        "ds-test-d3-sar-event",
    }
    assert ids == expected_jakobshavn

    # Verify physical location remains in raw/domain3/
    for item in items:
        assert "raw/domain3/" in item["relative_path"]


def test_8_domain3_retrieves_only_confirmed_earthquake_insar_datasets():
    """Verify D3 retrieves only confirmed Tyrnavos earthquake/InSAR datasets (6 datasets total)."""
    res = client.get("/api/datasets?domain=domain3")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 6

    ids = {d["id"] for d in items}
    expected_tyrnavos = {
        "ds-real-d4-disp",
        "ds-real-d4-coh",
        "ds-real-d4-ref",
        "ds-real-d4-exp",
        "ds-test-d4-disp",
        "ds-test-d4-coh",
    }
    assert ids == expected_tyrnavos

    # Verify NO glacier datasets in D3
    for item in items:
        assert item["product_type"] in ("insar_displacement", "insar_coherence", "reference_displacement", "exposure_assets")
        assert "jakobshavn" not in item["name"].lower()


def test_9_domain4_rejects_insar_displacement_as_agricultural_backscatter():
    """Verify D4 AgriculturePipeline requires sar_backscatter and rejects InSAR displacement inputs."""
    pipeline = AgriculturePipeline()
    assert pipeline.domain == "domain4"
    assert pipeline.implementation_status == "demonstration"

    # Verify input specifications require sar_backscatter
    base_input = next(i for i in pipeline.inputs if i.role == "baseline")
    assert base_input.product_types == ["sar_backscatter"]

    mon_input = next(i for i in pipeline.inputs if i.role == "monitoring")
    assert mon_input.product_types == ["sar_backscatter"]

    # When an InSAR displacement dataset is provided, execute raises PipelineInputError
    db: Session = next(get_db())
    proc_service = ProcessingService(db)

    with pytest.raises(PipelineInputError, match="requires one of: sar_backscatter"):
        proc_service.execute(
            pipeline,
            ProcessingRequest(
                inputs={"baseline": "ds-real-d4-disp", "monitoring": "ds-real-d4-disp"}
            ),
        )


def test_10_synthetic_fixtures_and_real_observations_clearly_flagged():
    """Verify is_synthetic=True for demo/test fixtures and False for real observations."""
    res = client.get("/api/datasets")
    assert res.status_code == 200
    items = res.json()

    for item in items:
        did = item["id"]
        is_synth = item["is_synthetic"]
        assert isinstance(is_synth, bool), f"Dataset {did} missing boolean is_synthetic"
        if (
            did.startswith("ds-demo-")
            or did.startswith("ds-test-")
            or did.startswith("ds-bench-")
            or did == "ds-dem-thessaly-basin"
        ):
            assert is_synth is True, f"Dataset {did} must have is_synthetic=True"
        elif (
            did.startswith("ds-real-")
            or did in ("5c351e81-1dfc-4d6b-9eec-9aed124eee8a", "15a8d70a-999e-4575-a2b7-b7b502f0dad8", "ds-exp-thessaly-assets")
        ):
            assert is_synth is False, f"Dataset {did} must have is_synthetic=False"
