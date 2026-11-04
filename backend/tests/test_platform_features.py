import io
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_place_search_and_custom_coordinates():
    """Verify place search gazetteer and coordinate/bbox parsing."""
    res = client.get("/api/explorer/places?q=Karla")
    assert res.status_code == 200
    places = res.json()
    assert len(places) >= 1
    assert "Lake Karla" in places[0]["name"]
    assert len(places[0]["bbox"]) == 4

    # Custom coordinate pair
    coord_res = client.get("/api/explorer/places?q=39.515, 22.875")
    assert coord_res.status_code == 200
    c_places = coord_res.json()
    assert len(c_places) == 1
    assert c_places[0]["category"] == "Custom Study Point"


def test_dataset_discovery_distinguishes_real_synthetic_and_empty_aoi():
    """Verify discovery separates real local datasets, synthetic fixtures, and unstaged AOIs."""
    # 1. Lake Karla AOI for domain1
    res = client.get("/api/explorer/discover?bbox=22.79,39.44,22.96,39.59&domain=domain1&include_external=true")
    assert res.status_code == 200
    data = res.json()

    assert data["summary"]["local_real_count"] >= 3  # S1 baseline, S1 event, permanent water, exposure assets
    assert data["summary"]["local_synthetic_count"] >= 1  # benchmark ref flood, DEM
    assert all(not d["is_synthetic"] for d in data["local_real_datasets"])
    assert all(d["is_synthetic"] for d in data["local_synthetic_datasets"])
    assert data["external_discovery"]["status"] in ("connected", "offline_or_blocked")

    # 2. Unstaged AOI (Tampa Bay / Hurricane Milton) must return 0 local ready datasets (no fabricated data)
    empty_res = client.get("/api/explorer/discover?bbox=-82.85,27.35,-81.80,28.15&domain=domain1")
    assert empty_res.status_code == 200
    empty_data = empty_res.json()
    assert empty_data["summary"]["local_real_count"] == 0
    assert empty_data["summary"]["local_synthetic_count"] == 0


def test_prepared_events_contain_only_verified_dataset_references():
    """Verify prepared events only expose valid, existing dataset IDs and accurate readiness flags."""
    ev_res = client.get("/api/explorer/events")
    assert ev_res.status_code == 200
    events = ev_res.json()

    ds_res = client.get("/api/datasets")
    all_ids = {d["id"] for d in ds_res.json() if d["file_available"]}

    for evt in events:
        for dom_id, role_map in evt.get("dataset_ids", {}).items():
            for role, ds_id in role_map.items():
                assert ds_id in all_ids, f"Event {evt['id']} references missing dataset {ds_id}"


def test_domain1_validation_error_explorer_method_comparison_and_exposure():
    """Verify classification validation (IoU/F1/Precision/Recall/Confusion Matrix), Error Explorer, Method Benchmark, and Asset Exposure."""
    payload = {
        "inputs": {
            "baseline": "5c351e81-1dfc-4d6b-9eec-9aed124eee8a",
            "event": "15a8d70a-999e-4575-a2b7-b7b502f0dad8",
            "reference_water": "ds-real-thessaly-perm-water",
            "dem": "ds-dem-thessaly-basin",
            "reference_flood": "ds-bench-thessaly-ref-flood",
            "exposure_assets": "ds-exp-thessaly-assets",
        },
        "parameters": {
            "threshold_mode": "bounded_otsu",
            "min_drop_db": 3.0,
            "filter_window": 5,
            "min_cluster_pixels": 8,
            "max_slope_deg": 5.0,
        },
    }
    res = client.post("/api/domains/domain1/process", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    # Check study area & georeferenced layer bounds
    assert data["study_area"]["bbox_wgs84"] is not None
    assert len(data["study_area"]["bbox_wgs84"]) == 4
    assert all(l["bounds_wgs84"] is not None for l in data["layers"])

    # Check validation results
    val = data["validation"]
    assert val["status"] == "compared_to_reference"
    assert val["evaluation_type"] == "classification"
    val_labels = [m["label"] for m in val["metrics"]]
    assert "Intersection over Union (IoU)" in val_labels
    assert "F1 Score (Dice)" in val_labels
    assert "Precision" in val_labels
    assert "Recall" in val_labels

    cm = val["confusion_matrix"]
    assert cm is not None
    assert cm["true_positive_pixels"] > 10_000
    assert cm["valid_evaluated_pixels"] > 1_000_000

    ee = val["error_explorer"]
    assert ee is not None
    assert "unresolved_discrepancy_pixels" in ee
    assert "unresolved_discrepancy_note" in ee

    # Check Baseline vs Physical vs Probabilistic Classifier comparison
    mc = val["method_comparison"]
    assert len(mc) == 3
    assert all("iou_pct" in item and "f1_pct" in item for item in mc)

    # Check spatial exposure results
    exp = data["exposure"]
    assert exp["status"] == "evaluated"
    assert len(exp["asset_breakdown"]) == 4
    assert any(a["exposed"] for a in exp["asset_breakdown"])

    # Check validation and exposure overlays are served over HTTP
    layer_keys = {l["key"]: l["url"] for l in data["layers"]}
    assert "validation_overlay" in layer_keys
    assert "exposure_overlay" in layer_keys
    assert client.get(layer_keys["validation_overlay"]).status_code == 200
    assert client.get(layer_keys["exposure_overlay"]).status_code == 200


def test_missing_reference_never_fabricates_validation_scores():
    """Verify that running without a reference dataset produces status='not_validated' and empty metrics."""
    payload = {
        "inputs": {
            "baseline": "ds-demo-d2-base",
            "event": "ds-demo-d2-event",
        }
    }
    res = client.post("/api/domains/domain2/process", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["validation"]["status"] == "not_validated"
    assert data["validation"]["metrics"] == []
    assert data["exposure"]["status"] == "not_evaluated"


def test_continuous_validation_and_exposure_domains_3_and_4():
    """Verify continuous validation (RMSE, MAE, Bias, Correlation) and exposure on Cryosphere and Land Movement."""
    # Domain 3: Cryosphere
    res3 = client.post(
        "/api/domains/domain3/process",
        json={
            "inputs": {
                "velocity": "ds-demo-d3-vel",
                "baseline_sar": "ds-demo-d3-sar-base",
                "event_sar": "ds-demo-d3-sar-event",
                "reference_velocity": "ds-demo-d3-ref",
                "exposure_assets": "ds-demo-d3-exp",
            }
        },
    )
    assert res3.status_code == 200, res3.text
    d3 = res3.json()
    assert d3["validation"]["status"] == "compared_to_reference"
    assert d3["validation"]["evaluation_type"] == "continuous"
    d3_vlabels = [m["label"] for m in d3["validation"]["metrics"]]
    assert "Root Mean Squared Error (RMSE)" in d3_vlabels
    assert "Mean Absolute Error (MAE)" in d3_vlabels
    assert "Pearson Correlation (r)" in d3_vlabels
    assert d3["exposure"]["status"] == "evaluated"

    # Domain 4: Land Movement
    res4 = client.post(
        "/api/domains/domain4/process",
        json={
            "inputs": {
                "displacement": "ds-demo-d4-disp",
                "coherence": "ds-demo-d4-coh",
                "reference_displacement": "ds-demo-d4-ref",
                "exposure_assets": "ds-demo-d4-exp",
            }
        },
    )
    assert res4.status_code == 200, res4.text
    d4 = res4.json()
    assert d4["validation"]["status"] == "compared_to_reference"
    assert d4["exposure"]["status"] == "evaluated"


def test_reopen_run_and_export_15_section_json_and_html_reports():
    """Verify run history listing, reopening by run_id, and exporting both 15-section JSON and printable HTML reports."""
    res5 = client.post(
        "/api/domains/domain5/process",
        json={
            "inputs": {
                "baseline": "ds-demo-d5-base",
                "event": "ds-demo-d5-event",
                "fire_detections": "ds-demo-d5-firms",
                "reference_disturbance": "ds-demo-d5-ref",
                "exposure_assets": "ds-demo-d5-exp",
            }
        },
    )
    assert res5.status_code == 200
    run_id = res5.json()["run_id"]

    # 1. List runs
    runs_res = client.get("/api/explorer/runs?domain=domain5")
    assert runs_res.status_code == 200
    assert any(r["id"] == run_id for r in runs_res.json())

    # 2. Reopen run by ID
    reopen_res = client.get(f"/api/explorer/runs/{run_id}")
    assert reopen_res.status_code == 200
    reopened = reopen_res.json()
    assert reopened["run_id"] == run_id
    assert reopened["validation"]["status"] == "compared_to_reference"
    assert reopened["exposure"]["status"] == "evaluated"

    # 3. Export 15-section JSON report
    json_rep_res = client.get(f"/api/explorer/runs/{run_id}/export?format=json")
    assert json_rep_res.status_code == 200
    jrep = json_rep_res.json()
    for section_key in [
        "1_analysis_id",
        "2_study_area",
        "3_selected_domain",
        "4_dataset_sources_and_identifiers",
        "5_acquisition_dates",
        "6_processing_method",
        "7_configuration_parameters",
        "8_before_after_visualization",
        "9_detected_change_map",
        "10_quantitative_measurements",
        "11_validation_results",
        "12_error_and_uncertainty_information",
        "13_potential_exposure_results",
        "14_known_limitations",
        "15_processing_provenance",
    ]:
        assert section_key in jrep, f"Missing report section {section_key}"

    # 4. Export printable HTML report
    html_rep_res = client.get(f"/api/explorer/runs/{run_id}/export?format=html")
    assert html_rep_res.status_code == 200
    assert "text/html" in html_rep_res.headers["content-type"]
    assert run_id in html_rep_res.text
    assert "11 & 12. Independent Reference Validation" in html_rep_res.text
    assert "13. Potential Asset Exposure Analysis" in html_rep_res.text


def test_dataset_upload_endpoint_validates_georeferencing():
    """Verify safe file upload accepts valid GeoJSON, rejects invalid extensions, and cleans up."""
    from pathlib import Path
    from app.config import settings
    from app.database.connection import SessionLocal
    from app.database.models import DatasetModel

    valid_geojson = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Test Exposure Bridge", "asset_class": "infrastructure"},
                "geometry": {"type": "Point", "coordinates": [22.84, 39.49]},
            }
        ],
    }).encode("utf-8")

    up_res = client.post(
        "/api/datasets/upload",
        data={
            "name": "Uploaded Test Exposure Asset",
            "domain": "domain1",
            "product_type": "exposure_assets",
            "source": "Unit Test Upload",
            "is_synthetic": "true",
        },
        files={"file": ("test_upload_asset.geojson", io.BytesIO(valid_geojson), "application/geo+json")},
    )
    assert up_res.status_code == 200, up_res.text
    created = up_res.json()
    try:
        assert created["format"] == "GeoJSON"
        assert created["bbox_wgs84"] == [22.84, 39.49, 22.84, 39.49]
        assert created["is_synthetic"] is True
    finally:
        # Clean up uploaded test artifact and DB row
        db = SessionLocal()
        try:
            rows = db.query(DatasetModel).filter(DatasetModel.name == "Uploaded Test Exposure Asset").all()
            for r in rows:
                p = Path(settings.DATA_ROOT_DIR) / r.relative_path
                if p.exists():
                    p.unlink()
                db.delete(r)
            db.commit()
        finally:
            db.close()

    bad_res = client.post(
        "/api/datasets/upload",
        data={
            "name": "Invalid File Upload",
            "domain": "domain1",
            "product_type": "sar_backscatter",
        },
        files={"file": ("malicious.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert bad_res.status_code == 400


def test_real_satellite_workflows_across_all_five_domains():
    """Verify end-to-end execution of verified REAL satellite/geophysical datasets across Domains 1–5 with independent real reference validation."""
    # Domain 1: Storm Daniel (Lake Karla, Greece) with real S1A RTC VV + Copernicus DEM + JRC GSW + Sentinel-2 NDWI Flood Reference
    r1 = client.post(
        "/api/domains/domain1/process",
        json={
            "inputs": {
                "baseline": "5c351e81-1dfc-4d6b-9eec-9aed124eee8a",
                "event": "15a8d70a-999e-4575-a2b7-b7b502f0dad8",
                "reference_water": "ds-real-thessaly-jrc-water",
                "dem": "ds-real-thessaly-cop-dem",
                "reference_flood": "ds-real-thessaly-s2-flood-ref",
                "exposure_assets": "ds-exp-thessaly-assets",
            }
        },
    )
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["is_synthetic_input"] is False
    assert d1["validation"]["status"] == "compared_to_reference"
    assert d1["validation"]["validation_category"] == "independent_real_reference"
    assert d1["validation"]["reference_independence"] == "independent_cross_sensor"
    assert d1["validation"]["reference_is_synthetic"] is False
    assert d1["domain_data"]["flood_km2"] > 5.0
    assert d1["validation"]["confusion_matrix"]["iou_pct"] > 35.0

    # Domain 2: Novo Progresso / BR-163 (Pará, Brazil) with real S1A RTC VH (2019 vs 2020) + JAXA ALOS-2 PALSAR-2 FNF
    r2 = client.post(
        "/api/domains/domain2/process",
        json={
            "inputs": {
                "baseline": "ds-real-d2-base",
                "event": "ds-real-d2-event",
                "forest_mask": "ds-real-d2-mask",
                "reference_disturbance": "ds-real-d2-ref",
                "exposure_assets": "ds-real-d2-exp",
            },
            "parameters": {
                "min_drop_db": 2.0,
                "filter_window": 5,
                "min_cluster_pixels": 6,
            },
        },
    )
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["is_synthetic_input"] is False
    assert d2["validation"]["status"] == "compared_to_reference"
    assert d2["validation"]["validation_category"] == "independent_real_reference"
    assert d2["validation"]["reference_independence"] == "independent_cross_sensor"
    assert d2["validation"]["reference_is_synthetic"] is False
    assert d2["domain_data"]["polarization"] == "VH"
    assert d2["domain_data"]["disturbed_ha"] > 5.0

    # Domain 3: Jakobshavn Isbræ (Greenland) with real NASA MEaSUREs ITS_LIVE v2 Velocity + Sentinel-1A HH Terminus Pair
    r3 = client.post(
        "/api/domains/domain3/process",
        json={
            "inputs": {
                "velocity": "ds-real-d3-vel",
                "baseline_sar": "ds-real-d3-sar-base",
                "event_sar": "ds-real-d3-sar-event",
                "reference_velocity": "ds-real-d3-ref",
                "exposure_assets": "ds-real-d3-exp",
            }
        },
    )
    assert r3.status_code == 200, r3.text
    d3 = r3.json()
    assert d3["is_synthetic_input"] is False
    assert d3["validation"]["status"] == "compared_to_reference"
    assert d3["validation"]["validation_category"] == "climatological_comparative_reference"
    assert d3["validation"]["reference_independence"] == "climatological_comparative_baseline"
    assert d3["validation"]["reference_is_synthetic"] is False
    assert d3["domain_data"]["max_velocity_m_yr"] > 2000.0

    # Domain 4: Tyrnavos Mw 6.3 Coseismic InSAR (Greece) with real COMET-LiCSAR Unwrapped LOS Displacement + Coherence + S1B Reference
    r4 = client.post(
        "/api/domains/domain4/process",
        json={
            "inputs": {
                "displacement": "ds-real-d4-disp",
                "coherence": "ds-real-d4-coh",
                "reference_displacement": "ds-real-d4-ref",
                "exposure_assets": "ds-real-d4-exp",
            },
            "parameters": {
                "min_coherence": 0.35,
                "subsidence_threshold_mm": -80.0,
                "color_stretch_mm": 300.0,
            },
        },
    )
    assert r4.status_code == 200, r4.text
    d4 = r4.json()
    assert d4["is_synthetic_input"] is False
    assert d4["validation"]["status"] == "compared_to_reference"
    assert d4["validation"]["validation_category"] == "partially_independent_real_reference"
    assert d4["validation"]["reference_independence"] == "partially_independent_cross_pair"
    assert d4["validation"]["reference_is_synthetic"] is False
    assert d4["domain_data"]["displacement_unit"] == "mm"
    assert d4["domain_data"]["peak_subsidence_mm"] < -250.0
    assert d4["domain_data"]["subsidence_bowl_km2"] > 10.0

    # Domain 5: Dadia Forest / Evros Megafire (Greece, Aug 2023) with real S1A VH + NASA MODIS MCD64A1 + MODIS Active Fire Points
    r5 = client.post(
        "/api/domains/domain5/process",
        json={
            "inputs": {
                "baseline": "ds-real-d5-base",
                "event": "ds-real-d5-event",
                "fire_detections": "ds-real-d5-firms",
                "reference_disturbance": "ds-real-d5-ref",
                "exposure_assets": "ds-real-d5-exp",
            },
            "parameters": {
                "burn_drop_db": 2.0,
                "filter_window": 5,
                "min_cluster_pixels": 5,
            },
        },
    )
    assert r5.status_code == 200, r5.text
    d5 = r5.json()
    assert d5["is_synthetic_input"] is False
    assert d5["validation"]["status"] == "compared_to_reference"
    assert d5["validation"]["validation_category"] == "independent_real_reference"
    assert d5["validation"]["reference_independence"] == "independent_cross_sensor"
    assert d5["validation"]["reference_is_synthetic"] is False
    assert d5["domain_data"]["thermal_total"] > 1000
    assert d5["domain_data"]["scar_ha"] > 50.0


def test_chronological_warning_and_html_report_path_safety():
    """Verify reversed baseline/event dates trigger a chronological warning and HTML reports never leak filesystem paths."""
    rev_res = client.post(
        "/api/domains/domain2/process",
        json={
            "inputs": {
                "baseline": "ds-real-d2-event",  # 2020-08-20 passed as baseline
                "event": "ds-real-d2-base",      # 2019-08-26 passed as event
            }
        },
    )
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert any("Chronological order warning" in w for w in rev_data["warnings"])

    run_id = rev_data["run_id"]
    html_res = client.get(f"/api/explorer/runs/{run_id}/export?format=html")
    assert html_res.status_code == 200
    assert "/Users/" not in html_res.text


def test_external_discovery_offline_fallback_and_retrieve_validation(monkeypatch):
    """Verify external discovery gracefully handles offline state without fabricating items and validates retrieval inputs."""
    import urllib.error
    import urllib.request

    def _raise_offline(*args, **kwargs):
        raise urllib.error.URLError("Simulated offline network")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_offline)
    res = client.get("/api/explorer/discover?bbox=22.79,39.44,22.96,39.59&domain=domain1&include_external=true")
    assert res.status_code == 200
    ext = res.json()["external_discovery"]
    assert ext["status"] == "offline_or_blocked"
    assert ext["items"] == []

    # Invalid collection on retrieve endpoint returns 400
    bad_ret = client.post(
        "/api/explorer/retrieve",
        json={
            "collection": "unsupported-collection",
            "granule_id": "test-granule-1",
            "domain": "domain1",
            "bbox": [22.80, 39.45, 22.90, 39.55],
        },
    )
    assert bad_ret.status_code == 400

    # Verify end-to-end on-demand AOI window extraction and registration using a mocked signed COG path
    import io
    from pathlib import Path
    from app.database.connection import SessionLocal
    from app.database.models import DatasetModel

    local_cog = str(Path("data/raw/domain1/thessaly_flood_baseline_vv.tif").resolve())

    class _MockResp:
        def __init__(self, payload: dict):
            self._bytes = json.dumps(payload).encode("utf-8")

        def read(self):
            return self._bytes

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/sas/v1/sign" in url:
            return _MockResp({"href": local_cog})
        return _MockResp({
            "id": "S1A_TEST_RETRIEVE_GRANULE",
            "properties": {"datetime": "2023-09-01T04:31:57Z", "platform": "Sentinel-1A"},
            "assets": {"vv": {"href": local_cog}},
        })

    monkeypatch.setattr(urllib.request, "urlopen", _mock_urlopen)
    good_ret = client.post(
        "/api/explorer/retrieve",
        json={
            "collection": "sentinel-1-rtc",
            "granule_id": "S1A_TEST_RETRIEVE_GRANULE",
            "domain": "domain1",
            "bbox": [22.82, 39.47, 22.88, 39.52],
            "asset_key": "vv",
        },
    )
    assert good_ret.status_code == 200, good_ret.text
    ret_body = good_ret.json()
    assert ret_body["status"] in ("retrieved_and_registered", "already_registered")
    assert ret_body["dataset"]["is_synthetic"] is False
    assert ret_body["dataset"]["crs"] == "EPSG:32634"

    # Clean up temporary retrieved test dataset row and file
    ds_id = ret_body["dataset"]["id"]
    rel_p = ret_body["dataset"]["relative_path"]
    db = SessionLocal()
    row = db.query(DatasetModel).filter(DatasetModel.id == ds_id).first()
    if row:
        db.delete(row)
        db.commit()
    db.close()
    full_p = Path("data") / rel_p
    if full_p.is_file():
        full_p.unlink()


def test_validation_nodata_exclusion_and_edge_cases(tmp_path):
    """Verify confusion matrix strictly excludes NoData from TN, handles all-zero/constant arrays safely, and computes geographic resolution in meters."""
    import numpy as np
    from affine import Affine
    from rasterio.crs import CRS
    from app.database.models import DatasetModel
    from app.services.pipeline import PipelineContext
    from app.utils.raster import RasterData, pixel_area_m2, write_geotiff
    from app.utils.validation import evaluate_binary_classification

    # Create a 20x20 geographic (EPSG:4326) raster where half (200 px) are valid and half (200 px) are NoData (NaN)
    h, w = 20, 20
    tr = Affine(0.00025, 0.0, 22.80, 0.0, -0.00025, 39.50)
    crs = CRS.from_epsg(4326)
    base_arr = np.ones((h, w), dtype="float64")
    base_arr[10:, :] = np.nan  # 200 NoData pixels
    base_raw = RasterData(array=base_arr, transform=tr, crs=crs, width=w, height=h)

    # Write a binary reference raster (0=negative, 1=positive, 255=nodata) where top 5x20=100 px are positive (1), next 5x20=100 px are negative (0), bottom 10x20=200 px are nodata (255)
    ref_arr = np.full((h, w), 255, dtype="uint8")
    ref_arr[:5, :] = 1
    ref_arr[5:10, :] = 0
    ref_tif = tmp_path / "ref_binary.tif"
    write_geotiff(ref_tif, ref_arr, base_raw, dtype="uint8", nodata=255)

    ref_ds = DatasetModel(
        id="ds-test-nodata-ref",
        name="Test Geographic Binary Reference",
        domain="domain1",
        product_type="reference_flood",
        relative_path="ref_binary.tif",
        source="Independent Optical Test Sensor",
        is_synthetic=False,
    )
    out_dir = tmp_path / "outputs" / "domain1" / "run-test-nodata"
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = PipelineContext(
        domain="domain1",
        run_id="run-test-nodata",
        datasets={"reference_flood": ref_ds},
        params={},
        data_root=tmp_path,
        output_dir=out_dir,
    )

    valid_mask = np.isfinite(base_arr)
    px_areas = pixel_area_m2(tr, crs, h)

    # Case 1: Partial overlap with 200 NoData pixels -> TN must ONLY count the 100 valid negative pixels, NOT the 200 NoData pixels!
    pred_mask = np.zeros((h, w), dtype=bool)
    pred_mask[:3, :] = True  # 60 TP pixels, 40 FN pixels, 0 FP pixels, 100 TN pixels (and 200 NoData excluded)
    val1 = evaluate_binary_classification(
        ctx=ctx,
        ref_role="reference_flood",
        predicted_mask=pred_mask,
        base_raw=base_raw,
        valid_mask=valid_mask,
        pixel_areas_m2=px_areas,
        area_unit="km²",
        feature_arrays={
            "static_signal": np.ones((h, w), dtype="float64"),  # constant array edge case (<400 px)
            "static_cutoff": 0.5,
            "primary_signal": np.ones((h, w), dtype="float64"),
            "secondary_signal": np.ones((h, w), dtype="float64"),
        },
        positive_class_label="Test Flood",
    )
    cm1 = val1.confusion_matrix
    assert cm1["true_positive_pixels"] == 60
    assert cm1["false_positive_pixels"] == 0
    assert cm1["false_negative_pixels"] == 40
    assert cm1["true_negative_pixels"] == 100  # Strictly excludes the 200 NoData pixels!
    assert cm1["valid_evaluated_pixels"] == 200
    assert cm1["missing_or_nodata_pixels"] == 200
    assert cm1["spatial_resolution_m"] > 20.0  # Geographic CRS converted to meters (~24.6m), not 0.0 degrees!
    assert len(val1.method_comparison) == 3

    # Case 2: All-zero prediction mask -> emits zero_positive_warning without crashing
    val_zero = evaluate_binary_classification(
        ctx=ctx,
        ref_role="reference_flood",
        predicted_mask=np.zeros((h, w), dtype=bool),
        base_raw=base_raw,
        valid_mask=valid_mask,
        pixel_areas_m2=px_areas,
        area_unit="km²",
        positive_class_label="Test Flood",
    )
    assert "zero_positive_warning" in val_zero.confusion_matrix
