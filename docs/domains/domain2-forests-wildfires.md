# Domain Technical Specification — Domain 2: Forests & Wildfires

**Document ID:** `SPEC-D2-FORESTS-WILDFIRES`
**Version:** 1.0 (Implementation-Ready Specification)
**Status:** Approved for Implementation
**Domain Owner:** Team Member 3 (`backend/app/domains/domain2/`, `frontend/src/domains/domain2/`)

---

## Section 1 — Domain Overview

* **Domain ID & Name:** `domain2` — Forests & Wildfires
* **Scientific Objective:** Detect, characterize, and monitor changes in forest canopy structure, biomass disturbance, and wildfire burn scars using cross-polarized Synthetic Aperture Radar (SAR) backscatter observations. The domain differentiates acute canopy loss from agricultural clearing, corroborates burn scars through dense smoke plumes with independent NASA FIRMS thermal detections, restricts analysis to established baseline forest masks, and assesses damage severity against independent satellite burned-area references.
* **Study Areas & Events:**
  1. *Novo Progresso / BR-163 Corridor, Pará, Brazil:* Tropical rainforest canopy disturbance and logging.
  2. *Dadia-Lefkimi-Soufli National Park / Evros, Greece:* European mega-wildfire (August 2023).
  3. *Butte & Tehama Counties, California, USA:* Park Fire complex (July 2024).
* **Assigned Team Member:** Team Member 3 (Lead Domain Specialist).
* **Main Research Questions:**
  1. How accurately can cross-polarized ($\text{VH}/\text{HV}$) backscatter attenuation ($\Delta\sigma^0 \le -3.0\text{ dB}$) delineate structural canopy damage relative to an intact forest baseline?
  2. How can forest canopy loss be rigorously distinguished from seasonal phenological leaf shedding, soil moisture fluctuations, and agricultural harvesting?
  3. Can SAR penetrate dense wildfire smoke to map active burn boundaries before optical satellite sensors clear cloud/smoke cover?
  4. How does spatial intersection with NASA FIRMS active thermal detections constrain radar disturbance to wildfire causes?
* **Expected Scientific Contribution:** A dual-mode radar disturbance pipeline separating forest disturbance from confirmed wildfire burn scars, enforcing rigorous scientific safeguards (never equating active thermal points with total burned area, and never labeling uncorroborated backscatter drop as legal deforestation), and delivering transparent 4-tier explainability for environmental monitors and emergency services.
* **Implementation Status:** `implemented` (operational backend pipeline and dual-region dataset fixtures active).

---

## Section 2 — Scientific Problem

### Physical Phenomenon Investigated
Intact forest canopies act as dense volumes of randomly oriented, dielectric scattering elements (leaves, twigs, branches, and boughs). In cross-polarized radar channels ($\text{VH}$ or $\text{HV}$), multiple volumetric scattering events depolarize the incident microwave pulse, producing a characteristically high volume-backscattering response ($\sigma^0_{\text{VH}} \approx -14\text{ dB}$ to $-11\text{ dB}$). When canopies are clear-cut, degraded by selective logging, or consumed by high-severity crown fires, the volumetric scatterers are removed, causing an immediate, marked reduction in cross-polarized backscatter ($\sigma^0_{\text{VH}} \le -18\text{ dB}$).

### Why SAR is Useful
Wildfires generate immense, dense smoke and aerosol plumes that completely obscure optical multispectral sensors (Sentinel-2, Landsat) for days or weeks. C-band and L-band microwaves easily penetrate smoke, clouds, and haze, allowing structural surface assessment during active fire progression. In tropical regions (e.g., Pará), cloud cover persists year-round, making SAR the only reliable tool for continuous canopy monitoring.

### What SAR Can Measure
* Relative drop in cross-polarized backscatter ($\Delta\sigma^0_{\text{VH}}$) indicating loss of leafy and branch biomass.
* Spatial perimeter and area of canopy structural disturbance.
* Post-disturbance backscatter recovery trends over multi-month time series indicating potential vegetation regeneration or persistent bare soil.

### What SAR Cannot Directly Measure
* The legal or socio-economic intent of forest clearing (e.g., illegal logging vs. permitted pasture conversion vs. natural treefall).
* Active fire flame temperature or Fire Radiative Power (FRP) without thermal sensors.
* Spectrally detailed vegetation indices (e.g., dNBR or NDVI char ratios).
* Tree species composition without auxiliary hyperspectral data.

### Factors Affecting Observation Quality
1. **Soil & Vegetation Moisture Swings:** Heavy rainfall immediately preceding a radar acquisition increases dielectric permittivity, artificially elevating backscatter and potentially masking real canopy thinning.
2. **Seasonal Phenology:** Deciduous trees shed foliage during dry/winter seasons, causing natural seasonal backscatter drops that must not be classified as deforestation.
3. **Acquisition Geometry & Orbit Heading:** Look angle differences between ascending and descending tracks cause geometric distortion on slopes, shifting apparent tree heights.
4. **Surface Roughness Post-Fire:** Severe fires that leave bare, rough soil with charred standing snags can produce specular ground-trunk double bounce, counteracting backscatter loss.

### Scientific Assumptions
* Pre-event baseline represents mature, established canopy cover verified by a baseline forest mask.
* Acute, significant drops in $\text{VH}$ backscatter ($\Delta\sigma^0 \le -3.0\text{ dB}$) within forested boundaries represent real physical canopy loss.
* Co-location of radar disturbance with NASA FIRMS thermal points provides empirical corroboration of fire-driven disturbance.
* Isolated single-pixel backscatter drops represent speckle artifacts and must be sieved out using a Minimum Mapping Unit (MMU).

---

## Section 3 — Dataset Inventory

The following table lists the 26 verified datasets assigned to Domain 2 across `data/manifests/datasets.json` (13 from `data/raw/domain2/` and 13 from `data/raw/domain5/`).

| Dataset ID | Dataset Name | Provider | Sensor | Product Type | Acquisition Date | Physical Path | Logical Domain | Availability | Scientific Suitability |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: | :---: | :--- |
| `ds-demo-d2-base` | Pará Canopy Baseline SAR HV (Synthetic Demo Fixture) | Simulated NISAR / S1 | Simulated SAR HV | `sar_backscatter` | 2025-06-01 | `data/raw/domain2/demo_forest_base.tif` | `domain2` | Available | Suitable: Synthetic tropical rainforest baseline. |
| `ds-demo-d2-event` | Pará Canopy Monitoring SAR HV (Synthetic Demo Fixture) | Simulated NISAR / S1 | Simulated SAR HV | `sar_backscatter` | 2025-08-15 | `data/raw/domain2/demo_forest_event.tif` | `domain2` | Available | Suitable: Synthetic clearing event. |
| `ds-demo-d2-exp` | Pará Protected Reserve Boundaries (Synthetic Exposure GeoJSON) | Vector GIS | Vector GIS | `exposure_assets` | None | `data/raw/domain2/demo_forest_exp.geojson` | `domain2` | Available | Suitable: Reserve boundary intersection. |
| `ds-demo-d2-mask` | Pará Baseline Forest Cover Mask (Synthetic Demo Fixture) | Synthetic Model | Forest Mask | `forest_mask` | 2025-01-01 | `data/raw/domain2/demo_forest_mask.tif` | `domain2` | Available | Suitable: Synthetic forest boundary mask. |
| `ds-demo-d2-ref` | Pará Reference Disturbance Mask (Synthetic Validation Fixture) | Synthetic Model | Validation Mask | `reference_disturbance` | 2025-08-15 | `data/raw/domain2/demo_forest_ref.tif` | `domain2` | Available | Suitable: Synthetic disturbance validation. |
| `ds-real-d2-base` | Sentinel-1A RTC Baseline Forest SAR VH (2019-08-26, Novo Progresso, Pará) | Copernicus / ESA | Sentinel-1A IW GRDH RTC | `sar_backscatter` | 2019-08-26 | `data/raw/domain2/para_s1_20190826_rtc_vh.tif` | `domain2` | Available | Suitable: Real pre-clearing tropical forest baseline. |
| `ds-real-d2-event` | Sentinel-1A RTC Monitoring Forest SAR VH (2020-08-20, Novo Progresso, Pará) | Copernicus / ESA | Sentinel-1A IW GRDH RTC | `sar_backscatter` | 2020-08-20 | `data/raw/domain2/para_s1_20200820_rtc_vh.tif` | `domain2` | Available | Suitable: Real post-clearing tropical forest monitoring. |
| `ds-real-d2-exp` | Novo Progresso / BR-163 Forest Buffer & Corridor Assets (GeoJSON) | Vector GIS Layer | Vector GIS | `exposure_assets` | None | `data/raw/domain2/para_exposure_assets.geojson` | `domain2` | Available | Suitable: Critical forest reserve buffer assets. |
| `ds-real-d2-mask` | JAXA ALOS-2 PALSAR-2 Baseline Forest Cover Mask (2019, Pará) | JAXA | ALOS-2 PALSAR-2 (L-band) | `forest_mask` | 2019-01-01 | `data/raw/domain2/para_jaxa_forest_mask_2019.tif` | `domain2` | Available | Suitable: High-confidence 25m L-band forest mask. |
| `ds-real-d2-ref` | JAXA ALOS-2 PALSAR-2 Independent Forest Loss Reference (2019→2020, Pará) | JAXA | ALOS-2 PALSAR-2 (L-band) | `reference_disturbance` | 2020-08-20 | `data/raw/domain2/para_jaxa_forest_loss_ref_2020.tif` | `domain2` | Available | Suitable: Independent cross-sensor L-band reference. |
| `ds-test-d2-base` | Test Forest Baseline HV | Internal Test Suite | Unspecified | `sar_backscatter` | None | `data/raw/domain2/test_forest_base.tif` | `domain2` | Available | Suitable: Fast $30\times 30$ unit test fixture. |
| `ds-test-d2-event` | Test Forest Monitoring HV | Internal Test Suite | Unspecified | `sar_backscatter` | None | `data/raw/domain2/test_forest_event.tif` | `domain2` | Available | Suitable: Fast $30\times 30$ unit test fixture. |
| `ds-test-d2-mask` | Test Forest Reference Mask | Internal Test Suite | Unspecified | `forest_mask` | None | `data/raw/domain2/test_forest_mask.tif` | `domain2` | Available | Suitable: Fast $30\times 30$ unit test fixture. |
| `ds-demo-d5-base` | Butte/Tehama Pre-Fire SAR HV (Synthetic Demo Fixture) | Simulated S1/NISAR | Simulated SAR HV | `sar_backscatter` | 2025-07-10 | `data/raw/domain5/demo_fire_base.tif` | `domain2` | Available | Suitable: Park Fire pre-burn baseline fixture. |
| `ds-demo-d5-event` | Butte/Tehama Active-Smoke Post-Fire SAR HV (Synthetic Demo Fixture) | Simulated S1/NISAR | Simulated SAR HV | `sar_backscatter` | 2025-07-28 | `data/raw/domain5/demo_fire_event.tif` | `domain2` | Available | Suitable: Park Fire active smoke penetration fixture. |
| `ds-demo-d5-exp` | Cohasset Ridge WUI Settlements & Roads (Synthetic Exposure GeoJSON) | Vector GIS | Vector GIS | `exposure_assets` | None | `data/raw/domain5/demo_fire_exp.geojson` | `domain2` | Available | Suitable: WUI asset exposure fixture. |
| `ds-demo-d5-firms` | Butte/Tehama Active Fire Thermal Points (Synthetic FIRMS Fixture) | Simulated FIRMS | VIIRS/MODIS Points | `fire_detections` | 2025-07-26 | `data/raw/domain5/demo_fire_firms.geojson` | `domain2` | Available | Suitable: Thermal corroboration test fixture. |
| `ds-demo-d5-ref` | Butte/Tehama Mapped Burn Perimeter Reference (Synthetic Validation Fixture) | Synthetic Model | Validation Mask | `reference_disturbance` | 2025-07-29 | `data/raw/domain5/demo_fire_ref.tif` | `domain2` | Available | Suitable: Burn perimeter validation fixture. |
| `ds-real-d5-base` | Sentinel-1A RTC Pre-Fire Baseline SAR VH (2023-08-09, Dadia Forest / Evros, Greece) | Copernicus / ESA | Sentinel-1A IW GRDH RTC | `sar_backscatter` | 2023-08-09 | `data/raw/domain5/dadia_s1_20230809_rtc_vh.tif` | `domain2` | Available | Suitable: Real pre-fire intact pine forest baseline. |
| `ds-real-d5-event` | Sentinel-1A RTC Post-Fire SAR VH (2023-09-02, Dadia Forest / Evros, Greece) | Copernicus / ESA | Sentinel-1A IW GRDH RTC | `sar_backscatter` | 2023-09-02 | `data/raw/domain5/dadia_s1_20230902_rtc_vh.tif` | `domain2` | Available | Suitable: Real post-fire consumed canopy SAR. |
| `ds-real-d5-exp` | Dadia-Lefkimi-Soufli National Park & WUI Evacuation Corridors (GeoJSON) | Vector GIS Layer | Vector GIS | `exposure_assets` | None | `data/raw/domain5/dadia_exposure_assets.geojson` | `domain2` | Available | Suitable: Protected biosphere reserve assets. |
| `ds-real-d5-firms` | NASA Terra/Aqua MODIS Active Fire Thermal Detections (Aug 2023, Dadia Forest / Evros) | NASA LANCE FIRMS | Terra/Aqua MODIS (MOD14) | `fire_detections` | 2023-08-23 | `data/raw/domain5/dadia_firms_modis_202308.geojson` | `domain2` | Available | Suitable: 1,422 real thermal fire detection points. |
| `ds-real-d5-ref` | NASA MODIS MCD64A1 Mapped Burned Area Reference (Aug 2023, Dadia Forest / Evros) | NASA EOSDIS | MODIS MCD64A1 v061 | `reference_disturbance` | 2023-08-31 | `data/raw/domain5/dadia_modis_mcd64a1_burned_area_ref.tif` | `domain2` | Available | Suitable: Independent global burned-area benchmark. |
| `ds-test-d5-base` | Test Wildfire Pre-Fire HV | Internal Test Suite | Unspecified | `sar_backscatter` | None | `data/raw/domain5/test_fire_base.tif` | `domain2` | Available | Suitable: Fast $30\times 30$ wildfire unit test. |
| `ds-test-d5-event` | Test Wildfire Post-Fire HV | Internal Test Suite | Unspecified | `sar_backscatter` | None | `data/raw/domain5/test_fire_event.tif` | `domain2` | Available | Suitable: Fast $30\times 30$ wildfire unit test. |
| `ds-test-d5-firms` | Test NASA FIRMS Thermal Hotspots | Internal Test Suite | Unspecified | `fire_detections` | None | `data/raw/domain5/test_firms.geojson` | `domain2` | Available | Suitable: Fast vector FIRMS unit test. |

### Dataset Grouping Breakdown
1. **Currently Available (26):** All 26 datasets are verified on disk.
2. **Suitable for Operational Processing (12):** `ds-real-d2-base`, `ds-real-d2-event`, `ds-real-d2-exp`, `ds-real-d2-mask`, `ds-real-d2-ref`, `ds-real-d5-base`, `ds-real-d5-event`, `ds-real-d5-exp`, `ds-real-d5-firms`, `ds-real-d5-ref`, plus 2 synthetic anchors.
3. **Available but Unsuitable for Cross-Polarized Analysis (0):** None; all SAR rasters in D2 are cross-polarized ($\text{VH}$ or $\text{HV}$).
4. **Additional Datasets Required (Future Acquisition):**
   * *NISAR L-band Polarimetric Covariance (L-GCOV):* For deeper penetration into dense multi-tier tropical rainforests.
   * *Sentinel-2 Level-2A Post-Fire Optical (B8A/B12):* To compute standardized differenced Normalized Burn Ratio ($\text{dNBR}$).
5. **Independent Validation Datasets (3):**
   * `ds-real-d2-ref`: JAXA ALOS-2 PALSAR-2 L-band forest-loss reference (Pará).
   * `ds-real-d5-ref`: NASA MODIS MCD64A1 500m Burned Area reference (Dadia).
   * `ds-real-d5-firms`: NASA FIRMS active fire hotspot records (Dadia).

---

## Section 4 — Input Requirements

### InputSpec Role Specifications
As declared in `ForestsPipeline.inputs` and `WildfiresPipeline.inputs`:
* `baseline` (**Required**, `sar_backscatter`): Pre-disturbance cross-polarized ($\text{VH}/\text{HV}$) RTC radar backscatter raster.
* `event` (**Required**, `sar_backscatter`): Post-disturbance or monitoring cross-polarized ($\text{VH}/\text{HV}$) RTC radar backscatter raster.
* `forest_mask` (*Optional*, `forest_mask`): Binary raster ($1=\text{established canopy}$, $0=\text{non-forest}$) restricting analysis to tree cover.
* `reference_disturbance` (*Optional Validation*, `reference_disturbance`): Independent disturbance or burn perimeter mask for accuracy metrics.
* `fire_detections` (*Optional Corroboration*, `fire_detections`): GeoJSON vector layer containing NASA FIRMS point thermal detections.
* `exposure_assets` (*Optional*, `exposure_assets`): GeoJSON vector layer of protected reserve boundaries, indigenous lands, or WUI settlements.

### Sensor & Technical Invariants
* **Sensor:** Sentinel-1A/B C-band SAR or NISAR L-band.
* **Polarization:** Cross-polarization ($\text{VH}$ or $\text{HV}$) **mandatory**; co-polarized ($\text{VV}/\text{HH}$) is rejected as it is dominated by direct surface roughness rather than volumetric canopy scattering.
* **Temporal Interval:** Baseline acquired within the same season (anniversary pass preferred to minimize phenological bias); event acquired within 30 days post-disturbance.
* **Spatial Coverage:** Must cover either the Pará study window ($[-55.5^\circ\text{W}, -7.2^\circ\text{S}]$) or the Dadia forest boundary ($[26.1^\circ\text{E}, 41.1^\circ\text{N}]$).
* **CRS:** Projected UTM (`EPSG:32722` for Pará, `EPSG:32635` for Dadia) required for accurate metric area math.
* **Resolution:** 10m to 25m grid spacing.

---

## Section 5 — Scientific Methods and Algorithms

### Method Classification Summary
* **1. Cross-Polarized Volume Scattering Differencing ($\Delta\sigma^0_{\text{VH}/\text{HV}}$):** `Scientifically established and correctly specified`.
* **2. Radar Forest Degradation Index (RFDI):** `Valid but requires calibration / Requires additional input data` (Strictly valid for $\text{HH}/\text{HV}$ sensors such as ALOS-2; incompatible with Sentinel-1 without empirical dual-pol modification).
* **3. Baseline Forest Canopy Masking:** `Scientifically established and correctly specified`.
* **4. Minimum Mapping Unit (MMU) Spatial Sieving:** `Scientifically established and correctly specified`.
* **5. Active Thermal Hotspot Corroboration (NASA FIRMS):** `Scientifically established and correctly specified` (Point-level temporal evidence; strictly non-equivalent to burned area).
* **6. Optical Differenced Normalized Burn Ratio ($\text{dNBR}$) Validation:** `Scientifically established and correctly specified`.
* **7. Multi-Temporal Secondary Regrowth Tracking:** `Planned future work`.

---

### Detailed Method Specifications

#### 1. Cross-Polarized Volume Scattering Differencing ($\Delta\sigma^0_{\text{VH}/\text{HV}}$)
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Measure the direct loss of randomized volumetric canopy scattering caused by commercial logging, clear-cutting, or intense wildfire crown consumption.
* **Mathematical Basis:**
  $$\Delta\sigma^0_{\text{cross, dB}} = 10 \log_{10}(\sigma^0_{\text{event, cross}}) - 10 \log_{10}(\sigma^0_{\text{baseline, cross}}) \le -\text{threshold}_{\text{drop}}$$
  where cross-polarization is $\text{VH}$ for Sentinel-1 C-band or $\text{HV}$ for ALOS-2 L-band.
* **Parameters:** `delta_drop_threshold_db` = 2.0 to 3.0 dB (default, range 1.0–8.0 dB). A drop of 3.0 dB corresponds to a 50% loss in volume scattering power.
* **Implementation Status:** `implemented`.

#### 2. Radar Forest Degradation Index (RFDI) & Polarization Requirements
* **Scientific Classification:** `Valid but requires calibration / Requires additional input data`.
* **Classical Formulation (Saatchi et al., 2000):**
  $$\text{RFDI} = \frac{\sigma_{\text{HH}}^0 - \sigma_{\text{HV}}^0}{\sigma_{\text{HH}}^0 + \sigma_{\text{HV}}^0} \quad (\text{linear power})$$
  In dense, unfragmented rainforest, multiple volume scattering produces high $\text{HV}$ and $\text{HH}$ backscatter, yielding $\text{RFDI} \in [0.1, 0.3]$. Severe structural degradation strips canopy volume scatterers while preserving or increasing horizontal surface returns ($\sigma_{\text{HH}}^0 \gg \sigma_{\text{HV}}^0$), driving $\text{RFDI} \to 0.6–0.9$.
* **Polarization Requirements & Sentinel-1 Incompatibility:**
  - **ALOS-2 PALSAR-2 L-band:** Provides true $\text{HH}$ and $\text{HV}$ channels; fully compatible with classical RFDI.
  - **Sentinel-1 C-band:** Transmits $\text{V}$ and receives $\text{V} + \text{H}$ (yielding $\text{VV}$ and $\text{VH}$). **Sentinel-1 DOES NOT provide HH.**
  - Substituting $\text{VV}$ for $\text{HH}$ ($\text{RFDI}_{\text{dual}} = \frac{\sigma_{\text{VV}}^0 - \sigma_{\text{VH}}^0}{\sigma_{\text{VV}}^0 + \sigma_{\text{VH}}^0}$) is a non-standard empirical proxy. Post-fire or logged ground exhibits high surface roughness and soil moisture fluctuations that directly inflate $\sigma_{\text{VV}}^0$, corrupting the index.
  - **Approved Operational Alternative for Sentinel-1:** Cross-polarized temporal differencing ($\Delta\sigma_{\text{VH}}^0$) or the Cross-Ratio ($\text{CR} = \sigma_{\text{VH}}^0 / \sigma_{\text{VV}}^0$), which cleanly isolates canopy volume scattering from direct surface returns.
* **Implementation Status:** Classical RFDI is `planned_future_work` for NISAR/ALOS L-band; operational pipeline uses $\Delta\sigma_{\text{VH}}^0$ differencing.

#### 3. Baseline Forest Masking
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Eliminate false positives caused by agricultural harvesting, seasonal grassland curing, or fallow field plowing.
* **Mathematical Basis:**
  $$\text{Disturbance}_{\text{valid}} = (\Delta\sigma^0_{\text{cross}} \le -\text{threshold}) \cap (\text{ForestMask} == 1)$$
  Derived from JAXA ALOS-2 Forest/Non-Forest (FNF) or Copernicus Global Land Cover tree canopy cover $\ge 50\%$.
* **Implementation Status:** `implemented`.

#### 4. Spatial Sieving (Minimum Mapping Unit Filter)
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Remove isolated single-pixel radar speckle noise and misregistration fringe artifacts that do not constitute contiguous clearings.
* **Parameters:** `min_cluster_pixels` = 5 to 6 pixels (4- or 8-connected neighborhood), corresponding to an MMU of $0.20–0.50\text{ ha}$ at 20m pixel spacing.
* **Implementation Status:** `implemented`.

#### 5. NASA FIRMS Active Thermal Hotspot Corroboration
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Provide independent thermal emission evidence to corroborate that radar-detected canopy loss was driven by active fire rather than mechanical logging:
  $$\text{Corroborated} = \text{DisturbancePolygon} \cap \text{Buffer}(\text{FIRMS}_{\text{points}}, r=500\text{m})$$
* **Non-Negotiable Scientific Safeguard:** Active thermal anomaly detections from MODIS or VIIRS represent instantaneous thermal radiative power ($FRP$ in $MW$) at the moment of satellite overpass. **Thermal detections must never be converted directly to burned area polygons.** True burned area extent must be delineated from radar structural canopy change and optical burn scars.
* **Implementation Status:** `implemented`.

#### 6. Sentinel-2 Differenced Normalized Burn Ratio ($\text{dNBR}$) Optical Validation
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Mathematical Basis:**
  $$\text{NBR} = \frac{\rho_{\text{NIR}} - \rho_{\text{SWIR2}}}{\rho_{\text{NIR}} + \rho_{\text{SWIR2}}} = \frac{\text{B8A} - \text{B12}}{\text{B8A} + \text{B12}}$$
  $$\text{dNBR} = \text{NBR}_{\text{pre}} - \text{NBR}_{\text{post}}$$
  USGS/USFS Burn Severity Classification:
  - $\text{dNBR} < 0.10$: Unburned / Regrowth
  - $0.10 \le \text{dNBR} < 0.27$: Low Severity
  - $0.27 \le \text{dNBR} < 0.66$: Moderate Severity
  - $\text{dNBR} \ge 0.66$: High Severity (Crown Fire)
* **Implementation Status:** `implemented`.

#### 7. Multi-Temporal Regrowth Tracking
* **Scientific Classification:** `Planned future work`.
* **Scientific Purpose:** Track secondary canopy succession, branch re-sprouting, and post-fire recovery trajectories over 3–5 year time series using multi-temporal L-band SAR backscatter recovery curves.
* **Implementation Status:** `future_research` (deferred in `ForestsPipeline.deferred_features`).

---

## Section 6 — Processing Workflow

### Dual-Workflow Execution Path

```
                    Dataset Selection (baseline, event, mask, FIRMS)
                                      │
                                      ▼
             Input Validation (verify cross-pol VH/HV, CRS, spatial overlap)
                                      │
                                      ▼
            Preprocessing (power-to-dB conversion, 5x5 boxcar speckle filter)
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
   [Mode A: Forest Disturbance]                  [Mode B: Wildfire Impact]
   ├─ Apply JAXA/ALOS forest mask                ├─ Intersect with NASA FIRMS points
   ├─ Flag pixels: Delta VH <= -3.0 dB           ├─ Calculate Fire Radiative Power stats
   ├─ Sieve clusters < 5 pixels                  ├─ Distinguish canopy loss from surface char
   └─ Classify into Low/High disturbance         └─ Classify into Moderate/Severe Burn Scar
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      │
                                      ▼
           Output Deliverables (Disturbance GeoTIFF, RGBA Preview Overlays)
                                      │
                                      ▼
           Accuracy Validation (Evaluate vs JAXA Loss Reference or MODIS MCD64A1)
                                      │
                                      ▼
          Spatial Exposure Intersection (Protected Reserves & WUI Settlements)
                                      │
                                      ▼
         Assemble StandardDomainResponse (KPI metrics, 4-tier explainability, caveats)
```

---

## Section 7 — Expected Scientific Outputs

| Output Layer Key | Layer Type | Units | Physical Meaning | Generation Method | Validation Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `disturbance_geotiff` | Raster (GeoTIFF) | Class (0..3) | Classified canopy loss ($0=\text{intact}$, $1=\text{moderate}$, $2=\text{severe}$) | Sieve-filtered cross-pol drop | JAXA PALSAR-2 Reference |
| `baseline_preview` | Preview (PNG) | dB | Pre-disturbance cross-pol backscatter | Grayscale linear stretch (-28 to -5 dB) | Visual inspection |
| `event_preview` | Preview (PNG) | dB | Post-disturbance cross-pol backscatter | Grayscale linear stretch (-28 to -5 dB) | Visual inspection |
| `change_preview` | Preview (PNG) | $\Delta\text{dB}$ | Cross-pol backscatter change map | Diverging color ramp (-10 to +5 dB) | Radiometric calibration |
| `disturbance_overlay` | Preview (PNG) | RGBA | Web overlay: Orange = Moderate, Red = Severe | Indexed RGBA palette mapping | JAXA / MODIS MCD64A1 |
| `validation_geotiff` | Raster (GeoTIFF) | Class (0..4) | Spatial residual confusion matrix | Pixel-level TP, FP, TN, FN | MODIS MCD64A1 / JAXA |
| `validation_overlay` | Preview (PNG) | RGBA | Visual Error Explorer map | Green=TP, Red=FP, Blue=FN | MODIS MCD64A1 / JAXA |

* **CRS:** UTM (`EPSG:32722` Pará, `EPSG:32635` Dadia).
* **Legend:** Red (#d90429) = Severe Disturbance/Burn, Orange (#fb8500) = Moderate Disturbance, Green (#38b000) = Intact Forest Canopy.

---

## Section 8 — Metrics and Calculations

### Summary Metrics Provided
1. **`disturbed_area_km2`:** Total land area experiencing cross-pol backscatter drop $\ge 3.0\text{ dB}$ within the forest boundary:
   $$\text{Area}_{\text{disturbed}} (\text{km}^2) = \frac{1}{10^6} \sum_{i \in \text{Disturbed}} A_i$$
2. **`disturbed_percentage`:** Proportion of baseline forest area affected ($\%$).
3. **`mean_attenuation_db`:** Average cross-pol attenuation magnitude across disturbed pixels.
4. **`corroborated_thermal_points`:** Count and percentage of NASA FIRMS thermal points intersecting detected radar burn scars.
5. **`reserve_area_encroached_km2`:** Forest loss area occurring inside protected reserve polygons.

---

## Section 9 — Validation Strategy

| Validation Source | What It Validates | Independence Tier | Spatial Comp. | Temporal Comp. | Accuracy Metrics |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `ds-real-d2-ref` (JAXA PALSAR-2) | Rainforest canopy clearing | Independent Cross-Sensor (L-band ALOS-2) | 25m grid resampled to 10m | Anniversary year pair (2019→2020) | IoU, Precision, Recall, F1 |
| `ds-real-d5-ref` (MODIS MCD64A1) | Wildfire burn scar perimeter | Independent Cross-Sensor (Optical Char) | 500m global grid resampled | End-of-month fire window | IoU, Precision, Recall, F1 |
| `ds-real-d5-firms` | Active thermal combustion | Empirical Thermal Corroboration | Point coordinates ($\pm 375\text{m}$) | Daily fire detection passes | Point intersection count & buffer overlap |

* **When Reference Data is Unavailable:** System outputs `"not_validated"`, warning users that uncorroborated backscatter drop reflects canopy alteration that could stem from non-anthropogenic stress or moisture shifts.

---

## Section 10 — Frontend Specification

### Workspace Layout (`Domain2Page.jsx`)
* **Study Area Selection:** Switch between *Pará (Deforestation)*, *Dadia Forest (Mega-Wildfire)*, and *Park Fire (Active Smoke)*.
* **Mode Toggle:** Seamless toggle between *Forest Disturbance Analysis* and *Wildfire Impact Analysis*.
* **Dataset Selection:** Dropdown menus populated dynamically from `GET /api/datasets?domain=domain2`.
* **Processing Controls:** Sliders for `delta_drop_threshold_db` (1.5 to 8.0 dB) and `filter_window` (3 to 15 px).
* **Map Display (`BeforeAfterViewer`):**
  * Left Canvas: Pre-fire/Pre-clearing SAR ($\text{VH}$ dB).
  * Right Canvas: Post-fire SAR through smoke or monitoring pass.
  * Overlays: Red/Orange disturbance layer, FIRMS thermal flame hotspots.
* **Validation Panel:** Interactive Error Explorer showing TP/FP/FN residuals against JAXA or MODIS reference perimeters.
* **Scientific Caveats Card:** Displays explicit notices regarding soil moisture confounding factors and non-equivalence of thermal points with burned area.

---

## Section 11 — Backend File Responsibilities

* `backend/app/domains/domain2/processor.py`: Implements `ForestsPipeline`, inheriting from `DomainPipeline` (`backend/app/services/pipeline.py`). Declares input specifications (`InputSpec`) for baseline/monitoring cross-pol SAR, forest masks, and reference data. Orchestrates execution via `run(ctx)`.
* `backend/app/domains/domain5/processor.py`: Implements `WildfiresPipeline`, inheriting from `DomainPipeline` (`backend/app/services/pipeline.py`), which executes Mode B (Wildfire Impact, thermal corroboration, and fire-perimeter validation).
* `backend/app/services/processing_service.py`: Central coordinator (`ProcessingService`) that resolves inputs, validates cross-polarization matching, and formats output into `StandardDomainResponse` (`backend/app/schemas/results.py`).
* `backend/app/domains/domain2/preprocessing.py`, `analysis.py`, `visualization.py`: Modular domain components for cross-pol calibration, $\Delta\sigma^0$ thresholding, and difference raster formatting.
* `backend/app/utils/raster.py` & `validation.py`: Shared platform utilities providing raster alignment, boxcar filtering, spatial area summation, and binary confusion matrix evaluation.

---

## Section 12 — API Integration

### Endpoint
`POST /api/domains/domain2/process`

### Sample Request Payload (Wildfire Mode)
```json
{
  "inputs": {
    "baseline": "ds-real-d5-base",
    "event": "ds-real-d5-event",
    "forest_mask": "ds-real-d2-mask",
    "reference_disturbance": "ds-real-d5-ref",
    "fire_detections": "ds-real-d5-firms",
    "exposure_assets": "ds-real-d5-exp"
  },
  "parameters": {
    "delta_drop_threshold_db": 3.0,
    "filter_window": 5,
    "min_cluster_pixels": 5
  },
  "study_area_bbox": [26.05, 41.00, 26.35, 41.25]
}
```

### Error Handling
* Submission of co-polarized data ($\text{VV}$ or $\text{HH}$) triggers HTTP 422 explaining that cross-polarization is required.
* Missing baseline or event triggers HTTP 422 (`PipelineInputError`).

---

## Section 13 — Testing and Acceptance Criteria

1. **Unit Tests (`test_domains_2_to_5.py`):**
   * Verification of cross-pol input validation.
   * Execution on synthetic $30\times 30$ forest fixtures (`ds-test-d2-base`, `ds-test-d2-event`).
2. **Wildfire Execution:** Pipeline processes Dadia Sentinel-1 pair with MODIS FIRMS points and returns $>1,000$ intersecting fire detections.
3. **Scientific Safeguards Test:** An uncorroborated single-pixel backscatter drop must never appear in the final output.
4. **Validation Test:** F1-score $\ge 0.70$ when evaluated against independent JAXA ALOS-2 reference.

---

## Section 14 — Limitations and Future Work

### Limitations
* C-band microwaves (5.6 cm) interact primarily with upper tree foliage and small twigs; severe ground fire that burns underbrush without defoliating upper tree crowns cannot be reliably detected.
* Sudden post-fire rainfall can wet charred soil, temporarily raising backscatter and masking burn scar boundaries.
* MODIS MCD64A1 burned-area validation product has a coarse 500m grid cell resolution.

### Future Work
* Integration of NISAR L-band quad-pol data to decompose sub-canopy stem and branch damage using polarimetric entropy ($H$) and alpha ($\alpha$) angle parameters.
* Machine-learned multi-temporal change detection trained on historical global burn libraries.
