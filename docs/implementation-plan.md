# MVP Implementation Plan & Scientific Audit — Dancing with the SARs

**Version:** 1.0
**Status:** Verification & Planning Complete
**Target:** 6-Person Parallel Development Team

---

## 1. Scientific Audit of Assumptions & Core Domain Methods

Before beginning implementation, the team must explicitly evaluate and resolve the scientific assumptions in the domain specifications.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Scientific Reality Check                        │
├───────────────────────┬────────────────────────────────────────────────┤
│ What the Radar Sees   │ Microwave backscatter (dB), Phase (rad),       │
│ (Raw Observable)      │ Coherence (0-1)                                │
├───────────────────────┼────────────────────────────────────────────────┤
│ What Algorithms Derive│ Relative change (Delta dB), Water mask,        │
│ (Derived Measurement) │ Velocity field, InSAR Line-of-Sight deformation│
├───────────────────────┼────────────────────────────────────────────────┤
│ What Requires External│ Flood depth, monetary damage, deforestation    │
│ Evidence & Validation │ cause, fire severity, vertical tectonic motion │
└───────────────────────┴────────────────────────────────────────────────┘
```

### Domain 1: Floods & Water Dynamics
- **Otsu Thresholding Assumption:** Otsu's method assumes a bimodal backscatter histogram (one mode for low-backscatter open water, one mode for higher-backscatter land). If an image contains $<5\%$ or $>95\%$ water, the histogram is unimodal, and Otsu will select an arbitrary split threshold that severely misclassifies land.
  - *Resolution/Mitigation for MVP:* Implement a sanity-bounded Otsu: threshold is clamped between $-22\text{ dB}$ and $-14\text{ dB}$. If the computed threshold falls outside these bounds, fallback to a standard static threshold ($-18.0\text{ dB}$).
- **Terrain & Permanent Water Effects:** Radar shadows on steep mountain slopes appear completely black ($<-25\text{ dB}$) and can be misclassified as water.
  - *Resolution/Mitigation for MVP:* For the MVP, select an open-plain floodplain AOI (e.g., lower Mississippi or Indus river basin) where topographic slope $<5^\circ$, or apply a static Copernicus DEM slope mask.

### Domain 2: Forests & Vegetation
- **Fixed Backscatter Threshold vs. True Deforestation:** A fixed drop in cross-polarized backscatter ($\Delta \text{HV} < -3.5\text{ dB}$) proves a loss of volume scattering. It does **not** prove anthropogenic deforestation. Severe drought, dry-season deciduous leaf drop, or seasonal soil moisture variations can also depress backscatter.
  - *Resolution/Mitigation for MVP:* The UI and report must explicitly label results as **"Potential Canopy Disturbance"** rather than "Deforestation". Observations must compare identical seasonal baseline windows to suppress deciduous phenology artifacts.

### Domain 3: Ice, Glaciers & Cryosphere
- **Distinction Between Movement, Velocity, Margin Shift, and Mass Loss:**
  - *Displacement vs. Velocity:* Feature tracking measures displacement between two dates; velocity is the rate over time ($\text{m/day}$ or $\text{m/year}$).
  - *Terminus Retreat vs. Mass Balance:* A glacier front retreating by 100 meters indicates calving, not total volumetric ice thinning or sea-level rise contribution.
  - *Melt Decorrelation:* Surface melt completely absorbs microwave pulses, causing backscatter drops and decorrelating speckle tracking.
  - *Resolution/Mitigation for MVP:* Focus the primary analysis on **Terminus Calving Margin Retreat** (edge detection comparison) and display **pre-computed NASA ITS_LIVE velocity tiles** rather than compiling raw FFT tracking engines during the hackathon.

### Domain 4: Land Movement & Urban Change
- **Line-of-Sight (LOS) vs. True Vertical Deformation:** Single-track InSAR measures displacement along the satellite's slanted line of sight. Sinking ground and horizontal tectonic motion both project into this 1D vector.
  - *Resolution/Mitigation for MVP:* The interface must clearly indicate the look direction (e.g., "Descending Track 114, Incidence Angle $37^\circ$") and state that vertical deformation is an estimate assuming negligible horizontal motion.
- **InSAR Processing Burden:** Computing multi-temporal SBAS or PSI time series from raw SLC granules requires specialized software (ISCE3/MintPy) and gigabytes of storage.
  - *Resolution/Mitigation for MVP:* Strictly utilize **pre-computed ASF HyP3 unwrapped GeoTIFF products**. The MVP code will handle geocoded displacement visualization, subsidence hotspot clustering, and interactive point time-series extraction.

### Domain 5: Wildfires & Land Disturbance
- **Limits of FIRMS Thermal Validation:** Active fire detections from MODIS/VIIRS indicate elevated heat at the instant of satellite overpass ($1-2\text{ times/day}$). They do not measure burnt area polygons, and smoldering understory fires under canopy may be missed.
  - *Resolution/Mitigation for MVP:* Use FIRMS active thermal points strictly as independent **corroborating spatial markers**, not as definitive ground-truth perimeters. Combine $\Delta \text{HV}$ radar canopy loss with FIRMS proximity to compute an explainable **Disturbance Evidence Score**.

### Domain 6: Earth Event Explorer
- **Distinguishing Observation from Interpretation:** Cross-hazard analyses must not assume causation without evidence.
  - *Resolution/Mitigation for MVP:* Maintain strict four-part documentation on every report: (1) Observation (what was measured), (2) Analysis (what was derived), (3) Interpretation (what the evidence suggests), and (4) Uncertainty (what remains unverified).

---

## 2. Minimum Viable Domain (MVD) Specifications

To guarantee successful delivery within the challenge timeframe, the team will implement one primary core feature per domain, strictly deferring complex multi-pass or multi-sensor algorithms.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      MVP Core Feature Matrix                           │
├─────────────────┬───────────────────────────────┬──────────────────────┤
│ Domain          │ MVP Core Feature (P0)         │ Deferred Feature(P2) │
├─────────────────┼───────────────────────────────┼──────────────────────┤
│ 1. Floods       │ Inundation Difference Layer   │ Double-bounce InSAR  │
│ 2. Forests      │ Canopy Disturbance Alert      │ Full Quad-Pol decomp │
│ 3. Cryosphere   │ Terminus Retreat & ITS_LIVE   │ Raw sub-pixel NCC    │
│ 4. Land Movement│ HyP3 Displacement Viewer & PS │ Raw SLC SBAS engine  │
│ 5. Wildfires    │ SAR Burn Scar + FIRMS Overlay │ Post-fire debris flow│
│ 6. Explorer     │ Multi-Hazard Timeline & DAG   │ AI Predictive models │
└─────────────────┴───────────────────────────────┴──────────────────────┘
```

### Detailed Domain Specifications

#### Domain 1: Floods & Water Dynamics
- **MVP Feature:** Before-and-after flood inundation change detection.
- **Inputs:** Pre-flood RTC GeoTIFF ($T_0$), post-flood RTC GeoTIFF ($T_1$) in HH or VV polarization.
- **Processing Logic:**
  1. Convert amplitudes to decibels: $\text{dB} = 10 \cdot \log_{10}(\text{amplitude})$.
  2. Compute relative difference: $\Delta \text{dB} = \text{dB}_{T_1} - \text{dB}_{T_0}$.
  3. Apply bounded Otsu threshold on $\text{dB}_{T_1}$ ($[-22\text{ dB}, -14\text{ dB}]$) combined with $\Delta \text{dB} < -3.0\text{ dB}$.
  4. Generate binary mask ($1 = \text{inundated}, 0 = \text{dry}$).
- **Output:** Flooded area ($\text{km}^2$), percentage increase, GeoTIFF mask, and PNG curtain preview.
- **Frontend Integration:** Uses `BeforeAfterViewer.jsx` for swipe comparison; `MetricsPanel.jsx` for area summary.
- **Deferred:** L-band polarimetric double-bounce wetland sub-canopy classification, hydrodynamic depth modeling.

#### Domain 2: Forests & Vegetation
- **MVP Feature:** Potential canopy disturbance detection.
- **Inputs:** Pre-event baseline RTC GeoTIFF ($T_0$), monitoring RTC GeoTIFF ($T_1$) in cross-polarization (HV or VH).
- **Processing Logic:**
  1. Compute backscatter drop: $\Delta \text{HV} = \text{HV}_{T_1} - \text{HV}_{T_0}$.
  2. Apply disturbance threshold: $\Delta \text{HV} < -3.5\text{ dB}$.
  3. Apply spatial filter (minimum mapping unit $\ge 4\text{ pixels}$) to discard speckle noise.
- **Output:** Disturbed canopy extent (hectares), mean backscatter drop ($\text{dB}$), GeoTIFF mask, and preview PNG.
- **Frontend Integration:** Uses `BeforeAfterViewer.jsx` with polarimetric color composite; `MetricsPanel.jsx` for hectares cleared.
- **Deferred:** Multi-year recovery trend modeling, full polarimetric matrix decomposition.

#### Domain 3: Ice, Glaciers & Cryosphere
- **MVP Feature:** Glacial terminus position change and precomputed ice velocity display.
- **Inputs:** Pre/post polar SAR pair spanning calving event + collocated NASA ITS_LIVE velocity GeoTIFF.
- **Processing Logic:**
  1. Apply Sobel/Canny edge detection to extract front margin polylines from $T_0$ and $T_1$.
  2. Measure linear retreat distance ($\text{meters}$) along central flowline.
  3. Overlay pre-computed ITS_LIVE velocity raster with standard flow color ramp.
- **Output:** Terminus retreat distance ($\text{m}$), peak velocity ($\text{m/year}$), GeoJSON margin vectors.
- **Frontend Integration:** Polar stereographic map frame; `BeforeAfterViewer.jsx` showing terminus shift; velocity legend.
- **Deferred:** From-scratch sub-pixel cross-correlation algorithm, grounding line DInSAR tidal analysis.

#### Domain 4: Land Movement & Urban Change
- **MVP Feature:** InSAR Line-of-Sight (LOS) ground deformation visualization and Persistent Scatterer inspector.
- **Inputs:** Pre-computed ASF HyP3 unwrapped displacement GeoTIFF + coherence raster + PS point GeoJSON.
- **Processing Logic:**
  1. Scale unwrapped phase to millimeter displacement: $d = \frac{\lambda}{4\pi} \Delta \phi \times 1000$.
  2. Mask out pixels with coherence $\gamma < 0.35$.
  3. Cluster contiguous subsidence zones ($<-15\text{ mm/year}$) using spatial contouring.
- **Output:** Subsidence bowl area ($\text{km}^2$), peak subsidence rate ($\text{mm/year}$), interactive PS time-series array.
- **Frontend Integration:** Diverging red-white-blue velocity heatmap; click-to-inspect modal plotting displacement curve.
- **Deferred:** Full SBAS time-series inversion from raw SLCs, atmospheric phase screen modeling.

#### Domain 5: Wildfires & Land Disturbance
- **MVP Feature:** Smoke-penetrating radar disturbance with NASA FIRMS active fire corroboration.
- **Inputs:** Pre/post wildfire dual-pol SAR GeoTIFFs + NASA FIRMS active fire point GeoJSON.
- **Processing Logic:**
  1. Compute cross-polarized backscatter difference: $\Delta \text{HV} < -3.2\text{ dB}$.
  2. Filter contiguous disturbance clusters ($\text{MMU} \ge 5\text{ pixels}$).
  3. Perform spatial point-in-polygon intersection against FIRMS thermal points.
  4. Compute Corroborated Evidence Score based on radar-thermal overlap.
- **Output:** Burn scar area (hectares), mean $\Delta \text{dB}$ drop, thermal detection count, burn perimeter GeoJSON.
- **Frontend Integration:** `BeforeAfterViewer.jsx` showing pre/post burn; thermal hot-spot toggle layer; evidence score card.
- **Deferred:** Post-fire rainfall debris flow simulation, optical dNBR cross-sensor calibration.

#### Domain 6: Earth Event Explorer
- **MVP Feature:** Unified multi-hazard crisis timeline and Evidence Chain synthesizer.
- **Inputs:** Curated multi-hazard event presets (e.g., Hurricane Helene, Turkey Earthquake, California Wildfire) + outputs from Domains 1–5.
- **Processing Logic:**
  1. Query active domain pipelines for the designated event bounding box.
  2. Aggregate multi-hazard metrics into a unified summary table.
  3. Render the Evidence Chain directed graph linking observations $\to$ methods $\to$ results $\to$ caveats.
- **Output:** Interactive multi-layer map, compound impact metrics, exportable investigation brief.
- **Frontend Integration:** Curated event selector grid; multi-layer map canvas; interactive Evidence Chain DAG modal.
- **Deferred:** Machine learning predictive damage modeling, real-time autonomous satellite tasking queries.

---

## 3. Feature Prioritization (P0 / P1 / P2)

### Priority P0 — Absolute Must-Have for Working End-to-End Demo
- [ ] Working shared REST API contract implemented across all backend domain endpoints.
- [ ] Single-slice operational workflow verified for Domain 1 (Floods) using pre/post sample arrays.
- [ ] Basic raster array processing logic operational for Domains 1, 2, 3, 4, 5.
- [ ] `BeforeAfterViewer.jsx` connected to real image pairs in all domain views.
- [ ] Standardized `MetricsPanel.jsx` rendering real computed numbers (no hardcoded strings).
- [ ] 4-Tier Explainability cards (Levels 1–4) populated with scientifically responsible text.
- [ ] Central Earth Event Explorer route implemented, linking to curated crisis events.

### Priority P1 — High-Value Improvements (Post Core Completion)
- [ ] Interactive Point-Inspector for Domain 4 (clicking PS points displays time-series graph).
- [ ] Live NASA FIRMS thermal point overlay for Domain 5.
- [ ] Permanent water masking for Domain 1 (using JRC Global Surface Water raster).
- [ ] Minimum mapping unit spatial filtering for Domain 2 to remove single-pixel speckle noise.
- [ ] Exportable JSON investigation report endpoint (`GET /runs/{id}/export`).

### Priority P2 — Advanced Features (Explicitly Deferred)
- Sub-canopy L-band polarimetric decomposition engines.
- Raw SLC interferometric phase unwrapping from scratch.
- Real-time client-side sub-pixel Normalized Cross-Correlation (NCC).
- 3D extruded urban building settlement visualization.
- Full cloud object storage deployment (AWS S3 / GCS).

---

## 4. Acceptance Checklists by Domain

### Domain 1: Floods & Water Dynamics
- [ ] User selects a flood event; pre-flood and post-flood rasters load in `BeforeAfterViewer`.
- [ ] Curtain slider operates smoothly without spatial misalignment.
- [ ] Backend runs bounded Otsu thresholding and returns binary inundation mask.
- [ ] `MetricsPanel` displays inundated extent ($\text{km}^2$) and percentage change.
- [ ] Level 1–4 explainability panel details the threshold used and warns of wind-induced roughness.

### Domain 2: Forests & Vegetation
- [ ] User selects forest AOI; pre/post cross-pol rasters load in `BeforeAfterViewer`.
- [ ] Backend computes $\Delta \text{HV}$ and flags pixels with $>3.5\text{ dB}$ drop.
- [ ] UI labels results as "Potential Canopy Disturbance" with hectares affected.
- [ ] Explainability panel explicitly states that backscatter drop does not prove legal status or timber harvesting cause.

### Domain 3: Ice, Glaciers & Cryosphere
- [ ] User selects glacier AOI; pre/post calving pair loads in polar stereographic projection.
- [ ] Terminus margin polylines render showing front position retreat.
- [ ] ITS_LIVE velocity color ramp renders over the glacier trunk.
- [ ] Metrics panel displays linear retreat ($\text{m}$) and peak velocity ($\text{m/year}$).
- [ ] Explainability panel distinguishes ice velocity from volumetric ice mass loss.

### Domain 4: Land Movement & Urban Change
- [ ] User selects subsidence AOI; pre-computed InSAR displacement raster renders with diverging color ramp.
- [ ] Coherence quality filter masks out decorrelated pixels ($\gamma < 0.35$).
- [ ] Metrics panel displays peak subsidence rate ($\text{mm/year}$) and affected bowl area ($\text{km}^2$).
- [ ] Explainability panel discloses the satellite Line-of-Sight geometry.

### Domain 5: Wildfires & Land Disturbance
- [ ] User selects wildfire event; pre/post SAR pair loads with burn scar overlay.
- [ ] NASA FIRMS thermal points render as an interactive verification layer.
- [ ] Metrics panel reports total burned canopy area (ha) and thermal correlation count.
- [ ] Explainability panel notes that soil moisture variations can alter post-fire backscatter.

### Domain 6: Earth Event Explorer
- [ ] User selects a curated multi-hazard event (e.g., Hurricane or Earthquake).
- [ ] Explorer coordinates and displays outputs from at least two analytical domains.
- [ ] Evidence Chain visualizer diagrams the provenance of satellite observations.
- [ ] The user can download an exported JSON investigation brief.
