# Domain Technical Specification — Domain 3: Earthquakes & Ground Deformation

**Document ID:** `SPEC-D3-EARTHQUAKES`
**Version:** 1.0 (Implementation-Ready Specification)
**Status:** Approved for Implementation
**Domain Owner:** Team Member 4 (`backend/app/domains/domain3/`, `frontend/src/domains/domain3/`)

---

## Section 1 — Domain Overview

* **Domain ID & Name:** `domain3` — Earthquakes & Ground Deformation
* **Scientific Objective:** Quantify, map, and analyze millimeter-scale Earth surface deformation caused by tectonic fault ruptures, coseismic slip, and post-seismic relaxation using repeat-pass Interferometric Synthetic Aperture Radar (InSAR). The domain isolates reliable phase signals through interferometric coherence masking, derives line-of-sight ($\text{LOS}$) displacement fields, detects maximum subsidence/uplift deformation gradients, intersects deformation lobes with critical infrastructure, and validates results against independent multi-temporal interferograms and projected GNSS vectors.
* **Study Area & Event:** Tyrnavos and Elassona basin, Thessaly, Greece (March 3, 2021, $M_w\ 6.3$ coseismic normal-faulting earthquake sequence).
* **Assigned Team Member:** Team Member 4 (Lead Domain Specialist).
* **Main Research Questions:**
  1. What is the spatial extent and maximum amplitude of coseismic Line-of-Sight surface displacement caused by the 2021 Tyrnavos earthquake sequence?
  2. How effectively does interferometric coherence filtering ($\gamma \ge 0.35$) eliminate decorrelated noise in agricultural valleys and vegetated hillsides?
  3. Where are maximum surface strain gradients concentrated, and do they trace known or previously unmapped blind normal faults?
  4. What is the residual agreement between primary 12-day InSAR observations and independent multi-temporal 18-day reference pairs or projected GNSS stations?
* **Expected Scientific Contribution:** An implementation of an InSAR deformation analysis pipeline that translates unwrapped interferometric phase into metric LOS displacement fields, filters out unreliable decorrelated signals, maps deformation gradient vectors, performs continuous residual validation against independent cross-pair baselines, and communicates geometric radar look-direction caveats to seismic hazard analysts.
* **Implementation Status:** `implemented` for supplied InSAR products (Workflow A); `planned` for raw Single Look Complex (SLC) phase unwrapping (Workflow B).

---

## Section 2 — Scientific Problem

### Physical Phenomenon Investigated
Tectonic earthquakes result from sudden frictional shear failure and slip along subsurface fault planes. Elastic strain accumulated in surrounding crustal blocks is instantaneously released, causing permanent displacement of the ground surface. For normal faulting events (such as Tyrnavos), the hanging wall drops relative to the footwall, producing asymmetric surface subsidence and localized uplift lobes.

### Why SAR is Useful
Traditional seismological networks detect high-frequency dynamic seismic waves, and GNSS stations record continuous 3D displacement at sparse point locations. InSAR uniquely provides continuous, two-dimensional spatial coverage with millions of coherent measurement points across hundreds of square kilometers, capturing localized deformation gradients and fault rupture traces that ground networks miss entirely.

### What SAR Can Measure
* Relative phase change ($\Delta\varphi$) between two coherent radar passes acquired from identical orbital geometry, measured in **radians** ($\text{rad}$).
* One-dimensional surface displacement along the satellite's Line-of-Sight ($\text{LOS}$) vector:
  $$\Delta R = -\frac{\lambda}{4\pi} \Delta\varphi_{\text{unw}}$$
  $$d_{\text{LOS}} = -\Delta R = +\frac{\lambda}{4\pi} \Delta\varphi_{\text{unw}}$$
  where $\lambda = 0.055465\text{ m}$ ($5.5465\text{ cm}$) for Sentinel-1 C-band ($f_0 = 5.405\text{ GHz}$), $\Delta R$ is radar range change, and $d_{\text{LOS}}$ is displacement along the line of sight.
* **Sign Convention Standard:**
  - $d_{\text{LOS}} > 0$ ($\Delta\varphi_{\text{unw}} > 0$): Ground motion **TOWARD** the satellite (range decrease / uplift).
  - $d_{\text{LOS}} < 0$ ($\Delta\varphi_{\text{unw}} < 0$): Ground motion **AWAY** from the satellite (range increase / subsidence).
  (Note: ASF HyP3 and LiCSAR GUNW unwrapped displacement GeoTIFFs provide values in meters following this convention).
* Local spatial gradients of surface displacement ($|\nabla d_{\text{LOS}}| = \sqrt{(\partial d_{\text{LOS}}/\partial x)^2 + (\partial d_{\text{LOS}}/\partial y)^2}$) indicating concentrated shear strain or active surface fault scarps.
* Interferometric coherence ($\gamma \in [0, 1]$), quantifying the temporal and geometric phase stability of surface scatterers.

### What SAR Cannot Directly Measure
* Full three-dimensional surface motion vectors ($u_{\text{East}}, u_{\text{North}}, u_{\text{Up}}$) from a single viewing geometry. A single InSAR pass measures only the 1D scalar projection of 3D motion onto the slanted radar beam.
* **Conditions Required for 3D Displacement Estimation:**
  - Resolving 2D motion (Vertical $u_{\text{Up}}$ and East-West $u_{\text{East}}$) requires at least two non-parallel viewing geometries (combining Ascending and Descending tracks).
  - Near-polar satellite orbits fly almost due North-South ($\approx 12^\circ$ off meridian), making InSAR fundamentally insensitive to horizontal North-South displacement ($u_{\text{North}}$). Resolving true 3D motion requires integrating InSAR with Multiple Aperture Interferometry (MAI), along-track pixel offset tracking, or dense permanent 3D GNSS stations.
* True slip distribution at depth on the subsurface fault plane without geophysical elastic dislocation modeling (e.g., Okada rectangular dislocation in an elastic half-space).
* Ground motion in completely decorrelated areas (dense forests, snow, or active tilled soil) where scatterers rearrange randomly between passes ($\gamma < 0.2$).

### Factors Affecting Observation Quality
1. **Temporal & Geometric Decorrelation:** Vegetation growth, farming, or large orbital baselines degrade interferometric coherence ($\gamma < 0.2$), introducing random phase noise.
2. **Atmospheric Phase Screen (APS):** Turbulent tropospheric water vapor variations and ionospheric electron density gradients delay the radar signal, generating spurious deformation signals of 2–10 cm if not corrected.
3. **Phase Unwrapping Ambiguities:** In steep deformation gradients where phase changes by $> \pi$ radians between adjacent pixels, phase unwrapping algorithms can introduce $2\pi$ integer cycle slips (multiples of $\lambda/2 = 2.8\text{ cm}$ for C-band).
4. **Orbital Baseline Inaccuracies:** Residual satellite orbital state vector errors induce linear or quadratic phase ramps across the scene.

### Scientific Assumptions
* The unwrapped phase product has been corrected for Earth curvature and topographic phase using an accurate DEM (e.g., Copernicus GLO-30).
* Atmospheric delay is smoothly varying across the $30\times 30\text{ km}$ study area and secondary to the primary coseismic signal ($>30\text{ cm}$).
* Displacement occurred during the coseismic window bounded by the master and slave acquisitions.
* Pixels with coherence $\gamma < 0.35$ contain excessive phase variance and must be masked out to prevent corrupted scientific metrics.

---

## Section 3 — Dataset Inventory

The following table lists the confirmed datasets available for Domain 3, sourced from `data/manifests/datasets.json` and `data/raw/domain4/`.

| Dataset ID | Dataset Name | Provider | Sensor | Product Type | Acquisition Date | Physical Path | Logical Domain | Availability | Scientific Suitability |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: | :---: | :--- |
| `ds-real-d4-coh` | COMET-LiCSAR Sentinel-1 Interferometric Coherence (2021-02-25→2021-03-09, Tyrnavos) | COMET / UK CEMS | Sentinel-1A InSAR (LiCSAR Frame 102A_04971_141314) | `insar_coherence` | 2021-03-09 | `data/raw/domain4/tyrnavos_licsar_coherence.tif` | `domain3` | Available | Suitable: Primary 12-day coherence quality mask. |
| `ds-real-d4-disp` | COMET-LiCSAR Sentinel-1 Unwrapped Coseismic LOS Displacement (2021-02-25→2021-03-09, Tyrnavos Mw 6.3) | COMET / UK CEMS | Sentinel-1A InSAR (LiCSAR Frame 102A_04971_141314) | `insar_displacement` | 2021-03-09 | `data/raw/domain4/tyrnavos_licsar_unwrapped_los_disp_mm.tif` | `domain3` | Available | Suitable: Calibrated primary coseismic LOS displacement ($mm$). |
| `ds-real-d4-exp` | Tyrnavos & Titarisios Valley Settlements and Highway Corridors (GeoJSON) | Vector GIS Layer | Vector GIS | `exposure_assets` | None | `data/raw/domain4/tyrnavos_exposure_assets.geojson` | `domain3` | Available | Suitable: Critical settlements, bridges, and infrastructure. |
| `ds-real-d4-ref` | COMET-LiCSAR Independent 18-Day Coseismic LOS Reference (2021-02-19→2021-03-09, Tyrnavos) | COMET / UK CEMS | Sentinel-1B/1A InSAR (LiCSAR Frame 102A_04971_141314) | `reference_displacement` | 2021-03-09 | `data/raw/domain4/tyrnavos_licsar_independent_ref_disp_mm.tif` | `domain3` | Available | Suitable: Independent temporal cross-pair validation. |
| `ds-test-d4-coh` | Test InSAR Coherence Mask | Internal Test Suite | Unspecified | `insar_coherence` | None | `data/raw/domain4/test_insar_coh.tif` | `domain3` | Available | Suitable: Fast $30\times 30$ unit test fixture. |
| `ds-test-d4-disp` | Test InSAR Displacement LOS | Internal Test Suite | Unspecified | `insar_displacement` | None | `data/raw/domain4/test_insar_disp.tif` | `domain3` | Available | Suitable: Fast $30\times 30$ unit test fixture. |

### Note on Unresolved Central Valley Subsidence Datasets
In addition to the 6 confirmed Tyrnavos datasets, `data/raw/domain4/` contains 4 Central Valley InSAR subsidence datasets:
* `ds-demo-d4-coh`, `ds-demo-d4-disp`, `ds-demo-d4-ref`, `ds-demo-d4-exp`.
These datasets were cataloged under `domain4` due to directory index numbering. They measure millimeter-scale aquifer compaction subsidence in California, not agricultural backscatter. They are physically InSAR products and **must not** be used as agricultural backscatter inputs. In this platform architecture, they remain documented as unresolved catalog anomalies.

### Dataset Grouping Breakdown
1. **Currently Available Confirmed Datasets (6):** `ds-real-d4-coh`, `ds-real-d4-disp`, `ds-real-d4-ref`, `ds-real-d4-exp`, `ds-test-d4-coh`, `ds-test-d4-disp`.
2. **Suitable for Operational Pipeline (4):** `ds-real-d4-coh`, `ds-real-d4-disp`, `ds-real-d4-ref`, `ds-real-d4-exp`.
3. **Available for Unit Testing (2):** `ds-test-d4-coh`, `ds-test-d4-disp`.
4. **Additional Datasets Required (Future Acquisition):**
   * *Sentinel-1 Descending Track Unwrapped InSAR Pair:* To perform 2.5D decomposition into East-West and Vertical displacement components.
   * *Continuous GNSS Station RINEX / Time Series:* Permanent stations in Thessaly (e.g., NOA, HxGN SmartNet) for in-situ geodetic validation.
5. **Independent Validation Datasets (1):** `ds-real-d4-ref` (COMET-LiCSAR independent 18-day cross-pair).

---

## Section 4 — Input Requirements

### InputSpec Role Specifications
As declared in `EarthquakesPipeline.inputs`:
* `displacement` (**Required**, `insar_displacement`): Calibrated Line-of-Sight surface deformation raster in millimeters ($mm$) or millimeters per year ($mm/\text{yr}$). Negative values indicate motion away from the satellite (subsidence or westward lateral motion); positive values indicate motion toward the satellite (uplift or eastward lateral motion).
* `coherence` (*Optional*, `insar_coherence`): Spatial interferometric coherence grid ($\gamma \in [0.0, 1.0]$).
* `reference_displacement` (*Optional Validation*, `reference_displacement`, `insar_displacement`): Independent cross-pair interferogram or interpolated geodetic field for continuous residual error computation (RMSE, MAE, Bias).
* `exposure_assets` (*Optional*, `exposure_assets`): GeoJSON vector layer of roads, buildings, bridges, and fault lines for spatial exposure intersection.

### Sensor & Technical Invariants
* **Sensor:** Sentinel-1A/B C-band SAR or NISAR L-band.
* **Product Form:** Geocoded Unwrapped Interferogram (e.g., COMET-LiCSAR or ASF HyP3 GUNW standard).
* **Temporal Interval:** Co-seismic pair spanning the March 3, 2021 earthquake window (Master: Feb 25, 2021; Slave: March 9, 2021; 12-day temporal baseline).
* **Spatial Coverage:** Must cover the Tyrnavos rupture basin ($[22.0^\circ\text{E}, 39.6^\circ\text{N}]$ to $[22.4^\circ\text{E}, 39.9^\circ\text{N}]$).
* **CRS:** `EPSG:4326` (WGS 84 geographic coordinates) or UTM Zone 34N (`EPSG:32634`).
* **Resolution:** 30m to 100m posting.

---

## Section 5 — Scientific Methods and Algorithms

### Method Classification Summary
* **1. Coherence Quality Thresholding ($\gamma \ge 0.35$):** `Scientifically established and correctly specified`.
* **2. Unwrapped Phase to LOS Displacement Scaling:** `Scientifically established and correctly specified`.
* **3. Spatial Deformation Gradient & Fault Trace Delineation ($|\nabla d_{\text{LOS}}|$):** `Scientifically established and correctly specified`.
* **4. Subsidence / Uplift Lobe Clustering & Hotspot Area Math:** `Scientifically established and correctly specified`.
* **5. Continuous Geodetic Field Validation (RMSE, MAE, Bias, Pearson $R^2$):** `Scientifically established and correctly specified`.
* **6. 3D GNSS Vector to 1D Radar Line-of-Sight Projection:** `Scientifically established and correctly specified`.
* **7. Multi-Track 2D/3D Displacement Decomposition:** `Requires additional input data (Ascending + Descending tracks + Along-track MAI)` / `Planned future work`.
* **8. Raw SLC Complex Interferogram Formation & SNAPHU Unwrapping (Workflow B):** `Planned future work`.

---

### Detailed Method Specifications

#### 1. Coherence Quality Thresholding
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Mask decorrelated and noisy pixels where phase variance destroys geodetic measurement confidence.
* **Mathematical Basis:**
  $$\text{Valid}(\mathbf{x}) = (\gamma(\mathbf{x}) \ge \gamma_{\text{threshold}}) \cap (\text{LOS}(\mathbf{x}) \ne \text{NoData})$$
  Interferometric coherence $\gamma \in [0, 1]$ represents the normalized complex cross-correlation between the two acquisitions. Pixels with $\gamma < 0.35$ exhibit phase standard deviations exceeding $30^\circ$, making phase unwrapping susceptible to $2\pi$ integer cycle slips.
* **Parameters:** `min_coherence` = 0.35 (default, range 0.10–0.80).
* **Implementation Status:** `implemented`.

#### 2. Unwrapped Phase to LOS Displacement Scaling
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Mathematical Basis:**
  For repeat-pass interferometry with radar wavelength $\lambda = 0.055465\text{ m}$ (Sentinel-1 C-band):
  $$d_{\text{LOS}} = +\frac{\lambda}{4\pi} \Delta\varphi_{\text{unw}} \quad (\text{meters})$$
  Under this geodetic standard:
  - Positive values ($d_{\text{LOS}} > 0$) indicate motion **toward** the satellite (uplift / range decrease).
  - Negative values ($d_{\text{LOS}} < 0$) indicate motion **away from** the satellite (subsidence / range increase).
* **Implementation Status:** `implemented`.

#### 3. Deformation Gradient & Fault Trace Delineation
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Locate surface rupture traces of active tectonic faults by identifying sharp localized discontinuities in the displacement field.
* **Mathematical Basis:**
  $$|\nabla d_{\text{LOS}}| = \sqrt{\left(\frac{\partial d_{\text{LOS}}}{\partial x}\right)^2 + \left(\frac{\partial d_{\text{LOS}}}{\partial y}\right)^2}$$
  Computed using central finite differencing across valid coherent neighbors. Sharp peaks delineate the surface scarp of the normal fault plane.
* **Implementation Status:** `implemented`.

#### 4. Subsidence Bowl Clustering & Area Quantification
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Delineate contiguous zones of severe coseismic ground displacement ($d_{\text{LOS}} \le -50\text{ mm}$ or uplift lobes $\ge +20\text{ mm}$):
  $$\text{Subsidence}_{\text{severe}} = (d_{\text{LOS}} \le -50.0\text{ mm}) \cap (\gamma \ge 0.35)$$
* **Parameters:** `subsidence_threshold_mm` = -50.0 mm (default), `min_cluster_pixels` = 8 pixels.
* **Implementation Status:** `implemented`.

#### 5. 3D GNSS Vector to 1D Line-of-Sight Projection
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Scientific Purpose:** Enable rigorous physical validation between 3D ground GNSS displacement stations and 1D satellite InSAR measurements.
* **Mathematical Basis:** Projecting 3D GNSS motion $\mathbf{u} = [u_e, u_n, u_u]^T$ (East, North, Up) onto the radar unit line-of-sight vector $\hat{\mathbf{e}}_{\text{LOS}}$:
  $$d_{\text{LOS}}^{\text{GNSS}} = \mathbf{u} \cdot \hat{\mathbf{e}}_{\text{LOS}} = -u_e \sin\theta \cos\alpha + u_n \sin\theta \sin\alpha + u_u \cos\theta$$
  where $\theta$ is radar incidence angle (measured from local zenith, $\approx 39.2^\circ$ over Tyrnavos) and $\alpha$ is satellite flight azimuth heading ($\approx -168^\circ$ for descending track).
* **Implementation Status:** `implemented`.

#### 6. Continuous Field Validation & Residual Mapping
* **Scientific Classification:** `Scientifically established and correctly specified`.
* **Mathematical Basis:** Evaluates cell-by-cell residuals against independent cross-pair reference rasters:
  $$\text{Residual}(i) = d_{\text{observed}}(i) - d_{\text{reference}}(i)$$
  $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N \left(d_{\text{observed}}(i) - d_{\text{reference}}(i)\right)^2}, \quad \text{MAE} = \frac{1}{N}\sum_{i=1}^N |d_{\text{obs}}(i) - d_{\text{ref}}(i)|$$
* **Implementation Status:** `implemented`.

#### 7. Multi-Track 2D/3D Displacement Decomposition
* **Scientific Classification:** `Requires additional input data (Ascending + Descending tracks)` / `Planned future work`.
* **Scientific Limitation:** Single-track InSAR is physically incapable of resolving 3D deformation vectors. Combining ascending ($\text{LOS}_{\text{asc}}$) and descending ($\text{LOS}_{\text{desc}}$) geometries enables full decomposition into 2D (East-West and Up-Down):
  $$\begin{bmatrix} d_{\text{LOS, asc}} \\ d_{\text{LOS, desc}} \end{bmatrix} = \begin{bmatrix} -\sin\theta_{\text{asc}}\cos\alpha_{\text{asc}} & \cos\theta_{\text{asc}} \\ -\sin\theta_{\text{desc}}\cos\alpha_{\text{desc}} & \cos\theta_{\text{desc}} \end{bmatrix} \begin{bmatrix} u_e \\ u_u \end{bmatrix}$$
  North-South motion ($u_n$) remains unconstrained without along-track MAI or GNSS integration.
* **Implementation Status:** `planned_future_work`.

#### 8. Raw Single Look Complex (SLC) Processing (Workflow B)
* **Scientific Classification:** `Planned future work`.
* **Scientific Purpose:** End-to-end interferogram generation from raw Sentinel-1 Level-1 SLC products: precise orbit ephemeris correction, sub-pixel coregistration, Goldstein adaptive phase filtering, and 2D SNAPHU statistical-cost phase unwrapping.
* **Implementation Status:** `planned_future_work` (deferred in `LandMovementPipeline.deferred_features`).

---

## Section 6 — Processing Workflow

```
Dataset Selection (displacement, coherence, reference, exposure)
  │
  ▼
Input Validation (verifies insar_displacement product type, bounding overlap)
  │
  ▼
Preprocessing (Reproject grids, handle NoData, apply boxcar smoothing if requested)
  │
  ▼
Scientific Analysis:
  ├─ Apply Coherence Quality Mask (gamma >= 0.35)
  ├─ Compute Summary Statistics (min, max, mean, std of LOS displacement)
  ├─ Calculate Surface Strain Gradient (|grad d_LOS|)
  └─ Segment Extreme Subsidence & Uplift Lobes (threshold: <= -50 mm, >= +20 mm)
  │
  ▼
Output Deliverables Generation:
  ├─ Export Filtered Displacement GeoTIFF
  ├─ Generate Diverging Cyan-White-Purple Preview Map
  ├─ Generate High-Coherence Phase Fringe Preview
  └─ Generate Hotspot Vector Overlay
  │
  ▼
Geodetic Validation:
  ├─ Compute difference raster vs independent 18-day reference
  ├─ Calculate RMSE, MAE, Mean Bias, and Pearson Correlation
  └─ Generate Validation Residual GeoTIFF & Error Explorer Preview
  │
  ▼
Infrastructure Exposure Analysis:
  └─ Intersect deformation lobes with roads, bridges, and settlements
  │
  ▼
Assemble StandardDomainResponse (KPI metrics, 4-tier explainability, caveats)
```

---

## Section 7 — Expected Scientific Outputs

| Output Layer Key | Layer Type | Units | Physical Meaning | Generation Method | Validation Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `displacement_geotiff` | Raster (GeoTIFF) | $mm$ | Unwrapped coseismic LOS surface motion | Coherence-filtered LOS grid | Independent 18-day InSAR pair |
| `displacement_preview` | Preview (PNG) | $mm$ | Calibrated web map of ground motion | Diverging ramp (-350 to +100 mm) | Visual inspection |
| `baseline_preview` | Preview (PNG) | $\gamma$ (0..1) | Spatial interferometric coherence map | Sequential grayscale/viridis | InSAR processing report |
| `change_overlay` | Preview (PNG) | RGBA | High-subsidence hotspots ($<-50\text{ mm}$) | Categorical threshold mapping | Geological field survey |
| `validation_geotiff` | Raster (GeoTIFF) | $mm$ | Residual error grid ($d_{\text{obs}} - d_{\text{ref}}$) | Pixel-by-pixel subtraction | Independent 18-day InSAR pair |
| `validation_overlay` | Preview (PNG) | RGBA | Visual Error Explorer residual heatmap | Diverging error ramp (-50 to +50 mm) | Independent 18-day InSAR pair |

* **CRS:** Geographic WGS84 (`EPSG:4326`) matching COMET-LiCSAR frame standards.
* **Legend:** Deep Purple/Navy (#7209b7, #3a0ca3) = Subsidence (away from satellite), Cyan/White (#4cc9f0, #ffffff) = Stable / Slight Uplift.

---

## Section 8 — Metrics and Calculations

### LOS-to-3D Projection Mathematics
When GNSS vectors are compared to InSAR, the 3D GNSS displacement vector $\mathbf{u} = [u_e, u_n, u_u]^T$ is projected into satellite Line-of-Sight:
$$d_{\text{LOS}} = -u_e \sin\theta \cos\alpha + u_n \sin\theta \sin\alpha + u_u \cos\theta$$
where $\theta$ is the radar incidence angle ($\approx 39^\circ$) and $\alpha$ is the satellite flight heading angle ($\approx -13^\circ$ for ascending track).

### Summary Metrics Provided
1. **`min_displacement_mm`:** Peak subsidence magnitude (e.g., $-341.2\text{ mm}$).
2. **`max_displacement_mm`:** Peak uplift magnitude (e.g., $+45.8\text{ mm}$).
3. **`mean_displacement_mm`:** Spatial average deformation across the coherent domain.
4. **`mean_coherence`:** Average interferometric phase stability.
5. **`severe_subsidence_area_km2`:** Contiguous land area experiencing subsidence $\le -50.0\text{ mm}$.
6. **`validation_rmse_mm`:** Root Mean Square Error against independent cross-pair reference.

---

## Section 9 — Validation Strategy

| Validation Source | What It Validates | Independence Tier | Spatial Comp. | Temporal Comp. | Accuracy Metrics |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `ds-real-d4-ref` (COMET-LiCSAR) | Coseismic deformation field | Partially Independent Cross-Pair (Same sensor, different master date Feb 19 vs Feb 25) | Exact $300\times 220$ grid alignment | Coincident slave date (March 9, 2021) | RMSE, MAE, Mean Bias, Pearson $R^2$ |
| GNSS Station Projections (Planned) | Absolute 3D point geodetic truth | Independent In-Situ Geodetic Network | Sparse station points | Continuous 30-sec kinematic GNSS | 1D projected offset ($\text{mm}$) |
| `ds-test-d4-disp` | Algorithmic logic and masking | Synthetic Test Fixture | $30\times 30$ grid | N/A | Unit regression test |

* **When Reference Data is Unavailable:** Pipeline outputs `"not_validated"`, flagging that atmospheric noise or unwrapping errors could be present.

---

## Section 10 — Frontend Specification

### Workspace Layout (`Domain3Page.jsx`)
* **Study Area Selection:** Tyrnavos Basin, Greece (March 2021 $M_w\ 6.3$ Earthquake).
* **Dataset Selection:** Dropdown populated from `GET /api/datasets?domain=domain3` (filtered to `insar_displacement` and `insar_coherence`).
* **Processing Controls:** Slider for `min_coherence` ($0.10$ to $0.80$), threshold slider for subsidence hotspot classification ($-20$ to $-100\text{ mm}$).
* **Map Display (`BeforeAfterViewer`):**
  * Left Canvas: Interferometric Coherence Map ($\gamma$).
  * Right Canvas: Line-of-Sight Ground Displacement Heatmap ($mm$).
  * Vector Overlay: Mapped surface fault traces and highway intersections.
* **Validation Panel:** Displays continuous validation metrics (RMSE in $mm$, Pearson $R^2$), accompanied by the Visual Error Explorer residual heatmap.
* **Scientific Caveats Card:** Explains satellite Line-of-Sight geometry, emphasizing that 1D LOS does not equal vertical motion and detailing atmospheric phase screen limits.

---

## Section 11 — Backend File Responsibilities

* `backend/app/domains/domain3/processor.py`: Implements `EarthquakesPipeline(LandMovementPipeline)`, where `LandMovementPipeline` resides in `backend/app/domains/domain4/processor.py` and inherits from `DomainPipeline` (`backend/app/services/pipeline.py`). Declares input specifications (`InputSpec`), algorithm parameters (`ParamSpec`), and produces results formatted for `StandardDomainResponse` (`backend/app/schemas/results.py`).
* `backend/app/api/endpoints/domain3.py`: API router dispatching requests to `EarthquakesPipeline` (or `CryospherePipeline` if velocity inputs are provided).
* `backend/app/services/processing_service.py`: Central coordinator (`ProcessingService`) managing run persistence, input resolution, and error propagation.
* `backend/app/domains/domain3/preprocessing.py`, `analysis.py`, `visualization.py`: Modular domain components for phase calibration, spatial gradient filtering, and deformation rendering.
* `backend/app/utils/raster.py` & `validation.py`: Shared platform utilities providing continuous error evaluation (`evaluate_continuous_field`), diverging color stretch, and GeoTIFF export.

---

## Section 12 — API Integration

### Endpoint
`POST /api/domains/domain3/process`

### Sample Request Payload
```json
{
  "inputs": {
    "displacement": "ds-real-d4-disp",
    "coherence": "ds-real-d4-coh",
    "reference_displacement": "ds-real-d4-ref",
    "exposure_assets": "ds-real-d4-exp"
  },
  "parameters": {
    "min_coherence": 0.35,
    "subsidence_threshold_mm": -50.0
  },
  "study_area_bbox": [22.05, 39.65, 22.35, 39.85]
}
```

### Error Handling
* Providing a `sar_backscatter` dataset as displacement triggers HTTP 422 explaining that InSAR displacement products are required.
* Missing `displacement` triggers HTTP 422 (`PipelineInputError`).

---

## Section 13 — Testing and Acceptance Criteria

1. **Unit Tests (`test_domains_2_to_5.py`):**
   * Verification that coherence values $<0.35$ are masked to NoData.
   * Execution on synthetic $30\times 30$ InSAR fixtures (`ds-test-d4-disp`, `ds-test-d4-coh`).
2. **Coseismic Displacement Benchmark:** Execution with `ds-real-d4-disp` yields peak subsidence $\le -300\text{ mm}$ and detects the primary normal fault rupture.
3. **Cross-Pair Validation Test:** RMSE $\le 15.0\text{ mm}$ and Pearson $R \ge 0.90$ when evaluated against `ds-real-d4-ref`.
4. **LOS Geometric Notice:** Response explanation payload must contain the explicit disclaimer that motion is measured along the slant range.

---

## Section 14 — Limitations and Future Work

### Limitations
* Single-orbit ascending InSAR cannot decouple horizontal east-west displacement from true vertical subsidence.
* Tropospheric water vapor turbulence introduces residual phase noise of $\pm 5–15\text{ mm}$.
* Vegetated river floodplains exhibit complete temporal decorrelation ($\gamma < 0.2$), preventing deformation measurement directly along the riverbank.

### Future Work
* Integration of descending Sentinel-1 tracks to compute true 2.5D East-West and Vertical vector fields.
* Implementation of Workflow B: raw SLC interferogram formation and SNAPHU phase unwrapping using NISAR L-band data.
