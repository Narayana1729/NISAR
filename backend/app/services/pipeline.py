"""Shared pipeline framework.

Each domain implements a `DomainPipeline` subclass that declares its input roles and
implements `run()`. The framework handles dataset resolution, product-type checks,
output directories, layer references, timing, and run persistence, so domain code
contains only domain-specific science.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.config import settings
from app.database.models import DatasetModel
from app.schemas.results import LayerReference


class PipelineInputError(ValueError):
    """Raised for invalid requests or unsuitable inputs (HTTP 422)."""


class PipelineExecutionError(RuntimeError):
    """Raised when pipeline execution fails scientifically or produces empty outputs (HTTP 500)."""


@dataclass
class InputSpec:
    role: str
    label: str
    product_types: list[str]
    required: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "label": self.label,
            "product_types": self.product_types,
            "required": self.required,
            "description": self.description,
        }


@dataclass
class ParamSpec:
    name: str
    label: str
    type: str  # number | integer | boolean | select | text
    default: Any
    description: str = ""
    options: Optional[list[str]] = None
    min: Optional[float] = None
    max: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class PipelineContext:
    run_id: str
    domain: str
    datasets: dict[str, DatasetModel]
    params: dict[str, Any]
    data_root: Path
    output_dir: Path
    bounds_wgs84: Optional[list[float]] = None
    layers: list[LayerReference] = field(default_factory=list)

    def path_of(self, role: str) -> Path:
        ds = self.datasets[role]
        p = (self.data_root / ds.relative_path).resolve()
        if not str(p).startswith(str(self.data_root)):
            raise PipelineInputError(f"Dataset for '{role}' resolves outside the data root.")
        if not p.is_file():
            raise PipelineInputError(f"File for dataset '{ds.name}' ({role}) is missing from storage.")
        return p

    def has(self, role: str) -> bool:
        return role in self.datasets

    def out(self, filename: str) -> Path:
        return self.output_dir / filename

    def add_layer(
        self,
        key: str,
        label: str,
        kind: str,
        filename: str,
        description: str = "",
        bounds_wgs84: Optional[list[float]] = None,
    ) -> None:
        rel = (self.output_dir / filename).relative_to(self.data_root).as_posix()
        url_part = (self.output_dir / filename).relative_to(self.data_root / "outputs").as_posix()
        self.layers.append(
            LayerReference(
                key=key,
                label=label,
                kind=kind,
                path=rel,
                url=f"/api/outputs/{url_part}",
                description=description or None,
                bounds_wgs84=bounds_wgs84 or self.bounds_wgs84,
            )
        )

from abc import ABC, abstractmethod


class DomainInterface(ABC):
    """Common domain interface defining the six standard lifecycle stages for all NISAR domain processors."""

    @abstractmethod
    def get_info(self) -> dict[str, Any]:
        """Stage 1: Return domain metadata, product type requirements, and parameter definitions."""
        ...

    @abstractmethod
    def validate_inputs(self, datasets: dict[str, Any], params: dict[str, Any]) -> None:
        """Stage 2: Validate dataset existence, product types, and parameter bounds."""
        ...

    @abstractmethod
    def preprocess(self, ctx: PipelineContext) -> Any:
        """Stage 3: Calibrate, multi-look, reproject, and align raw radar/optical inputs."""
        ...

    @abstractmethod
    def analyze(self, ctx: PipelineContext, preprocessed: Any = None) -> Any:
        """Stage 4: Execute domain-specific scientific algorithms."""
        ...

    @abstractmethod
    def generate_outputs(self, ctx: PipelineContext, analysis: Any = None) -> dict[str, Any]:
        """Stage 5: Produce GeoTIFF deliverables, RGB/RGBA preview overlays, and summary KPIs."""
        ...

    @abstractmethod
    def validate_results(self, ctx: PipelineContext, results: Any = None) -> Any:
        """Stage 6: Compute confusion matrices or continuous error statistics against reference benchmarks."""
        ...


class DomainPipeline(DomainInterface):
    domain: str = ""
    analysis_name: str = ""
    summary: str = ""
    inputs: list[InputSpec] = []
    params: list[ParamSpec] = []
    implementation_status: str = "planned"
    deferred_features: list[str] = []

    def get_info(self) -> dict[str, Any]:
        """Stage 1: Return domain metadata, inputs, and parameter specs."""
        return self.describe()

    def describe(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "analysis": self.analysis_name,
            "summary": self.summary,
            "implementation_status": self.implementation_status,
            "inputs": [i.to_dict() for i in self.inputs],
            "parameters": [p.to_dict() for p in self.params],
            "deferred_features": self.deferred_features,
        }

    def validate_inputs(self, datasets: dict[str, Any], params: dict[str, Any]) -> None:
        """Stage 2: Validate parameter bounds and required dataset roles."""
        self.resolve_params(params)
        for spec in self.inputs:
            if spec.required and spec.role not in datasets:
                raise PipelineInputError(f"Missing required input '{spec.label}' ({spec.role}).")

    def preprocess(self, ctx: PipelineContext) -> Any:
        """Stage 3: Domain-specific input ingestion and radiometric/geometric alignment."""
        raise NotImplementedError(f"Domain '{self.domain}' has not implemented scientific preprocess() stage.")

    def analyze(self, ctx: PipelineContext, preprocessed: Any = None) -> Any:
        """Stage 4: Domain-specific scientific analysis."""
        raise NotImplementedError(f"Domain '{self.domain}' has not implemented scientific analyze() stage.")

    def generate_outputs(self, ctx: PipelineContext, analysis: Any = None) -> dict[str, Any]:
        """Stage 5: Export rasters, preview PNGs, and compute quantitative metrics."""
        raise NotImplementedError(f"Domain '{self.domain}' has not implemented scientific generate_outputs() stage.")

    def validate_results(self, ctx: PipelineContext, results: Any = None) -> Any:
        """Stage 6: Compare against independent reference data if provided."""
        return None

    def resolve_params(self, supplied: dict[str, Any]) -> dict[str, Any]:
        known = {p.name: p for p in self.params}
        unknown = set(supplied) - set(known)
        if unknown:
            raise PipelineInputError(f"Unknown parameter(s): {', '.join(sorted(unknown))}")
        out: dict[str, Any] = {}
        for name, spec in known.items():
            value = supplied.get(name, spec.default)
            try:
                if spec.type == "number":
                    value = float(value)
                elif spec.type == "integer":
                    value = int(value)
                elif spec.type == "boolean":
                    value = value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes")
                elif spec.type == "select":
                    if value not in (spec.options or []):
                        raise PipelineInputError(f"Parameter '{name}' must be one of {spec.options}.")
                elif spec.type == "text":
                    value = None if value in (None, "") else str(value)
            except (TypeError, ValueError) as exc:
                if isinstance(exc, PipelineInputError):
                    raise
                raise PipelineInputError(f"Parameter '{name}' has an invalid value: {value!r}") from exc
            if spec.type in ("number", "integer"):
                if spec.min is not None and value < spec.min:
                    raise PipelineInputError(f"Parameter '{name}' must be >= {spec.min}.")
                if spec.max is not None and value > spec.max:
                    raise PipelineInputError(f"Parameter '{name}' must be <= {spec.max}.")
            out[name] = value
        return out

    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        """Execute domain pipeline orchestration."""
        prep = self.preprocess(ctx)
        analysis_data = self.analyze(ctx, prep)
        outputs = self.generate_outputs(ctx, analysis_data)
        validation_data = self.validate_results(ctx, outputs)
        if validation_data and isinstance(outputs, dict):
            outputs.setdefault("validation", validation_data)
        return outputs


def dataset_provenance(ds: DatasetModel) -> dict[str, Any]:
    from app.services.dataset_service import _to_response_dict

    info = _to_response_dict(ds)
    return {
        "dataset_id": ds.id,
        "name": ds.name,
        "product_type": ds.product_type,
        "sensor": ds.sensor,
        "polarization": ds.polarization,
        "acquisition_date": ds.acquisition_date,
        "value_scale": ds.value_scale,
        "units": ds.units,
        "source": ds.source,
        "crs": info.get("crs"),
        "bbox": info.get("bbox"),
        "bbox_wgs84": info.get("bbox_wgs84"),
        "dimensions": [info.get("width"), info.get("height")],
        "is_synthetic": bool(ds.is_synthetic),
    }


class Timer:
    def __init__(self) -> None:
        self.start = 0.0
        self.elapsed = 0.0

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        self.elapsed = time.perf_counter() - self.start


def max_pixels() -> int:
    return int(settings.MAX_RASTER_PIXELS)
