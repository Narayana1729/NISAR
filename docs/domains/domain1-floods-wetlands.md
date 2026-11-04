# Domain Technical Specification — Domain 1: Floods & Wetlands

**Document ID:** `SPEC-D1-FLOODS`
**Version:** 1.0 (Implementation-Ready Specification)
**Status:** Approved for Implementation
**Domain Owner:** Team Member 2 (`backend/app/domains/domain1/`, `frontend/src/domains/domain1/`)

---

## Section 1 — Domain Overview

* **Domain ID & Name:** `domain1` — Floods & Wetlands
* **Scientific Objective:** Detect, quantify, and explain changes in surface inundation, standing water dynamics, and wetland extent using repeat-pass Synthetic Aperture Radar (SAR) observations. The domain differentiates open specular floodwater from emergent vegetation double-bounce, subtracts permanent water bodies, masks steep terrain radar shadows, and validates results against independent high-resolution optical observations.
* **Study Area & Event:** Thessaly Basin and Lake Karla, Greece (Storm Daniel, September 2023 extreme precipitation and catastrophic plain flooding).
* **Assigned Team Member:** Team Member 2 (Lead Domain Specialist).
* **Main Research Questions:**
  1. Can relative specular backscatter drop ($\Delta\sigma^0$) combined with bimodal Otsu thresholding accurately isolate Storm Daniel's flood extent across agricultural plains?
  2. How do permanent water bodies (e.g., Lake Karla historical baseline) bias flood area statistics if not independently subtracted?
  3. To what degree do steep terrain slopes ($>5^\circ$) introduce false-positive radar shadow detections in surrounding foothills?
  4. What is the spatial agreement (Precision, Recall, F1, IoU) between C-band SAR inundation classification and independent Sentinel-2 optical NDWI reference maps?
* **Expected Scientific Contribution:** An explainable, reproducible, terrain-corrected flood mapping pipeline that provides conservative inundated area estimates, separates anomalous floodwater from seasonal and permanent water bodies, provides 4-tier explainability for disaster operators, and exposes pixel-level error classifications against multi-sensor optical benchmarks.
* **Implementation Status:** `implemented` (operational backend pipeline and dataset fixtures active).

---

## Section 2 — Scientific Problem

### Physical Phenomenon Investigated
During heavy precipitation events, overland runoff accumulates in topographic depressions, river corridors, and agricultural floodplains. When smooth standing water covers bare soil or short vegetation, the air-water dielectric discontinuity and smooth surface condition alter the microwave scattering regime from diffuse volume/surface backscatter to mirror-like specular reflection away from the radar antenna.

### Why SAR is Useful
Flooding typically occurs under persistent cloud cover, atmospheric convective storms, or nighttime conditions where optical satellite sensors (Sentinel-2, Landsat) cannot image the Earth's surface. Active microwave sensors (such as Sentinel-1 C-band and NISAR L/S-band) transmit their own illumination and penetrate clouds, rain haze, and darkness, providing timely observations during peak flood crests.

### What SAR Can Measure
* Relative drop in radar backscattering coefficient ($\sigma^0$) in co-polarized ($\text{VV}$ or $\text{HH}$) channels over smooth standing water compared to dry pre-event soil.
* Spatial boundaries of open water inundation bodies.
* Relative backscatter increases caused by "double-bounce" reflections between standing water surfaces and vertical structures (emergent crops, tree trunks, urban building walls) where signal geometry permits.

### What SAR Cannot Directly Measure
* Sub-canopy water depth or volumetric flood volume ($m^3$) without external hydraulic gauge telemetry or high-resolution bathymetric models.
* Flow velocity ($m/s$) of floodwaters.
* Water purity, suspended sediment concentration, or chemical contamination.
* True ground conditions beneath steep radar shadows or layover zones in mountainous terrain.
* Continuous flood duration (days inundated) from a single pre/post pair; true duration requires dense multi-temporal time series across the entire flood hydrograph.
* Sub-canopy standing water beneath closed, dense tree canopies at C-band without L-band polarimetric double-bounce decomposition.

### Factors Affecting Observation Quality
1. **Wind-Roughened Water:** High surface winds (>5–7 m/s) create capillary waves on open water, increasing surface roughness and backscatter ($\sigma^0$ rises from -18 dB to -12 dB), which causes false-negative water detections (water misclassified as land).
2. **Incidence Angle Variation:** Across a Sentinel-1 IW swath ($29^\circ–46^\circ$), water backscatter naturally decreases by 3–6 dB from near range to far range, making fixed global thresholds unreliable across large scenes.
3. **Soil Moisture Surges:** Pre-event saturated soils show high dielectric permittivity and high baseline backscatter; slight surface drying post-flood can mimic relative backscatter drops.
4. **Terrain Radar Shadows:** Mountain slopes facing away from the radar antenna return zero backscatter, mimicking smooth specular water.
5. **Vegetation Canopy Scattering:** Dense leafy agricultural or forest canopies at C-band attenuate microwave pulses, preventing detection of underlying standing water.

### Scientific Assumptions
* Pre-event baseline represents non-flooded, dry-to-moderate moisture ground conditions.
* Inundation causes a statistically significant, negative shift ($\Delta\text{dB} \le -3.0\text{ dB}$) in $\text{VV}$ backscatter over agricultural ground.
* Open water exhibits backscatter below a calibrated radiometric threshold ($\le -16.0\text{ dB}$ for Sentinel-1 IW $\text{VV}$ at mid-swath).
* Pixels with terrain slopes $>5^\circ$ are drained and any low-backscatter signals in those zones represent topographic radar shadow rather than stagnant inundation.

---

## Section 3 — Dataset Inventory

The following table lists the 11 verified datasets available for Domain 1 in `data/manifests/datasets.json` and `data/raw/domain1/`.

| Dataset ID | Dataset Name | Provider | Sensor | Product Type | Acquisition Date | Physical Path | Logical Domain | Availability | Scientific Suitability |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: | :---: | :--- |
| `15a8d70a-999e-4575-a2b7-b7b502f0dad8` | Sentinel-1A RTC Post-Flood Observation (Thessaly, Greece) | Copernicus / ESA | Sentinel-1A (C-band SAR) | `sar_backscatter` | 2023-09-13 | `data/raw/domain1/thessaly_flood_event_vv.tif` | `domain1` | Available | Suitable: Primary post-event crisis observation ($\text{VV}$). |
| `5c351e81-1dfc-4d6b-9eec-9aed124eee8a` | Sentinel-1A RTC Pre-Flood Baseline (Thessaly, Greece) | Copernicus / ESA | Sentinel-1A (C-band SAR) | `sar_backscatter` | 2023-09-01 | `data/raw/domain1/thessaly_flood_baseline_vv.tif` | `domain1` | Available | Suitable: Primary dry pre-event reference ($\text{VV}$). |
| `ds-bench-thessaly-ref-flood` | Lake Karla Reference Flood Benchmark Mask (Storm Daniel) | Operational Hydrology Benchmark | Benchmark Mask | `reference_flood` | 2023-09-13 | `data/raw/domain1/thessaly_reference_flood_benchmark.tif` | `domain1` | Available | Suitable: Synthetic benchmark for pipeline unit tests. |
| `ds-dem-thessaly-basin` | Lake Karla Basin Terrain Elevation Model (DEM) | Regional Model | DEM Model | `dem` | None | `data/raw/domain1/thessaly_terrain_dem.tif` | `domain1` | Available | Suitable: Topographic slope masking. |
| `ds-exp-thessaly-assets` | Lake Karla Basin Agricultural & Road Assets (GeoJSON) | OpenStreetMap / Regional GIS | Vector GIS | `exposure_assets` | None | `data/raw/domain1/thessaly_exposure_assets.geojson` | `domain1` | Available | Suitable: Infrastructure exposure intersection. |
| `ds-real-thessaly-cop-dem` | Copernicus GLO-30 Digital Elevation Model (Lake Karla / Thessaly) | ESA Copernicus | TanDEM-X SAR / GLO-30 | `dem` | 2021-01-01 | `data/raw/domain1/thessaly_copernicus_dem_30m.tif` | `domain1` | Available | Suitable: High-fidelity 30m terrain slope calculation. |
| `ds-real-thessaly-jrc-water` | JRC Global Surface Water Occurrence ≥50% (Lake Karla Reference) | European Commission JRC | Landsat GSW v1.3 | `reference_water` | 2020-12-31 | `data/raw/domain1/thessaly_jrc_gsw_reference_water.tif` | `domain1` | Available | Suitable: Independent multi-decadal permanent water reference. |
| `ds-real-thessaly-perm-water` | Lake Karla Baseline Permanent Water Mask (2023-09-01) | Baseline Derived | Sentinel-1A Derived | `reference_water` | 2023-09-01 | `data/raw/domain1/thessaly_permanent_water_mask.tif` | `domain1` | Available | Suitable: Semi-independent permanent water mask. |
| `ds-real-thessaly-s2-flood-ref` | Sentinel-2A Optical Post-Flood NDWI Reference (2023-09-15, Lake Karla) | Copernicus / ESA | Sentinel-2A MSI L2A | `reference_flood` | 2023-09-15 | `data/raw/domain1/thessaly_s2_20230915_ndwi_flood_ref.tif` | `domain1` | Available | Suitable: Independent optical cross-sensor validation. |
| `ds-test-base-flood` | Synthetic Pre-Flood Baseline | Internal Test Suite | Unspecified | `sar_backscatter` | None | `data/raw/domain1/test_flood_base.tif` | `domain1` | Available | Suitable: Fast $20\times 20$ unit test fixture. |
| `ds-test-event-flood` | Synthetic Post-Flood Crisis | Internal Test Suite | Unspecified | `sar_backscatter` | None | `data/raw/domain1/test_flood_event.tif` | `domain1` | Available | Suitable: Fast $20\times 20$ unit test fixture. |

### Dataset Grouping Breakdown
1. **Currently Available (11):** All 11 datasets listed above exist on disk in `data/raw/domain1/`.
2. **Suitable for Operational Pipeline (7):** `15a8d70a-...`, `5c351e81-...`, `ds-real-thessaly-cop-dem`, `ds-real-thessaly-jrc-water`, `ds-real-thessaly-perm-water`, `ds-real-thessaly-s2-flood-ref`, `ds-exp-thessaly-assets`.
3. **Available for Testing/Demo (4):** `ds-bench-thessaly-ref-flood`, `ds-dem-thessaly-basin`, `ds-test-base-flood`, `ds-test-event-flood`.
4. **Additional Datasets Required (Future Acquisition):**
   * *NISAR L-band Dual-Pol (HH/HV) GCOV:* To validate sub-canopy flood penetration via L-band double bounce.
   * *NASA GPM IMERG Precipitation Rates:* Half-hourly accumulation rasters ($mm/hr$) to confirm rainstorm timing.
5. **Independent Validation Datasets (2):** `ds-real-thessaly-s2-flood-ref` (Sentinel-2 NDWI) and `ds-real-thessaly-jrc-water` (JRC Global Surface Water).

---

## Section 4 — Input Requirements

### InputSpec Role Specifications
As declared in `FloodsPipeline.inputs`:
* `baseline` (**Required**, `sar_backscatter`): Pre-flood radiometrically terrain-corrected (RTC) radar backscatter raster. Must be in linear power or decibel scale.
* `event` (**Required**, `sar_backscatter`): Crisis or post-flood RTC radar backscatter raster matching geometry, sensor, and polarization of baseline.
* `reference_water` (*Optional*, `reference_water`): Binary or fractional permanent water mask ($1=\text{permanent water}$, $0=\text{dry}$). If omitted, baseline water is inferred.
* `dem` (*Optional*, `dem`): Elevation model in meters, used to calculate local slope angles and eliminate radar shadows on hillsides.
* `reference_flood` (*Optional Validation*, `reference_flood`): Independent binary raster ($1=\text{flooded}$, $0=\text{dry}$) for accuracy metrics (IoU, F1, Precision, Recall).
* `exposure_assets` (*Optional*, `exposure_assets`): GeoJSON vector layer of roads, towns, and agricultural parcels for spatial exposure intersection.

### Sensor & Technical Invariants
* **Sensor:** Sentinel-1A/B C-band SAR (5.405 GHz) or NISAR L-band (1.25 GHz).
* **Polarization:** $\text{VV}$ preferred for smooth open water; $\text{HH}$ accepted; cross-pol ($\text{VH}/\text{HV}$) rejected for open-water specular analysis.
* **Temporal Interval:** Baseline acquired within 12–24 days prior to flood onset; event acquired within 72 hours of peak flood stage.
* **Spatial Coverage:** Must cover Lake Karla basin ($[22.65^\circ\text{E}, 39.35^\circ\text{N}]$ to $[23.05^\circ\text{E}, 39.65^\circ\text{N}]$).
* **CRS:** Projected Coordinate System (`EPSG:32634` - UTM Zone 34N) preferred for accurate area math; geographic (`EPSG:4326`) reprojected on ingest.
* **Resolution:** 10m to 30m grid spacing.
* **NoData Handling:** Transparently masked; NoData pixels excluded from Otsu histograms, area summations, and confusion matrices.

---

## Section 5 — Scientific Methods and Algorithms

### Method Classification Summary
* **1. Radiometric Power-to-dB & Boxcar Filtering:** `Scientifically established and correctly specified`.
* **2. Bounded Otsu Histogram Thresholding:** `Valid but requires calibration` (requires bimodal histogram; bounded search window $[-24.0, -11.0]\text{ dB}$ prevents runaway mode splitting on unimodal scenes).
* **3. Fixed Backscatter Thresholding:** `Valid but requires calibration` (strongly dependent on local incidence angle $\theta \in [29^\circ, 46^\circ]$ and surface wind conditions).
* **4. Differential Relative Drop ($\Delta\sigma^0 \le -3.0\text{ dB}$):** `Scientifically established and correctly specified`.
* **5. DEM Topographic Slope Masking:** `Scientifically established and correctly specified`.
* **6. Spatial Morphological Sieve (MMU):** `Scientifically established and correctly specified`.
* **7. Permanent Water Body Subtraction:** `Scientifically established and correctly specified`.
* **8. Polarimetric Double-Bounce Decomposition (Emergent Crops):** `Requires additional input data (L-band)` / `Planned future work`.
* **9. Continuous Flood Duration Estimation:** `Requires additional input data (dense time series)`.

---

### Detailed Method Specifications

#### 1. Radiometric Conversion & Speckle Filtering
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Convert linear radar backscatter power to logarithmic decibels and attenuate granular multi-look speckle noise without destroying sharp land-water boundary transitions.
* **Mathematical Basis:**
  $$\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\sigma^0_{\text{linear}})$$
  $$\bar{\sigma}^0(i, j) = \frac{1}{K^2} \sum_{m=-k}^{k} \sum_{n=-k}^{k} \sigma^0(i+m, j+n)$$
* **Parameters:** `filter_window` = 5 (default odd boxcar kernel, range 3–15).
* **Implementation Status:** `implemented`.

#### 2. Bounded Otsu Thresholding on Event Backscatter
* **Scientific Classification:** `Valid but requires calibration`.
* **Scientific Purpose:** Automatically locate the optimal global separating threshold between the low-backscatter open-water distribution and higher-backscatter land distribution.
* **Calibration & Limitations:** Classical Otsu assumes a distinctly bimodal histogram with comparable class proportions. When flood extent is very low (<2% of scene) or very high (>90%), the distribution becomes unimodal, and classical Otsu fails by splitting the dominant land mode. To prevent this, the threshold search is strictly bounded between $[-24.0\text{ dB}, -11.0\text{ dB}]$. Furthermore, Otsu must be coupled with temporal relative drop ($\Delta\sigma^0$) to eliminate permanent specular scatterers (airports, smooth dry roads).
* **Mathematical Basis:** Maximizes between-class variance $\sigma_B^2(t)$:
  $$\sigma_B^2(t) = \omega_0(t)\omega_1(t) [\mu_0(t) - \mu_1(t)]^2, \quad t \in [-24.0\text{ dB}, -11.0\text{ dB}]$$
* **Implementation Status:** `implemented`.

#### 3. Fixed Radiometric Thresholding
* **Scientific Classification:** `Valid but requires calibration`.
* **Scientific Purpose:** Provide a user-defined deterministic cutoff when histogram distributions are unimodal.
* **Calibration Requirements:** Sentinel-1 C-band IW water backscatter varies with incidence angle $\theta$ (typically $-14\text{ dB}$ to $-16\text{ dB}$ at near range $\approx 30^\circ$, dropping to $-19\text{ dB}$ to $-22\text{ dB}$ at far range $\approx 45^\circ$). High surface wind (>5 m/s) elevates water backscatter to $-12\text{ dB}$. A fixed threshold of $-16.0\text{ dB}$ is calibrated for mid-range calm water and must be adjusted for windy or far-range scenes.
* **Parameters:** `fixed_threshold_db` = -16.0 dB (default, range -30.0 to -5.0 dB).
* **Implementation Status:** `implemented`.

#### 4. Differential Relative Drop ($\Delta\text{dB}$) Masking
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Distinguish real inundation from permanently low backscatter surfaces (smooth paved highways, dry sand playas, permanent radar shadows) by enforcing a mandatory temporal decrease:
  $$\Delta\sigma^0_{\text{dB}} = \sigma^0_{\text{event, dB}} - \sigma^0_{\text{baseline, dB}} \le -\text{threshold}_{\text{drop}}$$
  (equivalent to a linear backscatter power ratio $\sigma^0_{\text{event}} / \sigma^0_{\text{baseline}} \le 10^{-\text{threshold}/10} \approx 0.50$ for a 3.0 dB drop).
* **Parameters:** `min_drop_db` = 3.0 dB (default, range 1.0–10.0 dB).
* **Implementation Status:** `implemented`.

#### 5. Topographic Slope Masking
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Remove false-positive water classifications on steep mountain slopes where radar shadows mimic specular backscatter.
* **Mathematical Basis:** Evaluates Horn's DEM surface gradient:
  $$\text{Slope} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right) \le \text{max\_slope\_deg}$$
* **Parameters:** `max_slope_deg` = 5.0° (default, range 2.0°–15.0°). Pixels $>5^\circ$ are discarded.
* **Implementation Status:** `implemented`.

#### 6. Spatial Morphological Sieve (MMU Filter)
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Enforce a Minimum Mapping Unit (MMU) to eliminate isolated single-pixel radar speckle false detections.
* **Parameters:** `min_cluster_pixels` = 5 pixels (default, 4-connected clustering, discarding isolated patches $<500\text{ m}^2$ at 10m posting).
* **Implementation Status:** `implemented`.

#### 7. Permanent Water Subtraction
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Subtract multi-decadal permanent lake/river surface from total detected water to isolate net anomalous floodwater.
* **Mathematical Basis:**
  $$\text{Flood}_{\text{anomalous}} = \text{Water}_{\text{event}} \cap \neg \text{Water}_{\text{permanent}}$$
* **Implementation Status:** `implemented`.

#### 8. Flooded Vegetation & Sub-Canopy Double Bounce
* **Scientific Classification:** `Requires additional input data (L-band SAR)` / `Planned future work`.
* **Scientific Description:** Under C-band ($\lambda = 5.6\text{ cm}$), leafy agricultural canopies attenuate microwaves, obscuring sub-canopy floodwaters. At emergent stalks, double-bounce increases $\text{VV}$ backscatter (inverting the specular drop). Resolving flooded vegetation requires L-band ($\lambda = 24\text{ cm}$) polarimetric decomposition ($m-\chi$ or Freeman-Durden).
* **Implementation Status:** `future_research` (deferred in `FloodsPipeline.deferred_features`).

#### 9. Continuous Flood Duration Calculation
* **Scientific Classification:** `Requires additional input data (dense multi-temporal time series)`.
* **Scientific Description:** True inundation duration (days submerged) cannot be calculated from a single pre/post pair. It requires a sequence of co-flood passes spanning the hydrograph rise and recession. With current pairs, persistence is reported only between specific acquisition dates.
* **Implementation Status:** `planned_future_work`.

---

## Section 6 — Processing Workflow

```
Dataset Selection (baseline, event, DEM, ref_water)
  │
  ▼
Input Validation (_resolve_inputs: verifies required roles, product types, CRS, dimensions)
  │
  ▼
Preprocessing (Read raster bands, power-to-dB conversion, boxcar speckle filtering)
  │
  ▼
Scientific Analysis:
  ├─ Compute Bounded Otsu threshold on event dB raster
  ├─ Compute relative change (Delta dB = event - baseline)
  ├─ Apply DEM slope mask (slope <= 5 deg)
  ├─ Sieve connected clusters (< 5 pixels removed)
  └─ Inundation categorization:
       0 = Dry Land
       1 = Permanent Water
       2 = Anomalous Flood Inundation
  │
  ▼
Deliverable Generation (Write GeoTIFF, RGBA previews for BeforeAfterViewer)
  │
  ▼
Validation & Error Assessment (Compare with Sentinel-2 NDWI ref: compute IoU, F1, Precision, Recall)
  │
  ▼
Spatial Exposure Analysis (Intersect anomalous flood with infrastructure GeoJSON)
  │
  ▼
Standard Domain Response Assembly (Format summary_metrics, 4-tier explanation, caveats, layers)
```

* **Shared vs. Domain-Specific:**
  * Shared: `read_band`, `align_to`, `pixel_area_m2`, `mask_area_m2`, `write_geotiff`, `write_ramp_png`, `write_class_png`, `evaluate_binary_classification`, `evaluate_spatial_exposure`.
  * Domain-Specific: Dual-condition specular thresholding (Otsu + $\Delta\text{dB}$), permanent water subtraction, 4-tier flood explainability text.

---

## Section 7 — Expected Scientific Outputs

| Output Layer Key | Layer Type | Units | Physical Meaning | Generation Method | Validation Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `classification_geotiff` | Raster (GeoTIFF) | Class (0,1,2) | Categorized inundation ($0=\text{dry}$, $1=\text{perm}$, $2=\text{flood}$) | Sieve-filtered classified array | Independent S2 NDWI mask |
| `baseline_preview` | Preview (PNG) | dB | Pre-flood surface radar backscatter | Linear grayscale stretch (-25 to 0 dB) | Visual inspection |
| `event_preview` | Preview (PNG) | dB | Post-flood surface radar backscatter | Linear grayscale stretch (-25 to 0 dB) | Visual inspection |
| `change_preview` | Preview (PNG) | $\Delta\text{dB}$ | Backscatter difference ($-\Delta\text{dB}$) | Diverging color ramp (-8 to +8 dB) | Radiometric calibration |
| `flood_overlay` | Preview (PNG) | RGBA | Web overlay: Cyan = Flood, Navy = Permanent | Indexed color palette mapping | S2 NDWI & JRC |
| `validation_geotiff` | Raster (GeoTIFF) | Class (0..4) | Confusion matrix spatial residuals | TP, FP, TN, FN overlay | Sentinel-2 NDWI reference |
| `validation_overlay` | Preview (PNG) | RGBA | Visual Error Explorer residual map | Green=TP, Red=FP, Blue=FN | Sentinel-2 NDWI reference |

* **CRS:** Same as baseline input (`EPSG:32634`).
* **NoData:** $0$ / transparent.
* **Legend Requirements:** Dynamic legend with Cyan (#06b6d4) for Flood, Navy (#1e40af) for Permanent, Red (#ef4444) for False Positives.

---

## Section 8 — Metrics and Calculations

### Area Calculation Formula
For each cell $i$, ellipsoidal pixel area $A_i$ ($m^2$) is computed from raster transform and latitude:
$$\text{Area}_{\text{flood}} (\text{km}^2) = \frac{1}{10^6} \sum_{i \in \text{Flood}} A_i$$

### Summary Metrics Provided
1. **`flood_area_km2`:** Net anomalous standing floodwater area (excludes permanent water bodies).
2. **`permanent_water_km2`:** Baseline / permanent water surface area.
3. **`total_water_km2`:** Total water extent ($\text{flood} + \text{permanent}$).
4. **`otsu_threshold_db`:** Derived cutoff threshold in decibels (e.g., $-16.8\text{ dB}$).
5. **`mean_backscatter_drop_db`:** Average $\sigma^0$ attenuation across flooded pixels.
6. **`valid_coverage_pct`:** Percentage of non-NoData pixels analyzed within the study area.

---

## Section 9 — Validation Strategy

| Validation Source | What It Validates | Independence Tier | Spatial Comp. | Temporal Comp. | Accuracy Metrics |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `ds-real-thessaly-s2-flood-ref` | Inundation classification boundaries | Independent Cross-Sensor (Optical NDWI) | $690\times 762$ resampled to 10m | 48-hour gap (Sept 13 SAR vs Sept 15 S2) | IoU, Precision, Recall, F1, Balanced Accuracy |
| `ds-real-thessaly-jrc-water` | Permanent water baseline | Independent Climatological (Landsat GSW) | Continental 30m grid | 30-year climatology | Intersection percentage |
| `ds-bench-thessaly-ref-flood` | Algorithmic logic and edge cases | Synthetic Benchmark | Matched $1320\times 1470$ | Coincident | Unit test regression check |

* **When Reference Data is Unavailable:** Pipeline runs in non-validated mode (`validation.status = "not_validated"`), returning conservative metrics accompanied by explicit uncertainty caveats.

---

## Section 10 — Frontend Specification

### Workspace Layout (`Domain1Page.jsx`)
* **Study Area Selection:** Thessaly Basin (Lake Karla) auto-selected with focus buttons for *Lake Karla Core*, *Pineios River Inundation*, and *Palamas Floodplain*.
* **Dataset Selector:** Paired baseline and event dropdowns filtered by `domain1` and `product_type: sar_backscatter`.
* **Processing Controls:** Sliders for `min_drop_db` (1.0–10.0 dB) and `filter_window` (3–15 px), toggle for slope masking.
* **Map Controls (`SharedMap` / `BeforeAfterViewer`):**
  * Split-screen slider comparing Pre-Flood SAR (Left) to Post-Flood SAR (Right).
  * Layer toggle for Classified Flood Overlay (Cyan) and Permanent Water (Navy).
* **Metrics Panel:** Displays net flood area ($\text{km}^2$), mean backscatter drop ($\text{dB}$), Otsu threshold ($\text{dB}$), and IoU accuracy score.
* **Scientific Explainability Accordion:** 4-tier expandable card explaining visual detections, Otsu method, empirical evidence, and wind/shadow caveats.

---

## Section 11 — Backend File Responsibilities

* `backend/app/domains/domain1/processor.py`: Implements `FloodsPipeline`, inheriting from `DomainPipeline` (`backend/app/services/pipeline.py`). Declares input specifications (`InputSpec`), algorithm parameters (`ParamSpec`), orchestrates execution via `run(ctx)`, and produces outputs formatted for `StandardDomainResponse` (`backend/app/schemas/results.py`).
* `backend/app/services/processing_service.py`: Central execution coordinator (`ProcessingService`) that resolves datasets, checks spatial/polarization compatibility, tracks execution timing, and persists run records.
* `backend/app/domains/domain1/preprocessing.py`: Domain-specific modular preprocessing utilities (radiometric calibration, multi-looking, and DEM reprojection).
* `backend/app/domains/domain1/analysis.py`: Domain-specific modular scientific routines (bounded Otsu calculation, relative drop masking, and cluster sieving).
* `backend/app/domains/domain1/visualization.py`: Domain-specific raster rendering and preview generator.
* `backend/app/utils/raster.py` & `validation.py`: Shared platform utilities providing core raster I/O, georeferenced area calculation, and binary confusion matrix evaluation.

---

## Section 12 — API Integration

### Endpoint
`POST /api/domains/domain1/process`

### Sample Request Payload
```json
{
  "inputs": {
    "baseline": "5c351e81-1dfc-4d6b-9eec-9aed124eee8a",
    "event": "15a8d70a-999e-4575-a2b7-b7b502f0dad8",
    "reference_flood": "ds-real-thessaly-s2-flood-ref",
    "reference_water": "ds-real-thessaly-jrc-water",
    "dem": "ds-real-thessaly-cop-dem",
    "exposure_assets": "ds-exp-thessaly-assets"
  },
  "parameters": {
    "min_drop_db": 3.0,
    "filter_window": 5,
    "max_slope_deg": 5.0,
    "min_cluster_pixels": 5
  },
  "study_area_bbox": [22.75, 39.40, 23.00, 39.65]
}
```

### Error Scenarios Handled
* Missing `baseline` or `event` -> HTTP 422 (`PipelineInputError`).
* Product type mismatch (e.g. passing `insar_displacement` as baseline) -> HTTP 422 with rejected type explanation.
* Disjoint raster bounds -> HTTP 422 with coordinate overlap error.

---

## Section 13 — Testing and Acceptance Criteria

1. **Unit Tests (`test_domain1_pipeline.py`):**
   * Verification of power-to-dB conversion and Otsu threshold bounds.
   * Execution on synthetic $20\times 20$ test fixtures (`ds-test-base-flood`, `ds-test-event-flood`).
2. **Accuracy Assessment:** F1-score $\ge 0.85$ and IoU $\ge 0.75$ when evaluated against `ds-real-thessaly-s2-flood-ref`.
3. **Terrain Masking Verification:** Zero flood pixels reported on terrain slopes $>10^\circ$.
4. **Permanent Water Subtraction:** Calculated `flood_area_km2` must exclude known permanent water bodies.

---

## Section 14 — Limitations and Future Work

### Limitations
* Open-water specular assumption fails when sustained surface winds $>8\text{ m/s}$ generate rough capillary surface waves.
* C-band microwaves cannot penetrate dense tree canopies to detect submerged root systems.
* Cloud-free optical validation data was acquired 48 hours after the SAR observation, during which partial floodwaters had already receded.

### Future Work
* Integration of NISAR L-band dual-pol data to decompose sub-canopy double-bounce flood signatures.
* Assimilation of hydrologic river runoff models for dynamic water depth estimation.
