# Shared Architecture Specification — Dancing with the SARs

**Version:** 2.1 (Frozen Post-Audit Platform Specification)
**Status:** Frozen Production Architecture & Contract Definition
**Target:** 6-Member Parallel Development Team

---

## 1. Architectural Philosophy & Boundaries

Dancing with the SARs is built around a decoupled **Micro-Domain, Shared-Core** architecture. The application enforces clean boundaries between client presentation, API mediation, metadata storage, heavy raster computation, and scientific validation:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Frontend: React 18 + Vite                       │
│  - Presentation Layer & Reusable UI Components                         │
│  - World-Map-First Event Explorer (`InteractiveWorldMap.jsx`)          │
│  - Synchronized Before/After Visualizer (`BeforeAfterViewer.jsx`)       │
│  - Domain Workspaces (`frontend/src/domains/domain1` .. `domain5`)     │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ HTTP REST (JSON & GeoJSON)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Backend: FastAPI Gateway                        │
│  - Central Route Registry (`backend/app/api/routes.py`)               │
│  - Shared Pipeline Framework (`backend/app/services/pipeline.py`)      │
│  - Validation & Error Engine (`backend/app/utils/validation.py`)       │
│  - Path-Traversal Sandbox & Storage (`storage/local_storage.py`)        │
└────────────┬───────────────────────┬───────────────────────┬───────────┘
             │                       │                       │
             ▼                       ▼                       ▼
┌────────────────────────┐  ┌─────────────────────┐  ┌───────────────────┐
│ Metadata & Catalog     │  │  Domain Processors  │  │ Filesystem Data   │
│ SQLite (`models.py`)   │  │ (Domains 1-5)       │  │ (`data/` Staged)  │
│ - Datasets, Assets     │  │ - Preprocessing     │  │ - raw/            │
│ - Runs & History       │  │ - Domain Science    │  │ - processed/      │
│ - Provenance Records   │  │ - Visualization     │  │ - outputs/        │
└────────────────────────┘  └─────────────────────┘  └───────────────────┘
```

### Core Architecture Rules
1. **Directory Isolation:** Domain specialists work exclusively inside `backend/app/domains/domainX/` and `frontend/src/domains/domainX/`.
2. **Centralized Platform Utilities:** The shared database schemas, dataset discovery, STAC retrieval, raster math, validation algorithms, and report generation live in shared modules and are coordinated by Team Member 6.
3. **No Breaking Schema Changes:** All domain pipelines communicate via the frozen `StandardDomainResponse` and `ProcessingRequest` Pydantic contracts.

---

## 2. Frozen Data Contracts (`backend/app/schemas/results.py`)

All domain pipelines must adhere to common Pydantic and JSON schemas so that the frontend UI, `MetricsPanel`, `BeforeAfterViewer`, and `EarthEventExplorer` can ingest and render results uniformly without domain-specific client hacks.

### 2.1 Standard Processing Request Schema
Submitted to `POST /api/domains/{domain_id}/process`:

```python
class ProcessingRequest(BaseModel):
    inputs: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    study_area_bbox: Optional[list[float]] = None
```

- `inputs`: Maps a domain-defined role (e.g., `"baseline"`, `"event"`, `"reference_water"`, `"dem"`, `"reference_flood"`, `"exposure_assets"`) to a registered dataset ID.
- `parameters`: Configurable domain parameters (e.g., `min_drop_db`, `filter_window`, `min_coherence`).
- `study_area_bbox`: Optional geographic bounding box override `[min_lon, min_lat, max_lon, max_lat]`.

### 2.2 Standard Processing Response Schema (`StandardDomainResponse`)
Returned by `POST /api/domains/{domain_id}/process`:

```python
class StandardDomainResponse(BaseModel):
    run_id: str                              # UUID for the execution
    domain: str                              # "domain1" .. "domain5"
    status: RunStatus                        # "completed", "failed", "pending"
    analysis: str                            # Human-readable analysis name
    execution_time_seconds: float
    is_synthetic_input: bool = False
    study_area: dict[str, Any] = Field(default_factory=dict)
    summary_metrics: list[MetricItem]        # Key statistics rendered by MetricsPanel
    layers: list[LayerReference]             # All output rasters, PNG previews, and vectors
    explanation: ExplanationLevels           # 4-tier explainability payload
    caveats: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    observation_dates: list[str] = Field(default_factory=list)
    provenance: dict[str, Any]               # Sensor metadata, timestamps, granule IDs
    validation: ValidationInfo               # Accuracy assessment & error explorer
    exposure: ExposureInfo                   # Infrastructure/asset intersection
    domain_data: dict[str, Any]              # Domain-specific auxiliary numerical values
```

### 2.3 Layer Reference Contract (`LayerReference`)
```python
class LayerReference(BaseModel):
    key: str                                 # Unique identifier (e.g., "flood_extent", "preview_event")
    label: str                               # Display label for UI
    kind: Literal["raster", "preview", "vector", "report"]
    path: str                                # Relative to DATA_ROOT_DIR (e.g., "outputs/domain1/.../mask.tif")
    url: str                                 # Servable API URL (e.g., "/api/outputs/domain1/.../preview.png")
    description: Optional[str] = None
    bounds_wgs84: Optional[list[float]] = None # [min_lon, min_lat, max_lon, max_lat]
```

### 2.4 Four-Level Explainability Contract (`ExplanationLevels`)
All domain pipelines must systematically generate text for the four tiers of scientific communication:

1. **Level 1 (Visual):** Clear descriptions of what visual layers are being presented (e.g., "Calibrated Sentinel-1A VV backscatter amplitude showing pre-flood baseline vs. crisis acquisition").
2. **Level 2 (Method):** Explicit statement of the algorithms, filtering windows, and threshold criteria used (e.g., "Bounded Otsu thresholding (-15.1 dB) applied to 5x5 boxcar filtered backscatter difference with slope masking <= 5.0°").
3. **Level 3 (Evidence):** Numerical measurements and ancillary data supporting the observation (e.g., "Specular drop of >= 3.0 dB over 4.16 km²; corroborated by Sentinel-2A MSI NDWI optical flood extent").
4. **Level 4 (Uncertainty & Caveats):** Non-negotiable scientific safeguards documenting conditions where the result may be uncalibrated, ambiguous, or false (e.g., "Emergent vegetation canopy and wind-roughened surface waves can elevate VV backscatter, leading to flood omission along agricultural basin margins").

### 2.5 Validation Contract & 4-Tier Independence Model (`ValidationInfo`)
Every validation run must report its category and independence tier honestly:

```python
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
```

---

## 3. Storage, Geospatial & Deliverable Conventions

### 3.1 Storage Root & Path Safety
- All data operations must resolve paths relative to `DATA_ROOT_DIR` (`data/` in the project root).
- The storage adapter (`backend/app/storage/local_storage.py`) strictly enforces base path confinement:
  ```python
  target_path = (self.base_path / relative_path).resolve()
  if not str(target_path).startswith(str(self.base_path)):
      raise ValueError("Access denied: Path traversal detected outside storage root.")
  ```
- **Rule:** Never return absolute host filesystem paths in API responses or HTML reports. Always return relative paths or servable URLs.

### 3.2 Raster & Web Visual Deliverables
1. **Analytical Deliverables:** Saved as georeferenced GeoTIFFs (`.tif`) with explicit CRS, transform, and nodata sentinels (`nodata=255` for binary uint8 masks, `nodata=-9999.0` for float32).
2. **Web Visual Deliverables:** Every pipeline generates accompanying optimized `.png` previews with alpha transparency formatted for the `BeforeAfterViewer` component and map overlays.

### 3.3 Vector Deliverables
- Vector layers (exposure assets, FIRMS hotspots, infrastructure footprints) are formatted strictly as standard **GeoJSON (FeatureCollection)** in `EPSG:4326` (WGS84 lat/lon).

---

## 4. Exportable Scientific Investigation Reports

All domains must support the exportable report endpoints:
- `GET /api/explorer/runs/{run_id}/export?format=json`: 15-section comprehensive structured JSON report.
- `GET /api/explorer/runs/{run_id}/export?format=html`: Standalone, printable scientific investigation report with HTML escaping and zero host path leakage.

---

## 5. Domain Pipeline Implementation Pattern

Every domain specialist implements their logic using the unified pipeline framework in `backend/app/services/pipeline.py`:

```python
class MyDomainPipeline(DomainPipeline):
    domain = "domainX"
    analysis_name = "My Domain Analysis"
    inputs = [
        InputSpec(role="baseline", label="Pre-Event Baseline", product_types=["sar_backscatter"]),
        InputSpec(role="event", label="Post-Event Observation", product_types=["sar_backscatter"]),
        InputSpec(role="reference", label="Reference Dataset", product_types=["reference_disturbance"], required=False),
    ]
    params = [
        ParamSpec(name="threshold_db", label="Threshold (dB)", type="number", default=2.0, min=0.5, max=10.0),
    ]

    def run(self, ctx: PipelineContext) -> StandardDomainResponse:
        # 1. Resolve inputs safely
        base_path = ctx.path_of("baseline")
        event_path = ctx.path_of("event")

        # 2. Read and align rasters using shared utilities
        base_r = read_band(base_path)
        event_r = read_band(event_path)
        event_aligned = reproject_to_match(event_r, base_r)

        # 3. Domain physics computation
        # ...

        # 4. Save analytical GeoTIFF and web preview PNG
        out_tif = ctx.out("change_mask.tif")
        out_png = ctx.out("change_preview.png")
        write_geotiff(out_tif, result_arr, base_r)
        write_preview_png(out_png, result_arr, palette)
        ctx.add_layer("change_mask", "Change Mask", "raster", "change_mask.tif")
        ctx.add_layer("change_preview", "Change Preview", "preview", "change_preview.png")

        # 5. Optional validation via shared validation engine
        val_info = ValidationInfo()
        if ctx.has("reference"):
            val_info = evaluate_binary_classification(ctx, "reference", result_bool, base_r, ...)

        # 6. Return unified response
        return StandardDomainResponse(
            run_id=ctx.run_id,
            domain=self.domain,
            status="completed",
            analysis=self.analysis_name,
            execution_time_seconds=...,
            summary_metrics=[MetricItem(label="Affected Area", value="12.4", unit="km²")],
            layers=ctx.layers,
            explanation=ExplanationLevels(...),
            validation=val_info,
            domain_data={...},
        )
```
