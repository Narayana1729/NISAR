# Team Domain Ownership & Frozen Interface Agreement
**NISAR — Dancing with the SARs (Phase 4 Foundation)**

**Status:** Frozen Platform Contract & Domain Ownership Charter
**Version:** 2.1 (Post-Scientific Audit & Multi-Domain Verification)
**Target:** 6-Member Specialized Development Team

---

## 1. Team Allocation & Architectural Boundaries

To enable five domain specialists to develop their science and algorithms in parallel without merge conflicts or application breakage, strict directory boundaries and frozen core contracts are established:

```
                               ┌────────────────────────────────────────────────────────┐
                               │ Team Member 1: Platform Integration Lead & D5 Cryo     │
                               │ - Frozen API Schemas, Shared Storage & Raster Utils   │
                               │ - D5 Glaciers & Snow/Ice Pipeline & Terminus Analysis  │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
          ┌────────────────────────┬───────────────────────┼───────────────────────┬────────────────────────┐
          ▼                        ▼                       ▼                       ▼                        ▼
   ┌──────────────┐         ┌──────────────┐        ┌──────────────┐        ┌──────────────┐         ┌──────────────┐
   │   Member 2   │         │   Member 3   │        │   Member 4   │        │   Member 5   │         │   Member 6   │
   │   Floods &   │         │  Forests &   │        │ Earthquakes  │        │ Agriculture  │         │  Data QA &   │
   │   Wetlands   │         │  Wildfires   │        │& Deformation │        │    & Soil    │         │Earth Event   │
   │  (Domain 1)  │         │  (Domain 2)  │        │  (Domain 3)  │        │  (Domain 4)  │         │  Explorer    │
   └──────────────┘         └──────────────┘        └──────────────┘        └──────────────┘         └──────────────┘
```

### Responsibility Matrix & Technical Specifications

| Team Member | Role | Owned Directory Boundaries | Technical Specification | Core Physical Phenomenon & Investigation Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Member 1** | **Integration Lead + D5 Glaciers** | `backend/app/domains/domain5/`<br>`frontend/src/domains/domain5/`<br>`backend/app/services/` | [domain5-glaciers-ice.md](domains/domain5-glaciers-ice.md) | Platform integration, shared pipeline contracts, glacier surface velocity dynamics, ice stream discharging trunks, calving front retreat, and ITS_LIVE climatological anomaly. |
| **Member 2** | **D1 Floods & Wetlands** | `backend/app/domains/domain1/`<br>`frontend/src/domains/domain1/` | [domain1-floods-wetlands.md](domains/domain1-floods-wetlands.md) | Detect changes in inundation, flooded areas and wetland extent. Specular radar scattering reduction, smooth open water vs. wind-roughened waves, permanent water dynamics, DEM slope drainage masking, and optical NDWI validation. |
| **Member 3** | **D2 Forests & Wildfires** | `backend/app/domains/domain2/`<br>`frontend/src/domains/domain2/` | [domain2-forests-wildfires.md](domains/domain2-forests-wildfires.md) | Analyse changes in forest structure and fire-affected areas. Cross-polarized ($\text{VH}/\text{HV}$) volume-scattering drop, baseline forest masking, smoke penetration, NASA FIRMS thermal anomaly corroboration, and MMU sieving. |
| **Member 4** | **D3 Earthquakes & Deformation** | `backend/app/domains/domain3/`<br>`frontend/src/domains/domain3/` | [domain3-earthquakes-deformation.md](domains/domain3-earthquakes-deformation.md) | Investigate surface displacement and coseismic fault offsets. Interferometric phase unwrapping, Line-of-Sight ($\text{LOS}$) displacement geometry, temporal/geometric decorrelation, phase coherence filtering, and cross-pair geodetic residual validation. |
| **Member 5** | **D4 Agriculture & Soil Conditions** | `backend/app/domains/domain4/`<br>`frontend/src/domains/domain4/` | [domain4-agriculture-soil.md](domains/domain4-agriculture-soil.md) | Analyse agricultural surface changes in demonstration mode. Multi-temporal repeat-pass $\text{VV}/\text{VH}$ backscatter dynamics, relative soil moisture proxies, crop canopy development vs. harvesting, agricultural parcel masking, and data acquisition planning. |
| **Member 6** | **Data QA & Event Explorer** | `backend/app/api/endpoints/explorer.py`<br>`frontend/src/components/`<br>`data/manifests/` | [domains/README.md](domains/README.md) | Catalog consistency audits, multi-hazard event correlation, cross-domain test suites, shared visualization components, and before-and-after synchronizers. |

---

## 2. Frozen Platform Contracts (Do Not Modify Independently)

To avoid breaking the shared frontend, database, and report exporters, the following contracts are **FROZEN**. Domain owners must implement their logic inside these boundaries.

### 2.1 The Standard Processing Pipeline Interface (`DomainPipeline`)

Every domain implements a `DomainPipeline` subclass inside `backend/app/domains/domainX/processor.py`:

```python
class DomainPipeline(ABC):
    domain: str                     # e.g., "domain1"
    analysis_name: str              # e.g., "Flood Extent & Water Dynamics"
    inputs: list[InputSpec]         # Declared input roles (required/optional, product_types)
    params: list[ParamSpec]         # Configurable algorithm parameters (min, max, defaults)

    @abstractmethod
    def run(self, ctx: PipelineContext) -> StandardDomainResponse:
        """Execute domain-specific physics, generate layers, compute metrics, and return StandardDomainResponse."""
        pass
```

### 2.2 Standard Request Contract (`POST /api/domains/{domain}/process`)

```json
{
  "inputs": {
    "baseline": "dataset-id-001",
    "event": "dataset-id-002",
    "reference_water": "dataset-id-003",
    "dem": "dataset-id-004",
    "reference_flood": "dataset-id-005",
    "exposure_assets": "dataset-id-006"
  },
  "parameters": {
    "min_drop_db": 3.0,
    "smoothing_window": 5
  },
  "study_area_bbox": [22.79, 39.44, 22.96, 39.59]
}
```

### 2.3 Standard Response Contract (`StandardDomainResponse`)

All domain endpoints **must** return this unified Pydantic model (`backend/app/schemas/results.py`):

1. **`summary_metrics` (`list[MetricItem]`):** Primary headline numbers (`label`, `value`, `unit`, `description`) rendered in the frontend `MetricsPanel`.
2. **`layers` (`list[LayerReference]`):** Output georeferenced rasters (`.tif`), web transparent previews (`.png`), and vector overlays (`.geojson`) with geographic bounding boxes (`bounds_wgs84`).
3. **`explanation` (`ExplanationLevels`):**
   - `level1_visual`: What the user sees on the screen.
   - `level2_method`: The exact algorithm, thresholds, and filters applied.
   - `level3_evidence`: Corroborating physical values (backscatter drops, velocities, thermal points).
   - `level4_uncertainty`: Physical limitations, false positive drivers, and edge-case caveats.
4. **`validation` (`ValidationInfo`):**
   - `status`: `"compared_to_reference"` or `"not_validated"`.
   - `validation_category`: `"independent_real_reference"`, `"partially_independent_real_reference"`, `"climatological_comparative_reference"`, or `"demonstration_synthetic_benchmark"`.
   - `reference_independence`: Explicit tier string (`"independent_cross_sensor"`, `"partially_independent_cross_pair"`, `"climatological_comparative_baseline"`, `"synthetic_benchmark"`).
   - `confusion_matrix` / `error_metrics`: Numerical accuracy measures excluding NoData pixels.
   - `method_comparison`: 3 distinct candidate methods evaluated with isolated `runtime_ms`.
5. **`exposure` (`ExposureInfo`):** Spatial intersection breakdown with population, road, or agricultural vectors.
6. **`provenance` (`dict[str, Any]`):** Exact sensor names, orbit states, acquisition timestamps, and processing hashes.

---

## 3. Centralized Shared Core (Managed by Member 6)

Domain owners **must not** duplicate or rewrite core utilities. If changes are needed, propose them to Team Member 6:

- **Storage & File Safety (`backend/app/storage/`):** Path confinement ensuring no path traversal outside `data/` and no host filesystem paths leaked in reports.
- **Shared Raster Math (`backend/app/utils/raster.py`):** `read_band`, `write_geotiff`, `reproject_to_match`, `box_mean`, `bounded_otsu`, `pixel_area_m2`, `to_power`, `power_to_db`.
- **Validation Engine (`backend/app/utils/validation.py`):** `evaluate_binary_classification`, `evaluate_continuous_field`, confusion matrix calculation with strict NoData exclusion.
- **Exposure Intersection (`backend/app/utils/exposure.py`):** `evaluate_exposure` vector rasterization.
- **Earth Event Explorer & STAC (`backend/app/api/endpoints/explorer.py`):** Multi-collection planetary queries and AOI COG window extraction.
- **Frontend Reusable UI Components (`frontend/src/components/`):** `BeforeAfterViewer.jsx`, `MetricsPanel.jsx`, `ProcessingStatus.jsx`, `InteractiveWorldMap.jsx`.

---

## 4. Current Baseline Readiness & Domain Owner Charter

Each domain owner begins with an existing real-data baseline verified during the Phase 3 audit. The tasks for Phase 4 are to master the physics, test the limits, and refine the domain pipeline:

### Member 1: Domain 1 — Floods & Water Dynamics
- **Audit Baseline:** Lake Karla / Thessaly, Greece (Storm Daniel). Sentinel-1A RTC VV baseline (`2023-09-01`) and event (`2023-09-13`), Copernicus DEM GLO-30, JRC Global Surface Water, and Sentinel-2 MSI optical NDWI reference (`2023-09-15`). Audited metrics: $\text{IoU} = 40.1\%$, $\text{F1} = 57.2\%$, $\text{Precision} = 72.5\%$, $\text{Recall} = 47.3\%$.
- **Phase 4 Investigation Tasks:**
  1. Investigate the $4.64\,\text{km}^2$ false negatives along basin edges: distinguish shallow standing water with emergent crop stalks (where VV double-bounce prevents specular drop) from pure water bodies.
  2. Implement adaptive thresholding across terrain slopes (using Copernicus DEM) to prevent false positives in steep shadow areas.
  3. Validate against additional flood events (e.g., riverine vs. coastal storm surge).

### Member 2: Domain 2 — Forests & Vegetation
- **Audit Baseline:** Novo Progresso / BR-163, Pará, Brazil. Sentinel-1A RTC VH baseline (`2019-08-26`) and monitoring pass (`2020-08-20`), JAXA ALOS-2 PALSAR-2 FNF 2019 baseline mask, and ALOS-2 2019→2020 annual loss reference. Audited metrics: $\text{IoU} = 2.8\%$, $\text{Precision} = 15.2\%$, $\text{Recall} = 3.4\%$.
- **Phase 4 Investigation Tasks:**
  1. Address the primary scientific finding from the audit: on `2019-08-26`, candidate deforestation parcels were already clearing-stage bare soil (median $\text{VH} = -18.0\,\text{dB}$ vs. $-16.0\,\text{dB}$ in intact forest). Evaluate multi-temporal baselines rather than a single late dry-season date.
  2. Compensate for scene-wide canopy moisture variations ($+0.81\,\text{dB}$ shift across intact forest) using relative change ratio ($\Delta \text{VH} / \text{baseline}$).
  3. Formulate clear scientific explanations why single-pass C-band detects *structural canopy disturbance* while L-band measures *multi-year forest loss*.

### Member 3: Domain 3 — Ice, Glaciers & Cryosphere
- **Audit Baseline:** Jakobshavn Isbræ (Sermeq Kujalleq), Greenland. NASA MEaSUREs ITS_LIVE v2 2022 annual velocity mosaic ($120\,\text{m}$, `EPSG:3413`) and static multi-year climatological reference, plus Sentinel-1A HH terminus pair (`2023-08-28` vs. `2023-09-09`). Audited metrics: $\text{RMSE} = 1444.15\,\text{m/year}$, $r = 0.965$, peak velocity $14,178\,\text{m/year}$.
- **Phase 4 Investigation Tasks:**
  1. Incorporate shear margin strain rate calculations ($\partial u / \partial y$) from the velocity field to map high-risk crevasse zones.
  2. Refine terminus calving-front edge extraction using Sentinel-1 HH texture/co-occurrence filters to separate melange icebergs from the grounded ice tongue.
  3. Clearly maintain the distinction between an interannual velocity anomaly (compared to climatology) and independent ground-truth validation.

### Member 4: Domain 4 — Land Movement & Urban Change
- **Audit Baseline:** Tyrnavos Basin $M_w\ 6.3$ Earthquake, Thessaly, Greece. COMET-LiCSAR Sentinel-1A 12-day unwrapped LOS displacement (`2021-02-25` → `2021-03-09`, `mm`) and coherence ($0\text{--}1$), compared against 18-day Sentinel-1B/1A pair (`2021-02-19` → `2021-03-09`). Audited metrics: $\text{RMSE} = 4.99\,\text{mm}$, $r = 0.999$, peak subsidence $-368.5\,\text{mm}$.
- **Phase 4 Investigation Tasks:**
  1. Add gradient/strain analysis along subsidence bowls to detect differential settlement hazards across mapped infrastructure corridors (e.g., California Aqueduct, Greek EO3 highway).
  2. Implement coherence-guided spatial unwrapping error detection (identifying phase jump discontinuities across river channels or steep terrain).
  3. Maintain the explicit label of *partially independent cross-pair* validation due to the shared post-seismic acquisition and LiCSAR processing chain.

### Member 5: Domain 5 — Wildfires & Land Disturbance
- **Audit Baseline:** Dadia Forest / Evros Megafire, Greece. Sentinel-1A RTC VH pre-fire (`2023-08-09`) and post-fire (`2023-09-02`), 1,422 NASA MODIS active thermal points, and NASA MODIS `MCD64A1` burned area reference. Audited metrics: $\text{IoU} = 31.9\%$, $\text{Precision} = 99.99\%$, $\text{Recall} = 31.9\%$.
- **Phase 4 Investigation Tasks:**
  1. Bridge the resolution gap between coarse $500\,\text{m}$ optical burn perimeters and fine $29.5\,\text{m}$ SAR crown-burn clusters: implement sub-pixel fractional severity analysis.
  2. Investigate low-severity understory burns where surviving pine canopies preserve C-band volume scattering (causing false negatives in SAR).
  3. Use thermal point density weighting (FRP — Fire Radiative Power) to guide burn scar thresholding in active perimeter zones.

### Member 6: Platform Coordinator & Integration Lead
- **Phase 4 Coordination Tasks:**
  1. Maintain system integrity: ensure all 30 tests pass continuously as domain specialists push improvements.
  2. Support external data ingestion: ensure `POST /api/explorer/retrieve` smoothly feeds new AOI windows into domain workspaces.
  3. Guard common code: review any proposed changes to `backend/app/schemas/` or `backend/app/utils/`.
  4. Ensure all domain responses render smoothly in the Before/After curtain viewer and 15-section report export.

---

## 5. Domain Development Checklist (For Every Team Member)

Before proposing integration of an updated domain processor, the domain owner must complete this 8-step verification:

- [ ] **1. Physical Justification:** Does your algorithm reflect SAR interaction mechanisms (specular reflection, volume scattering, double bounce, interferometric phase, or offset tracking) rather than a generic threshold?
- [ ] **2. Provenance Integrity:** Are all sensor names, polarization channels, acquisition dates, and source URLs accurately recorded in `provenance`?
- [ ] **3. Input Validation:** Does your processor raise `PipelineInputError` for missing roles, incompatible product types, or mismatched spatial projections?
- [ ] **4. Robust NoData Handling:** Are `NaN` and sentinel values (`-9999.0`, `-32767.0`, `255`) strictly masked out of statistics, area calculations, and confusion matrices?
- [ ] **5. Validation Independence:** Is your validation data classified honestly according to the 4-tier model (`independent_cross_sensor`, `partially_independent_cross_pair`, `climatological_comparative_baseline`, or `synthetic_benchmark`)?
- [ ] **6. 4-Tier Explainability:** Are all four explanation levels (`level1_visual`, `level2_method`, `level3_evidence`, `level4_uncertainty`) fully drafted with accurate units?
- [ ] **7. Visual Deliverables:** Does your pipeline generate both analytical GeoTIFFs (`.tif`) and transparent web visual overlays (`.png`) with accurate `bounds_wgs84`?
- [ ] **8. Automated Tests:** Have you written or updated automated unit tests in `backend/tests/` verifying valid inputs, invalid inputs, and edge cases?
