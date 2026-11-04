from datetime import datetime
from typing import Optional, Any, Literal
from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["pending", "processing", "completed", "failed"]


class ProcessingRequest(BaseModel):
    """Shared request contract for POST /api/domains/{domain}/process.

    `inputs` maps a domain-defined input role (e.g. "baseline", "event",
    "reference_water") to a registered dataset ID. Each domain validates which
    roles are required and which product types they must have.
    """
    inputs: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    study_area_bbox: Optional[list[float]] = None


class MetricItem(BaseModel):
    label: str
    value: str
    unit: Optional[str] = None
    description: Optional[str] = None


class LayerReference(BaseModel):
    """A file produced by a run. `path` is relative to the data root; `url` is servable by the API."""
    key: str
    label: str
    kind: Literal["raster", "preview", "vector", "report"]
    path: str
    url: str
    description: Optional[str] = None
    bounds_wgs84: Optional[list[float]] = None


class ExplanationLevels(BaseModel):
    """Four-level explainability contract (see docs/shared-architecture.md)."""
    level1_visual: str
    level2_method: str
    level3_evidence: str
    level4_uncertainty: str


class ValidationInfo(BaseModel):
    status: Literal["not_validated", "compared_to_reference"] = "not_validated"
    validation_category: Literal[
        "not_validated",
        "independent_real_reference",
        "partially_independent_real_reference",
        "climatological_comparative_reference",
        "demonstration_synthetic_benchmark",
    ] = "not_validated"
    reference_independence: Optional[
        Literal[
            "not_validated",
            "independent_cross_sensor",
            "partially_independent_cross_pair",
            "climatological_comparative_baseline",
            "synthetic_benchmark",
        ]
    ] = None
    reference_independence_label: Optional[str] = None
    reference_dataset_id: Optional[str] = None
    reference_dataset_name: Optional[str] = None
    reference_source: Optional[str] = None
    reference_is_synthetic: bool = False
    evaluation_type: Optional[Literal["classification", "continuous"]] = None
    positive_class_definition: Optional[str] = None
    negative_class_definition: Optional[str] = None
    metrics: list[MetricItem] = Field(default_factory=list)
    confusion_matrix: Optional[dict[str, Any]] = None
    error_explorer: Optional[dict[str, Any]] = None
    method_comparison: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = "No independent reference data were supplied; results are unvalidated."


class ExposureInfo(BaseModel):
    status: Literal["not_evaluated", "evaluated"] = "not_evaluated"
    asset_dataset_id: Optional[str] = None
    asset_dataset_name: Optional[str] = None
    asset_source: Optional[str] = None
    asset_is_synthetic: bool = False
    metrics: list[MetricItem] = Field(default_factory=list)
    asset_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = "No supporting exposure asset dataset was supplied for spatial intersection."
    limitations: list[str] = Field(default_factory=list)


class StandardDomainResponse(BaseModel):
    run_id: str
    domain: str
    status: RunStatus
    analysis: str  # Short name of the analysis performed
    execution_time_seconds: float
    implementation_status: Literal["implemented", "partial", "demonstration", "planned"] = "implemented"
    is_synthetic_input: bool = False
    study_area: dict[str, Any] = Field(default_factory=dict)
    summary_metrics: list[MetricItem] = Field(default_factory=list)
    layers: list[LayerReference] = Field(default_factory=list)
    explanation: ExplanationLevels
    caveats: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    observation_dates: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    validation: ValidationInfo = Field(default_factory=ValidationInfo)
    exposure: ExposureInfo = Field(default_factory=ExposureInfo)
    domain_data: dict[str, Any] = Field(default_factory=dict)


class ProcessingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: Optional[str] = None
    domain: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    analysis: Optional[str] = None
    implementation_status: Optional[str] = None
    is_synthetic_input: Optional[bool] = None
    observation_dates: list[str] = Field(default_factory=list)
    validation_status: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
