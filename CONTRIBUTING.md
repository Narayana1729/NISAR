# Contributing to NISAR — Dancing with the SARs

Welcome to the **NISAR (Dancing with the SARs)** collaborative development platform.

This guide outlines our team branching strategy, domain directory boundaries, shared API contracts, coding standards, and Pull Request procedures to enable seamless parallel development across our 6-person engineering team.

---

## 1. Quick Start & Installation

### Prerequisites
* **Node.js:** `v20.x` or `v24.x` (enforced by `package.json`)
* **Python:** `3.10` or `3.11` (Python 3.11 recommended)
* **Git:** Latest Git client with LFS support (if needed)

### Clone the Repository
```bash
git clone https://github.com/Narayana1729/NISAR.git
cd NISAR
```

### Backend Setup (FastAPI & GDAL/Rasterio)
```bash
# Create and activate Python virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate  # On Windows: backend\venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# Start backend development server
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
The backend API documentation is available at:
* Swagger UI: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`
* Health Check: `http://localhost:8000/api/health`

### Frontend Setup (Vite Console & Cesium 3D Globe)
```bash
# In the repository root
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:4173/` (or `http://localhost:5173/` depending on port assignment).

---

## 2. Six-Person Team Allocation & Domain Ownership

To prevent merge conflicts and architecture breakage, each team member is assigned an exclusive directory boundary and feature branch:

| Team Member | Role | Owned Directory Boundaries | Technical Specification | Assigned Feature Branch |
| :--- | :--- | :--- | :--- | :--- |
| **Member 1** | **Integration Lead + D5 Glaciers** | `backend/app/domains/domain5/`<br>`frontend/src/domains/domain5/`<br>`backend/app/services/` | [`docs/domains/domain5-glaciers-ice.md`](docs/domains/domain5-glaciers-ice.md) | `feature/domain5-glaciers-integration` |
| **Member 2** | **D1 Floods & Wetlands** | `backend/app/domains/domain1/`<br>`frontend/src/domains/domain1/` | [`docs/domains/domain1-floods-wetlands.md`](docs/domains/domain1-floods-wetlands.md) | `feature/domain1-floods` |
| **Member 3** | **D2 Forests & Wildfires** | `backend/app/domains/domain2/`<br>`frontend/src/domains/domain2/` | [`docs/domains/domain2-forests-wildfires.md`](docs/domains/domain2-forests-wildfires.md) | `feature/domain2-forests` |
| **Member 4** | **D3 Earthquakes & Deformation** | `backend/app/domains/domain3/`<br>`frontend/src/domains/domain3/` | [`docs/domains/domain3-earthquakes-deformation.md`](docs/domains/domain3-earthquakes-deformation.md) | `feature/domain3-earthquakes` |
| **Member 5** | **D4 Agriculture & Soil Conditions** | `backend/app/domains/domain4/`<br>`frontend/src/domains/domain4/` | [`docs/domains/domain4-agriculture-soil.md`](docs/domains/domain4-agriculture-soil.md) | `feature/domain4-agriculture` |
| **Member 6** | **Data QA + Earth Event Explorer** | `backend/app/api/endpoints/explorer.py`<br>`frontend/src/components/`<br>`data/manifests/` | [`docs/domains/README.md`](docs/domains/README.md) | `feature/data-qa-event-explorer` |

---

## 3. Project Structure & Directory Layout

```
gods-eye-view/
├── backend/
│   ├── app/
│   │   ├── api/routes.py              # Central FastAPI route aggregator
│   │   ├── api/endpoints/             # Domain endpoints (domain1..5, datasets, health)
│   │   ├── domains/                   # Micro-domain science processors
│   │   │   ├── domain1/               # Floods & Wetlands (Member 2)
│   │   │   ├── domain2/               # Forests & Wildfires (Member 3)
│   │   │   ├── domain3/               # Earthquakes & Ground Deformation (Member 4)
│   │   │   ├── domain4/               # Agriculture & Soil Conditions (Member 5)
│   │   │   └── domain5/               # Glaciers, Snow & Ice (Member 1)
│   │   ├── database/                  # SQLite models and connection
│   │   ├── schemas/results.py         # FROZEN Pydantic models (StandardDomainResponse)
│   │   ├── services/pipeline.py       # FROZEN pipeline base class (DomainPipeline)
│   │   ├── services/processing_service.py # Central execution coordinator
│   │   └── utils/                     # Shared raster math, validation, and exposure utils
│   ├── tests/                         # Pytest automated test suite
│   ├── nisar.db                       # Pre-seeded SQLite database catalog (90 KB)
│   └── requirements.txt               # Backend Python dependencies
├── data/
│   ├── manifests/datasets.json        # Single source of truth catalog (60 datasets)
│   ├── raw/                           # 60 verified input SAR rasters (25 MB total)
│   ├── intermediate/                  # Transient scratch arrays (.gitignore)
│   └── outputs/                       # Generated run outputs (.gitignore)
├── docs/
│   ├── architecture.md                # System boundaries & principles
│   ├── shared-architecture.md         # Frozen platform contracts
│   ├── team-work-plan.md              # Team responsibility matrix
│   └── domains/                       # Technical Specifications & Audit Report
│       ├── DOMAIN_SPECIFICATION_AUDIT.md # Official scientific & architecture audit
│       ├── domain1-floods-wetlands.md
│       ├── domain2-forests-wildfires.md
│       ├── domain3-earthquakes-deformation.md
│       ├── domain4-agriculture-soil.md
│       └── domain5-glaciers-ice.md
├── frontend/                          # React 18 + Vite frontend components
│   └── src/domains/                   # React domain workspaces
├── src/                               # CesiumJS 3D HUD & Observation console
└── package.json                       # Root NPM scripts & test runners
```

---

## 4. Team Git Rules & Workflow

All team members must adhere to these eight non-negotiable Git rules:

1. **Never directly push to `main`:** The `main` branch is protected and contains only tested, production-ready code.
2. **Work exclusively on your assigned branch:** Each member creates and commits only to their designated feature branch:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/<your-domain-branch>
   git push -u origin feature/<your-domain-branch>
   ```
3. **Pull Requests for all changes:** Code enters `main` only through GitHub Pull Requests with passing CI checks.
4. **Architectural Review Required:** Any proposed modifications to shared files require review and sign-off by **Team Member 1** (Integration Lead).
5. **Frozen API & Contract Policy:** No team member may independently edit:
   - `backend/app/schemas/results.py` (`StandardDomainResponse`, `LayerReference`, etc.)
   - `backend/app/services/pipeline.py` (`DomainPipeline`, `InputSpec`, `ParamSpec`)
   - `data/manifests/datasets.json` (Managed exclusively by Member 6)
6. **Always rebase or pull before branching:** Keep your local branch synchronized with `main` to prevent divergent commit histories.
7. **Test before opening a PR:** All frontend and backend tests must be green before PR submission.
8. **Never commit large generated files or secrets:**
   - Never commit files in `data/outputs/` or `data/intermediate/`
   - Never commit `.env`, credentials, or private tokens
   - Never commit files $> 10\text{ MB}$

### Pull Request & Integration Flowchart
```
                main (Protected, Stable)
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
  D1 Branch   D2 Branch   D3 Branch (etc.)
       │           │           │
   Develop     Develop     Develop
       │           │           │
       └─────► Pull Requests ◄─┘
                   │
           Lead Peer Review
                   │
             Merge to main
                   │
         CI Integration Testing
                   │
             Stable main
```

---

## 5. Coding Standards & Conventions

### Python Backend Standards
* **Python Version:** 3.11 with strict static typing.
* **Style:** Follow PEP 8 (4-space indentation, descriptive variable names).
* **Interface Inheritance:** All domain processors must inherit from `DomainPipeline` (`backend/app/services/pipeline.py`):
  ```python
  from app.services.pipeline import DomainPipeline, InputSpec, ParamSpec, PipelineContext

  class CustomDomainPipeline(DomainPipeline):
      domain = "domainX"
      analysis_name = "My Scientific Analysis"
      inputs = [InputSpec(...)]
      params = [ParamSpec(...)]

      def run(self, ctx: PipelineContext) -> dict:
          # Scientific logic here
          return {
              "metrics": [...],
              "explanation": {...},
              "validation": {...}
          }
  ```
* **No Raster Data in SQLite:** The SQLite database (`backend/nisar.db`) stores only metadata, run records, and scalar metrics. Rasters are written to `data/outputs/` and registered via `LayerReference`.

### Frontend Standards
* **Framework:** React 18 + Vite (ES modules, 2-space indentation, single quotes).
* **Shared UI Widgets:** Leverage common components (`BeforeAfterViewer.jsx`, `MetricsPanel.jsx`, `ProcessingStatus.jsx`) rather than implementing redundant UI logic.
* **Decoupled API Client:** Use `src/services/api.js` with `ENDPOINTS` from `src/services/endpoints.js`. Never hardcode `http://localhost:8000`.

---

## 6. Testing Commands

Before pushing commits or opening a Pull Request, run the complete verification suite locally:

### 1. Backend Pytest Suite
```bash
# Run all 49 backend test suites
backend/venv/bin/pytest backend/tests/
```
*Expected Result:* `49 passed, 0 failed` in $<10\text{s}$.

### 2. Frontend Unit Test Suite
```bash
# Run full unit and regression test suite
npm test
```
*Expected Result:* `1189 passed, 0 failed, 1 skipped`.

### 3. Production Build Check
```bash
# Verify Vite production bundle compiles cleanly
npm run build
```
*Expected Result:* `built in ~1.2s` with 0 syntax or bundling errors.

### 4. Git Whitespace & Formatting Check
```bash
git diff --check
```
*Expected Result:* Clean exit with code `0` (zero trailing whitespace errors).

---

## 7. Dataset Management Policy

* **60 Core Datasets:** All 60 verified datasets in `data/raw/` are tracked in version control (25 MB total). Do not rename, relocate, or delete files in `data/raw/`.
* **Demonstration Quarantining (Domain 4):** The 4 InSAR subsidence files in `data/raw/domain4/` (`demo_insar_*`) are quarantined historical artifacts and must not be used for agriculture. Domain 4 operates strictly in `demonstration` status until real Sentinel-1 RTC dual-pol time series are procured.
* **Adding New Datasets:** New datasets must be registered through Team Member 6 via `scripts/generate_dataset_manifest.py` and validated against `test_scientific_dataset_ownership.py`.
