# NISAR Domain Technical Specifications — Scientific & Architectural Audit Report

**Platform:** Dancing with the SARs (NISAR Earth Observation Console)
**Document ID:** `AUDIT-DOMAINS-2026-11`
**Date:** November 4, 2026
**Auditor:** Scientific Architecture & Security Review Team
**Scope:** Deep-dive scientific and architectural audit of all five Domain Technical Specifications (`domain1-floods-wetlands.md` through `domain5-glaciers-ice.md`), shared architecture dependencies, and physical dataset manifests.

---

## 1. Executive Assessment

A comprehensive review of the five NISAR Domain Technical Specifications was conducted across three analytical vectors:
1. **Physical & Mathematical Rigor:** Assessing whether documented algorithms, sensor polarizations, radiometric thresholds, and physical equations strictly reflect established microwave radar theory.
2. **Dataset Alignment & Integrity:** Verifying that all 60 datasets registered in `data/manifests/datasets.json` exist at their specified paths on disk, match declared sensor and polarization characteristics, and genuinely support the proposed scientific workflows.
3. **Architectural Compatibility:** Auditing the documented class hierarchies, schema models, and service interfaces against the actual codebase in `backend/app/` and `frontend/src/`.

### Summary of Findings
* **Scientific Quality:** The specifications are structurally thorough and mathematically well-grounded. However, the initial versions contained several critical scientific simplifications:
  - Bimodal Otsu thresholding in D1 was specified without addressing unimodal histogram breakdown in sparse flood scenarios.
  - Classical RFDI in D2 was conflated with Sentinel-1 dual-polarization without noting the lack of $\text{HH}$ polarization on Sentinel-1.
  - Line-of-sight displacement in D3 required rigorous sign convention and unit harmonization with geodetic standards and explicit clarification of 3D motion limits.
  - Radar Vegetation Index in D4 lacked explicit dual-polarization mathematical formulation, and relative surface backscatter changes were insufficiently decoupled from volumetric soil moisture.
  - Surface ice flow velocity in D5 lacked explicit decoupling from volumetric ice sheet mass loss, and the distinction between physical interannual anomalies and measurement error required formal clarification.
* **Dataset Allocation:** All 60 datasets in `data/manifests/datasets.json` exist on disk. Four domains (D1, D2, D3, D5) have verified real datasets supporting their core workflows. Domain 4 (Agriculture) has **zero** real agricultural SAR backscatter datasets, with four quarantined InSAR subsidence files in its raw folder; it correctly remains locked in `demonstration` status.
* **Architectural Alignment:** The documented interfaces were reconciled with actual codebase classes: `DomainPipeline` (inheriting from `DomainInterface`) in `backend/app/services/pipeline.py`, `StandardDomainResponse` in `backend/app/schemas/results.py`, and `ProcessingService` in `backend/app/services/processing_service.py`. Non-existent legacy references (such as `BaseDomainService`) were eradicated.

---

## 2. Scientific Issues Found

### Domain 1: Floods & Wetlands
1. **Bimodal Otsu Failure on Unimodal Distributions:** Standard Otsu thresholding assumes a distinctly bimodal histogram where foreground (water) and background (land) have comparable proportions. During early-stage flash flooding or minor overflow (<2% of scene area) or extreme drowning (>90%), the backscatter histogram is unimodal. Unbounded Otsu splits the dominant land peak, generating catastrophic false positives.
2. **Fixed Threshold Incidence Angle & Wind Sensitivity:** A static threshold (e.g. $-16.0\text{ dB}$) in Sentinel-1 IW mode fails across swath extremes: near-range water ($30^\circ$) reflects at $-14\text{ dB}$, while far-range water ($45^\circ$) drops to $-20\text{ dB}$. Furthermore, sustained winds $>5–7\text{ m/s}$ generate capillary waves that elevate water backscatter by 4–8 dB, exceeding static thresholds.
3. **Emergent Vegetation & C-Band Double-Bounce:** At C-band ($\lambda = 5.6\text{ cm}$), microwave pulses cannot penetrate dense closed canopies. Over vertical emergent stalks (rice, reeds), double-bounce can elevate $\text{VV}$ backscatter, inverting the expected specular drop. True sub-canopy flood detection requires L-band polarimetric decomposition.
4. **Flood Duration Misconception:** Inundation duration (days submerged) cannot be calculated from a single pre/post SAR pair; it requires a dense multi-temporal sequence capturing flood rise, peak crest, and drainage recession.

### Domain 2: Forests & Wildfires
1. **Classical RFDI vs. Sentinel-1 Polarization Incompatibility:** Classical Radar Forest Degradation Index (Saatchi et al., 2000) is strictly defined for polarimetric radar with $\text{HH}$ and $\text{HV}$ polarizations:
   $$\text{RFDI} = \frac{\sigma_{\text{HH}}^0 - \sigma_{\text{HV}}^0}{\sigma_{\text{HH}}^0 + \sigma_{\text{HV}}^0}$$
   Sentinel-1 provides only $\text{VV}$ and $\text{VH}$. Substituting $\text{VV}$ for $\text{HH}$ yields an uncalibrated proxy corrupted by direct soil moisture and surface roughness. For Sentinel-1, cross-polarized differencing ($\Delta\sigma_{\text{VH}}^0$) or Cross-Ratio ($\sigma_{\text{VH}}^0 / \sigma_{\text{VV}}^0$) is the established standard.
2. **Thermal Hotspots vs. Burned Area:** NASA FIRMS thermal anomaly points represent instantaneous radiant combustion during satellite overpass. They are point detections with positional uncertainties and cannot be equated with burned area polygons without multi-temporal SAR/optical boundary mapping.

### Domain 3: Earthquakes & Ground Deformation
1. **LOS Displacement Sign Convention & Units:** Unwrapped phase is dimensionless (in radians). Converting to line-of-sight displacement requires explicit radar wavelength ($\lambda = 0.055465\text{ m}$ for Sentinel-1) and geodetic sign convention. Different InSAR software use opposite signs. In geodetic convention:
   $$d_{\text{LOS}} = +\frac{\lambda}{4\pi} \Delta\varphi_{\text{unw}}$$
   where positive is motion toward the satellite (uplift) and negative is motion away (subsidence).
2. **Physical Impossibility of Single-Track 3D InSAR:** A single InSAR track measures only the 1D projection of surface motion onto the line-of-sight vector. Near-polar orbital geometry makes InSAR fundamentally insensitive to horizontal North-South displacement. Resolving true 3D motion requires Ascending + Descending tracks combined with along-track MAI or GNSS networks.

### Domain 4: Agriculture & Soil Conditions
1. **Lack of Explicit Dual-Pol RVI Formula:** Classical RVI requires quad-polarimetric SAR. For dual-pol Sentinel-1, the operational formulation of Mandal et al. (2020) must be specified:
   $$\text{RVI}_{\text{dual}} = \frac{4\sigma_{\text{VH}}^0}{\sigma_{\text{VV}}^0 + \sigma_{\text{VH}}^0}$$
2. **Backscatter vs. Volumetric Soil Moisture Ambiguity:** Microwave backscatter over bare soil depends simultaneously on soil dielectric permittivity ($\varepsilon_r$, driven by moisture) and surface geometric roughness (RMS height $s$). Backscatter changes ($\Delta\text{dB}$) can only serve as relative surface wetness proxies; calculating absolute volumetric soil moisture ($\text{cm}^3/\text{cm}^3$) without solving a physical dielectric inversion model (Dubois/IEM) is scientifically invalid.
3. **Footprint Mismatch (SMAP vs. SAR):** Comparing 10m–20m Sentinel-1 SAR against 9km SMAP radiometer grids without aggregating parcel-level SAR backscatter across the radiometer footprint is physically meaningless.

### Domain 5: Glaciers, Snow & Ice
1. **Surface Flow Velocity vs. Volumetric Mass Loss:** High ice surface speeds ($>10,000\text{ m/yr}$) indicate rapid dynamic transport but do not equate to volumetric ice sheet mass loss ($\text{Gt/yr}$). Calculating mass discharge requires ice thickness $H(x)$ across a cross-sectional flux gate (BedMachine Greenland v5) and Surface Mass Balance ($\text{SMB}$).
2. **Interannual Anomaly vs. Measurement Error:** Comparing a 2022 annual velocity map against the NASA ITS_LIVE multi-decadal climatology measures physical interannual flow acceleration or deceleration ($\Delta v = v_{2022} - v_{\text{climatology}}$). It must not be labeled as observational measurement error.

---

## 3. Corrections Made

All five domain specifications and their master catalog have been updated with precise scientific formulations and framework references:

| Specification Document | Section | Corrections & Enhancements Applied |
|:---|:---:|:---|
| [`domain1-floods-wetlands.md`](domain1-floods-wetlands.md) | Sec 2, 5, 11 | Added bounded Otsu search window ($[-24.0, -11.0]\text{ dB}$) and minimum flood fraction caveat ($2\%$); documented incidence angle ($29^\circ–46^\circ$) and wind wave shifts; classified C-band flooded vegetation and flood duration as requiring additional data; harmonized `FloodsPipeline` inheritance from `backend/app/services/pipeline.py`. |
| [`domain2-forests-wildfires.md`](domain2-forests-wildfires.md) | Sec 5, 11 | Explicitly formulated classical RFDI ($\text{HH}/\text{HV}$ for ALOS-2); documented Sentinel-1 $\text{VV}/\text{VH}$ incompatibility and justified cross-pol differencing ($\Delta\sigma_{\text{VH}}^0$); added Sentinel-2 dNBR formula and USGS severity tiers; reinforced FIRMS thermal point vs burned area polygon separation; harmonized `ForestsPipeline` and `WildfiresPipeline` class paths. |
| [`domain3-earthquakes-deformation.md`](domain3-earthquakes-deformation.md) | Sec 2, 5, 11 | Added unwrapped phase units ($\text{rad}$), exact Sentinel-1 C-band wavelength ($\lambda = 0.055465\text{ m}$), and geodetic sign convention ($d_{\text{LOS}} = +\frac{\lambda}{4\pi}\Delta\varphi_{\text{unw}}$); added 3D GNSS to 1D LOS projection formula; detailed mathematical conditions proving single-track 3D estimation is impossible; harmonized `EarthquakesPipeline` inheritance. |
| [`domain4-agriculture-soil.md`](domain4-agriculture-soil.md) | Sec 2, 5, 11 | Added Mandal et al. (2020) dual-pol RVI formula; added Cross-Ratio definition; established non-negotiable safeguard that $\Delta\text{dB}$ is a relative surface wetness proxy and not volumetric moisture; documented the 810,000:1 pixel footprint mismatch with 9km SMAP; harmonized `AgriculturePipeline` inheritance. |
| [`domain5-glaciers-ice.md`](domain5-glaciers-ice.md) | Sec 2, 5, 11 | Formulated flux gate mass balance equation ($Q = \rho_{\text{ice}}\int \bar{v}\cdot H\,dx$) and documented BedMachine v5 thickness dependency; documented offset tracking requirements (correlation window, FFT oversampling, bedrock calibration); derived velocity uncertainty scaling ($\sigma_v \approx 15.2\text{ m/yr}$ for 12-day S1); clarified interannual anomaly vs error; harmonized `GlaciersPipeline` inheritance. |
| [`README.md`](README.md) | Sec 1, 3 | Indexed this audit report; updated Implementation Readiness statuses; verified frozen architecture contracts against actual codebase paths. |

---

## 4. Dataset Suitability Findings

The 60 datasets in `data/manifests/datasets.json` and `data/raw/` were verified against their respective scientific specifications:

```
Dataset Inventory Cross-Check (60 Total):
├── D1 Floods & Wetlands:           11 confirmed on disk (data/raw/domain1/)
├── D2 Forests & Wildfires:          26 confirmed on disk (13 in raw/domain2/, 13 in raw/domain5/)
├── D3 Earthquakes & Deformation:     6 confirmed on disk (in raw/domain4/)
├── D4 Agriculture & Soil:            0 confirmed on disk (4 InSAR subsidence datasets quarantined)
└── D5 Glaciers, Snow & Ice:         13 confirmed on disk (in raw/domain3/)
```

### Detailed Domain Suitability Breakdown

1. **Domain 1 (Floods & Wetlands — 11 Datasets):**
   - *Status:* **100% Suitable.**
   - Includes dry pre-flood baseline (`5c351e81-...`), post-flood crisis raster (`15a8d70a-...`), GLO-30 DEM, multi-decadal JRC surface water occurrence, and independent Sentinel-2 optical NDWI reference map (`ds-real-thessaly-s2-flood-ref`). Full operational inundation mapping and error residual evaluation are supported.
2. **Domain 2 (Forests & Wildfires — 26 Datasets):**
   - *Status:* **100% Suitable.**
   - Mode A (Forest Disturbance) is supported by 13 Pará tiles with ALOS-2 L-band forest-loss validation. Mode B (Wildfire Impact) is supported by 13 Dadia/Park Fire tiles with NASA FIRMS active fire records and MODIS MCD64A1 burned area references.
3. **Domain 3 (Earthquakes & Ground Deformation — 6 Datasets):**
   - *Status:* **100% Suitable for Workflow A.**
   - 3 unwrapped interferograms and 3 coherence rasters spanning the March 2021 Tyrnavos earthquake window support coherence masking ($\gamma \ge 0.35$), LOS displacement mapping, fault trace delineation, and cross-pair geodetic validation against COMET-LiCSAR reference data.
4. **Domain 4 (Agriculture & Soil Conditions — 0 Datasets):**
   - *Status:* **Unsuitable for Operational Processing; Suitable for Demonstration Only.**
   - The 4 Central Valley datasets physically located in `data/raw/domain4/` (`ds-demo-d4-coh`, `ds-demo-d4-disp`, `ds-demo-d4-ref`, `ds-demo-d4-exp`) are InSAR subsidence products from historical batch indexing. They **cannot** be used as agricultural backscatter inputs. Domain 4 is correctly quarantined to `demonstration` status using synthetic dual-pol test fixtures until real Sentinel-1 RTC dual-pol data is procured.
5. **Domain 5 (Glaciers, Snow & Ice — 13 Datasets):**
   - *Status:* **100% Suitable for Workflow A & B.**
   - Supported by calibrated NASA ITS_LIVE 2022 velocity mosaics ($0–14,000\text{ m/yr}$), multi-year climatological baselines, and real Sentinel-1A $\text{HH}$ pre/post calving terminus observations.

---

## 5. Architectural Mismatches Resolved

During the audit, the following discrepancies between early technical documentation and actual implementation were identified and resolved:

1. **Base Class Hierarchy:**
   - *Documentation Assumption:* Stated domain processors inherit from `BaseDomainService`.
   - *Codebase Truth:* There is no `BaseDomainService`. Processors inherit from `DomainPipeline` (which implements `DomainInterface`), defined in `backend/app/services/pipeline.py`.
   - *Resolution:* All specifications and README updated to `DomainPipeline` from `backend/app/services/pipeline.py`.
2. **Schema Locations:**
   - *Documentation Assumption:* Stated schemas reside in `backend/app/schemas/domain_schemas.py`.
   - *Codebase Truth:* Standard response contracts (`StandardDomainResponse`, `LayerReference`, `MetricItem`, `ExplanationLevels`, `ValidationInfo`, `ExposureInfo`) reside in `backend/app/schemas/results.py`.
   - *Resolution:* Schema paths updated across all specifications.
3. **Pipeline Return Type vs. Execution Service:**
   - *Documentation Assumption:* Implied domain `run()` method returns `StandardDomainResponse` directly.
   - *Codebase Truth:* `DomainPipeline.run(ctx)` returns a dictionary of layers and metrics; the centralized `ProcessingService(db).execute()` validates inputs, checks spatial bounds and polarizations, times execution, persists database records, and constructs the validated `StandardDomainResponse`.
   - *Resolution:* Processing workflow diagrams and file responsibility sections updated to reflect this separation of concerns.
4. **Multi-Domain API Routing & Aliasing:**
   - *Codebase Reality:* Due to historical data directory assignments, `backend/app/api/endpoints/domain3.py`, `domain4.py`, and `domain5.py` implement dynamic dispatch:
     - `domain3.py` routes to `EarthquakesPipeline` (or `CryospherePipeline` if `velocity` input is present).
     - `domain4.py` routes to `AgriculturePipeline` (or `LandMovementPipeline` if `displacement` input is present).
     - `domain5.py` routes to `GlaciersPipeline` (or `WildfiresPipeline` if `fire_detections` input is present).
   - *Resolution:* Documented in Section 11 of respective specifications.

---

## 6. Unverified Assumptions

The following scientific assumptions remain unverified in the current operational environment and require empirical validation during Phase 4 implementation:

1. **Pre-Event Baseline Moisture Homogeneity (D1 & D2):** It is assumed that pre-flood and pre-fire baseline scenes represent dry, stable ground conditions. In reality, antecedent precipitation within 48 hours prior to baseline acquisition can elevate baseline backscatter by 2–4 dB, artificially exaggerating observed post-event backscatter drops.
2. **Atmospheric Delay Invariance Across Fault Traces (D3):** It is assumed that tropospheric water vapor delay varies smoothly across the Tyrnavos basin. In the presence of localized convective cells or steep topography, turbulent atmospheric delays can reach 2–5 cm, which could distort subtle fault scarp gradient peaks.
3. **Surface Roughness Invariance in Demonstration Moisture Proxy (D4):** The demonstration agricultural wetness proxy assumes that parcel-level backscatter changes reflect surface dielectric wetting. If a farmer plowed or disked the field between passes, the resulting change in surface RMS roughness ($s$) could easily generate a 3–5 dB backscatter change completely unrelated to soil moisture.
4. **Depth-Averaged Ice Velocity Ratio (D5):** It is assumed that surface ice velocity represents $90–95\%$ of depth-averaged velocity across the Jakobshavn trough. In fast-streaming ice streams underlain by deformable till, basal sliding may account for $>90\%$ of total motion (plug flow), making depth-averaged velocity nearly $100\%$ of surface velocity.

---

## 7. Domain Implementation Readiness

Based on scientific rigor, dataset availability, and architectural compliance, each domain is assigned an implementation readiness status:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ DOMAIN IMPLEMENTATION READINESS SUMMARY                                                │
├────────┬──────────────────────────────────┬───────────────────────────┬────────────────┤
│ Domain │ Scientific Scope                 │ Implementation Readiness  │ Critical Path  │
├────────┼──────────────────────────────────┼───────────────────────────┼────────────────┤
│ D1     │ Floods & Wetlands                │ READY FOR IMPLEMENTATION  │ None           │
│ D2     │ Forests & Wildfires              │ READY FOR IMPLEMENTATION  │ None           │
│ D3     │ Earthquakes & Ground Deformation │ READY FOR IMPLEMENTATION  │ Workflow A     │
│ D4     │ Agriculture & Soil Conditions    │ BLOCKED BY DATA           │ SAR Data Acq.  │
│ D5     │ Glaciers, Snow & Ice             │ READY FOR IMPLEMENTATION  │ None           │
└────────┴──────────────────────────────────┴───────────────────────────┴────────────────┘
```

### Domain 1: Floods & Wetlands
* **Status:** `READY FOR IMPLEMENTATION`
* **Justification:** Complete inventory of 11 verified datasets (Sentinel-1 RTC pre/post pair, DEM, JRC water, Sentinel-2 NDWI validation). Algorithms are scientifically established (Otsu with decibel bounds, relative $\Delta\sigma^0$, DEM slope masking, permanent water subtraction). Operational test suite passes without failure.

### Domain 2: Forests & Wildfires
* **Status:** `READY FOR IMPLEMENTATION`
* **Justification:** Complete inventory of 26 verified datasets covering Pará deforestation and Dadia/Park Fire wildfire impacts. Algorithms (cross-pol $\Delta\sigma^0$, baseline forest masking, MMU sieving, FIRMS thermal corroboration, optical dNBR validation) are scientifically sound and preserve non-negotiable boundaries between active fire detections and burned area polygons.

### Domain 3: Earthquakes & Ground Deformation
* **Status:** `READY FOR IMPLEMENTATION` (Workflow A)
* **Justification:** Complete inventory of 6 verified InSAR datasets covering the Tyrnavos Mw 6.3 earthquake. Algorithms for processing pre-computed unwrapped interferograms (coherence quality filtering $\ge 0.35$, displacement scaling, surface strain gradients, geodetic residual evaluation against COMET-LiCSAR) are fully specified and operational. Workflow B (raw SLC processing) is correctly classified as planned future work.

### Domain 4: Agriculture & Soil Conditions
* **Status:** `BLOCKED BY DATA` (Demonstration Mode Only)
* **Justification:** Zero real agricultural SAR backscatter datasets currently exist in the repository. The 4 Central Valley datasets in `data/raw/domain4/` are InSAR subsidence products and must not be used for agriculture. The mathematical pipeline (dual-pol RVI, Cross-Ratio, relative surface wetness proxy) is implemented and verified in `demonstration` mode using synthetic test fixtures, but the domain is strictly blocked from `production` status until real Sentinel-1 RTC dual-pol time series are procured.

### Domain 5: Glaciers, Snow & Ice
* **Status:** `READY FOR IMPLEMENTATION`
* **Justification:** Complete inventory of 13 verified datasets covering Jakobshavn Isbræ (calibrated ITS_LIVE velocity mosaics, multi-year climatology baseline, pre/post calving Sentinel-1 $\text{HH}$ observations). Scientific algorithms (fast-stream trunk segmentation $\ge 1,000\text{ m/yr}$, calving margin differencing, interannual anomaly evaluation) are verified and operational.

---

## 8. Remaining Blockers & Next Immediate Steps

### Remaining Technical & Data Blockers
1. **Domain 4 Real SAR Data Acquisition:** Member 5 and Member 6 must execute the procurement workflow documented in `domain4-agriculture-soil.md` Section 3 to acquire 12 Sentinel-1 Level-1 GRDH RTC dual-pol ($\text{VV}+\text{VH}$) acquisitions over the Central Valley growing season, along with the USDA Cropland Data Layer (CDL).
2. **DEM Slope Mask Execution in High Latitudes (D5):** While slope masking is operational in D1, ice sheet topography in D5 uses Polar Stereographic North (`EPSG:3413`). Reprojecting DEMs across geographic boundaries must preserve ellipsoid heights to avoid distortion in steep fjord walls.
3. **No Code Implementation Blockers:** All shared pipeline contracts, schemas, test suites, and frontend components are functional and passing.

### Immediate Action Items for Parallel Sprint Kickoff
1. **Team Member 1 (Lead & D5):** Freeze platform specifications and lead the implementation of the fast-stream outlet contour export in D5.
2. **Team Member 2 (D1):** Finalize sub-swath incidence angle normalization in `backend/app/domains/domain1/preprocessing.py`.
3. **Team Member 3 (D2):** Implement dynamic FIRMS point radius buffering in `backend/app/domains/domain2/analysis.py`.
4. **Team Member 4 (D3):** Implement 3D GNSS station projection vector calculations in `backend/app/domains/domain3/analysis.py`.
5. **Team Member 5 (D4):** Maintain demonstration mode and coordinate with Member 6 on Sentinel-1 RTC dual-pol procurement.
6. **Team Member 6 (QA & Explorer):** Run daily regression test suites and monitor catalog integrity across all 60 registered datasets.
