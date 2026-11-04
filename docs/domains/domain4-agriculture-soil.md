# Domain Technical Specification — Domain 4: Agriculture & Soil Conditions

**Document ID:** `SPEC-D4-AGRICULTURE-SOIL`
**Version:** 1.0 (Implementation-Ready Specification)
**Status:** Approved for Implementation (Demonstration Status Pending Data Acquisition)
**Domain Owner:** Team Member 5 (`backend/app/domains/domain4/`, `frontend/src/domains/domain4/`)

---

## Section 1 — Domain Overview

* **Domain ID & Name:** `domain4` — Agriculture & Soil Conditions
* **Scientific Objective:** Monitor agricultural surface dynamics, crop canopy phenological progression, relative soil moisture proxies, and field tillage or waterlogging events using multi-temporal dual-polarization ($\text{VV}/\text{VH}$) Synthetic Aperture Radar (SAR) backscatter observations. The domain isolates cultivated agricultural parcels using boundary masks, models seasonal backscatter ratio dynamics ($\sigma^0_{\text{VH}} / \sigma^0_{\text{VV}}$), provides relative surface dielectric indicators, and establishes a demonstration framework for multi-sensor assimilation with optical vegetation indices (NDVI) and radiometer-scale soil moisture models (NASA SMAP).
* **Study Area & Event:** Central Valley, California, USA (Sacramento & San Joaquin agricultural basins; multi-crop seasonal cycles, orchard cultivation, and drought irrigation regimes).
* **Assigned Team Member:** Team Member 5 (Lead Domain Specialist).
* **Main Research Questions:**
  1. How effectively does multi-temporal dual-pol SAR backscatter ($\text{VV}$ and $\text{VH}$) delineate distinct stages of crop development (bare soil, emergence, peak vegetative canopy, senescence, harvest)?
  2. Can relative backscatter fluctuations over bare cultivated fields serve as a proxy for surface soil dielectric shifts without physical in-situ calibration?
  3. How can agricultural field parcel masking eliminate non-agricultural backscatter confounding factors (urban edges, riparian zones, roads)?
  4. What are the resolution and scaling challenges when comparing 10m–30m SAR observations to 9km SMAP or 9km ERA5-Land reanalysis products?
* **Expected Scientific Contribution:** An implementation of an agricultural SAR processing pipeline operating in demonstration mode that exposes multi-temporal parcel analysis, computes dual-pol canopy indices, estimates relative surface dielectric changes, and provides an explainable foundation for when high-resolution NISAR L-band and Sentinel-1 C-band agricultural time series are ingested.
* **Implementation Status:** `demonstration` (explicitly locked to demonstration mode; 0 real agricultural SAR backscatter datasets currently in repository; ready for execution via synthetic demonstration fixtures and cross-domain test harnesses).

---

## Section 2 — Scientific Problem

### Physical Phenomenon Investigated
Agricultural fields undergo continuous physical transformation: soil tillage alters surface geometric roughness; rainfall and irrigation alter the soil volumetric water content and complex dielectric constant ($\varepsilon = \varepsilon' + i\varepsilon''$); crop growth introduces dense vertical stalks, broad leaves, and canopies that shift microwave scattering from direct surface reflection to complex volume and double-bounce scattering; harvesting or grazing rapidly strips canopy scatterers, returning the field to bare soil.

### Why SAR is Useful
Crop growth and surface wetness change rapidly over days and weeks. Optical satellite observations are frequently interrupted by marine fog, seasonal overcast, or cloud shadows in critical growing months. Active SAR penetrates cloud and haze, observes day or night, and responds directly to the geometric structure and dielectric properties (water content) of plants and soil.

### What SAR Can Measure
* Multi-temporal variations in co-polarized ($\sigma^0_{\text{VV}}$) and cross-polarized ($\sigma^0_{\text{VH}}$) radar backscatter.
* Polarization ratio:
  $$\text{PR} = \frac{\sigma^0_{\text{VH}}}{\sigma^0_{\text{VV}}} \quad \left(\text{or } \text{PR}_{\text{dB}} = \sigma^0_{\text{VH, dB}} - \sigma^0_{\text{VV, dB}}\right)$$
  which correlates with canopy structure and vegetation water content.
* Significant relative backscatter changes ($\Delta\text{dB}$) over bare soil indicating surface wetness surges or sudden tillage/harvest events.

### What SAR Cannot Directly Measure
* Direct absolute volumetric soil moisture ($\text{m}^3/\text{m}^3$ or $\%$) from raw radar backscatter without solving the coupled soil roughness-moisture inversion problem (e.g., Dubois, Oh, or Integral Equation Models) or assimilating in-situ soil probe networks.
* Crop-specific yield ($kg/\text{ha}$) without calibrated agronomical growth models.
* Root-zone soil moisture ($>5\text{ cm}$ depth) using C-band radar, which penetrates only the top $1–3\text{ cm}$ of the surface layer.
* Direct validation against regional radiometers (SMAP) without spatial field parcel aggregation, as single SAR pixels cannot be matched to 9km footprint averages.

### Factors Affecting Observation Quality
1. **Roughness-Dielectric Ambiguity:** A rough, dry field produces a nearly identical radar backscatter signature to a smooth, wet field. Without auxiliary roughness data or multi-angle passes, backscatter cannot uniquely determine soil moisture.
2. **Canopy Attenuation:** Dense crop canopies (mature corn, dense orchards) attenuate the radar signal, preventing microwaves from reaching the ground and masking underlying soil moisture conditions.
3. **Row Orientation Effects:** Radar look direction perpendicular to tilled crop rows creates artificial Bragg or geometric double-bounce reflections, artificially boosting backscatter by up to 6–10 dB.
4. **Resolution & Footprint Mismatch (SMAP vs. SAR):**
   - Sentinel-1 SAR: $10\text{m} \times 10\text{m}$ (or $20\text{m}$ multi-looked).
   - NASA SMAP L4: $9\text{km} \times 9\text{km}$ (or $36\text{km}$ radiometer grid).
   - A single $9\text{km}$ SMAP pixel encompasses $\approx 810,000$ Sentinel-1 pixels, spanning multiple distinct crop types, irrigation schedules, and fallow parcels. Direct pixel-level point comparison between S1 and SMAP is physically invalid without parcel-level aggregation and soil texture weighting.

### Scientific Assumptions
* The pipeline operates in demonstration mode until validated multi-temporal SAR backscatter time series are ingested.
* Agricultural parcels are delineated using valid crop masks (e.g., USDA Cropland Data Layer).
* Dual-pol ratio $\sigma^0_{\text{VH}} / \sigma^0_{\text{VV}}$ increases monotonically with crop canopy volume.
* Sharp drops in backscatter ($\le -2.0\text{ dB}$) during peak harvest months represent crop clearing.
* Backscatter increases over bare soil indicate relative dielectric surface wetting, but are explicitly caveated as uncalibrated proxies rather than volumetric moisture content.

---

## Section 3 — Dataset Inventory

### Current Repository Inventory Status
* **Real Agricultural SAR Backscatter Datasets Available:** **0**
* **Synthetic / Benchmark Agricultural Datasets Available:** Demonstration fixtures generated by test harnesses.
* **Unresolved Datasets in `data/raw/domain4/`:** 4 Central Valley datasets (`ds-demo-d4-coh`, `ds-demo-d4-disp`, `ds-demo-d4-ref`, `ds-demo-d4-exp`).
  > [!WARNING]
  > **Catalog Inconsistency:** These 4 datasets measure millimeter land subsidence and interferometric coherence in the San Joaquin Valley. They are InSAR products and **cannot** be used as agricultural backscatter inputs. They are documented below to maintain complete repository traceability.

| Dataset ID | Dataset Name | Provider | Sensor | Product Type | Acquisition Date | Physical Path | Logical Domain | Availability | Scientific Suitability |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: | :---: | :--- |
| `ds-demo-d4-coh` | San Joaquin Valley Interferometric Coherence (Synthetic Demo Fixture) | Synthetic InSAR | Simulated InSAR | `insar_coherence` | 2025-09-01 | `data/raw/domain4/demo_insar_coh.tif` | `domain4` | Available | **Unsuitable** for Agriculture (InSAR coherence, not backscatter). |
| `ds-demo-d4-disp` | San Joaquin Valley InSAR LOS Velocity (Synthetic HyP3 Demo Fixture) | Simulated ASF HyP3 | Simulated InSAR | `insar_displacement` | 2025-09-01 | `data/raw/domain4/demo_insar_disp.tif` | `domain4` | Available | **Unsuitable** for Agriculture (InSAR subsidence rate, not backscatter). |
| `ds-demo-d4-exp` | San Joaquin Aqueduct & District Footprints (Synthetic Exposure GeoJSON) | Vector GIS | Vector GIS | `exposure_assets` | None | `data/raw/domain4/demo_insar_exp.geojson` | `domain4` | Available | Suitable: Canal and parcel infrastructure vector boundaries. |
| `ds-demo-d4-ref` | San Joaquin Reference GNSS/Leveling Field (Synthetic Validation Fixture) | Synthetic Model | Validation Grid | `reference_displacement` | 2025-09-01 | `data/raw/domain4/demo_insar_ref.tif` | `domain4` | Available | **Unsuitable** for Agriculture (Deformation field, not crop reference). |

### Additional Datasets Required for Operational Status (Procurement Plan)
To transition Domain 4 from `demonstration` to `implemented`, the following datasets must be acquired and cataloged:

1. **Sentinel-1A/B Level-1 GRDH RTC Dual-Pol Backscatter ($\text{VV} + \text{VH}$):**
   * *Provider:* Copernicus / Alaska Satellite Facility (ASF DAAC).
   * *Target Area:* Central Valley, California (Fresno/Kern Counties; Path 137, Frame 115).
   * *Temporal Requirements:* Multi-temporal time series across one complete growing season (March–October, 12-day repeat).
   * *Product Type:* `sar_backscatter`.
2. **USDA NASS Cropland Data Layer (CDL):**
   * *Provider:* USDA National Agricultural Statistics Service.
   * *Purpose:* Parcel-level crop classification and boundary masking.
   * *Product Type:* `forest_mask` / `crop_mask`.
3. **NASA SMAP L4 Global 9km Surface Soil Moisture:**
   * *Provider:* NASA NSIDC DAAC.
   * *Purpose:* Regional comparative soil moisture baseline.
   * *Product Type:* `reference_condition`.
4. **USDA SCAN / In-Situ Soil Moisture Telemetry:**
   * *Provider:* USDA NRCS Soil Climate Analysis Network.
   * *Purpose:* In-situ point validation of volumetric water content ($\text{cm}^3/\text{cm}^3$).

---

## Section 4 — Input Requirements

### InputSpec Role Specifications
As declared in `AgriculturePipeline.inputs`:
* `baseline` (**Required**, `sar_backscatter`): Pre-change or early-season calibrated SAR backscatter raster ($\text{VV}$ or $\text{VH}$, linear power or decibel scale).
* `monitoring` (**Required**, `sar_backscatter`): Repeat-pass SAR backscatter raster acquired during crop growth, irrigation, or post-harvest.
* `crop_mask` (*Optional*, `forest_mask`, `reference_water`): Binary agricultural field boundary raster ($1=\text{cultivated field}$, $0=\text{non-agricultural}$).
* `reference_condition` (*Optional Validation*, `reference_disturbance`, `reference_flood`): Independent reference crop condition or ground truth moisture mask for validation.
* `exposure_assets` (*Optional*, `exposure_assets`): GeoJSON vector layer of irrigation canals, parcel boundaries, or water storage basins.

### Sensor & Technical Invariants
* **Sensor:** Sentinel-1 C-band SAR or NISAR L-band / S-band.
* **Polarization:** Dual-polarization ($\text{VV} + \text{VH}$) required for full crop development index; single-pol $\text{VV}$ accepted for relative soil moisture proxies.
* **Resolution:** 10m to 30m grid spacing.
* **CRS:** UTM Zone 10N / 11N (`EPSG:32610` / `EPSG:32611`) or Web Mercator (`EPSG:3857`).
* **Missing Data:** Out-of-bounds parcel pixels or cloud/shadow masks set to NoData and excluded from agricultural indices.

---

## Section 5 — Scientific Methods and Algorithms

### Method Classification Summary
* **1. Dual-Polarization Radar Vegetation Index ($\text{RVI}_{\text{dual}}$):** `Valid but requires calibration` (Mandal et al., 2020 formulation for $\text{VV}/\text{VH}$ sensors; classical RVI requires quad-pol).
* **2. Polarization Cross-Ratio ($\text{CR} = \sigma_{\text{VH}}^0 / \sigma_{\text{VV}}^0$):** `Scientifically established and correctly specified`.
* **3. Relative Surface Dielectric Change ($\Delta\sigma_{\text{VV}}^0$):** `Valid as a relative proxy; uncalibrated for absolute volumetric moisture`.
* **4. Agricultural Field Parcel Boundary Masking:** `Scientifically established and correctly specified`.
* **5. Surface Disturbance / Harvest Drop Thresholding:** `Scientifically established and correctly specified`.
* **6. Physical Dielectric & Roughness Inversion (Dubois / IEM Model):** `Requires additional input data (L-band quad-pol)` / `Planned future work`.
* **7. Footprint Spatial Aggregation for SMAP Validation:** `Valid but requires calibration / spatial aggregation`.

---

### Detailed Method Specifications

#### 1. Dual-Polarization Radar Vegetation Index ($\text{RVI}_{\text{dual}}$)
* **Scientific Classification:** `Valid but requires calibration`.
* **Mathematical Basis:**
  Classical RVI (Kim & van Zyl, 2009) requires quad-polarimetric data ($\text{HH}, \text{HV}, \text{VV}$). For dual-polarized Sentinel-1 ($\text{VV} + \text{VH}$), the operational dual-pol formulation of Mandal et al. (2020) is adopted:
  $$\text{RVI}_{\text{dual}} = \frac{4 \cdot \sigma^0_{\text{VH, linear}}}{\sigma^0_{\text{VV, linear}} + \sigma^0_{\text{VH, linear}}}$$
  where inputs are strictly in linear power scale.
  - For smooth bare soil ($\sigma^0_{\text{VH}} \ll \sigma^0_{\text{VV}}$): $\text{RVI}_{\text{dual}} \to 0$.
  - For dense random vegetative canopy volume scattering ($\sigma^0_{\text{VV}} \approx 3 \sigma^0_{\text{VH}}$): $\text{RVI}_{\text{dual}} \to 1.0$.
* **Implementation Status:** `demonstration` (implemented in pipeline; pending real agricultural SAR inputs).

#### 2. Polarization Cross-Ratio ($\text{CR}$)
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Mathematical Basis:**
  $$\text{CR}_{\text{linear}} = \frac{\sigma^0_{\text{VH}}}{\sigma^0_{\text{VV}}} \quad \text{or in decibels: } \text{CR}_{\text{dB}} = \sigma^0_{\text{VH, dB}} - \sigma^0_{\text{VV, dB}}$$
  Because soil moisture variations alter the dielectric constant and scale both $\sigma^0_{\text{VV}}$ and $\sigma^0_{\text{VH}}$ simultaneously, their ratio cancels out common background soil moisture signals, isolating vertical crop structure, biomass volume, and canopy phenological growth.
* **Implementation Status:** `demonstration`.

#### 3. Relative Surface Dielectric Change ($\Delta\text{dB}$) Proxy
* **Scientific Classification:** `Valid as a relative proxy; uncalibrated for absolute volumetric moisture`.
* **Mathematical Basis:** Over bare or short-vegetated parcels:
  $$\Delta\sigma^0_{\text{VV, dB}} = 10 \log_{10}(\sigma^0_{\text{monitoring, VV}}) - 10 \log_{10}(\sigma^0_{\text{baseline, VV}})$$
* **Non-Negotiable Scientific Safeguard:** Surface backscatter is simultaneously governed by soil moisture (dielectric constant $\varepsilon_r$) and surface geometric roughness (RMS height $s$ and correlation length $l$). **Relative backscatter shifts ($\Delta\text{dB}$) must NEVER be reported as absolute volumetric soil moisture ($\text{cm}^3/\text{cm}^3$ or $\%$) without solving a physical scattering inversion model.**
* **Implementation Status:** `demonstration`.

#### 4. Surface Disturbance & Harvest Thresholding
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Delineate field plowing, crop mowing, or vegetative destruction by identifying sharp drops in canopy backscatter.
* **Parameters:** `delta_threshold_db` = -2.0 dB (default, range -12.0 to -0.5 dB).
* **Implementation Status:** `demonstration`.

#### 5. Spatial Aggregation for Regional Radiometer Validation (SMAP)
* **Scientific Classification:** `Valid but requires calibration / spatial aggregation`.
* **Scientific Limitation:** Comparing 10m–20m SAR backscatter against 9km SMAP L4 soil moisture requires aggregating parcel backscatter across the 9km radiometer footprint:
  $$\langle \sigma^0 \rangle_{9\text{km}} = \frac{1}{M}\sum_{k=1}^M \sigma^0_k$$
  Point-to-pixel validation without aggregation is physically invalid.
* **Implementation Status:** `planned_future_work`.

#### 6. Physical Soil Moisture & Roughness Inversion (Dubois / IEM)
* **Scientific Classification:** `Requires additional input data (L-band quad-pol)` / `Planned future work`.
* **Scientific Purpose:** Simultaneously invert surface RMS roughness height ($s$) and complex dielectric constant ($\varepsilon_r$) to compute true volumetric water content ($m_v$) independently of roughness.
* **Implementation Status:** `future_research` (requires NISAR polarimetric L-band data).

---

## Section 6 — Processing Workflow

```
Dataset Selection (baseline backscatter, monitoring backscatter, crop mask)
  │
  ▼
Input Validation (enforces sar_backscatter; explicitly rejects insar_displacement)
  │
  ▼
Preprocessing (dB conversion, 5x5 boxcar speckle filter, spatial alignment)
  │
  ▼
Demonstration Agricultural Analysis:
  ├─ Apply Agricultural Crop Boundary Mask (restricts math to cultivated fields)
  ├─ Compute Relative Delta Backscatter (Delta dB = monitoring - baseline)
  ├─ Calculate Dual-Pol Canopy Ratio (if VH available)
  ├─ Detect Disturbance / Harvest (Delta dB <= -2.0 dB)
  └─ Segment Relative Wetness Surges (Delta dB >= +2.5 dB on bare soil)
  │
  ▼
Deliverable Generation (Export Delta GeoTIFF, Change Overlay PNG previews)
  │
  ▼
Comparative Validation (Evaluate against reference condition mask if provided)
  │
  ▼
Exposure Intersection (Quantify affected crop acreage inside irrigation zones)
  │
  ▼
Assemble StandardDomainResponse (Flag is_synthetic_input, summary metrics, caveats)
```

---

## Section 7 — Expected Scientific Outputs

| Output Layer Key | Layer Type | Units | Physical Meaning | Generation Method | Validation Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `change_mask` | Raster (GeoTIFF) | Class (0..3) | Agricultural surface change ($0=\text{stable}$, $1=\text{harvest}$, $2=\text{wetness}$) | Thresholded $\Delta\text{dB}$ | USDA CDL / S2 NDVI |
| `delta_db` | Raster (GeoTIFF) | $\Delta\text{dB}$ | Continuous backscatter difference grid | $\sigma^0_{\text{monitoring}} - \sigma^0_{\text{baseline}}$ | Radiometric calibration |
| `baseline_preview` | Preview (PNG) | dB | Pre-change agricultural SAR backscatter | Linear grayscale stretch (-25 to 0 dB) | Visual inspection |
| `monitoring_preview`| Preview (PNG) | dB | Monitoring agricultural SAR backscatter | Linear grayscale stretch (-25 to 0 dB) | Visual inspection |
| `delta_map` | Preview (PNG) | $\Delta\text{dB}$ | Continuous backscatter change web map | Diverging color ramp (-6 to +6 dB) | Radiometric calibration |
| `change_overlay` | Preview (PNG) | RGBA | Web overlay: Amber = Harvest/Clearing, Blue = Moisture Surge | Categorical RGBA palette mapping | Demonstration benchmark |

* **CRS:** UTM (`EPSG:32610` / `EPSG:32611`).
* **Legend:** Amber (#bc6c25) = Crop Clearing/Harvest, Blue/Teal (#2a9d8f) = Surface Wetness Surge, Green (#2d6a4f) = Stable Vegetative Canopy.

---

## Section 8 — Metrics and Calculations

### Summary Metrics Provided
1. **`cultivated_area_km2`:** Total agricultural land area analyzed inside the crop mask.
2. **`harvested_area_km2`:** Acreage exhibiting significant canopy backscatter drop ($\Delta\text{dB} \le -2.0\text{ dB}$).
3. **`wetness_surge_area_km2`:** Acreage exhibiting significant relative backscatter increase ($\Delta\text{dB} \ge +2.5\text{ dB}$).
4. **`mean_delta_backscatter_db`:** Average change in radar backscatter across cultivated parcels.
5. **`crop_canopy_stability_pct`:** Percentage of agricultural area maintaining stable vegetative canopy.

---

## Section 9 — Validation Strategy

| Validation Source | What It Validates | Independence Tier | Spatial Comp. | Temporal Comp. | Accuracy Metrics |
| :--- | :--- | :--- | :---: | :---: | :--- |
| USDA NASS Cropland Data Layer (Planned) | Crop classification & parcel borders | Independent Real Reference (USDA CDL) | 30m national raster grid | Annual crop census | IoU, Boundary F1 |
| Sentinel-2 NDVI Time Series (Planned) | Vegetative canopy growth vs harvest | Independent Cross-Sensor (Optical NDVI) | 10m grid | Cloud-free matching pass (5-day) | Pearson $R^2$, Harvest Date Bias |
| NASA SMAP L4 Surface Soil Moisture (Planned) | Regional soil moisture trends | Climatological Comparative Reference | 9km radiometer footprint | Daily assimilation | Trend Correlation ($R$) |
| Demonstration Test Fixtures (`ds-test-d2-base`) | Algorithmic logic and schema checks | Demonstration Synthetic Benchmark | $30\times 30$ grid | N/A | Unit regression test |

* **Demonstration Safeguard:** Because real agricultural SAR datasets are currently pending acquisition, the validation tier is permanently reported as `"demonstration_synthetic_benchmark"` until verified field data is landed.

---

## Section 10 — Frontend Specification

### Workspace Layout (`Domain4Page.jsx`)
* **Demonstration Status Banner:** A prominent amber status banner at the top of the workspace:
  > **DEMONSTRATION WORKSPACE:** Real dual-polarization agricultural SAR backscatter datasets for the Central Valley are pending acquisition. Analysis algorithms are demonstrated using calibrated synthetic fixtures.
* **Study Area Selection:** Central Valley, California (Sacramento & San Joaquin Agricultural Districts).
* **Processing Controls:** Slider for `delta_threshold_db` (-12.0 to -0.5 dB).
* **Map Display (`BeforeAfterViewer`):**
  * Left Canvas: Baseline Agricultural SAR backscatter.
  * Right Canvas: Monitoring / Post-Harvest SAR backscatter.
  * Overlays: Amber crop disturbance parcels, irrigation canal vectors.
* **Scientific Caveats Card:** Explains the physical difference between radar backscatter (roughness + dielectric) and absolute soil moisture, detailing why SMAP radiometer data cannot be directly equated with 10m radar pixels.

---

## Section 11 — Backend File Responsibilities

* `backend/app/domains/domain4/processor.py`: Implements `AgriculturePipeline`, inheriting from `DomainPipeline` (`backend/app/services/pipeline.py`) in `demonstration` status. Declares input specifications (`InputSpec`) for dual-pol SAR backscatter, crop masks, and exposure assets. (Also houses `LandMovementPipeline` for historical InSAR subsidence execution).
* `backend/app/api/endpoints/domain4.py`: API router dispatching requests to `AgriculturePipeline` (or routing to `LandMovementPipeline` if displacement/coherence inputs are supplied).
* `backend/app/services/processing_service.py`: Central coordinator (`ProcessingService`) that resolves inputs, validates that inputs have `sar_backscatter` product types, and formats output into `StandardDomainResponse` (`backend/app/schemas/results.py`).
* `backend/app/domains/domain4/preprocessing.py`, `analysis.py`, `visualization.py`: Modular domain components for crop parcel masking, dual-pol RVI math, and harvest difference mapping.
* `backend/app/utils/raster.py` & `validation.py`: Shared platform utilities providing raster I/O, boxcar filtering, and spatial exposure assessment.

---

## Section 12 — API Integration

### Endpoint
`POST /api/domains/domain4/process`

### Sample Request Payload (Demonstration Mode)
```json
{
  "inputs": {
    "baseline": "ds-demo-d2-base",
    "monitoring": "ds-demo-d2-event",
    "crop_mask": "ds-demo-d2-mask"
  },
  "parameters": {
    "delta_threshold_db": -2.0,
    "filter_window": 5
  },
  "study_area_bbox": [-120.5, 36.5, -119.5, 37.2]
}
```

### Critical API Rejection Test
If a client attempts to pass InSAR subsidence datasets (e.g., `ds-real-d4-disp` or `ds-demo-d4-disp`) as `baseline`, the pipeline raises `PipelineInputError`, returning HTTP 422:
```json
{
  "detail": "Input 'Baseline Agricultural SAR (VV/VH)' (baseline) requires one of: sar_backscatter. Got 'insar_displacement'."
}
```

---

## Section 13 — Testing and Acceptance Criteria

1. **Rejection Unit Test (`test_scientific_dataset_ownership.py`::`test_9`):**
   * Verifies that `AgriculturePipeline` strictly rejects `insar_displacement` inputs with HTTP 422.
2. **Demonstration Execution Test:**
   * Pipeline executes successfully with synthetic dual-pol fixtures, returning `status: "completed"`, `is_synthetic_input: true`, and valid summary metrics.
3. **Soil Moisture Disclaimer Test:**
   * Response explanation payload must contain the explicit disclaimer that backscatter changes indicate surface wetness/roughness proxies and not calibrated volumetric soil moisture.
4. **Demonstration Flagging:**
   * Domain status must report `demonstration` in both backend descriptors and frontend badges.

---

## Section 14 — Limitations and Future Work

### Limitations
* Zero real agricultural SAR backscatter datasets currently cataloged in the repository.
* Absolute volumetric soil moisture inversion is impossible without auxiliary surface roughness measurements.
* C-band microwaves do not penetrate dry soil beyond the top $1–3\text{ cm}$.

### Future Work
* Acquisition of 12-day repeat Sentinel-1 dual-pol ($\text{VV}+\text{VH}$) RTC time series over Central Valley agricultural stations.
* Integration of NISAR L-band observations for deeper soil and sub-canopy penetration.
* Coupling with USDA Cropland Data Layer (CDL) for parcel-specific crop type phenology tracking.
