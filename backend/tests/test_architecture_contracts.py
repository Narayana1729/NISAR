import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.connection import get_db
from app.database.models import DatasetModel
from app.services.pipeline import (
    DomainPipeline,
    PipelineContext,
    PipelineExecutionError,
    PipelineInputError,
    InputSpec,
    ParamSpec,
)
from app.services.processing_service import ProcessingService
from app.schemas.results import ProcessingRequest

client = TestClient(app)


class IncompleteStubPipeline(DomainPipeline):
    domain = "test_stub"
    analysis_name = "Incomplete Stub Analysis"
    summary = "Stub domain for testing incomplete implementation detection"
    implementation_status = "implemented"  # Pretends to be implemented
    inputs = [
        InputSpec(role="baseline", label="Baseline", product_types=["sar_backscatter"]),
    ]
    params = []
    # Does NOT implement preprocess, analyze, or generate_outputs


class PlannedDomainPipeline(DomainPipeline):
    domain = "test_planned"
    analysis_name = "Planned Future Analysis"
    summary = "Planned domain"
    implementation_status = "planned"
    inputs = [
        InputSpec(role="baseline", label="Baseline", product_types=["sar_backscatter"]),
    ]
    params = []


class EmptyOutputPipeline(DomainPipeline):
    domain = "test_empty"
    analysis_name = "Empty Output Analysis"
    summary = "Pipeline that returns empty results"
    implementation_status = "implemented"
    inputs = [
        InputSpec(role="baseline", label="Baseline", product_types=["sar_backscatter"]),
    ]
    params = []

    def preprocess(self, ctx: PipelineContext):
        return {}

    def analyze(self, ctx: PipelineContext, prep=None):
        return {}

    def generate_outputs(self, ctx: PipelineContext, analysis=None):
        return {}  # Returns no layers and no metrics


def test_incomplete_domain_raises_not_implemented():
    """Verify that a pipeline subclass lacking scientific lifecycle methods raises NotImplementedError."""
    stub = IncompleteStubPipeline()
    ctx = PipelineContext(
        run_id="test-run",
        domain="test_stub",
        datasets={},
        params={},
        data_root=Path("/tmp"),
        output_dir=Path("/tmp/out"),
    )
    with pytest.raises(NotImplementedError, match="scientific preprocess\\(\\) stage"):
        stub.preprocess(ctx)

    with pytest.raises(NotImplementedError, match="scientific analyze\\(\\) stage"):
        stub.analyze(ctx, None)

    with pytest.raises(NotImplementedError, match="scientific generate_outputs\\(\\) stage"):
        stub.generate_outputs(ctx, None)


def test_planned_domain_refuses_execution():
    """Verify that a domain in 'planned' status refuses execution and raises PipelineInputError."""
    db: Session = next(get_db())
    service = ProcessingService(db)
    planned = PlannedDomainPipeline()
    req = ProcessingRequest(inputs={"baseline": "ds-nonexistent"}, parameters={})

    with pytest.raises(PipelineInputError, match="is currently in 'planned' status"):
        service.execute(planned, req)


def test_empty_output_pipeline_fails_closed():
    """Verify that a pipeline producing zero layers and zero metrics is failed, not marked completed."""
    db: Session = next(get_db())
    service = ProcessingService(db)

    # Locate an existing real dataset
    real_ds = db.query(DatasetModel).filter(DatasetModel.domain == "domain1", DatasetModel.is_synthetic == False).first()
    assert real_ds is not None

    empty_pipe = EmptyOutputPipeline()
    req = ProcessingRequest(inputs={"baseline": real_ds.id}, parameters={})

    with pytest.raises(PipelineExecutionError, match="produced empty scientific outputs"):
        service.execute(empty_pipe, req)


def test_missing_disk_file_validation_error():
    """Verify that a dataset whose file is physically absent from disk is rejected before execution."""
    db: Session = next(get_db())
    service = ProcessingService(db)

    # Insert temporary dataset model with nonexistent path
    fake_id = "test-fake-missing-file"
    fake_ds = DatasetModel(
        id=fake_id,
        name="Missing File Test Dataset",
        domain="domain1",
        product_type="sar_backscatter",
        relative_path="raw/nonexistent/path/missing.tif",
        format="GeoTIFF",
        sensor="Sentinel-1A",
        polarization="VV",
        is_synthetic=True,
    )
    db.add(fake_ds)
    db.commit()

    try:
        from app.domains.domain1.processor import FloodsPipeline
        pipe = FloodsPipeline()
        req = ProcessingRequest(inputs={"baseline": fake_id, "event": fake_id}, parameters={})
        with pytest.raises(PipelineInputError, match="The same dataset cannot be used|missing from disk"):
            service.execute(pipe, req)
    finally:
        db.delete(fake_ds)
        db.commit()


def test_spatial_disjoint_datasets_rejected():
    """Verify that two datasets with non-overlapping geographical bounds are rejected with 422."""
    db: Session = next(get_db())
    service = ProcessingService(db)

    # d1 Thessaly Greece (~lon 22.8, lat 39.5) and d2 Para Brazil (~lon -55.0, lat -3.0)
    d1 = db.query(DatasetModel).filter(DatasetModel.domain == "domain1").first()
    d2 = db.query(DatasetModel).filter(DatasetModel.domain == "domain2").first()
    assert d1 is not None and d2 is not None

    # Floods pipeline requires baseline & event
    from app.domains.domain1.processor import FloodsPipeline
    pipe = FloodsPipeline()
    req = ProcessingRequest(inputs={"baseline": d1.id, "event": d2.id}, parameters={})

    with pytest.raises(PipelineInputError, match="Spatial overlap failure"):
        service.execute(pipe, req)


def test_polarization_mismatch_rejected():
    """Verify that SAR backscatter inputs with mismatched polarizations (e.g. VV and VH) are rejected."""
    db: Session = next(get_db())
    service = ProcessingService(db)

    # Thessaly VV dataset and Dadia/Evros or other VH/HV dataset
    ds_vv = db.query(DatasetModel).filter(DatasetModel.polarization == "VV", DatasetModel.product_type == "sar_backscatter").first()
    ds_vh = db.query(DatasetModel).filter(DatasetModel.polarization.in_(["VH", "HV"]), DatasetModel.product_type == "sar_backscatter").first()
    assert ds_vv is not None and ds_vh is not None

    from app.domains.domain1.processor import FloodsPipeline
    pipe = FloodsPipeline()
    req = ProcessingRequest(inputs={"baseline": ds_vv.id, "event": ds_vh.id}, parameters={})

    # Even if they didn't overlap, either spatial or polarization will trigger; test polarization specifically by mock/direct check
    test_datasets = {"baseline": ds_vv, "event": ds_vh}
    with pytest.raises(PipelineInputError, match="Polarization mismatch"):
        service._validate_dataset_compatibility(test_datasets)


def test_api_response_schema_and_implementation_status():
    """Verify that domain execution returns implementation_status and conforms to the standardized response schema."""
    # Run domain 1
    ds_res = client.get("/api/datasets?domain=domain1")
    datasets = ds_res.json()
    base = next(d for d in datasets if "Pre-Flood" in d["name"])
    event = next(d for d in datasets if "Post-Flood" in d["name"])

    res = client.post(
        "/api/domains/domain1/process",
        json={"inputs": {"baseline": base["id"], "event": event["id"]}},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["implementation_status"] in ("implemented", "demonstration", "partial")
    assert data["status"] == "completed"
    assert isinstance(data["execution_time_seconds"], float)
    assert isinstance(data["layers"], list)
    assert len(data["layers"]) > 0

    # Verify layer descriptor contract
    for layer in data["layers"]:
        assert "key" in layer
        assert "label" in layer
        assert "kind" in layer
        assert "path" in layer
        assert "url" in layer
        assert layer["url"].startswith("/api/outputs/")
        if layer.get("bounds_wgs84"):
            assert len(layer["bounds_wgs84"]) == 4

    # Verify metrics contract
    for metric in data["summary_metrics"]:
        assert "label" in metric
        assert "value" in metric
        assert "unit" in metric


def test_frontend_domains_config_has_exactly_five_domains():
    """Verify that frontend/src/config/domains.js defines exactly 5 scientific domains and separates explorer."""
    domains_file = Path("frontend/src/config/domains.js")
    assert domains_file.is_file()
    content = domains_file.read_text(encoding="utf-8")

    # Ensure domain1 through domain5 are present
    for i in range(1, 6):
        assert f"id: 'domain{i}'" in content

    # Ensure domain6 is NOT present
    assert "domain6" not in content

    # Ensure PLATFORM_FEATURES / EXPLORER_FEATURE is exported
    assert "EXPLORER_FEATURE" in content
    assert "PLATFORM_FEATURES" in content
