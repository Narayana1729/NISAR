# NISAR Scientific Domain Technical Specifications Index
**Platform:** Dancing with the SARs (NISAR Earth Observation Console)
**Version:** 2.0 (Post-Audit Domain Architecture Specifications)
**Status:** Approved Technical Contracts for 6-Person Parallel Development Team

---

## 1. Domain Specifications Catalog

> **Scientific & Architectural Audit Report:** See [`DOMAIN_SPECIFICATION_AUDIT.md`](DOMAIN_SPECIFICATION_AUDIT.md) for the complete scientific classification, threshold verification, and contract audit across all 5 specifications.

| Domain ID | Domain Name | Scientific Specification Document | Team Owner | Study Area & Event | Validated Datasets | Implementation Readiness |
| :---: | :--- | :--- | :---: | :--- | :---: | :---: |
| **D1** | Floods & Wetlands | [domain1-floods-wetlands.md](domain1-floods-wetlands.md) | **Team Member 2** | Thessaly Basin & Lake Karla, Greece (Storm Daniel) | **11** | `READY FOR IMPLEMENTATION` |
| **D2** | Forests & Wildfires | [domain2-forests-wildfires.md](domain2-forests-wildfires.md) | **Team Member 3** | Pará, Brazil (Clearing); Dadia, Greece (Fire); Park Fire, CA | **26** | `READY FOR IMPLEMENTATION` |
| **D3** | Earthquakes & Ground Deformation | [domain3-earthquakes-deformation.md](domain3-earthquakes-deformation.md) | **Team Member 4** | Tyrnavos Basin, Greece (2021 $M_w\ 6.3$ Earthquake) | **6** | `READY FOR IMPLEMENTATION` (Workflow A) |
| **D4** | Agriculture & Soil Conditions | [domain4-agriculture-soil.md](domain4-agriculture-soil.md) | **Team Member 5** | Central Valley, California (Sacramento/San Joaquin) | **0 Real** *(4 Unresolved SJV InSAR)* | `BLOCKED BY DATA` (Demonstration Mode Only) |
| **D5** | Glaciers, Snow & Ice | [domain5-glaciers-ice.md](domain5-glaciers-ice.md) | **Team Member 1** *(Lead)* | Jakobshavn Isbræ & Ilulissat Icefjord, Greenland | **13** | `READY FOR IMPLEMENTATION` |
| **Total** | | | | | **60 Datasets** | |

---

## 2. Six-Person Team Ownership & Allocation

```
                        ┌────────────────────────────────────────────────────────────┐
                        │   Team Member 1: Integration Lead & Cryosphere (D5) Lead   │
                        │   - Frozen API Architecture, Engine Pipeline Core, D5       │
                        └─────────────────────────────┬──────────────────────────────┘
                                                      │
         ┌─────────────────────┬──────────────────────┼──────────────────────┬─────────────────────┐
         ▼                     ▼                      ▼                      ▼                     ▼
  ┌──────────────┐      ┌──────────────┐       ┌──────────────┐       ┌──────────────┐      ┌──────────────┐
  │   Member 2   │      │   Member 3   │       │   Member 4   │       │   Member 5   │      │   Member 6   │
  │   Floods &   │      │  Forests &   │       │ Earthquakes  │       │ Agriculture  │      │ Data QA &    │
  │   Wetlands   │      │  Wildfires   │       │& Deformation │       │   & Soil     │      │ Event Explorer│
  │  (Domain 1)  │      │  (Domain 2)  │       │  (Domain 3)  │       │  (Domain 4)  │      │  (Explorer)  │
  └──────────────┘      └──────────────┘       └──────────────┘       └──────────────┘      └──────────────┘
```

| Team Member | Primary Role | Directory Boundaries | Core Physical Scope |
| :--- | :--- | :--- | :--- |
| **Team Member 1** | **Integration Lead + D5 Glaciers** | `backend/app/domains/domain5/`<br>`frontend/src/domains/domain5/`<br>`backend/app/services/` | Overall platform architecture, shared pipeline engine, glacier velocity fields, ice stream dynamics, and calving margin analysis. |
| **Team Member 2** | **D1 Floods & Wetlands** | `backend/app/domains/domain1/`<br>`frontend/src/domains/domain1/` | Specular radar scattering drops, open-water bimodal thresholding, permanent water subtraction, DEM slope drainage masking, and optical NDWI validation. |
| **Team Member 3** | **D2 Forests & Wildfires** | `backend/app/domains/domain2/`<br>`frontend/src/domains/domain2/` | Cross-polarized volume scattering loss, forest baseline masking, smoke-penetrating burn scar mapping, and NASA FIRMS thermal corroboration. |
| **Team Member 4** | **D3 Earthquakes & Deformation** | `backend/app/domains/domain3/`<br>`frontend/src/domains/domain3/` | Line-of-Sight InSAR displacement, coherence quality filtering, surface strain gradients, and cross-pair geodetic residual validation. |
| **Team Member 5** | **D4 Agriculture & Soil Conditions** | `backend/app/domains/domain4/`<br>`frontend/src/domains/domain4/` | Multi-temporal dual-pol canopy ratios, relative surface wetness proxies, parcel boundary masking, and demonstration pipeline maintenance. |
| **Team Member 6** | **Data QA + Earth Event Explorer** | `backend/app/api/endpoints/explorer.py`<br>`frontend/src/components/`<br>`data/manifests/` | Catalog consistency audits, multi-hazard event correlation, cross-domain test suites, and shared visualization components. |

---

## 3. Shared Architecture & Frozen Contracts

Every domain operates strictly within the frozen platform architecture documented in `docs/shared-architecture.md` and `docs/architecture.md`:

### Backend Invariants (`backend/app/`)
* **Pipeline Base Class:** Every domain subclass must inherit from `DomainPipeline` (`backend/app/services/pipeline.py`), declaring typed `inputs: list[InputSpec]` and `params: list[ParamSpec]`.
* **Execution Service:** Endpoints dispatch work exclusively through `ProcessingService(db).execute(pipeline, payload)`.
* **Standard Response:** Every domain endpoint must return a valid `StandardDomainResponse` (`backend/app/schemas/results.py`), including:
  * `summary_metrics: list[MetricItem]`
  * `layers: list[LayerReference]`
  * `explanation: ExplanationLevels` (4-tier explainability: Visual, Method, Evidence, Uncertainty)
  * `validation: ValidationInfo`
  * `exposure: ExposureInfo`
* **Frozen Contracts:** No domain developer may independently modify files under `backend/app/schemas/`, `backend/app/services/pipeline.py`, or `backend/app/database/models.py`.

### Frontend Invariants (`frontend/src/`)
* **Shared UI Components:** All domain workspaces utilize shared components:
  * `BeforeAfterViewer`: Synchronized side-by-side or swipe comparison.
  * `MetricsPanel`: Headline KPI cards.
  * `ProcessingStatus`: Bounded execution spinners and status banners.
  * `InteractiveWorldMap` & `SharedMap`: Leaflet/Cesium geospatial displays.
* **Domain Directory Isolation:** Domain-specific views and controls reside strictly inside `frontend/src/domains/domainX/`.

---

## 4. Cross-Domain Output Conventions

To ensure uniform client rendering, map tiling, and automated report generation, all five domains follow these standard output layer conventions:

| Layer Key Convention | Layer Kind | Format | Content & Styling Standard |
| :--- | :--- | :--- | :--- |
| `baseline_preview` | `preview` | RGBA PNG | Grayscale or standard baseline image representing the pre-event reference state. |
| `event_preview` / `monitoring_preview` | `preview` | RGBA PNG | Grayscale or standard observation representing the active or post-event state. |
| `change_preview` / `delta_map` | `preview` | RGBA PNG | Continuous difference map with calibrated diverging color ramps. |
| `*_overlay` | `preview` | Transparent RGBA PNG | High-contrast categorical classification overlay (Cyan=Flood, Red=Burn, Amber=Harvest). |
| `*_geotiff` | `raster` | Cloud-Optimized GeoTIFF | Deliverable georeferenced metric float32/uint8 raster with embedded projection and NoData mask. |
| `validation_overlay` | `preview` | RGBA PNG | Four-color Error Explorer map (Green=TP, Red=FP, Blue=FN, Gray=TN). |
| `validation_geotiff` | `raster` | Cloud-Optimized GeoTIFF | Residual difference grid ($d_{\text{observed}} - d_{\text{reference}}$). |

---

## 5. Domain Integration Checklist

Before any domain is tagged as `implemented` and merged to `main`, the domain specialist must complete this verification checklist:

- [ ] **Input Product Validation:** Pipeline rejects incorrect product types (e.g., InSAR passed to Agriculture) with clean HTTP 422 errors.
- [ ] **Physical File Preservation:** No physical files in `data/raw/` have been moved, renamed, or modified.
- [ ] **Real vs. Synthetic Integrity:** When processing demonstration datasets, `is_synthetic_input` is truthfully set to `true`.
- [ ] **4-Tier Explainability:** All four explanation fields (`level1_visual`, `level2_method`, `level3_evidence`, `level4_uncertainty`) are populated with domain-accurate scientific text.
- [ ] **NoData Exclusion:** All metric calculations and confusion matrices strictly exclude NoData pixels.
- [ ] **Validation Independence Level:** The validation payload specifies an approved tier string (`"independent_cross_sensor"`, `"partially_independent_cross_pair"`, `"climatological_comparative_baseline"`, or `"demonstration_synthetic_benchmark"`).
- [ ] **Automated Test Coverage:** Complete unit tests pass in `backend/tests/` without warnings or skips.
- [ ] **Vite Production Build:** Frontend compiles cleanly with `npm run build`.
