# Architecture Overview — NISAR Platform

## 1. System Philosophy & Boundaries

The NISAR project provides a modular platform for processing, analyzing, and visualizing Synthetic Aperture Radar (SAR) products across 5 independent domains. The design enforces clean boundaries:

```
[ Frontend: React + Vite ]
           │ (HTTP / JSON / REST)
           ▼
[ Common Backend: FastAPI API Gateway & Middleware ]
           ├──────────────┬──────────────────┬─────────────────┐
           ▼              ▼                  ▼                 ▼
   [Dataset API]   [Domain Endpoints]   [Storage Engine]  [SQLite Meta DB]
                          │                  │
                          ▼                  ▼
                  [Domain Processors]    [Data Dirs]
                  (Indep. pipelines)   (raw/staging/out)
```

### 1.1 Frontend Boundary
- **Framework:** React + Vite (Single Page Application).
- **Navigation:** Config-driven routing via `AppRoutes.jsx` and domain registration in `config/domains.js`.
- **Decoupled API Client:** Centralized `services/api.js` using `import.meta.env.VITE_API_BASE_URL` prevents hardcoding of server addresses.
- **Shared Components:** Reusable, domain-agnostic UI widgets (`BeforeAfterViewer`, `MetricsPanel`, `DatasetSelector`, `FileUploader`, `ProcessingStatus`, `LoadingSpinner`) provide a uniform experience while letting each domain customize its sub-views.

### 1.2 Backend Boundary
- **Framework:** Python + FastAPI.
- **Routing:** Centralized aggregator `api/routes.py` cleanly separates common dataset operations from domain-specific endpoints.
- **Independence:** Domain algorithms reside in `backend/app/domains/<domain_id>/` and operate as decoupled micro-modules with isolated preprocessing, analysis, visualization, and orchestration steps.
- **Safety:** Storage utilities sanitize incoming file names, check extensions and sizes, and enforce base directory boundaries to prevent path traversal vulnerabilities.

### 1.3 Database vs. Storage Boundary
- **SQLite Database (`backend/app/database/`):** Dedicated exclusively to lightweight metadata (dataset catalog, processing runs, status tracking, scalar metrics). **Raster imagery and large binary files are never stored in SQLite.**
- **Storage Layer (`backend/app/storage/`):** Handles files on disk or cloud object storage. Adapters enforce root path isolation and expose an abstract interface `ObjectStorageInterface` for zero-friction migration to AWS S3, Google Cloud Storage, or Azure Blob in the future.

### 1.4 Domain Pipeline Modules
Each domain (`domain1` through `domain5`) contains four core lifecycle files:
1. `preprocessing.py`: Ingestion, calibration, and filtering of SAR inputs.
2. `analysis.py`: Scientific calculation (interferometric displacement, polarimetric decomposition, classification).
3. `visualization.py`: Generation of difference maps, GeoTIFFs, and PNG previews.
4. `processor.py`: Orchestrator sequencing preprocessing -> analysis -> visualization.
