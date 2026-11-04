# Domain Technical Specification — Domain 5: Glaciers & Snow/Ice

**Document ID:** `SPEC-D5-GLACIERS-ICE`
**Version:** 1.0 (Implementation-Ready Specification)
**Status:** Approved for Implementation
**Domain Owner:** Team Member 1 — Platform Integration Lead (`backend/app/domains/domain5/`, `frontend/src/domains/domain5/`)

---

## Section 1 — Domain Overview

* **Domain ID & Name:** `domain5` — Glaciers, Snow & Ice
* **Scientific Objective:** Quantify, visualize, and monitor ice stream surface flow velocity dynamics, fast-flowing outlet glacier discharge corridors, terminus calving front advance and retreat, and interannual velocity anomalies using repeat-pass Synthetic Aperture Radar (SAR) observations and validated satellite ice velocity products (e.g., NASA MEaSUREs ITS_LIVE). The domain delineates high-velocity ice streams ($\ge 1,000\text{ m/yr}$), segments terminus calving margin shifts, estimates exposed fjord melange areas, evaluates continuous interannual velocity anomalies against decadal climatologies, and intersects discharging ice streams with protected UNESCO marine corridors.
* **Study Area & Event:** Jakobshavn Isbræ (Sermeq Kujalleq) and Ilulissat Icefjord, West Greenland (fastest-discharging outlet glacier in the northern hemisphere, rapid terminus retreat and seasonal calving cycles).
* **Assigned Team Member:** Team Member 1 (Platform Integration Lead & Domain Specialist).
* **Main Research Questions:**
  1. What is the spatial distribution and peak magnitude of surface flow speed ($m/\text{yr}$) across Jakobshavn Isbræ's main trunk and tributary shear margins?
  2. How can fast-streaming ice ($>1,000\text{ m/yr}$) be segmented from slow inland sheet flow ($<100\text{ m/yr}$) without arbitrary heuristic thresholds?
  3. What is the spatial extent of terminus calving margin retreat between pre-calving and post-calving repeat SAR passes?
  4. How does an annual velocity field deviate from a multi-year climatological baseline, and how can this interannual anomaly be communicated without mislabeling it as independent in-situ error?
* **Expected Scientific Contribution:** A cryosphere pipeline that maps surface velocity fields with calibrated color ramps, separates ice speed from volumetric mass loss, differentiates interannual anomalies from sensor validation, tracks terminus margin positions, and provides 4-tier explainability for polar researchers and climate hazard monitoring.
* **Implementation Status:** `implemented` (operational backend pipeline and full Jakobshavn dataset inventory active).

---

## Section 2 — Scientific Problem

### Physical Phenomenon Investigated
Outlet glaciers and ice streams drain the vast interior Greenland Ice Sheet into ocean fjords. Under gravitational driving stress, ice deforms internally through viscoplastic creep and slides over bedrock or deformable subglacial till, accelerating into narrow bedrock troughs. At the terminus, intense longitudinal stretching produces dense transverse crevasses and periodic calving of monumental icebergs into proglacial melange.

### Why SAR is Useful
Polar regions experience months of continuous polar night during winter and frequent summer storm fog and cloud cover. Optical satellites cannot image polar glaciers in darkness or through clouds. Active SAR illuminates the ice sheet day or night, penetrates dry polar surface snow, and interacts with structural crevasses and surface roughness, enabling year-round velocity tracking and terminus mapping.

### What SAR Can Measure
* Horizontal surface flow velocity magnitude ($m/\text{yr}$) using sub-pixel radar offset tracking (cross-correlation of speckle patterns and large crevasse features) between repeat passes.
* Calving front terminus margin positions using backscatter contrast between rough, crevassed glacial ice and smooth fjord sea ice/open water.
* Structural shear margins, moraines, and crevasse field development.
* Surface freeze-thaw state transitions (dry snow vs. wet summer meltwater).

### What SAR Cannot Directly Measure
* Volumetric ice mass loss ($\text{Gt}/\text{yr}$) or sea-level rise contribution directly from surface velocity without knowing ice thickness across the flux gate (e.g., from BedMachine Greenland v5 bed topography and ice-penetrating radar) and regional surface mass balance:
  $$Q_{\text{discharge}} = \rho_{\text{ice}} \int_{\text{gate}} \bar{v}(x) \cdot H(x) \, dx$$
  where $\rho_{\text{ice}} \approx 917\text{ kg/m}^3$, $\bar{v}$ is depth-averaged velocity, and $H(x)$ is ice thickness. Surface velocity alone represents only boundary kinematic flow.
* Basal sliding velocity vs. internal plastic deformation (Glen's Flow Law: $\dot{\varepsilon} = A \tau^n$) within the internal ice column.
* Subglacial water pressure, basal lubricating film thickness, or subglacial conduit geometry beneath the glacier bed.

### Factors Affecting Observation Quality
1. **Summer Surface Melt:** During warm summer months, liquid meltwater pools on the glacier surface, absorbing microwaves and drastically reducing backscatter ($\sigma^0$), which causes offset tracking cross-correlation to decorrelate.
2. **Fast Dynamic Crevasse Rearrangement:** In fast-moving ice streams ($>5,000\text{ m/yr}$), crevasses deform and open/close rapidly within a 12-day repeat pass, causing feature tracking algorithms to lose correlation.
3. **Temporal Sampling Interval:** A 12-day or 24-day baseline represents average velocity over that interval; it smooths over short-term tidal velocity pulses.
4. **Ionospheric Scintillation:** In high-latitude Greenland, auroral electron density irregularities distort radar wave propagation, introducing azimuth streaks and false displacement signals.

### Scientific Assumptions
* Surface velocity vectors are predominantly horizontal and parallel to local ice surface slopes.
* Feature tracking cross-correlation peak represents true physical ice advection between passes.
* Comparing an annual velocity mosaic to a multi-year climatology measures physical interannual flow anomaly ($\Delta v$), not sensor error.
* Backscatter transitions across the fjord boundary delineate the calving front edge.

---

## Section 3 — Dataset Inventory

The following table lists the 13 verified datasets assigned to Domain 5, located in `data/raw/domain3/` and registered in `data/manifests/datasets.json`.

| Dataset ID | Dataset Name | Provider | Sensor | Product Type | Acquisition Date | Physical Path | Logical Domain | Availability | Scientific Suitability |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: | :---: | :--- |
| `ds-demo-d3-exp` | Ilulissat Icefjord Monitoring Zone (Synthetic Exposure GeoJSON) | Vector GIS | Vector GIS | `exposure_assets` | None | `data/raw/domain3/demo_cryo_exp.geojson` | `domain5` | Available | Suitable: UNESCO World Heritage site boundary fixture. |
| `ds-demo-d3-ref` | Jakobshavn Independent Reference Velocity (Synthetic Validation Fixture) | Synthetic Model | Validation Raster | `reference_velocity` | 2025-07-15 | `data/raw/domain3/demo_cryo_ref.tif` | `domain5` | Available | Suitable: Synthetic baseline velocity for unit tests. |
| `ds-demo-d3-sar-base` | Jakobshavn Pre-Calving Terminus SAR (Synthetic Demo Fixture) | Simulated SAR HH | Simulated SAR HH | `sar_backscatter` | 2025-07-01 | `data/raw/domain3/demo_cryo_sar_base.tif` | `domain5` | Available | Suitable: Pre-calving terminus backscatter fixture. |
| `ds-demo-d3-sar-event` | Jakobshavn Post-Calving Terminus SAR (Synthetic Demo Fixture) | Simulated SAR HH | Simulated SAR HH | `sar_backscatter` | 2025-07-20 | `data/raw/domain3/demo_cryo_sar_event.tif` | `domain5` | Available | Suitable: Post-calving terminus backscatter fixture. |
| `ds-demo-d3-vel` | Jakobshavn Surface Ice Velocity (Synthetic ITS_LIVE Demo Fixture) | Simulated ITS_LIVE | Simulated Velocity | `ice_velocity` | 2025-07-15 | `data/raw/domain3/demo_cryo_vel.tif` | `domain5` | Available | Suitable: Calibrated $0–14,000\text{ m/yr}$ velocity fixture. |
| `ds-real-d3-exp` | Ilulissat Icefjord UNESCO Monitoring Sectors (GeoJSON) | Vector GIS Layer | Vector GIS | `exposure_assets` | None | `data/raw/domain3/jakobshavn_exposure_assets.geojson` | `domain5` | Available | Suitable: Protected marine reserve and navigation channels. |
| `ds-real-d3-ref` | NASA MEaSUREs ITS_LIVE Multi-Year Reference Ice Velocity (Jakobshavn Isbræ) | NASA JPL / NSIDC | Multi-Sensor Climatology | `reference_velocity` | 2020-01-01 | `data/raw/domain3/jakobshavn_itslive_mmy_reference_velocity.tif` | `domain5` | Available | Suitable: Multi-year climatological reference velocity ($m/\text{yr}$). |
| `ds-real-d3-sar-base` | Sentinel-1A RTC Terminus Baseline SAR HH (2023-08-28, Jakobshavn Isbræ) | Copernicus / ESA | Sentinel-1A IW GRDH RTC | `sar_backscatter` | 2023-08-28 | `data/raw/domain3/jakobshavn_s1_20230828_rtc_hh.tif` | `domain5` | Available | Suitable: Real pre-calving polar SAR backscatter ($\text{HH}$). |
| `ds-real-d3-sar-event` | Sentinel-1A RTC Terminus Repeat SAR HH (2023-09-09, Jakobshavn Isbræ) | Copernicus / ESA | Sentinel-1A IW GRDH RTC | `sar_backscatter` | 2023-09-09 | `data/raw/domain3/jakobshavn_s1_20230909_rtc_hh.tif` | `domain5` | Available | Suitable: Real post-calving polar SAR backscatter ($\text{HH}$). |
| `ds-real-d3-vel` | NASA MEaSUREs ITS_LIVE 2022 Annual Ice Velocity (Jakobshavn Isbræ, Greenland) | NASA JPL / NSIDC | ITS_LIVE Multi-Mission (S1/L8) | `ice_velocity` | 2022-07-01 | `data/raw/domain3/jakobshavn_itslive_2022_velocity_m_yr.tif` | `domain5` | Available | Suitable: Calibrated 2022 annual ice velocity field ($m/\text{yr}$). |
| `ds-test-d3-sar-base` | Test Terminus Pre-Calving SAR | Internal Test Suite | Unspecified | `sar_backscatter` | None | `data/raw/domain3/test_terminus_base.tif` | `domain5` | Available | Suitable: Fast $30\times 30$ unit test fixture. |
| `ds-test-d3-sar-event` | Test Terminus Post-Calving SAR | Internal Test Suite | Unspecified | `sar_backscatter` | None | `data/raw/domain3/test_terminus_event.tif` | `domain5` | Available | Suitable: Fast $30\times 30$ unit test fixture. |
| `ds-test-d3-vel` | Test Ice Velocity ITS_LIVE | Internal Test Suite | Unspecified | `ice_velocity` | None | `data/raw/domain3/test_ice_velocity.tif` | `domain5` | Available | Suitable: Fast $30\times 30$ unit test fixture. |

### Dataset Grouping Breakdown
1. **Currently Available (13):** All 13 datasets exist on disk in `data/raw/domain3/`.
2. **Suitable for Operational Pipeline (5):** `ds-real-d3-vel`, `ds-real-d3-ref`, `ds-real-d3-sar-base`, `ds-real-d3-sar-event`, `ds-real-d3-exp`.
3. **Available for Unit Testing / Demo (8):** `ds-demo-d3-vel`, `ds-demo-d3-ref`, `ds-demo-d3-sar-base`, `ds-demo-d3-sar-event`, `ds-demo-d3-exp`, `ds-test-d3-vel`, `ds-test-d3-sar-base`, `ds-test-d3-sar-event`.
4. **Additional Datasets Required (Future Acquisition):**
   * *NASA ICESat-2 Land Ice Height (ATL06):* Along-track laser altimetry profiles to measure surface elevation thinning ($dh/dt$).
   * *BedMachine Greenland v5 (Ice Thickness / Bed Topography):* To enable mass flux gate calculations ($Q = \int v \cdot H \, dx$).
5. **Independent Reference Products (1):** `ds-real-d3-ref` (NASA ITS_LIVE multi-decadal climatology).

---

## Section 4 — Input Requirements

### InputSpec Role Specifications
As declared in `GlaciersPipeline.inputs`:
* `velocity` (**Required**, `ice_velocity`): Calibrated ice surface velocity magnitude raster in meters per year ($m/\text{yr}$) from pre-computed feature tracking (e.g., NASA MEaSUREs ITS_LIVE).
* `reference_velocity` (*Optional Validation*, `reference_velocity`): Independent reference velocity raster or multi-year climatological baseline ($m/\text{yr}$) for continuous anomaly and residual evaluation.
* `baseline_sar` (*Optional Terminus Mode*, `sar_backscatter`): Polarimetric calibrated $\text{HH}$ backscatter raster acquired prior to calving.
* `event_sar` (*Optional Terminus Mode*, `sar_backscatter`): Polarimetric calibrated $\text{HH}$ backscatter raster acquired after calving.
* `exposure_assets` (*Optional*, `exposure_assets`): GeoJSON vector layer of UNESCO monitoring zones, shipping channels, or research stations.

### Sensor & Technical Invariants
* **Sensors:** Sentinel-1A/B C-band SAR, NISAR L-band, Landsat-8/9 OLI, or composite ITS_LIVE mosaics.
* **Polarization:** $\text{HH}$ preferred over polar ice (higher co-pol SNR over dry firn and crevasses); $\text{VV}$ accepted.
* **Velocity Units:** Meters per year ($m/\text{yr}$); non-standard products ($m/\text{day}$) automatically scaled ($v_{yr} = v_{day} \times 365.25$).
* **Spatial Coverage:** Must cover Jakobshavn Isbræ outlet trunk ($[-50.5^\circ\text{W}, 69.0^\circ\text{N}]$ to $[-49.2^\circ\text{W}, 69.4^\circ\text{N}]$).
* **CRS:** Polar Stereographic North (`EPSG:3413` - standard for Greenland) preferred; UTM Zone 22N (`EPSG:32622`) reprojected on ingest.
* **Posting:** 100m to 240m grid spacing for velocity fields; 10m to 20m for terminus SAR rasters.

---

## Section 5 — Scientific Methods and Algorithms

### Method Classification Summary
* **1. Offset Tracking Velocity Field Ingestion & Scaling:** `Scientifically established and correctly specified`.
* **2. Fast-Streaming Outlet Trunk Segmentation ($\ge 1,000\text{ m/yr}$):** `Scientifically established and correctly specified`.
* **3. Continuous Interannual Climatological Anomaly Evaluation:** `Scientifically established and correctly specified` (Quantifies dynamic acceleration/deceleration; strictly non-equivalent to observation error).
* **4. Calving Front Terminus Margin Differencing:** `Scientifically established and correctly specified`.
* **5. Sub-Pixel Normalized Cross-Correlation (NCC) Feature Tracking Engine:** `Planned future work`.
* **6. Volumetric Ice Discharge Flux Gate Mass Balance:** `Requires additional input data (BedMachine Greenland v5)` / `Planned future work`.
* **7. Grounding Line Tidal Flexure Double-Differential InSAR:** `Planned future work`.

---

### Detailed Method Specifications

#### 1. Offset Tracking Ingestion & Velocity Field Mapping
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Mathematical Basis:** Velocity vector fields derived from repeat-pass SAR amplitude cross-correlation:
  $$v_x = \frac{\Delta x}{\Delta t}, \quad v_y = \frac{\Delta y}{\Delta t}$$
  $$\lvert v \rvert = \sqrt{v_x^2 + v_y^2} \quad (\text{meters per year})$$
  Daily flow velocities are scaled to annual rates: $v_{\text{yr}} = v_{\text{day}} \times 365.25$.
* **Offset Tracking Requirements:**
  - Matching window: $64\times 64$ to $128\times 128$ pixels.
  - Frequency domain oversampling factor: $2\times$ to $4\times$ via FFT interpolation to achieve sub-pixel resolution ($\sim 0.05$ pixel).
  - Stagnant bedrock calibration: Bedrock outcrops around the fjord margins are masked to determine and subtract residual orbital offsets ($\bar{v}_{\text{bedrock}} \to 0\text{ m/yr}$).
* **Velocity Uncertainty Scaling:**
  $$\sigma_v = \frac{\sigma_{\Delta x}}{\Delta t}$$
  where $\sigma_{\Delta x} \approx 0.05 \times \Delta x_{\text{pixel}} \approx 0.5\text{ m}$. For a 12-day Sentinel-1 temporal baseline:
  $$\sigma_v \approx \frac{0.5\text{ m}}{12 / 365.25\text{ yr}} \approx 15.2\text{ m/yr}$$
* **Implementation Status:** `implemented`.

#### 2. Fast-Streaming Trunk Segmentation
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Isolate the fast-discharging central ice stream trunk from slow-moving interior ice sheet flow and lateral bedrock margins.
* **Mathematical Basis:**
  $$\text{FastStream} = v_{\text{surface}}(\mathbf{x}) \ge v_{\text{threshold}}$$
* **Parameters:** `fast_stream_threshold_m_yr` = 1,000.0 m/yr (default, range 200–5,000 m/yr). Peak velocities along Jakobshavn's floating tongue reach $12,000–14,000\text{ m/yr}$.
* **Implementation Status:** `implemented`.

#### 3. Continuous Interannual Anomaly Evaluation
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Mathematical Basis:** Evaluates spatial dynamic shifts relative to the multi-decadal baseline:
  $$\Delta v(i) = v_{\text{observed}}(i) - v_{\text{climatology}}(i)$$
  $$\text{Mean Anomaly} = \frac{1}{N} \sum_{i=1}^N \Delta v(i), \quad \text{RMSE}_{\text{anomaly}} = \sqrt{\frac{1}{N}\sum_{i=1}^N (\Delta v(i))^2}$$
* **Critical Scientific Safeguard:** This continuous field comparison measures **physical interannual ice flow acceleration or deceleration** between epochs. **It must never be reported as observational measurement error.** True sensor error validation requires contemporaneous GPS stake telemetry or synchronous independent cross-sensor tracking (e.g., Landsat-8/9 feature tracking).
* **Implementation Status:** `implemented`.

#### 4. Terminus Calving Front Margin Differencing
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Measure calving retreat and ice area detached into the proglacial fjord melange between repeat passes.
* **Mathematical Basis:**
  $$\Delta\text{Area}_{\text{calved}} = \text{Area}(\text{Terminus}_{\text{baseline}}) - \text{Area}(\text{Terminus}_{\text{event}})$$
  Detected via step gradient backscatter thresholding ($\Delta\sigma^0 \ge 4.0\text{ dB}$) across the high-backscatter crevassed terminus ice and low-backscatter open water or smooth melange.
* **Implementation Status:** `implemented`.

#### 5. Volumetric Ice Discharge Flux Gate Mass Balance
* **Scientific Classification:** `Requires additional input data (BedMachine Greenland v5)` / `Planned future work`.
* **Scientific Limitation:** Converting surface velocity to volumetric mass discharge requires bed elevation and ice thickness $H(x)$ across a cross-sectional flux gate:
  $$Q = \rho_{\text{ice}} \int_{\text{gate}} \bar{v}(x) \cdot H(x) \, dx$$
  where $\rho_{\text{ice}} \approx 917\text{ kg/m}^3$ and $\bar{v}(x)$ is depth-averaged velocity ($0.90–0.95 \times v_{\text{surface}}$).
* **Implementation Status:** `future_research` (requires BedMachine Greenland v5).

#### 6. Sub-Pixel NCC Feature Tracking Engine
* **Scientific Classification:** `Planned future work`.
* **Scientific Purpose:** Direct ingestion and cross-correlation of raw Level-1 SAR SLC pairs to compute custom velocity grids from scratch.
* **Implementation Status:** `planned_future_work` (deferred in `CryospherePipeline.deferred_features`).

---

## Section 6 — Processing Workflow

```
Dataset Selection (velocity mosaic, climatology, baseline SAR, event SAR)
  │
  ▼
Input Validation (verifies ice_velocity product type, velocity units)
  │
  ▼
Preprocessing (Read velocity bands, convert m/day to m/yr if needed, clip to AOI)
  │
  ▼
Scientific Velocity Analysis:
  ├─ Compute Velocity Summary Metrics (min, max, mean, std in m/yr)
  ├─ Segment Fast-Streaming Outlet Trunk (>= 1,000 m/yr)
  ├─ Calculate Fast-Streaming Area (km2) and Domain Percentage (%)
  └─ If baseline/event SAR supplied:
       ├─ Delineate Terminus Advance/Retreat Boundary
       └─ Compute Calved Area Loss (km2)
  │
  ▼
Deliverable Generation:
  ├─ Export Clipped Velocity GeoTIFF
  ├─ Generate Calibrated Viridis/Magma Velocity Heatmap Preview
  ├─ Generate Terminus Calving Boundary Preview
  └─ Generate High-Velocity Trunk Polygon Overlay
  │
  ▼
Climatological Anomaly Evaluation:
  ├─ Compute continuous residual grid vs multi-year climatological reference
  ├─ Calculate RMSE, Mean Interannual Anomaly, and Bias (m/yr)
  └─ Generate Anomaly Residual GeoTIFF & Preview
  │
  ▼
Exposure Intersection:
  └─ Intersect fast-streaming ice with UNESCO World Heritage boundary
  │
  ▼
Assemble StandardDomainResponse (KPI metrics, 4-tier explainability, caveats)
```

---

## Section 7 — Expected Scientific Outputs

| Output Layer Key | Layer Type | Units | Physical Meaning | Generation Method | Validation Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `velocity_geotiff` | Raster (GeoTIFF) | $m/\text{yr}$ | Calibrated surface flow velocity field | Clipped & aligned velocity array | ITS_LIVE Multi-Year Reference |
| `velocity_preview` | Preview (PNG) | $m/\text{yr}$ | Web visualizer velocity heatmap | Sequential magma/viridis (0 to 14,000 m/yr) | Visual inspection |
| `fast_stream_overlay` | Preview (PNG) | RGBA | Fast-flowing ice stream trunk ($\ge 1,000\text{ m/yr}$) | Binary threshold mask | NASA MEaSUREs |
| `validation_geotiff` | Raster (GeoTIFF) | $m/\text{yr}$ | Interannual velocity anomaly grid ($\Delta v$) | $v_{2022} - v_{\text{climatology}}$ | ITS_LIVE Climatology |
| `validation_overlay` | Preview (PNG) | RGBA | Web anomaly heatmap (Blue=Decel, Red=Accel) | Diverging ramp (-2,000 to +2,000 m/yr) | ITS_LIVE Climatology |

* **CRS:** Polar Stereographic North (`EPSG:3413`).
* **Legend:** Yellow/White (#fde047, #ffffff) = Fast Streaming ($>5,000\text{ m/yr}$), Purple/Blue (#a855f7, #0077b6) = Moderate Flow, Dark Navy (#03045e) = Stagnant Ice / Rock Margin ($\approx 0\text{ m/yr}$).

---

## Section 8 — Metrics and Calculations

### Summary Metrics Provided
1. **`max_velocity_m_yr`:** Peak surface flow velocity recorded on the main outlet trunk (e.g., $11,842\text{ m/yr}$).
2. **`mean_velocity_m_yr`:** Mean surface flow speed across all non-zero ice pixels.
3. **`fast_streaming_area_km2`:** Area of the ice stream discharging at $\ge 1,000\text{ m/yr}$:
   $$\text{Area}_{\text{fast}} (\text{km}^2) = \frac{1}{10^6} \sum_{v \ge 1000} A_i$$
4. **`fast_streaming_percentage`:** Proportion of observed glacier domain exceeding the fast-flow threshold ($\%$).
5. **`terminus_change_km2`:** Net area of ice detached during calving events ($\text{km}^2$).
6. **`mean_velocity_anomaly_m_yr`:** Average interannual speedup or slowdown relative to climatology.

---

## Section 9 — Validation Strategy

| Validation Source | What It Validates | Independence Tier | Spatial Comp. | Temporal Comp. | Accuracy Metrics |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `ds-real-d3-ref` (ITS_LIVE MMY) | Interannual velocity anomaly & acceleration | Climatological Comparative Baseline (Same processing system, multi-year static composite) | Matched $107\times 101$ grid (`EPSG:3413`) | 2020 climatology vs 2022 annual | Anomaly Mean, RMSE, MAE, Correlation |
| In-Situ GPS Stakes / Bed Topography (Planned) | Absolute physical ground displacement | Independent In-Situ Geodetic Truth | Point stakes along glacier centerline | Continuous GPS records | Offset bias in $m/\text{yr}$ |
| `ds-test-d3-vel` | Pipeline logic and units handling | Synthetic Demonstration Fixture | $30\times 30$ grid | N/A | Unit regression test |

* **Scientific Truth Guard:** Comparing an annual ITS_LIVE velocity product against its multi-year climatology **must not** be described as independent in-situ validation. It measures physical interannual flow anomaly.

---

## Section 10 — Frontend Specification

### Workspace Layout (`Domain5Page.jsx`)
* **Study Area Selection:** Jakobshavn Isbræ (Sermeq Kujalleq), Ilulissat Icefjord, Greenland.
* **Study Focus Mode:** Switch between *Ice Stream Velocity Dynamics* and *Terminus Calving Front Migration*.
* **Processing Controls:** Slider for `fast_stream_threshold_m_yr` (200 to 5,000 m/yr).
* **Map Display (`BeforeAfterViewer`):**
  * Left Canvas: Pre-Calving SAR Backscatter / Velocity Map.
  * Right Canvas: Post-Calving SAR Backscatter / Interannual Anomaly Map.
  * Vector Overlay: UNESCO World Heritage boundary and fast-flow contour ($1,000\text{ m/yr}$).
* **Metrics Panel:** Displays peak speed ($m/\text{yr}$), fast-streaming area ($\text{km}^2$), and mean anomaly ($\Delta m/\text{yr}$).
* **Scientific Caveats Card:** Explains that surface flow velocity does not equal volumetric mass loss without ice thickness data and notes that summer meltwater lowers radar backscatter without indicating structural collapse.

---

## Section 11 — Backend File Responsibilities

* `backend/app/domains/domain5/processor.py`: Implements `GlaciersPipeline(CryospherePipeline)`, where `CryospherePipeline` resides in `backend/app/domains/domain3/processor.py` and inherits from `DomainPipeline` (`backend/app/services/pipeline.py`). Declares input specifications (`InputSpec`), algorithm parameters (`ParamSpec`), and produces outputs formatted for `StandardDomainResponse` (`backend/app/schemas/results.py`).
* `backend/app/api/endpoints/domain5.py`: API router dispatching requests to `GlaciersPipeline` (or `WildfiresPipeline` if fire detections/baseline inputs are provided).
* `backend/app/services/processing_service.py`: Central coordinator (`ProcessingService`) managing run persistence, input role resolution, and execution timing.
* `backend/app/domains/domain5/preprocessing.py`, `analysis.py`, `visualization.py`: Modular domain components for velocity clipping, fast-stream segmentation, and polar stereographic rasterization.
* `backend/app/utils/raster.py` & `validation.py`: Shared platform utilities providing continuous field error assessment (`evaluate_continuous_field`), sequential color stretching, and GeoTIFF export.

---

## Section 12 — API Integration

### Endpoint
`POST /api/domains/domain5/process`

### Sample Request Payload (Velocity Mode)
```json
{
  "inputs": {
    "velocity": "ds-demo-d3-vel",
    "reference_velocity": "ds-demo-d3-ref",
    "exposure_assets": "ds-demo-d3-exp"
  },
  "parameters": {
    "fast_stream_threshold_m_yr": 1000.0,
    "max_velocity_scale": 14000.0
  },
  "study_area_bbox": [-50.2, 69.1, -49.5, 69.3]
}
```

### Error Handling
* Providing an uncalibrated SAR intensity image as `velocity` triggers HTTP 422 explaining that `ice_velocity` products are required.
* Missing `velocity` triggers HTTP 422 (`PipelineInputError`).

---

## Section 13 — Testing and Acceptance Criteria

1. **Unit Tests (`test_domains_2_to_5.py`):**
   * Verification of velocity units scaling ($m/\text{day} \times 365.25 \to m/\text{yr}$).
   * Execution on synthetic $30\times 30$ cryosphere fixtures (`ds-test-d3-vel`, `ds-test-d3-sar-base`).
2. **Jakobshavn Velocity Benchmark:** Pipeline processes `ds-real-d3-vel` and detects peak velocity $>10,000\text{ m/yr}$ on the primary outlet trunk.
3. **Mass Loss Disclaimer Test:** Response payload explanation must explicitly state that velocity does not equal volumetric mass loss.
4. **Climatology Anomaly Test:** Continuous anomaly evaluation against `ds-real-d3-ref` produces mean interannual residual metrics without throwing exceptions.

---

## Section 14 — Limitations and Future Work

### Limitations
* Surface flow velocity does not directly quantify ice volume discharge ($m^3/\text{yr}$) or ice shelf melting without subglacial bathymetry and ice thickness measurements.
* Severe summer surface meltwater causes radar speckle decorrelation, creating data gaps during peak July heatwaves.
* ITS_LIVE annual products represent composite time-integrated averages that cannot capture transient sub-weekly calving events.

### Future Work
* Integration of NASA ICESat-2 ATL06 laser altimetry to compute spatial ice sheet thinning rates ($dh/dt$).
* Assimilation of BedMachine Greenland v5 subglacial bed topography to compute physical mass flux across the grounding line ($Q = \int v(x) \cdot H(x) \, dx$).
