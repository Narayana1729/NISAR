import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import DatasetModel, ProcessingRunModel, ResultModel
from app.schemas.results import (
    ExposureInfo,
    ExplanationLevels,
    ProcessingRequest,
    StandardDomainResponse,
    ValidationInfo,
)
from app.services.dataset_service import _to_response_dict
from app.services.pipeline import (
    DomainPipeline,
    PipelineContext,
    PipelineExecutionError,
    PipelineInputError,
    Timer,
    dataset_provenance,
)
from app.utils.raster import RasterInputError

PLATFORM_SOFTWARE_VERSION = "NISAR-DancingWithTheSARs/2.0.0"


class ProcessingService:
    """Validates inputs, executes domain pipelines, and persists run records and results."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ queries
    def get_run(self, run_id: str) -> Optional[ProcessingRunModel]:
        return self.db.query(ProcessingRunModel).filter(ProcessingRunModel.id == run_id).first()

    def list_runs(self, domain: Optional[str] = None) -> list[dict[str, Any]]:
        q = self.db.query(ProcessingRunModel)
        if domain:
            q = q.filter(ProcessingRunModel.domain == domain)
        runs = q.order_by(ProcessingRunModel.started_at.desc()).all()
        out: list[dict[str, Any]] = []
        for r in runs:
            item: dict[str, Any] = {
                "id": r.id,
                "dataset_id": r.dataset_id,
                "domain": r.domain,
                "status": r.status,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "error_message": r.error_message,
                "analysis": None,
                "implementation_status": None,
                "is_synthetic_input": None,
                "observation_dates": [],
                "validation_status": None,
            }
            if r.result_json:
                try:
                    parsed = json.loads(r.result_json)
                    item["analysis"] = parsed.get("analysis")
                    item["implementation_status"] = parsed.get("implementation_status")
                    item["is_synthetic_input"] = parsed.get("is_synthetic_input")
                    item["observation_dates"] = parsed.get("observation_dates") or []
                    item["validation_status"] = (parsed.get("validation") or {}).get("status")
                except Exception:
                    pass
            out.append(item)
        return out

    def get_result(self, run_id: str) -> Optional[dict[str, Any]]:
        run = self.get_run(run_id)
        if not run or not run.result_json:
            return None
        return json.loads(run.result_json)

    # ------------------------------------------------------------------ execution
    def _validate_dataset_compatibility(self, datasets: dict[str, DatasetModel]) -> list[str]:
        """Validate temporal ordering, polarization matching, dimensions, and spatial overlap."""
        warnings: list[str] = []
        # 1. Temporal ordering check for sequential roles
        temporal_pairs = [
            ("baseline", "event"),
            ("pre_event", "post_event"),
            ("pre_fire", "post_fire"),
            ("t1", "t2"),
        ]
        for pre_role, post_role in temporal_pairs:
            if pre_role in datasets and post_role in datasets:
                d_pre = datasets[pre_role]
                d_post = datasets[post_role]
                if d_pre.acquisition_date and d_post.acquisition_date:
                    if str(d_pre.acquisition_date) > str(d_post.acquisition_date):
                        warnings.append(
                            f"Chronological order warning: Baseline acquisition ({d_pre.acquisition_date}) is later than "
                            f"Event acquisition ({d_post.acquisition_date}). Verify pre/post role assignment."
                        )
                # 2. Polarization compatibility check for radar backscatter change detection
                if (
                    d_pre.product_type == "sar_backscatter"
                    and d_post.product_type == "sar_backscatter"
                    and d_pre.polarization
                    and d_post.polarization
                ):
                    p1 = d_pre.polarization.strip().upper()
                    p2 = d_post.polarization.strip().upper()
                    if p1 != p2:
                        raise PipelineInputError(
                            f"Polarization mismatch: '{pre_role}' has polarization '{p1}' ({d_pre.name}), "
                            f"but '{post_role}' has polarization '{p2}' ({d_post.name}). Direct change detection requires matching polarizations."
                        )

        # 3. Dimension sanity checks
        for role, ds in datasets.items():
            meta = _to_response_dict(ds, self.db)
            w = meta.get("width")
            h = meta.get("height")
            if w is not None and w <= 0:
                raise PipelineInputError(f"Invalid dataset dimension: '{ds.name}' ({role}) has width={w} <= 0.")
            if h is not None and h <= 0:
                raise PipelineInputError(f"Invalid dataset dimension: '{ds.name}' ({role}) has height={h} <= 0.")

        # 4. Geographic spatial overlap check between raster pairs
        items = list(datasets.items())
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                r1, ds1 = items[i]
                r2, ds2 = items[j]
                m1 = _to_response_dict(ds1, self.db)
                m2 = _to_response_dict(ds2, self.db)
                b1 = m1.get("bbox_wgs84")
                b2 = m2.get("bbox_wgs84")
                if b1 and b2 and len(b1) == 4 and len(b2) == 4:
                    # Bounding boxes are [min_lon, min_lat, max_lon, max_lat]
                    inter_min_lon = max(b1[0], b2[0])
                    inter_min_lat = max(b1[1], b2[1])
                    inter_max_lon = min(b1[2], b2[2])
                    inter_max_lat = min(b1[3], b2[3])
                    if inter_min_lon > inter_max_lon or inter_min_lat > inter_max_lat:
                        raise PipelineInputError(
                            f"Spatial overlap failure: Dataset '{ds1.name}' ({r1}, bbox: {b1}) and dataset "
                            f"'{ds2.name}' ({r2}, bbox: {b2}) do not intersect geographically."
                        )
        return warnings

    def _resolve_inputs(self, pipeline: DomainPipeline, request: ProcessingRequest) -> dict[str, DatasetModel]:
        specs = {s.role: s for s in pipeline.inputs}
        unknown = set(request.inputs) - set(specs)
        if unknown:
            raise PipelineInputError(f"Unknown input role(s) for {pipeline.domain}: {', '.join(sorted(unknown))}")
        resolved: dict[str, DatasetModel] = {}
        data_root = Path(settings.DATA_ROOT_DIR).resolve()
        for role, spec in specs.items():
            ds_id = request.inputs.get(role)
            if not ds_id:
                if spec.required:
                    raise PipelineInputError(f"Missing required input '{spec.label}' ({role}).")
                continue
            ds = self.db.query(DatasetModel).filter(DatasetModel.id == ds_id).first()
            if ds is None:
                raise PipelineInputError(f"Dataset '{ds_id}' for input '{role}' was not found.")

            file_path = (data_root / ds.relative_path).resolve()
            if not str(file_path).startswith(str(data_root)):
                raise PipelineInputError(f"Dataset '{ds.name}' ({role}) path resolves outside data root.")
            if not file_path.is_file():
                raise PipelineInputError(f"Dataset file for '{ds.name}' ({role}) is missing from disk at: {ds.relative_path}")

            if ds.product_type not in spec.product_types:
                raise PipelineInputError(
                    f"Dataset '{ds.name}' has product type '{ds.product_type}', but input '{spec.label}' "
                    f"requires one of: {', '.join(spec.product_types)}."
                )
            resolved[role] = ds
        ids = [d.id for d in resolved.values()]
        if len(ids) != len(set(ids)):
            raise PipelineInputError("The same dataset cannot be used for more than one input role.")

        compat_warnings = self._validate_dataset_compatibility(resolved)
        return resolved, compat_warnings

    def execute(self, pipeline: DomainPipeline, request: ProcessingRequest) -> dict[str, Any]:
        """Run a pipeline. Raises PipelineInputError for user-correctable problems.

        A failed run is still recorded so the failure is visible in run history.
        """
        impl_status = getattr(pipeline, "implementation_status", "implemented")
        if impl_status == "planned":
            raise PipelineInputError(
                f"Domain '{pipeline.domain}' is currently in 'planned' status and has no runnable implementation."
            )

        params = pipeline.resolve_params(request.parameters)
        datasets, compat_warnings = self._resolve_inputs(pipeline, request)

        run_id = str(uuid.uuid4())
        data_root = Path(settings.DATA_ROOT_DIR).resolve()
        output_dir = data_root / "outputs" / pipeline.domain / run_id
        primary = next(iter(datasets.values()), None)
        primary_info = _to_response_dict(primary, self.db) if primary else {}
        bounds_wgs84 = primary_info.get("bbox_wgs84") or request.study_area_bbox

        run = ProcessingRunModel(
            id=run_id,
            dataset_id=primary.id if primary else None,
            domain=pipeline.domain,
            status="processing",
            params=json.dumps({
                "inputs": request.inputs,
                "parameters": params,
                "study_area_bbox": bounds_wgs84,
            }),
        )
        self.db.add(run)
        self.db.commit()

        ctx = PipelineContext(
            run_id=run_id,
            domain=pipeline.domain,
            datasets=datasets,
            params=params,
            data_root=data_root,
            output_dir=output_dir,
            bounds_wgs84=bounds_wgs84,
        )
        try:
            with Timer() as t:
                output = pipeline.run(ctx)
        except (PipelineInputError, RasterInputError) as exc:
            self._fail(run, str(exc))
            shutil.rmtree(output_dir, ignore_errors=True)
            raise PipelineInputError(str(exc)) from exc
        except Exception as exc:
            self._fail(run, f"Unexpected processing error: {type(exc).__name__}: {exc}")
            shutil.rmtree(output_dir, ignore_errors=True)
            raise

        if not output or (not ctx.layers and not output.get("metrics")):
            msg = f"Domain '{pipeline.domain}' produced empty scientific outputs (0 layers, 0 metrics). Incomplete domains cannot be marked completed."
            self._fail(run, msg)
            shutil.rmtree(output_dir, ignore_errors=True)
            raise PipelineExecutionError(msg)

        is_synthetic = any(bool(d.is_synthetic) for d in datasets.values())
        warnings = list(output.get("warnings", []))
        for cw in compat_warnings:
            if cw not in warnings:
                warnings.append(cw)
        if is_synthetic:
            warnings.insert(0, "One or more inputs are SYNTHETIC test data. Results are not Earth observations.")

        study_area = output.get("study_area") or {
            "bbox_wgs84": bounds_wgs84,
            "native_crs": primary_info.get("crs"),
            "native_bbox": primary_info.get("bbox"),
            "width": primary_info.get("width"),
            "height": primary_info.get("height"),
        }

        response = StandardDomainResponse(
            run_id=run_id,
            domain=pipeline.domain,
            status="completed",
            analysis=pipeline.analysis_name,
            execution_time_seconds=round(t.elapsed, 3),
            implementation_status=impl_status,
            is_synthetic_input=is_synthetic,
            study_area=study_area,
            summary_metrics=output.get("metrics", []),
            layers=ctx.layers,
            explanation=ExplanationLevels(**output["explanation"]),
            caveats=output.get("caveats", []),
            warnings=warnings,
            observation_dates=sorted({d.acquisition_date for d in datasets.values() if d.acquisition_date}),
            provenance={
                "algorithm": pipeline.analysis_name,
                "algorithm_version": "2.0.0",
                "software_version": PLATFORM_SOFTWARE_VERSION,
                "parameters": params,
                "study_area": study_area,
                "inputs": {role: dataset_provenance(ds) for role, ds in datasets.items()},
                "processing_notes": output.get("processing_notes", []),
                "started_at": run.started_at.isoformat() + "Z" if run.started_at else None,
                "executed_at": datetime.utcnow().isoformat() + "Z",
            },
            validation=output.get("validation") or ValidationInfo(),
            exposure=output.get("exposure") or ExposureInfo(),
            domain_data=output.get("domain_data", {}),
        )
        result = response.model_dump(mode="json")
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.result_json = json.dumps(result)
        for m in response.summary_metrics:
            self.db.add(
                ResultModel(id=str(uuid.uuid4()), run_id=run_id, result_type="metric", key=m.label, value=m.value)
            )
        for layer in response.layers:
            self.db.add(
                ResultModel(id=str(uuid.uuid4()), run_id=run_id, result_type=layer.kind, key=layer.key, value=layer.path)
            )
        self.db.commit()
        return result

    def _fail(self, run: ProcessingRunModel, message: str) -> None:
        run.status = "failed"
        run.error_message = message
        run.completed_at = datetime.utcnow()
        self.db.commit()
