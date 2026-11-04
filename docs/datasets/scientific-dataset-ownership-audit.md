# NISAR Scientific Dataset Ownership & Metadata Audit

**Document:** `docs/datasets/scientific-dataset-ownership-audit.md`
**Date:** November 3, 2026
**Scope:** Read-Only Audit of all 60 Physical & Manifest Datasets
**Status:** Audit Completed — Architectural Catalog Inconsistencies Identified

---

## 1. Executive Summary

A comprehensive, non-destructive, read-only audit of all 60 datasets in the NISAR platform was conducted across `data/manifests/datasets.json`, the SQLite metadata catalog (`backend/nisar.db`), backend API query filters, domain processor `InputSpec` declarations, and physical files on disk.

### Key Audit Discoveries:
1. **Physical Path Invariant:** Physical storage directories reflect historical ingestion batch numbering (`raw/domain1/` through `raw/domain5/`). As mandated by repository rules, physical paths must **never** be used as the source of truth for scientific domain assignment.
2. **Extensive Catalog Mismatch (32 of 60 Datasets):** In `datasets.json` and the SQLite database, 32 datasets have their catalog `domain` set to the legacy directory index rather than their scientific domain:
   - **13 Glaciers datasets** (`jakobshavn_*`) are cataloged as `domain3` and stored in `data/raw/domain3/`. Scientifically, they belong to **D5 (Glaciers & Snow/Ice)**.
   - **13 Wildfire datasets** (`evros_*` and `parkfire_*`) are cataloged as `domain5` and stored in `data/raw/domain5/`. Scientifically, they belong to **D2 (Forests & Wildfires)**.
   - **6 InSAR earthquake datasets** (`tyrnavos_*` and `test_insar_*`) are cataloged as `domain4` and stored in `data/raw/domain4/`. Scientifically, they belong to **D3 (Earthquakes & Ground Deformation)**.
3. **Scientific Workflow Suitability Failure for D4:**
   - Domain 4 is **Agriculture & Soil Conditions**, whose processing pipeline (`AgriculturePipeline`) requires dual-polarization SAR backscatter (`sar_backscatter` VV/VH) to compute crop growth and soil moisture change metrics.
   - However, the 4 Central Valley datasets (`centralvalley_*`) stored in `raw/domain4/` and cataloged as `domain4` are InSAR subsidence products (`insar_coherence`, `insar_displacement`, `reference_displacement`). They measure millimeter surface motion away from the satellite, not radar backscatter.
   - There are currently **0 real agricultural SAR backscatter datasets** in the repository. As a result, the backend API currently uses a temporary workaround injecting Thessaly flood backscatter datasets into D4 queries.
4. **API Filtering Contamination:**
   - `GET /api/datasets?domain=domain3` returns 21 datasets: 13 Jakobshavn glacier datasets + 8 InSAR deformation datasets.
   - `GET /api/datasets?domain=domain5` returns 21 datasets: 13 Dadia/Park Fire wildfire datasets + 8 Jakobshavn glacier datasets.
   - `GET /api/datasets?domain=domain4` returns 13 datasets: 10 InSAR deformation datasets + 3 Thessaly flood backscatter datasets.
   - Only `domain1` (11 datasets) and `domain2` (26 datasets, retrieving both Pará and raw/domain5 wildfire datasets) operate correctly.

---

## 2. Expected Scientific Domain Allocation

| Scientific Domain | Scientific Focus | Approved Study Areas | Expected Datasets | Current Catalog Domain |
| :--- | :--- | :--- | :---: | :--- |
| **D1** | Floods & Wetlands | Thessaly, Greece (Storm Daniel) | **11** | `domain1` (11) |
| **D2** | Forests & Wildfires | Pará, Brazil (BR-163 Deforestation); Dadia/Evros, Greece (Wildfire); Park Fire, CA (Wildfire) | **26** | `domain2` (13) + `domain5` (13) |
| **D3** | Earthquakes & Ground Deformation | Tyrnavos, Greece (2021 Mw 6.3 InSAR); San Joaquin Valley subsidence | **6** (or **10** with SJV) | `domain4` (6) |
| **D4** | Agriculture & Soil Conditions | Central / Sacramento Valley, CA (Crop phenology & soil conditions) | **4** (Synthetic fixtures, awaiting SAR) | `domain4` (4) |
| **D5** | Glaciers & Snow/Ice | Jakobshavn Isbræ, Greenland (Ice velocity & terminus calving) | **13** | `domain3` (13) |
| **Total** | | | **60** | |

---

## 3. Physical Storage Paths vs. Logical Scientific Ownership

The physical storage directory structure under `data/raw/` is an immutable legacy artifact from early ingestion batches. It does not reflect scientific domain boundaries:

```
data/raw/
├── domain1/  --> 11 Datasets: Thessaly Storm Daniel Flood  [Scientifically D1]
├── domain2/  --> 13 Datasets: Pará BR-163 Deforestation    [Scientifically D2]
├── domain3/  --> 13 Datasets: Jakobshavn Glacier Ice        [Scientifically D5]
├── domain4/  --> 10 Datasets: Tyrnavos & SJV InSAR         [Scientifically D3]
└── domain5/  --> 13 Datasets: Dadia & Park Fire Wildfire   [Scientifically D2]
```

> [!IMPORTANT]
> **Non-Destructive Invariant:** Physical files must **never** be moved or renamed on disk. Changing paths breaks relative path resolution, checksum integrity, and Git history. The correct architectural remedy is to update the metadata catalog `domain` field in `data/manifests/datasets.json` and `backend/nisar.db`, while preserving `relative_path` pointing to existing files.

---

## 4. Full 60-Dataset Comprehensive Audit Inventory

| # | Dataset ID | Name | Current Domain | Expected Domain | Study Area | Product Type | Sensor | Pol | Acq Date | CRS | Dimensions | Real/Synth | Scientific Suitability |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| 1 | `15a8d70a-999e-4575-a2b7-b7b502f0dad8` | Sentinel-1A RTC Post-Flood Observation (Thessaly, Greece) | `domain1` | **`domain1`** | Thessaly, Greece | `sar_backscatter` | Sentinel-1A (C-band SAR) | VV | 2023-09-13 | `EPSG:32634` | 1320×1470 | Real | Suitable |
| 2 | `5c351e81-1dfc-4d6b-9eec-9aed124eee8a` | Sentinel-1A RTC Pre-Flood Baseline (Thessaly, Greece) | `domain1` | **`domain1`** | Thessaly, Greece | `sar_backscatter` | Sentinel-1A (C-band SAR) | VV | 2023-09-01 | `EPSG:32634` | 1320×1470 | Real | Suitable |
| 3 | `ds-bench-thessaly-ref-flood` | Lake Karla Reference Flood Benchmark Mask (Storm Daniel) | `domain1` | **`domain1`** | Thessaly, Greece | `reference_flood` | Benchmark Reference Mask | N/A | 2023-09-13 | `EPSG:32634` | 1320×1470 | Synthetic | Suitable |
| 4 | `ds-dem-thessaly-basin` | Lake Karla Basin Terrain Elevation Model (DEM) | `domain1` | **`domain1`** | Thessaly, Greece | `dem` | Regional DEM Model | N/A | None | `EPSG:32634` | 1320×1470 | Synthetic | Suitable |
| 5 | `ds-exp-thessaly-assets` | Lake Karla Basin Agricultural & Road Assets (GeoJSON) | `domain1` | **`domain1`** | Thessaly, Greece | `exposure_assets` | Vector GIS Layer | N/A | None | `EPSG:4326` | 4 feats | Real | Suitable |
| 6 | `ds-real-thessaly-cop-dem` | Copernicus GLO-30 Digital Elevation Model (Lake Karla / Thessaly) | `domain1` | **`domain1`** | Thessaly, Greece | `dem` | Copernicus GLO-30 (TanDEM-X SAR) | N/A | 2021-01-01 | `EPSG:4326` | 565×485 | Real | Suitable |
| 7 | `ds-real-thessaly-jrc-water` | JRC Global Surface Water Occurrence ≥50% (Lake Karla Reference) | `domain1` | **`domain1`** | Thessaly, Greece | `reference_water` | Landsat JRC Global Surface Water v1.3 | N/A | 2020-12-31 | `EPSG:4326` | 628×539 | Real | Suitable |
| 8 | `ds-real-thessaly-perm-water` | Lake Karla Baseline Permanent Water Mask (2023-09-01) | `domain1` | **`domain1`** | Thessaly, Greece | `reference_water` | Sentinel-1A Derived | N/A | 2023-09-01 | `EPSG:32634` | 1320×1470 | Real | Suitable |
| 9 | `ds-real-thessaly-s2-flood-ref` | Sentinel-2A Optical Post-Flood NDWI Reference (2023-09-15, Lake Karla) | `domain1` | **`domain1`** | Thessaly, Greece | `reference_flood` | Sentinel-2A MSI L2A (Optical NDWI) | N/A | 2023-09-15 | `EPSG:32634` | 690×762 | Real | Suitable |
| 10 | `ds-test-base-flood` | Synthetic Pre-Flood Baseline | `domain1` | **`domain1`** | Thessaly, Greece | `sar_backscatter` | Unspecified | N/A | None | `EPSG:32632` | 20×20 | Synthetic | Suitable |
| 11 | `ds-test-event-flood` | Synthetic Post-Flood Crisis | `domain1` | **`domain1`** | Thessaly, Greece | `sar_backscatter` | Unspecified | N/A | None | `EPSG:32632` | 20×20 | Synthetic | Suitable |
| 12 | `ds-demo-d2-base` | Pará Canopy Baseline SAR HV (Synthetic Demo Fixture) | `domain2` | **`domain2`** | Pará, Brazil | `sar_backscatter` | Simulated NISAR L-band / S1 HV | HV | 2025-06-01 | `EPSG:32721` | 60×60 | Synthetic | Suitable |
| 13 | `ds-demo-d2-event` | Pará Canopy Monitoring SAR HV (Synthetic Demo Fixture) | `domain2` | **`domain2`** | Pará, Brazil | `sar_backscatter` | Simulated NISAR L-band / S1 HV | HV | 2025-08-15 | `EPSG:32721` | 60×60 | Synthetic | Suitable |
| 14 | `ds-demo-d2-exp` | Pará Protected Reserve Boundaries (Synthetic Exposure GeoJSON) | `domain2` | **`domain2`** | Pará, Brazil | `exposure_assets` | Unspecified | N/A | None | `EPSG:4326` | 2 feats | Synthetic | Suitable |
| 15 | `ds-demo-d2-mask` | Pará Baseline Forest Cover Mask (Synthetic Demo Fixture) | `domain2` | **`domain2`** | Pará, Brazil | `forest_mask` | Unspecified | N/A | 2025-01-01 | `EPSG:32721` | 60×60 | Synthetic | Suitable |
| 16 | `ds-demo-d2-ref` | Pará Reference Disturbance Mask (Synthetic Validation Fixture) | `domain2` | **`domain2`** | Pará, Brazil | `reference_disturbance` | Unspecified | N/A | 2025-08-15 | `EPSG:32721` | 60×60 | Synthetic | Suitable |
| 17 | `ds-real-d2-base` | Sentinel-1A RTC Baseline Forest SAR VH (2019-08-26, Novo Progresso, Pará) | `domain2` | **`domain2`** | Pará, Brazil | `sar_backscatter` | Sentinel-1A IW GRDH RTC (C-band SAR) | VH | 2019-08-26 | `EPSG:32722` | 298×298 | Real | Suitable |
| 18 | `ds-real-d2-event` | Sentinel-1A RTC Monitoring Forest SAR VH (2020-08-20, Novo Progresso, Pará) | `domain2` | **`domain2`** | Pará, Brazil | `sar_backscatter` | Sentinel-1A IW GRDH RTC (C-band SAR) | VH | 2020-08-20 | `EPSG:32722` | 298×298 | Real | Suitable |
| 19 | `ds-real-d2-exp` | Novo Progresso / BR-163 Forest Buffer & Corridor Assets (GeoJSON) | `domain2` | **`domain2`** | Pará, Brazil | `exposure_assets` | Vector GIS Layer | N/A | None | `EPSG:4326` | 3 feats | Real | Suitable |
| 20 | `ds-real-d2-mask` | JAXA ALOS-2 PALSAR-2 Baseline Forest Cover Mask (2019, Pará) | `domain2` | **`domain2`** | Pará, Brazil | `forest_mask` | JAXA ALOS-2 PALSAR-2 (L-band SAR) | N/A | 2019-01-01 | `EPSG:4326` | 120×120 | Real | Suitable |
| 21 | `ds-real-d2-ref` | JAXA ALOS-2 PALSAR-2 Independent Forest Loss Reference (2019→2020, Pará) | `domain2` | **`domain2`** | Pará, Brazil | `reference_disturbance` | JAXA ALOS-2 PALSAR-2 (L-band SAR) | N/A | 2020-08-20 | `EPSG:4326` | 120×120 | Real | Suitable |
| 22 | `ds-test-d2-base` | Test Forest Baseline HV | `domain2` | **`domain2`** | Pará, Brazil | `sar_backscatter` | Unspecified | HV | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 23 | `ds-test-d2-event` | Test Forest Monitoring HV | `domain2` | **`domain2`** | Pará, Brazil | `sar_backscatter` | Unspecified | HV | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 24 | `ds-test-d2-mask` | Test Forest Reference Mask | `domain2` | **`domain2`** | Pará, Brazil | `forest_mask` | Unspecified | N/A | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 25 | `ds-demo-d3-exp` | Ilulissat Icefjord Monitoring Zone (Synthetic Exposure GeoJSON) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `exposure_assets` | Unspecified | N/A | None | `EPSG:4326` | 1 feats | Synthetic | Suitable |
| 26 | `ds-demo-d3-ref` | Jakobshavn Independent Reference Velocity (Synthetic Validation Fixture) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `reference_velocity` | Unspecified | N/A | 2025-07-15 | `EPSG:32622` | 60×60 | Synthetic | Suitable |
| 27 | `ds-demo-d3-sar-base` | Jakobshavn Pre-Calving Terminus SAR (Synthetic Demo Fixture) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `sar_backscatter` | Simulated SAR HH | HH | 2025-07-01 | `EPSG:32622` | 60×60 | Synthetic | Suitable |
| 28 | `ds-demo-d3-sar-event` | Jakobshavn Post-Calving Terminus SAR (Synthetic Demo Fixture) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `sar_backscatter` | Simulated SAR HH | HH | 2025-07-20 | `EPSG:32622` | 60×60 | Synthetic | Suitable |
| 29 | `ds-demo-d3-vel` | Jakobshavn Surface Ice Velocity (Synthetic ITS_LIVE Demo Fixture) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `ice_velocity` | Simulated ITS_LIVE / SAR Offset Tracking | N/A | 2025-07-15 | `EPSG:32622` | 60×60 | Synthetic | Suitable |
| 30 | `ds-real-d3-exp` | Ilulissat Icefjord UNESCO Monitoring Sectors (GeoJSON) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `exposure_assets` | Vector GIS Layer | N/A | None | `EPSG:4326` | 2 feats | Real | Suitable |
| 31 | `ds-real-d3-ref` | NASA MEaSUREs ITS_LIVE Multi-Year Reference Ice Velocity (Jakobshavn Isbræ) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `reference_velocity` | NASA MEaSUREs ITS_LIVE v2 Climatology | N/A | 2020-01-01 | `EPSG:3413` | 107×101 | Real | Suitable |
| 32 | `ds-real-d3-sar-base` | Sentinel-1A RTC Terminus Baseline SAR HH (2023-08-28, Jakobshavn Isbræ) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `sar_backscatter` | Sentinel-1A IW GRDH RTC (C-band SAR) | HH | 2023-08-28 | `EPSG:32622` | 400×376 | Real | Suitable |
| 33 | `ds-real-d3-sar-event` | Sentinel-1A RTC Terminus Repeat SAR HH (2023-09-09, Jakobshavn Isbræ) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `sar_backscatter` | Sentinel-1A IW GRDH RTC (C-band SAR) | HH | 2023-09-09 | `EPSG:32622` | 400×376 | Real | Suitable |
| 34 | `ds-real-d3-vel` | NASA MEaSUREs ITS_LIVE 2022 Annual Ice Velocity (Jakobshavn Isbræ, Greenland) | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `ice_velocity` | NASA MEaSUREs ITS_LIVE v2 (Landsat 8/9 & Sentinel-1/2) | N/A | 2022-07-01 | `EPSG:3413` | 107×101 | Real | Suitable |
| 35 | `ds-test-d3-sar-base` | Test Terminus Pre-Calving SAR | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `sar_backscatter` | Unspecified | N/A | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 36 | `ds-test-d3-sar-event` | Test Terminus Post-Calving SAR | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `sar_backscatter` | Unspecified | N/A | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 37 | `ds-test-d3-vel` | Test Ice Velocity ITS_LIVE | `domain3` | **`domain5`** | Jakobshavn Isbræ, Greenland | `ice_velocity` | Unspecified | N/A | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 38 | `ds-demo-d4-coh` | San Joaquin Valley Interferometric Coherence (Synthetic Demo Fixture) | `domain4` | **`domain4`** | Central Valley, California, USA | `insar_coherence` | Unspecified | N/A | 2025-09-01 | `EPSG:32611` | 60×60 | Synthetic | Unsuitable for AgriculturePipeline (contains InSAR deformation data) |
| 39 | `ds-demo-d4-disp` | San Joaquin Valley InSAR LOS Velocity (Synthetic HyP3 Demo Fixture) | `domain4` | **`domain4`** | Central Valley, California, USA | `insar_displacement` | Simulated ASF HyP3 / NISAR L2 GUNW | N/A | 2025-09-01 | `EPSG:32611` | 60×60 | Synthetic | Unsuitable for AgriculturePipeline (contains InSAR deformation data) |
| 40 | `ds-demo-d4-exp` | San Joaquin Aqueduct & District Footprints (Synthetic Exposure GeoJSON) | `domain4` | **`domain4`** | Central Valley, California, USA | `exposure_assets` | Unspecified | N/A | None | `EPSG:4326` | 2 feats | Synthetic | Suitable |
| 41 | `ds-demo-d4-ref` | San Joaquin Reference GNSS/Leveling Field (Synthetic Validation Fixture) | `domain4` | **`domain4`** | Central Valley, California, USA | `reference_displacement` | Unspecified | N/A | 2025-09-01 | `EPSG:32611` | 60×60 | Synthetic | Unsuitable for AgriculturePipeline (contains InSAR deformation data) |
| 42 | `ds-real-d4-coh` | COMET-LiCSAR Sentinel-1 Interferometric Coherence (2021-02-25→2021-03-09, Tyrnavos) | `domain4` | **`domain3`** | Tyrnavos, Greece | `insar_coherence` | Sentinel-1A InSAR (COMET-LiCSAR Frame 102A_04971_141314) | N/A | 2021-03-09 | `EPSG:4326` | 300×220 | Real | Suitable |
| 43 | `ds-real-d4-disp` | COMET-LiCSAR Sentinel-1 Unwrapped Coseismic LOS Displacement (2021-02-25→2021-03-09, Tyrnavos Mw 6.3) | `domain4` | **`domain3`** | Tyrnavos, Greece | `insar_displacement` | Sentinel-1A InSAR (COMET-LiCSAR Frame 102A_04971_141314) | N/A | 2021-03-09 | `EPSG:4326` | 300×220 | Real | Suitable |
| 44 | `ds-real-d4-exp` | Tyrnavos & Titarisios Valley Settlements and Highway Corridors (GeoJSON) | `domain4` | **`domain3`** | Tyrnavos, Greece | `exposure_assets` | Vector GIS Layer | N/A | None | `EPSG:4326` | 3 feats | Real | Suitable |
| 45 | `ds-real-d4-ref` | COMET-LiCSAR Independent 18-Day Coseismic LOS Reference (2021-02-19→2021-03-09, Tyrnavos) | `domain4` | **`domain3`** | Tyrnavos, Greece | `reference_displacement` | Sentinel-1B/1A InSAR (COMET-LiCSAR Frame 102A_04971_141314) | N/A | 2021-03-09 | `EPSG:4326` | 300×220 | Real | Suitable |
| 46 | `ds-test-d4-coh` | Test InSAR Coherence Mask | `domain4` | **`domain3`** | Tyrnavos, Greece | `insar_coherence` | Unspecified | N/A | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 47 | `ds-test-d4-disp` | Test InSAR Displacement LOS | `domain4` | **`domain3`** | Tyrnavos, Greece | `insar_displacement` | Unspecified | N/A | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 48 | `ds-demo-d5-base` | Butte/Tehama Pre-Fire SAR HV (Synthetic Demo Fixture) | `domain5` | **`domain2`** | Park Fire, California, USA | `sar_backscatter` | Simulated NISAR / S1 HV | HV | 2025-07-10 | `EPSG:32610` | 60×60 | Synthetic | Suitable |
| 49 | `ds-demo-d5-event` | Butte/Tehama Active-Smoke Post-Fire SAR HV (Synthetic Demo Fixture) | `domain5` | **`domain2`** | Park Fire, California, USA | `sar_backscatter` | Simulated NISAR / S1 HV | HV | 2025-07-28 | `EPSG:32610` | 60×60 | Synthetic | Suitable |
| 50 | `ds-demo-d5-exp` | Cohasset Ridge WUI Settlements & Roads (Synthetic Exposure GeoJSON) | `domain5` | **`domain2`** | Park Fire, California, USA | `exposure_assets` | Unspecified | N/A | None | `EPSG:4326` | 2 feats | Synthetic | Suitable |
| 51 | `ds-demo-d5-firms` | Butte/Tehama Active Fire Thermal Points (Synthetic FIRMS Fixture) | `domain5` | **`domain2`** | Park Fire, California, USA | `fire_detections` | Simulated VIIRS/MODIS FIRMS | N/A | 2025-07-26 | `EPSG:4326` | 4 feats | Synthetic | Suitable |
| 52 | `ds-demo-d5-ref` | Butte/Tehama Mapped Burn Perimeter Reference (Synthetic Validation Fixture) | `domain5` | **`domain2`** | Park Fire, California, USA | `reference_disturbance` | Unspecified | N/A | 2025-07-29 | `EPSG:32610` | 60×60 | Synthetic | Suitable |
| 53 | `ds-real-d5-base` | Sentinel-1A RTC Pre-Fire Baseline SAR VH (2023-08-09, Dadia Forest / Evros, Greece) | `domain5` | **`domain2`** | Dadia/Evros, Greece | `sar_backscatter` | Sentinel-1A IW GRDH RTC (C-band SAR) | VH | 2023-08-09 | `EPSG:32635` | 386×400 | Real | Suitable |
| 54 | `ds-real-d5-event` | Sentinel-1A RTC Post-Fire SAR VH (2023-09-02, Dadia Forest / Evros, Greece) | `domain5` | **`domain2`** | Dadia/Evros, Greece | `sar_backscatter` | Sentinel-1A IW GRDH RTC (C-band SAR) | VH | 2023-09-02 | `EPSG:32635` | 386×400 | Real | Suitable |
| 55 | `ds-real-d5-exp` | Dadia-Lefkimi-Soufli National Park & WUI Evacuation Corridors (GeoJSON) | `domain5` | **`domain2`** | Dadia/Evros, Greece | `exposure_assets` | Vector GIS Layer | N/A | None | `EPSG:4326` | 3 feats | Real | Suitable |
| 56 | `ds-real-d5-firms` | NASA Terra/Aqua MODIS Active Fire Thermal Detections (Aug 2023, Dadia Forest / Evros) | `domain5` | **`domain2`** | Dadia/Evros, Greece | `fire_detections` | NASA Terra/Aqua MODIS (MOD14A1 & MYD14A1 v061) | N/A | 2023-08-23 | `EPSG:4326` | 1422 feats | Real | Suitable |
| 57 | `ds-real-d5-ref` | NASA MODIS MCD64A1 Mapped Burned Area Reference (Aug 2023, Dadia Forest / Evros) | `domain5` | **`domain2`** | Dadia/Evros, Greece | `reference_disturbance` | NASA Terra/Aqua MODIS (MCD64A1 v061) | N/A | 2023-08-31 | `EPSG:32635` | 386×400 | Real | Suitable |
| 58 | `ds-test-d5-base` | Test Wildfire Pre-Fire HV | `domain5` | **`domain2`** | Park Fire, California, USA | `sar_backscatter` | Unspecified | HV | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 59 | `ds-test-d5-event` | Test Wildfire Post-Fire HV | `domain5` | **`domain2`** | Park Fire, California, USA | `sar_backscatter` | Unspecified | HV | None | `EPSG:32632` | 30×30 | Synthetic | Suitable |
| 60 | `ds-test-d5-firms` | Test NASA FIRMS Thermal Hotspots | `domain5` | **`domain2`** | Park Fire, California, USA | `fire_detections` | Unspecified | N/A | None | `EPSG:4326` | 1 feats | Synthetic | Suitable |

---

## 5. Itemized Domain-by-Domain Audit Findings

### Domain 1: Floods & Wetlands (Thessaly, Greece)
**Total Scientifically Assigned Datasets:** 11

| ID | Name | Physical Path | Catalog Domain | Product Type | Suitability Analysis |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `15a8d70a-999e-4575-a2b7-b7b502f0dad8` | Sentinel-1A RTC Post-Flood Observation (Thessaly, Greece) | `raw/domain1/thessaly_flood_event_vv.tif` | `domain1` | `sar_backscatter` | Fully aligned and verified. |
| `5c351e81-1dfc-4d6b-9eec-9aed124eee8a` | Sentinel-1A RTC Pre-Flood Baseline (Thessaly, Greece) | `raw/domain1/thessaly_flood_baseline_vv.tif` | `domain1` | `sar_backscatter` | Fully aligned and verified. |
| `ds-bench-thessaly-ref-flood` | Lake Karla Reference Flood Benchmark Mask (Storm Daniel) | `raw/domain1/thessaly_reference_flood_benchmark.tif` | `domain1` | `reference_flood` | Fully aligned and verified. |
| `ds-dem-thessaly-basin` | Lake Karla Basin Terrain Elevation Model (DEM) | `raw/domain1/thessaly_terrain_dem.tif` | `domain1` | `dem` | Fully aligned and verified. |
| `ds-exp-thessaly-assets` | Lake Karla Basin Agricultural & Road Assets (GeoJSON) | `raw/domain1/thessaly_exposure_assets.geojson` | `domain1` | `exposure_assets` | Fully aligned and verified. |
| `ds-real-thessaly-cop-dem` | Copernicus GLO-30 Digital Elevation Model (Lake Karla / Thessaly) | `raw/domain1/thessaly_copernicus_dem_30m.tif` | `domain1` | `dem` | Fully aligned and verified. |
| `ds-real-thessaly-jrc-water` | JRC Global Surface Water Occurrence ≥50% (Lake Karla Reference) | `raw/domain1/thessaly_jrc_gsw_reference_water.tif` | `domain1` | `reference_water` | Fully aligned and verified. |
| `ds-real-thessaly-perm-water` | Lake Karla Baseline Permanent Water Mask (2023-09-01) | `raw/domain1/thessaly_permanent_water_mask.tif` | `domain1` | `reference_water` | Fully aligned and verified. |
| `ds-real-thessaly-s2-flood-ref` | Sentinel-2A Optical Post-Flood NDWI Reference (2023-09-15, Lake Karla) | `raw/domain1/thessaly_s2_20230915_ndwi_flood_ref.tif` | `domain1` | `reference_flood` | Fully aligned and verified. |
| `ds-test-base-flood` | Synthetic Pre-Flood Baseline | `raw/domain1/test_flood_base.tif` | `domain1` | `sar_backscatter` | Fully aligned and verified. |
| `ds-test-event-flood` | Synthetic Post-Flood Crisis | `raw/domain1/test_flood_event.tif` | `domain1` | `sar_backscatter` | Fully aligned and verified. |

### Domain 2: Forests & Wildfires (Pará, Brazil; Dadia/Evros, Greece; Park Fire, CA)
**Total Scientifically Assigned Datasets:** 26

| ID | Name | Physical Path | Catalog Domain | Product Type | Suitability Analysis |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `ds-demo-d2-base` | Pará Canopy Baseline SAR HV (Synthetic Demo Fixture) | `raw/domain2/para_forest_baseline_hv.tif` | `domain2` | `sar_backscatter` | Fully aligned and verified. |
| `ds-demo-d2-event` | Pará Canopy Monitoring SAR HV (Synthetic Demo Fixture) | `raw/domain2/para_forest_monitoring_hv.tif` | `domain2` | `sar_backscatter` | Fully aligned and verified. |
| `ds-demo-d2-exp` | Pará Protected Reserve Boundaries (Synthetic Exposure GeoJSON) | `raw/domain2/para_protected_assets.geojson` | `domain2` | `exposure_assets` | Fully aligned and verified. |
| `ds-demo-d2-mask` | Pará Baseline Forest Cover Mask (Synthetic Demo Fixture) | `raw/domain2/para_forest_canopy_mask.tif` | `domain2` | `forest_mask` | Fully aligned and verified. |
| `ds-demo-d2-ref` | Pará Reference Disturbance Mask (Synthetic Validation Fixture) | `raw/domain2/para_forest_reference_disturbance.tif` | `domain2` | `reference_disturbance` | Fully aligned and verified. |
| `ds-real-d2-base` | Sentinel-1A RTC Baseline Forest SAR VH (2019-08-26, Novo Progresso, Pará) | `raw/domain2/para_real_s1a_20190826_vh_pre.tif` | `domain2` | `sar_backscatter` | Fully aligned and verified. |
| `ds-real-d2-event` | Sentinel-1A RTC Monitoring Forest SAR VH (2020-08-20, Novo Progresso, Pará) | `raw/domain2/para_real_s1a_20200820_vh_post.tif` | `domain2` | `sar_backscatter` | Fully aligned and verified. |
| `ds-real-d2-exp` | Novo Progresso / BR-163 Forest Buffer & Corridor Assets (GeoJSON) | `raw/domain2/para_real_br163_assets.geojson` | `domain2` | `exposure_assets` | Fully aligned and verified. |
| `ds-real-d2-mask` | JAXA ALOS-2 PALSAR-2 Baseline Forest Cover Mask (2019, Pará) | `raw/domain2/para_real_alos_fnf_2019_mask.tif` | `domain2` | `forest_mask` | Fully aligned and verified. |
| `ds-real-d2-ref` | JAXA ALOS-2 PALSAR-2 Independent Forest Loss Reference (2019→2020, Pará) | `raw/domain2/para_real_alos_fnf_2019_2020_loss_ref.tif` | `domain2` | `reference_disturbance` | Fully aligned and verified. |
| `ds-test-d2-base` | Test Forest Baseline HV | `raw/domain2/test_forest_base.tif` | `domain2` | `sar_backscatter` | Fully aligned and verified. |
| `ds-test-d2-event` | Test Forest Monitoring HV | `raw/domain2/test_forest_event.tif` | `domain2` | `sar_backscatter` | Fully aligned and verified. |
| `ds-test-d2-mask` | Test Forest Reference Mask | `raw/domain2/test_forest_mask.tif` | `domain2` | `forest_mask` | Fully aligned and verified. |
| `ds-demo-d5-base` | Butte/Tehama Pre-Fire SAR HV (Synthetic Demo Fixture) | `raw/domain5/parkfire_prefire_hv.tif` | `domain5` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-demo-d5-event` | Butte/Tehama Active-Smoke Post-Fire SAR HV (Synthetic Demo Fixture) | `raw/domain5/parkfire_postfire_hv.tif` | `domain5` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-demo-d5-exp` | Cohasset Ridge WUI Settlements & Roads (Synthetic Exposure GeoJSON) | `raw/domain5/parkfire_wui_assets.geojson` | `domain5` | `exposure_assets` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-demo-d5-firms` | Butte/Tehama Active Fire Thermal Points (Synthetic FIRMS Fixture) | `raw/domain5/parkfire_firms_hotspots.geojson` | `domain5` | `fire_detections` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-demo-d5-ref` | Butte/Tehama Mapped Burn Perimeter Reference (Synthetic Validation Fixture) | `raw/domain5/parkfire_reference_perimeter.tif` | `domain5` | `reference_disturbance` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-real-d5-base` | Sentinel-1A RTC Pre-Fire Baseline SAR VH (2023-08-09, Dadia Forest / Evros, Greece) | `raw/domain5/evros_real_s1a_20230809_vh_prefire.tif` | `domain5` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-real-d5-event` | Sentinel-1A RTC Post-Fire SAR VH (2023-09-02, Dadia Forest / Evros, Greece) | `raw/domain5/evros_real_s1a_20230902_vh_postfire.tif` | `domain5` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-real-d5-exp` | Dadia-Lefkimi-Soufli National Park & WUI Evacuation Corridors (GeoJSON) | `raw/domain5/evros_real_dadia_assets.geojson` | `domain5` | `exposure_assets` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-real-d5-firms` | NASA Terra/Aqua MODIS Active Fire Thermal Detections (Aug 2023, Dadia Forest / Evros) | `raw/domain5/evros_real_modis_active_fire_points.geojson` | `domain5` | `fire_detections` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-real-d5-ref` | NASA MODIS MCD64A1 Mapped Burned Area Reference (Aug 2023, Dadia Forest / Evros) | `raw/domain5/evros_real_modis_mcd64a1_burn_reference.tif` | `domain5` | `reference_disturbance` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-test-d5-base` | Test Wildfire Pre-Fire HV | `raw/domain5/test_fire_base.tif` | `domain5` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-test-d5-event` | Test Wildfire Post-Fire HV | `raw/domain5/test_fire_event.tif` | `domain5` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |
| `ds-test-d5-firms` | Test NASA FIRMS Thermal Hotspots | `raw/domain5/test_firms.geojson` | `domain5` | `fire_detections` | Domain mismatch: Cataloged under 'domain5' (domain5), scientifically belongs to 'domain2'.; Wildfire dataset stored in raw/domain5/ and cataloged as domain5, but belongs to D2 Forests & Wildfires. |

### Domain 3: Earthquakes & Ground Deformation (Tyrnavos, Greece; San Joaquin Valley, CA)
**Total Scientifically Assigned Datasets:** 6

| ID | Name | Physical Path | Catalog Domain | Product Type | Suitability Analysis |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `ds-real-d4-coh` | COMET-LiCSAR Sentinel-1 Interferometric Coherence (2021-02-25→2021-03-09, Tyrnavos) | `raw/domain4/tyrnavos_real_licsar_20210225_20210309_coherence.tif` | `domain4` | `insar_coherence` | Domain mismatch: Cataloged under 'domain4' (domain4), scientifically belongs to 'domain3'.; InSAR coseismic deformation dataset stored in raw/domain4/ and cataloged as domain4, but belongs to D3 Earthquakes & Deformation. |
| `ds-real-d4-disp` | COMET-LiCSAR Sentinel-1 Unwrapped Coseismic LOS Displacement (2021-02-25→2021-03-09, Tyrnavos Mw 6.3) | `raw/domain4/tyrnavos_real_licsar_20210225_20210309_los_mm.tif` | `domain4` | `insar_displacement` | Domain mismatch: Cataloged under 'domain4' (domain4), scientifically belongs to 'domain3'.; InSAR coseismic deformation dataset stored in raw/domain4/ and cataloged as domain4, but belongs to D3 Earthquakes & Deformation. |
| `ds-real-d4-exp` | Tyrnavos & Titarisios Valley Settlements and Highway Corridors (GeoJSON) | `raw/domain4/tyrnavos_real_infrastructure.geojson` | `domain4` | `exposure_assets` | Domain mismatch: Cataloged under 'domain4' (domain4), scientifically belongs to 'domain3'.; InSAR coseismic deformation dataset stored in raw/domain4/ and cataloged as domain4, but belongs to D3 Earthquakes & Deformation. |
| `ds-real-d4-ref` | COMET-LiCSAR Independent 18-Day Coseismic LOS Reference (2021-02-19→2021-03-09, Tyrnavos) | `raw/domain4/tyrnavos_real_licsar_20210219_20210309_ref_los_mm.tif` | `domain4` | `reference_displacement` | Domain mismatch: Cataloged under 'domain4' (domain4), scientifically belongs to 'domain3'.; InSAR coseismic deformation dataset stored in raw/domain4/ and cataloged as domain4, but belongs to D3 Earthquakes & Deformation. |
| `ds-test-d4-coh` | Test InSAR Coherence Mask | `raw/domain4/test_insar_coh.tif` | `domain4` | `insar_coherence` | Domain mismatch: Cataloged under 'domain4' (domain4), scientifically belongs to 'domain3'.; InSAR coseismic deformation dataset stored in raw/domain4/ and cataloged as domain4, but belongs to D3 Earthquakes & Deformation. |
| `ds-test-d4-disp` | Test InSAR Displacement LOS | `raw/domain4/test_insar_disp.tif` | `domain4` | `insar_displacement` | Domain mismatch: Cataloged under 'domain4' (domain4), scientifically belongs to 'domain3'.; InSAR coseismic deformation dataset stored in raw/domain4/ and cataloged as domain4, but belongs to D3 Earthquakes & Deformation. |

### Domain 4: Agriculture & Soil Conditions (Central Valley, CA)
**Total Scientifically Assigned Datasets:** 4

| ID | Name | Physical Path | Catalog Domain | Product Type | Suitability Analysis |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `ds-demo-d4-coh` | San Joaquin Valley Interferometric Coherence (Synthetic Demo Fixture) | `raw/domain4/centralvalley_insar_coherence.tif` | `domain4` | `insar_coherence` | Product type is InSAR deformation/coherence; AgriculturePipeline expects sar_backscatter (VV/VH). Scientifically unsuitable for crop/soil backscatter change analysis. |
| `ds-demo-d4-disp` | San Joaquin Valley InSAR LOS Velocity (Synthetic HyP3 Demo Fixture) | `raw/domain4/centralvalley_insar_los.tif` | `domain4` | `insar_displacement` | Product type is InSAR deformation/coherence; AgriculturePipeline expects sar_backscatter (VV/VH). Scientifically unsuitable for crop/soil backscatter change analysis. |
| `ds-demo-d4-exp` | San Joaquin Aqueduct & District Footprints (Synthetic Exposure GeoJSON) | `raw/domain4/centralvalley_infrastructure.geojson` | `domain4` | `exposure_assets` | Fully aligned and verified. |
| `ds-demo-d4-ref` | San Joaquin Reference GNSS/Leveling Field (Synthetic Validation Fixture) | `raw/domain4/centralvalley_gnss_reference.tif` | `domain4` | `reference_displacement` | Product type is InSAR deformation/coherence; AgriculturePipeline expects sar_backscatter (VV/VH). Scientifically unsuitable for crop/soil backscatter change analysis. |

### Domain 5: Glaciers & Snow/Ice (Jakobshavn Isbræ, Greenland)
**Total Scientifically Assigned Datasets:** 13

| ID | Name | Physical Path | Catalog Domain | Product Type | Suitability Analysis |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `ds-demo-d3-exp` | Ilulissat Icefjord Monitoring Zone (Synthetic Exposure GeoJSON) | `raw/domain3/jakobshavn_fjord_assets.geojson` | `domain3` | `exposure_assets` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-demo-d3-ref` | Jakobshavn Independent Reference Velocity (Synthetic Validation Fixture) | `raw/domain3/jakobshavn_velocity_ref.tif` | `domain3` | `reference_velocity` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-demo-d3-sar-base` | Jakobshavn Pre-Calving Terminus SAR (Synthetic Demo Fixture) | `raw/domain3/jakobshavn_terminus_pre.tif` | `domain3` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-demo-d3-sar-event` | Jakobshavn Post-Calving Terminus SAR (Synthetic Demo Fixture) | `raw/domain3/jakobshavn_terminus_post.tif` | `domain3` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-demo-d3-vel` | Jakobshavn Surface Ice Velocity (Synthetic ITS_LIVE Demo Fixture) | `raw/domain3/jakobshavn_velocity_demo.tif` | `domain3` | `ice_velocity` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-real-d3-exp` | Ilulissat Icefjord UNESCO Monitoring Sectors (GeoJSON) | `raw/domain3/jakobshavn_real_fjord_assets.geojson` | `domain3` | `exposure_assets` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-real-d3-ref` | NASA MEaSUREs ITS_LIVE Multi-Year Reference Ice Velocity (Jakobshavn Isbræ) | `raw/domain3/jakobshavn_real_itslive_clim_ref_velocity.tif` | `domain3` | `reference_velocity` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-real-d3-sar-base` | Sentinel-1A RTC Terminus Baseline SAR HH (2023-08-28, Jakobshavn Isbræ) | `raw/domain3/jakobshavn_real_s1a_20230828_hh_pre.tif` | `domain3` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-real-d3-sar-event` | Sentinel-1A RTC Terminus Repeat SAR HH (2023-09-09, Jakobshavn Isbræ) | `raw/domain3/jakobshavn_real_s1a_20230909_hh_post.tif` | `domain3` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-real-d3-vel` | NASA MEaSUREs ITS_LIVE 2022 Annual Ice Velocity (Jakobshavn Isbræ, Greenland) | `raw/domain3/jakobshavn_real_itslive_2022_velocity.tif` | `domain3` | `ice_velocity` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-test-d3-sar-base` | Test Terminus Pre-Calving SAR | `raw/domain3/test_terminus_base.tif` | `domain3` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-test-d3-sar-event` | Test Terminus Post-Calving SAR | `raw/domain3/test_terminus_event.tif` | `domain3` | `sar_backscatter` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |
| `ds-test-d3-vel` | Test Ice Velocity ITS_LIVE | `raw/domain3/test_ice_velocity.tif` | `domain3` | `ice_velocity` | Domain mismatch: Cataloged under 'domain3' (domain3), scientifically belongs to 'domain5'.; Glacier cryosphere dataset stored in raw/domain3/ and cataloged as domain3, but belongs to D5 Glaciers & Snow/Ice. |

---

## 6. API Filtering & Endpoint Verification Analysis

Testing the backend endpoint `GET /api/datasets?domain={domain_id}` revealed how the backend currently compensates for catalog misassignments:

```python
# Current logic in backend/app/services/dataset_service.py:
if domain == 'domain3':
    query = query.filter((DatasetModel.domain == 'domain3') | (DatasetModel.product_type.in_(['insar_displacement', ...])))
elif domain == 'domain4':
    query = query.filter((DatasetModel.domain == 'domain4') | (DatasetModel.id.in_([...flood_ids...])))
elif domain == 'domain5':
    query = query.filter((DatasetModel.domain == 'domain5') | (DatasetModel.product_type.in_(['ice_velocity', ...])) | (DatasetModel.id.in_([...jakobshavn_ids...])))
elif domain == 'domain2':
    query = query.filter((DatasetModel.domain == 'domain2') | (DatasetModel.domain == 'domain5'))
```

### Deficiencies of this Workaround:
1. **Cross-Domain Contamination in Responses:**
   - Requesting `domain=domain3` returns glacier ice velocity and terminus backscatter alongside InSAR earthquake displacement rasters.
   - Requesting `domain=domain5` returns Dadia wildfire burn rasters and FIRMS active thermal point vectors alongside Jakobshavn glacier flow velocity rasters.
2. **Frontend Confusion:** Although `DomainWorkspace.jsx` filters candidate datasets by `inputSpec.product_types`, the unfiltered dataset response populates `availableDatasets` with geographically and scientifically irrelevant data from other continents.
3. **Spatial Overlap Trigger:** If a user manually selects an input from another continent (e.g. Pará baseline with Dadia event in D2), `ProcessingService` correctly triggers a spatial mismatch error:
   `Spatial overlap failure: Dataset '...' and dataset '...' do not intersect geographically.`

---

## 7. Ambiguous or Incorrect Product Types

1. **Central Valley Subsidence (`centralvalley_insar_los.tif`):** Cataloged under `domain4` with product type `insar_displacement`. In Domain 4 (Agriculture), `insar_displacement` is invalid because `AgriculturePipeline` requires `sar_backscatter` (VV/VH).
2. **Central Valley Coherence (`centralvalley_insar_coherence.tif`):** Cataloged under `domain4` with product type `insar_coherence`. Not used in agricultural backscatter pipelines.
3. **Synthetic Pre/Post Fire Terminus Backscatter (`ds-test-d3-sar-base`, `ds-test-d3-sar-event`):** Labeled `sar_backscatter` with no declared polarization. For rigorous multi-temporal change detection, polarization (e.g., `HH`) should be explicitly declared.

---

## 8. Datasets Awaiting Acquisition

The following data acquisitions are required to upgrade domains from demonstration/proxy status to full operational status:

1. **Domain 4 (Agriculture & Soil Conditions):**
   - **Required Data:** Multi-temporal repeat-pass L-band SAR backscatter (or Sentinel-1 C-band RTC VV/VH) over agricultural parcels in the Sacramento/San Joaquin Valley.
   - **Auxiliary Layers:** USDA NASS Cropland Data Layer (CDL) field crop boundary mask, and in-situ soil moisture sensor data (e.g., SMAP validation core sites).
   - **Current Status:** Awaiting on-orbit NISAR launch or staging of real calibrated Sentinel-1 agricultural time-series.
2. **Domain 3 (Earthquakes & Ground Deformation):**
   - **Required Data:** Dual-track ascending and descending InSAR pairs over Tyrnavos or Crete to enable full 3D vector decomposition (vertical vs horizontal fault displacement).
   - **Current Status:** Single descending COMET-LiCSAR unwrapped interferogram is operational.

---

## 9. Final Domain-Wise Dataset Counts Comparison

| Domain ID | Domain Name | Current Catalog Count | Correct Scientific Allocation Count | Net Adjustment |
| :--- | :--- | :---: | :---: | :---: |
| **domain1** | Floods & Wetlands | 11 | **11** | 0 |
| **domain2** | Forests & Wildfires | 13 | **26** | +13 (Wildfires from D5) |
| **domain3** | Earthquakes & Ground Deformation | 13 | **6** (or **10** w/ SJV) | -7 (or -3 w/ SJV) |
| **domain4** | Agriculture & Soil Conditions | 10 | **4** (or **0** true agri) | -6 (or -10) |
| **domain5** | Glaciers & Snow/Ice | 13 | **13** | 0 (Replaced wildfires with glaciers) |
| **Total** | | **60** | **60** | **0** |

---

## 10. Required Corrections (Remediation Plan)

To transition from temporary API workarounds to a clean, production-grade architecture without modifying raw files on disk:

1. **Update `data/manifests/datasets.json`:**
   - Reassign `domain` for the 13 wildfire datasets (`ds-demo-d5-*`, `ds-real-d5-*`, `ds-test-d5-*`) from `domain5` to `domain2`.
   - Reassign `domain` for the 13 Jakobshavn glacier datasets (`ds-demo-d3-*`, `ds-real-d3-*`, `ds-test-d3-*`) from `domain3` to `domain5`.
   - Reassign `domain` for the 6 Tyrnavos InSAR datasets (`ds-real-d4-coh`, `ds-real-d4-disp`, `ds-real-d4-exp`, `ds-real-d4-ref`, `ds-test-d4-coh`, `ds-test-d4-disp`) from `domain4` to `domain3`.
   - Reassign `domain` for the 4 San Joaquin Valley InSAR datasets (`ds-demo-d4-*`) from `domain4` to `domain3` (Ground Deformation).
   - **Keep all `relative_path` attributes completely unchanged**.
2. **Synchronize SQLite Database:**
   - Re-run `ensure_platform_datasets()` or update `datasets.domain` in SQLite to mirror `datasets.json`.
3. **Simplify `DatasetService.list_datasets()`:**
   - Remove the hardcoded multi-domain union hacks (`domain == 'domain3' | product_type == 'insar_displacement'`).
   - Revert to a clean, direct filter: `query = query.filter(DatasetModel.domain == domain)`.
4. **Stage Agricultural Time-Series for Domain 4:**
   - Ingest true Sentinel-1 RTC C-band (or proxy L-band) SAR backscatter over Central Valley agricultural crop fields.

---

## 11. Final Repository Readiness Verdict

**Readiness Verdict: CONDITIONAL APPROVAL — Catalog Metadata Corrections Required Before Domain Development**

### Justification:
1. **Core Processing Engine is Solid:** All 39 backend tests, frontend builds, and 1,189 legacy Node tests pass. The pre-execution validation gates and abstract pipeline interfaces work correctly.
2. **Catalog Misalignment will Confuse Domain Developers:** If parallel development begins while 32 datasets are assigned to the wrong domain in the catalog and database:
   - Member 4 (Earthquakes) will query `domain3` and receive Greenland glaciers.
   - Member 6 (Glaciers) will query `domain5` and receive Greek wildfires.
   - Member 5 (Agriculture) will query `domain4` and receive InSAR deformation and Thessaly flood data.
3. **Recommended Action:** Execute the metadata-only catalog correction (reassigning `domain` values in `datasets.json` and `backend/nisar.db` without moving any raw files) **first**, verify that `GET /api/datasets?domain=domainX` cleanly returns only that domain's scientific data, and then hand off the repository to the six team members.


---

## 12. Corrective Actions & Post-Correction State (Remediation Execution)

### 12.1 Overview of Implemented Corrections

In accordance with the findings of this audit, logical dataset ownership and API filtering were systematically remediated to restore scientific integrity across all five NISAR domains without altering physical file paths or moving disk assets.

| Scientific Domain | Description | Prior Manifest / DB Count | Reassigned Datasets | Corrected Count |
| :--- | :--- | :---: | :--- | :---: |
| **Domain 1** | Floods & Water Dynamics | 11 | Unchanged (Thessaly flood observations & benchmarks) | **11** |
| **Domain 2** | Forests & Vegetation / Wildfires | 13 | +13 Wildfire datasets (Dadia/Evros real + Park Fire demo/test) from `domain5` | **26** |
| **Domain 3** | Earthquakes & Ground Deformation | 13 | -13 Jakobshavn glaciers reallocated to D5; +6 Tyrnavos InSAR coseismic datasets from `domain4` | **6** |
| **Domain 4** | Agriculture & Soil Conditions | 10 | -6 Tyrnavos InSAR reallocated to D3; -4 Central Valley InSAR marked as `unresolved` | **0** |
| **Domain 5** | Glaciers, Snow & Ice | 13 | -13 Wildfire datasets reallocated to D2; +13 Jakobshavn glacier datasets from `domain3` | **13** |
| **Unresolved** | Unassigned InSAR Subsidence | 0 | +4 Central Valley InSAR subsidence datasets quarantined from D4 | **4** |
| **Total** | | **60** | **36 logical domain reassignments** | **60** |

---

### 12.2 Detailed Reassignment Mapping

All 36 reassigned datasets preserve their physical file locations (`relative_path`), sensor descriptors, coordinate reference systems, and synthetic flags:

| Dataset ID | Name | Product Type | Physical Path (`relative_path`) | Old Domain | New Domain | Scientific Rationale |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `ds-demo-d3-exp` | Ilulissat Icefjord Monitoring Zone | `exposure_assets` | `raw/domain3/jakobshavn_fjord_assets.geojson` | `domain3` | `domain5` | Glaciers / Cryosphere monitoring |
| `ds-demo-d3-ref` | Jakobshavn Independent Reference Velocity | `reference_velocity` | `raw/domain3/jakobshavn_velocity_ref.tif` | `domain3` | `domain5` | Ice velocity validation benchmark |
| `ds-demo-d3-sar-base` | Jakobshavn Pre-Calving Terminus SAR | `sar_backscatter` | `raw/domain3/jakobshavn_terminus_pre.tif` | `domain3` | `domain5` | Glacier calving front baseline |
| `ds-demo-d3-sar-event` | Jakobshavn Post-Calving Terminus SAR | `sar_backscatter` | `raw/domain3/jakobshavn_terminus_post.tif` | `domain3` | `domain5` | Glacier calving front repeat |
| `ds-demo-d3-vel` | Jakobshavn Surface Ice Velocity | `ice_velocity` | `raw/domain3/jakobshavn_velocity_demo.tif` | `domain3` | `domain5` | Ice surface flow velocity field |
| `ds-real-d3-exp` | Ilulissat Icefjord UNESCO Monitoring Sectors | `exposure_assets` | `raw/domain3/jakobshavn_real_fjord_assets.geojson` | `domain3` | `domain5` | Fjord asset exposure layer |
| `ds-real-d3-ref` | NASA MEaSUREs ITS_LIVE Multi-Year Reference | `reference_velocity` | `raw/domain3/jakobshavn_real_itslive_clim_ref_velocity.tif` | `domain3` | `domain5` | Ice velocity climatology |
| `ds-real-d3-sar-base` | Sentinel-1A RTC Terminus Baseline SAR HH | `sar_backscatter` | `raw/domain3/jakobshavn_real_s1a_20230828_hh_pre.tif` | `domain3` | `domain5` | Calving front observation |
| `ds-real-d3-sar-event` | Sentinel-1A RTC Terminus Repeat SAR HH | `sar_backscatter` | `raw/domain3/jakobshavn_real_s1a_20230909_hh_post.tif` | `domain3` | `domain5` | Calving front repeat observation |
| `ds-real-d3-vel` | NASA MEaSUREs ITS_LIVE 2022 Velocity | `ice_velocity` | `raw/domain3/jakobshavn_real_itslive_2022_velocity.tif` | `domain3` | `domain5` | Glacier velocity mosaic |
| `ds-test-d3-sar-base` | Test Terminus Pre-Calving SAR | `sar_backscatter` | `raw/domain3/test_terminus_base.tif` | `domain3` | `domain5` | Calving front test fixture |
| `ds-test-d3-sar-event` | Test Terminus Post-Calving SAR | `sar_backscatter` | `raw/domain3/test_terminus_event.tif` | `domain3` | `domain5` | Calving front test fixture |
| `ds-test-d3-vel` | Test Ice Velocity ITS_LIVE | `ice_velocity` | `raw/domain3/test_ice_velocity.tif` | `domain3` | `domain5` | Ice velocity test fixture |
| `ds-real-d4-coh` | COMET-LiCSAR Sentinel-1 Coherence | `insar_coherence` | `raw/domain4/tyrnavos_real_licsar_20210225_20210309_coherence.tif` | `domain4` | `domain3` | Coseismic InSAR coherence |
| `ds-real-d4-disp` | COMET-LiCSAR Unwrapped Coseismic LOS Disp | `insar_displacement` | `raw/domain4/tyrnavos_real_licsar_20210225_20210309_los_mm.tif` | `domain4` | `domain3` | Coseismic earthquake subsidence |
| `ds-real-d4-exp` | Tyrnavos Valley Settlements and Highways | `exposure_assets` | `raw/domain4/tyrnavos_real_infrastructure.geojson` | `domain4` | `domain3` | Earthquake exposure assets |
| `ds-real-d4-ref` | COMET-LiCSAR Independent 18-Day Coseismic Ref | `reference_displacement` | `raw/domain4/tyrnavos_real_licsar_20210219_20210309_ref_los_mm.tif` | `domain4` | `domain3` | Cross-pair earthquake validation |
| `ds-test-d4-coh` | Test InSAR Coherence Mask | `insar_coherence` | `raw/domain4/test_insar_coh.tif` | `domain4` | `domain3` | InSAR coherence test fixture |
| `ds-test-d4-disp` | Test InSAR Displacement LOS | `insar_displacement` | `raw/domain4/test_insar_disp.tif` | `domain4` | `domain3` | InSAR displacement test fixture |
| `ds-demo-d4-coh` | San Joaquin Valley InSAR Coherence | `insar_coherence` | `raw/domain4/centralvalley_insar_coherence.tif` | `domain4` | `unresolved` | InSAR product quarantined from D4 |
| `ds-demo-d4-disp` | San Joaquin Valley InSAR LOS Velocity | `insar_displacement` | `raw/domain4/centralvalley_insar_los.tif` | `domain4` | `unresolved` | InSAR product quarantined from D4 |
| `ds-demo-d4-exp` | San Joaquin Aqueduct & District Footprints | `exposure_assets` | `raw/domain4/centralvalley_infrastructure.geojson` | `domain4` | `unresolved` | InSAR infrastructure asset |
| `ds-demo-d4-ref` | San Joaquin Reference GNSS/Leveling Field | `reference_displacement` | `raw/domain4/centralvalley_gnss_reference.tif` | `domain4` | `unresolved` | InSAR validation benchmark |
| `ds-demo-d5-base` | Butte/Tehama Pre-Fire SAR HV | `sar_backscatter` | `raw/domain5/parkfire_prefire_hv.tif` | `domain5` | `domain2` | Wildfire canopy loss fixture |
| `ds-demo-d5-event` | Butte/Tehama Active-Smoke Post-Fire SAR HV | `sar_backscatter` | `raw/domain5/parkfire_postfire_hv.tif` | `domain5` | `domain2` | Wildfire canopy loss fixture |
| `ds-demo-d5-exp` | Cohasset Ridge WUI Settlements & Roads | `exposure_assets` | `raw/domain5/parkfire_wui_assets.geojson` | `domain5` | `domain2` | Wildfire exposure fixture |
| `ds-demo-d5-firms` | Butte/Tehama Active Fire Thermal Points | `fire_detections` | `raw/domain5/parkfire_firms_hotspots.geojson` | `domain5` | `domain2` | Active thermal fire detections |
| `ds-demo-d5-ref` | Butte/Tehama Mapped Burn Perimeter Ref | `reference_disturbance` | `raw/domain5/parkfire_reference_perimeter.tif` | `domain5` | `domain2` | Wildfire validation benchmark |
| `ds-real-d5-base` | Sentinel-1A RTC Pre-Fire Baseline SAR VH | `sar_backscatter` | `raw/domain5/evros_real_s1a_20230809_vh_prefire.tif` | `domain5` | `domain2` | Megafire canopy loss observation |
| `ds-real-d5-event` | Sentinel-1A RTC Post-Fire SAR VH | `sar_backscatter` | `raw/domain5/evros_real_s1a_20230902_vh_postfire.tif` | `domain5` | `domain2` | Megafire canopy loss observation |
| `ds-real-d5-exp` | Dadia-Lefkimi-Soufli National Park & WUI Assets | `exposure_assets` | `raw/domain5/evros_real_dadia_assets.geojson` | `domain5` | `domain2` | Megafire exposure layer |
| `ds-real-d5-firms` | NASA Terra/Aqua MODIS Active Fire Detections | `fire_detections` | `raw/domain5/evros_real_modis_active_fire_points.geojson` | `domain5` | `domain2` | 1,422 real thermal points |
| `ds-real-d5-ref` | NASA MODIS MCD64A1 Burned Area Reference | `reference_disturbance` | `raw/domain5/evros_real_modis_mcd64a1_burn_reference.tif` | `domain5` | `domain2` | Independent satellite burn mask |
| `ds-test-d5-base` | Test Wildfire Pre-Fire HV | `sar_backscatter` | `raw/domain5/test_fire_base.tif` | `domain5` | `domain2` | Wildfire test fixture |
| `ds-test-d5-event` | Test Wildfire Post-Fire HV | `sar_backscatter` | `raw/domain5/test_fire_event.tif` | `domain5` | `domain2` | Wildfire test fixture |
| `ds-test-d5-firms` | Test NASA FIRMS Thermal Hotspots | `fire_detections` | `raw/domain5/test_firms.geojson` | `domain5` | `domain2` | Wildfire test points |

---

### 12.3 Manifest & SQLite Catalog Synchronization

- **`data/manifests/datasets.json`:** Successfully updated with exact corrected domain IDs for all 60 datasets.
- **`backend/app/config.py`:** Added `"unresolved"` to `VALID_DOMAINS = ["domain1", "domain2", "domain3", "domain4", "domain5", "unresolved"]` to permit catalog registration of quarantined datasets without throwing schema errors.
- **`backend/app/services/seed_service.py`:** Synchronized registration calls so idempotent startup seeding registers datasets into their true scientific domains (`domain5` for Jakobshavn, `domain2` for Wildfires, `domain3` for Tyrnavos, `unresolved` for Central Valley).
- **`backend/nisar.db`:** SQLite table `datasets` updated via automated SQL transactions. Database record count is exactly 60, identical to the manifest.

---

### 12.4 Decoupling `DatasetService.list_datasets()`

The ad-hoc multi-domain union hacks in `backend/app/services/dataset_service.py` (lines 202–226) were removed and replaced with a clean, direct filter:

```python
if domain:
    query = query.filter(DatasetModel.domain == domain)
```

Now `GET /api/datasets?domain=domainX` cleanly and exclusively returns datasets belonging to `domainX` without bleeding cross-domain records:
- `domain1`: 11 datasets
- `domain2`: 26 datasets
- `domain3`: 6 datasets
- `domain4`: 0 datasets
- `domain5`: 13 datasets
- `unresolved`: 4 datasets

---

### 12.5 Decision on Central Valley InSAR Subsidence Datasets

The Central Valley InSAR products (`centralvalley_insar_los.tif`, `centralvalley_insar_coherence.tif`, etc.) represent millimeter-scale Line-of-Sight ground subsidence caused by aquifer compaction. They are **not** agricultural SAR backscatter. In accordance with architectural principles:
1. They have **not** been converted or coerced into agricultural backscatter (`sar_backscatter`).
2. They have **not** been automatically assigned to Domain 3 (which is reserved strictly for confirmed Tyrnavos coseismic earthquake datasets).
3. They are categorized as `"unresolved"` in the catalog while retaining their native product types (`insar_displacement`, `insar_coherence`, `reference_displacement`, `exposure_assets`).
4. This preserves the staged files for future multi-track InSAR integration while preventing cross-domain contamination.

---

### 12.6 Status of Domain 4 (Agriculture & Soil Conditions)

With Central Valley InSAR datasets quarantined, **Domain 4 currently has 0 staged datasets in the local repository**.
- `AgriculturePipeline` remains in `implementation_status = "demonstration"`.
- `AgriculturePipeline.inputs` strictly requires `sar_backscatter` (VV/VH repeat-pass backscatter) and rejects InSAR displacement inputs with a `PipelineInputError`.
- In the frontend workspace (`DomainWorkspace.jsx`), when `availableDatasets.length === 0`, an honest empty-state banner alerts the user:
  > *"No Staged Datasets Available: There are currently no staged datasets matching Agriculture & Soil Conditions. Real agricultural SAR backscatter datasets are pending ingestion. InSAR ground deformation datasets belong to Domain 3."*
- Team Member 5 (Agriculture) can now ingest true Sentinel-1 RTC dual-pol (VV+VH) time-series over agricultural zones without working against mismatched InSAR data.

---

### 12.7 Automated Verification Suite Results

All verification suites were executed against the updated codebase:

1. **Dedicated Scientific Ownership Test Suite (`test_scientific_dataset_ownership.py`):**
   - `test_1_manifest_and_sqlite_id_consistency`: **PASSED** (60/60 IDs match 1-to-1)
   - `test_2_correct_logical_domain_counts`: **PASSED** (D1:11, D2:26, D3:6, D4:0, D5:13, Unresolved:4)
   - `test_3_api_filtering_for_all_domains`: **PASSED** (Endpoints return exact counts)
   - `test_4_no_cross_domain_contamination`: **PASSED** (Zero cross-domain overlap)
   - `test_5_physical_file_paths_on_disk_preserved`: **PASSED** (All 60 files exist and are intact)
   - `test_6_domain2_retrieves_wildfire_and_forest_datasets`: **PASSED** (D2 has 26 datasets)
   - `test_7_domain5_retrieves_jakobshavn_glacier_datasets`: **PASSED** (D5 has 13 datasets)
   - `test_8_domain3_retrieves_only_confirmed_earthquake_insar_datasets`: **PASSED** (D3 has 6 Tyrnavos datasets)
   - `test_9_domain4_rejects_insar_displacement_as_agricultural_backscatter`: **PASSED** (Rejects InSAR with 422/PipelineInputError)
   - `test_10_synthetic_fixtures_and_real_observations_clearly_flagged`: **PASSED** (`is_synthetic` flag verified)

2. **Full Backend Pytest Suite:**
   - **49 passed**, 0 failed (including architecture contracts, raster processing, and domain workflows).

3. **Dataset Verification Script (`scripts/validate_datasets.py`):**
   - **60 verified successfully, 0 errors**. All staged rasters and GeoJSON vectors georeferenced and intact.

4. **Frontend Production Build (`npm run build --prefix frontend`):**
   - Built successfully in **405 ms** (65 modules transformed, 0 errors).

5. **Legacy Map-Engine Suite (`scripts/run-unit-tests.mjs`):**
   - **1,189 passed, 1 skipped, 0 failed**.
