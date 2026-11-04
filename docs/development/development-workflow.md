# NISAR Development & Git Workflow Guide

**Project:** NASA Space Apps — Dancing with the SARs (NISAR)
**Document:** `docs/development/development-workflow.md`
**Status:** Approved Team Standard

---

## 1. Branch Strategy & Naming Conventions

All contributors must adhere to domain-isolated feature branches created from `main`:

```
main (protected — stable, tested code only)
 └── feat/domain<X>-<feature-description>
 └── fix/domain<X>-<bug-description>
 └── data/manifest-<update-description>
 └── core/<platform-refactor>
```

### Allowed Branch Prefix Examples:
- `feat/domain1-otsu-refinement`
- `feat/domain2-burn-ratio-colormap`
- `feat/domain3-gnss-benchmark-eval`
- `feat/domain4-harvest-detection-proxy`
- `feat/domain5-terminus-edge-tracker`
- `data/manifest-evros-modis-update`
- `fix/cesium-overlay-depth-fail`

---

## 2. Local Development Environment

### Prerequisites:
- Python 3.11+
- Node.js 18+ (Node 20 or 24 recommended)
- GDAL / PROJ compatible environment

### Starting the Backend:
```bash
# From repository root:
source backend/venv/bin/activate
uvicorn app.main:app --app-dir backend --reload --port 8000
```
- Interactive Swagger API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### Starting the Frontend:
```bash
# From repository root:
cd frontend
npm install
npm run dev
```
- Web Application: `http://localhost:5173`

---

## 3. Pull Request Requirements & Quality Gates

Every Pull Request must pass the three mandatory verification suites before merging:

1. **Backend Integration Suite:**
   ```bash
   ./backend/venv/bin/pytest backend/tests
   ```
   *Requirement:* 100% pass (0 failures).

2. **Frontend Production Build:**
   ```bash
   npm run build --prefix frontend
   ```
   *Requirement:* Clean build with zero missing imports or broken JSX syntax.

3. **Geospatial Dataset Integrity:**
   ```bash
   backend/venv/bin/python scripts/validate_datasets.py
   ```
   *Requirement:* All registered GeoTIFFs and GeoJSONs must resolve, have valid CRS, and non-empty bounds.

4. **Map Engine Compatibility:**
   ```bash
   npm test
   ```
   *Requirement:* Legacy Cesium camera, geoid, and render governor unit tests must stay green.

---

## 4. Dataset Immutability Rules

- **Raw Data is Read-Only:** Files in `data/raw/` must NEVER be modified or overwritten in-place.
- **No Large GeoTIFF Commits to Git:** Large satellite rasters (>10 MB) must be managed via LFS or staged through download scripts (`scripts/acquire_real_sar_data.py`).
- **Manifest Edits:** Updates to `data/manifests/datasets.json` must be coordinated with Member 6 (Data Coordinator) to prevent schema drifts.

---

## 5. Conflict Resolution Protocol

1. **Domain Isolation:** Because domain logic is partitioned into `backend/app/domains/domainX/` and `frontend/src/domains/domainX/`, developers working on different domains should almost never encounter code conflicts.
2. **Shared Code Updates:** When modifying `frontend/src/components/DomainWorkspace.jsx` or `backend/app/services/pipeline.py`, developers must communicate with Member 1 (Integration Lead) before rebasing on `main`.
3. **No Direct Pushes to `main`:** All merges into `main` require a reviewed PR.
