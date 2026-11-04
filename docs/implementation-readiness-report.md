# Implementation Readiness & Scientific Audit Report: Dancing with the SARs

**Date:** October 2026
**Scope:** Repository audit, scientific feasibility evaluation, implementation gap analysis, and team MVP roadmap.
**Constraint:** Audit and documentation only — no application code was modified.

---

## Executive Summary

The project repository contains a clean, working architectural scaffold:
- **Frontend:** React + Vite single-page application with modular routing (`AppRoutes.jsx`), shared layout wrappers (`MainLayout`, `DomainLayout`), reusable UI components, and centralized API communication.
- **Backend:** FastAPI application with modular endpoint routers, SQLite metadata models, local storage abstraction, and modular domain pipelines (`domain1` through `domain5`).
- **Data Architecture:** Fully staged file-system directories (`data/raw/`, `data/staging/`, `data/processed/`, `data/intermediate/`, `data/outputs/`) with JSON catalog manifests.

However, a sharp divergence exists between the **high-level scientific aspirations** in the comprehensive domain documentation (e.g., full SBAS InSAR time-series inversion, sub-pixel feature tracking, cross-canopy double-bounce polarimetry) and the **immediate technical reality** of the repository (starter scaffold with placeholder mocks and basic web dependencies).

Attempting to implement complex raw SAR interferometric and polarimetric processing engines from scratch during a hackathon/challenge window introduces immense risk. To guarantee a **working, scientifically defensible, challenge-ready submission**, the team must adopt a **pragmatic MVP strategy**: utilize pre-processed analysis-ready data (ARD) and Radiometrically Terrain-Corrected (RTC) products, implement core raster operations cleanly, and enforce consistent Level 1–4 scientific explainability.

---

## 1. Codebase Inventory: Documented vs. Existing Assets

### 1.1 Frontend Routes & Pages
| Documented Domain / Screen | Route | Existing File Path | Current Status |
| :--- | :--- | :--- | :--- |
| **Home** | `/` | `frontend/src/pages/Home.jsx` | Implemented (renders hero & CTA) |
| **Dashboard** | `/dashboard` | `frontend/src/pages/Dashboard.jsx` | Implemented (renders 5 domain cards) |
| **Domain 1: Floods & Water Dynamics** | `/domain1` | `frontend/src/domains/domain1/Domain1Page.jsx` | Implemented (uses `DomainLayout`) |
| **Domain 2: Forests & Vegetation** | `/domain2` | `frontend/src/domains/domain2/Domain2Page.jsx` | Implemented (uses `DomainLayout`) |
| **Domain 3: Ice, Glaciers & Cryosphere** | `/domain3` | `frontend/src/domains/domain3/Domain3Page.jsx` | Implemented (uses `DomainLayout`) |
| **Domain 4: Land Movement & Urban Change** | `/domain4` | `frontend/src/domains/domain4/Domain4Page.jsx` | Implemented (uses `DomainLayout`) |
| **Domain 5: Wildfires & Land Disturbance** | `/domain5` | `frontend/src/domains/domain5/Domain5Page.jsx` | Implemented (uses `DomainLayout`) |
| **Domain 6: Earth Event Explorer** | Proposed `/earth-event-explorer` | *Not yet created* | **Gap:** Documented in `docs/domains/`, needs page & route |
| **Not Found** | `*` | `frontend/src/pages/NotFound.jsx` | Implemented (404 fallback) |

### 1.2 Reusable Shared Components
All eight core components requested in the specifications are physically implemented in `frontend/src/components/`:
1. `Navbar.jsx`: Top-level branding and primary navigation links.
2. `Sidebar.jsx`: Dynamic navigation driven by `config/domains.js`.
3. `DomainCard.jsx`: Overview card for the dashboard with configurable color accent.
4. `DatasetSelector.jsx`: Controlled dropdown for selecting registered observations.
5. `FileUploader.jsx`: File selection input with format filtering (`.h5`, `.tif`, `.nc`, `.zip`).
6. `ProcessingStatus.jsx`: Multi-state status badge and animated progress bar (`idle`, `pending`, `processing`, `completed`, `failed`).
7. `BeforeAfterViewer.jsx`: Interactive split-curtain range slider comparing baseline vs. post-event layers.
8. `MetricsPanel.jsx`: Two-column grid displaying key quantitative indicators with units.
9. `LoadingSpinner.jsx`: CSS-animated loading indicator for async operations.

### 1.3 Backend Modules & Endpoints
| Component | Existing File | Current Implementation State |
| :--- | :--- | :--- |
| **Application Entry** | `backend/app/main.py` | FastAPI app, CORS middleware, `/api/health`, router inclusion |
| **API Router** | `backend/app/api/routes.py` | Aggregates datasets and `domain1` through `domain5` |
| **Dataset API** | `backend/app/api/endpoints/datasets.py` | `GET /api/datasets`, `GET /api/datasets/{id}`, `POST /api/datasets/upload` |
| **Domain Endpoints** | `backend/app/api/endpoints/domainX.py` | `GET /info`, `POST /process`, `GET /runs` (returns starter mock payloads) |
| **Pipeline Modules** | `backend/app/domains/domainX/*.py` | Scaffolding files (`preprocessing.py`, `analysis.py`, `visualization.py`, `processor.py`) present with interface stubs |
| **Database & Models** | `backend/app/database/models.py` | SQLite schema with `DatasetModel`, `AssetModel`, `ProcessingRunModel`, `ResultModel` |
| **Storage & Security** | `backend/app/storage/local_storage.py` | Path traversal protection, safe file resolution within `data/` |
| **File Validation** | `backend/app/utils/validation.py` | File extension checking, size capping, filename sanitization |
| **Cloud Storage** | `backend/app/storage/object_storage.py` | Abstract interface `ObjectStorageInterface` + placeholder `CloudObjectStorageAdapter` |

---

## 2. Scientific Audit: Claims vs. Implementation Feasibility

| Domain | Documented Method / Claim | Scientific Feasibility in Challenge Timeline | Required Data & Pragmatic Audit Recommendation |
| :--- | :--- | :--- | :--- |
| **Floods** | Automatic Otsu thresholding, permanent water masking, sub-canopy L-band double bounce | **High for open water; Medium for sub-canopy.** Otsu thresholding on calibrated decibel imagery ($\Delta \text{dB} < -3\text{ dB}$) works reliably over open water. Sub-canopy detection requires dual-pol L-band data. | **MVP Approach:** Ingest pre-calibrated RTC Sentinel-1/NISAR GeoTIFFs. Compute Otsu threshold on single polarization (HH or VV). Mask static water using pre-packaged JRC water baseline or threshold baseline pass. |
| **Forests** | Cross-pol HV drop, multi-temporal persistence across $\ge 2$ passes, phenology filtering | **High for backscatter anomaly; Low for raw multi-year SAR time-series.** Ingesting and processing dozens of multi-date SLCs will overwhelm hackathon resources. | **MVP Approach:** Use a 2-date or 3-date RTC stack (pre-event dry season vs. post-disturbance). Calculate $\Delta \text{HV}$ anomaly. Filter with a static forest-cover mask (Copernicus or Hansen). Label as **"Potential Canopy Disturbance"** (never claim unverified deforestation). |
| **Cryosphere** | Sub-pixel Normalized Cross-Correlation (NCC) feature tracking, melt-onset absorption | **Medium for feature tracking; High for before/after terminus retreat.** True sub-pixel NCC on large rasters requires FFT libraries (`scipy`, `skimage`, or `opencv`) and high spatial texture. | **MVP Approach:** Focus on: (1) terminus calving edge retreat using edge detection and before/after curtain comparison; (2) melt onset via simple backscatter drop threshold ($\Delta \text{dB} < -5\text{ dB}$); (3) For velocity, integrate **pre-computed NASA ITS_LIVE velocity GeoTIFFs** rather than compiling raw cross-correlation engines. |
| **Land Movement** | Full SBAS/PSI time-series inversion, phase unwrapping via SNAPHU | **Unrealistic from raw SLCs; High using precomputed products.** Full InSAR unwrapping requires gigabytes of raw SLC data, complex orbit coregistration, and specialized software (ISCE3, GMTSAR, MintPy). | **MVP Approach:** Do not process raw phase in Python during the challenge. Ingest **pre-computed InSAR products from ASF HyP3** (wrapped interferograms, unwrapped displacement, coherence). Demonstrate point sampling, subsidence hotspot delineation, and Line-of-Sight explainability. |
| **Wildfires** | InSAR coherence collapse, HV canopy loss, FIRMS active thermal validation | **High using RTC + FIRMS API.** Cross-polarized backscatter difference combined with real NASA FIRMS thermal hotspot GeoJSON points provides an exceptional, scientifically defensible story. | **MVP Approach:** Calculate $\Delta \text{HV}$ between pre-fire and post-fire RTC rasters. Query or mock NASA FIRMS active fire points within the burn window. Intersect the two layers to generate a **Corroborated Disturbance Evidence Score**. |
| **Event Explorer** | Cascading-hazard cross-layer analysis, Evidence Chain DAG | **High as an orchestrator.** Feasible if Domain 1–5 processors return standardized JSON responses and GeoTIFF outputs. | **MVP Approach:** Build a central event selector with 3 curated crises (e.g., Hurricane Helene flood/forest impact, California wildfire, Turkey earthquake). Dispatch queries to underlying domain services and present unified findings. |

---

## 3. Dependency & Infrastructure Analysis

### Current Installed Stack
- **Frontend Dependencies:** `react (18.3)`, `react-dom (18.3)`, `react-router-dom (6.23)`, `vite (5.2)`.
- **Backend Dependencies:** `fastapi (0.110)`, `uvicorn (0.28)`, `pydantic (2.6)`, `pydantic-settings (2.2)`, `sqlalchemy (2.0)`, `python-multipart (0.0.9)`, `pytest (8.0)`, `httpx (0.27)`.

### Missing Scientific & Geospatial Dependencies (To Be Added)
The existing backend lacks raster and geospatial libraries. To execute true raster difference operations without external heavy GIS software, the backend will require:
1. `numpy`: Array operations, decibel conversions, and thresholding.
2. `rasterio`: Reading and writing GeoTIFF metadata, coordinate transforms, and bands.
3. `scipy`: Basic Gaussian speckle filtering and Otsu thresholding.
4. `shapely` & `geopandas` (optional): Vector polygon intersection for FIRMS points and administrative boundaries.

> **Recommendation for Challenge Environment:** Keep geospatial processing lightweight. If GDAL/Rasterio C-bindings pose installation issues on certain team OS environments, use `numpy` + `PIL` / `scipy` on normalized 2D matrices, or pre-convert GeoTIFFs to lightweight NumPy arrays (`.npz`) and PNG preview overlays.

---

## 4. The Realistic MVP: Scope & Interaction Model

To ensure completion, every domain must support the **identical core user interaction loop**:

```
Select Event / Preset
        ↓
Select Region & Dates (Pre & Post)
        ↓
Inspect Calibrated Observations (Before vs. After Slider)
        ↓
Examine Detected Change Overlay (Thresholded Anomaly)
        ↓
Review Multi-Tier Evidence & Uncertainty Panel (Levels 1–4)
        ↓
Export Findings & Provenance Summary (JSON / GeoTIFF)
```

### Domain-by-Domain MVP Core Feature Backlog

| Domain | MVP Core Analysis Feature | Input Data Requirement | Processing Method | Deliverable Output |
| :--- | :--- | :--- | :--- | :--- |
| **Domain 1: Floods** | Before-and-after flood inundation change layer | Pre/post RTC GeoTIFFs (HH or VV) | Log difference ($\Delta \text{dB}$) + Otsu thresholding | Binary inundation raster, flooded area ($\text{km}^2$), curtain viewer |
| **Domain 2: Forests** | Potential canopy disturbance alert layer | Pre/post dual-pol RTC GeoTIFFs (HV) | Relative HV drop threshold ($\Delta \text{HV} < -3.5\text{ dB}$) | Disturbance mask, affected area (ha), polarimetric preview |
| **Domain 3: Cryosphere** | Glacier terminus change & precomputed velocity display | Pre/post polar SAR pair + ITS_LIVE velocity tile | Calving margin edge detection + velocity color mapping | Terminus shift vectors, peak flow speed ($\text{m/yr}$), velocity heatmap |
| **Domain 4: Land Movement** | Ground deformation velocity display & point inspector | Precomputed ASF HyP3 unwrapped InSAR GeoTIFF | Line-of-sight velocity color mapping + PS point time-series extraction | Subsidence bowl contours, peak subsidence ($\text{mm/yr}$), PS curve |
| **Domain 5: Wildfires** | Smoke-penetrating burn scar with FIRMS thermal overlay | Pre/post SAR RTC GeoTIFFs + NASA FIRMS GeoJSON | Backscatter drop ($\Delta \text{HV}$) + thermal spatial cross-match | Burn scar perimeter, thermal correlation count, hazard area |
| **Domain 6: Event Explorer** | Unified multi-hazard event timeline & evidence brief | Chained outputs from Domains 1–5 | Multi-layer timeline aggregation + Evidence Chain DAG | Multi-hazard overlay map, combined impact brief, JSON report |

---

## 5. Domain Ownership & Team Integration Plan

A balanced 6-person team allocation ensuring parallel development without file conflicts:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Shared Infrastructure Lead (Team Member 6 - Earth Event Explorer Lead) │
│  - Centralizes API contracts, common types, event catalog, and exports │
└────────────────────────────────────────────────────────────────────────┘
       │                 │                 │                 │
       ▼                 ▼                 ▼                 ▼
 ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
 │ Member 1 │      │ Member 2 │      │ Member 3 │      │ Member 4 │
 │  Floods  │      │ Forests  │      │Cryosphere│      │Land Mvmt │
 │(Domain 1)│      │(Domain 2)│      │(Domain 3)│      │(Domain 4)│
 └──────────┘      └──────────┘      └──────────┘      └──────────┘
                         │
                         ▼
                   ┌──────────┐
                   │ Member 5 │
                   │Wildfires │
                   │(Domain 5)│
                   └──────────┘
```

### Detailed Role Assignments & Immediate Deliverables

#### Team Member 1: Floods & Water Dynamics (`domain1`)
- **Frontend Focus:** `frontend/src/domains/domain1/Domain1Page.jsx` (integrate `BeforeAfterViewer` and inundation layer switcher).
- **Backend Focus:** `backend/app/domains/domain1/analysis.py` (implement Otsu/difference thresholding on pre/post arrays).
- **Data Responsibility:** Procure 1 representative pre/post flood pair (e.g., Midwest USA flood or Pakistan flood Sentinel-1 RTC).
- **First Task:** Replace placeholder metrics in `domain1.py` with real inundation calculations from two test arrays.

#### Team Member 2: Forests & Vegetation (`domain2`)
- **Frontend Focus:** `frontend/src/domains/domain2/Domain2Page.jsx` (implement canopy change inspection and multi-pass toggle).
- **Backend Focus:** `backend/app/domains/domain2/analysis.py` (implement $\Delta \text{HV}$ thresholding and forest baseline masking).
- **Data Responsibility:** Procure 1 pre/post deforestation or storm blowdown pair (e.g., Pará, Brazil or Pacific Northwest).
- **First Task:** Connect `Domain2Page` to `POST /api/domains/domain2/process` to display detected disturbance hectares.

#### Team Member 3: Ice, Glaciers & Cryosphere (`domain3`)
- **Frontend Focus:** `frontend/src/domains/domain3/Domain3Page.jsx` (polar map framing and terminus retreat curtain viewer).
- **Backend Focus:** `backend/app/domains/domain3/visualization.py` & `analysis.py` (terminus edge filtering and ITS_LIVE velocity tile ingestion).
- **Data Responsibility:** Procure 1 calving glacier pair (e.g., Jakobshavn Isbræ or Pine Island Glacier) + 1 NASA ITS_LIVE velocity tile.
- **First Task:** Render terminus shift vectors and sample velocity values at the glacier centerline.

#### Team Member 4: Land Movement & Urban Change (`domain4`)
- **Frontend Focus:** `frontend/src/domains/domain4/Domain4Page.jsx` (divergent deformation color-bar and PS point-click inspector).
- **Backend Focus:** `backend/app/domains/domain4/analysis.py` (ingest precomputed ASF HyP3 unwrapped GeoTIFF, extract LOS subsidence contours).
- **Data Responsibility:** Procure 1 precomputed InSAR deformation product from ASF HyP3 (e.g., Central Valley, CA or Mexico City subsidence).
- **First Task:** Enable user click on the deformation map to display a multi-date subsidence time-series chart.

#### Team Member 5: Wildfires & Land Disturbance (`domain5`)
- **Frontend Focus:** `frontend/src/domains/domain5/Domain5Page.jsx` (burn scar curtain view with active FIRMS thermal point overlay).
- **Backend Focus:** `backend/app/domains/domain5/analysis.py` (compute $\Delta \text{HV}$ drop, ingest FIRMS GeoJSON points, calculate correlation count).
- **Data Responsibility:** Procure 1 pre/post wildfire pair (e.g., Canadian mega-fires or California wildfire) + concurrent FIRMS active fire GeoJSON.
- **First Task:** Intersect radar disturbance polygons with FIRMS points to generate the Disturbance Evidence Score.

#### Team Member 6: Earth Event Explorer & Platform Integration (`domain6`)
- **Frontend Focus:** Create `frontend/src/pages/EarthEventExplorer.jsx` and register in `routes/AppRoutes.jsx`; build the Evidence Chain DAG.
- **Backend Focus:** Create `backend/app/api/endpoints/explorer.py`; implement multi-domain task dispatcher.
- **Data Responsibility:** Curate `data/manifests/events.json` containing 3 multi-hazard crisis presets with metadata and pre-staged sample data.
- **First Task:** Build the unified multi-hazard timeline view that loads and displays outputs from Domains 1–5 in a single coherent screen.

---

## 6. Shared Data Contract Standardization

To guarantee seamless integration between all domain pipelines and the Earth Event Explorer, all domain endpoints must adhere to a strict shared contract:

### 6.1 Standard Domain Request Schema
```python
class StandardDomainRequest(BaseModel):
    dataset_id: str
    aoi_bbox: Optional[list[float]] = None  # [min_lon, min_lat, max_lon, max_lat]
    observation_dates: list[str]            # ["YYYY-MM-DD", "YYYY-MM-DD"]
    params: dict[str, Any] = {}
```

### 6.2 Standard Domain Response Schema
```python
class MetricItem(BaseModel):
    label: str
    value: str
    unit: Optional[str] = None

class ExplanationLevels(BaseModel):
    level1_visual: str
    level2_method: str
    level3_evidence: str
    level4_uncertainty: str

class StandardDomainResponse(BaseModel):
    domain: str
    status: str                             # "completed", "failed", "pending"
    summary_metrics: list[MetricItem]
    output_rasters: list[str]               # Relative file paths in data/outputs/
    output_vectors: Optional[list[str]] = []
    explanation: ExplanationLevels
    provenance: dict[str, Any]             # Granules, sensor, algorithm version, timestamps
```

---

## 7. Immediate Action Plan & Next Steps

1. **Team Alignment:** Review this readiness audit with all 6 team members and confirm individual domain ownership.
2. **Freeze MVP Scope:** Formally commit to the pre-processed RTC / ARD pipeline model; defer raw phase unwrapping and sub-pixel cross-correlation engines to post-challenge development.
3. **Data Staging:** Each domain owner places one sample pre/post GeoTIFF pair in `data/raw/domainX/` and registers it in `data/manifests/datasets.json`.
4. **Implement First End-to-End Slice:** Team Member 1 (Floods) completes the first working pipeline slice (`Domain1Page` $\leftrightarrow$ `domain1.py` $\leftrightarrow$ array difference $\leftrightarrow$ `BeforeAfterViewer`).
5. **Replicate Pattern:** Members 2–5 replicate the established pattern for their respective domains.
6. **Cross-Domain Synthesis:** Member 6 integrates all 5 outputs into the Earth Event Explorer.
