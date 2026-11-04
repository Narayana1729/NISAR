# NISAR Data Storage Conventions & Lineage Specification

**Project:** NASA Space Apps — Dancing with the SARs (NISAR)
**Document:** `docs/architecture/data-storage-conventions.md`
**Location:** `data/`
**Status:** Approved Standard

---

## 1. Directory Structure & Responsibilities

```
data/
├── raw/                 # IMMUTABLE raw Earth observation data & GeoJSONs
│   ├── domain1/         # Thessaly flood rasters, DEM, permanent water masks
│   ├── domain2/         # Pará deforestation & Dadia/Evros wildfire rasters
│   ├── domain3/         # Tyrnavos InSAR LOS displacement & coherence grids
│   ├── domain4/         # Agricultural boundary & multi-temporal SAR rasters
│   └── domain5/         # Jakobshavn ITS_LIVE velocity & terminus SAR pairs
├── staging/             # Temporary ingestion area for unverified uploads
├── intermediate/        # Ephemeral multi-look, warped, or clipped GeoTIFFs
├── outputs/             # Persisted run outputs partitioned by domain and run_id
│   └── <domain>/<run_id>/
├── references/          # Independent ground truth benchmarks and validation masks
└── manifests/           # Versioned platform registries
    ├── datasets.json    # Catalog of all registered physical & demo datasets
    └── processing_runs.json # Exported run history metadata
```

---

## 2. Directory Semantics

### `data/raw/` (IMMUTABLE)
- Contains source satellite rasters (Copernicus Sentinel-1 RTC, Sentinel-2 Optical, JAXA ALOS-2, COMET-LiCSAR, NASA MEaSUREs ITS_LIVE).
- **Rule:** Raw data files must **NEVER** be modified, overwritten, or deleted by any pipeline.
- All algorithms must treat files in `data/raw/` as read-only inputs.

### `data/staging/`
- Serves as the landing area for newly uploaded files before metadata extraction and validation.
- Files here are transient and undergo CRS and bounding box verification before promotion to `data/raw/`.

### `data/intermediate/`
- Contains temporary warped, reprojected, or multi-looked rasters generated during pipeline execution.
- Can be safely cleared between batch processing runs without affecting reproducibility.

### `data/outputs/<domain>/<run_id>/`
- Houses all artifacts produced during a specific processing run:
  - Deliverable GeoTIFF rasters (e.g., `classification.tif`, `displacement.tif`).
  - Web-servable 8-bit RGBA preview overlays (e.g., `flood_overlay.png`).
  - Spatial agreement discrepancy maps (e.g., `validation_overlay.png`).
  - Intersected asset overlays (e.g., `exposure_overlay.png`).
- Directory name must be the exact UUID4 `run_id`.

### `data/manifests/`
- **`datasets.json`**: The authoritative registry storing geospatial metadata:
  - `id`: Unique identifier (UUID or human-readable slug).
  - `name`: Descriptive satellite product title.
  - `domain`: Associated domain (`domain1` through `domain5`).
  - `product_type`: e.g. `sar_backscatter`, `insar_displacement`, `ice_velocity`.
  - `sensor`, `polarization`, `acquisition_date`, `value_scale`, `units`, `source`.
  - `crs`: EPSG code (e.g. `EPSG:32634`).
  - `bbox_wgs84`: `[west, south, east, north]`.
  - `is_synthetic`: Boolean flag distinguishing real Earth observations from demo benchmarks.

---

## 3. Dataset Naming Conventions

### File Naming Convention:
`<region>_<theme>_<phase>_<polarization_or_metric>.<ext>`
- *Example 1:* `thessaly_flood_baseline_vv.tif`
- *Example 2:* `thessaly_flood_event_vv.tif`
- *Example 3:* `para_forest_monitoring_hv.tif`
- *Example 4:* `tyrnavos_insar_displacement_los.tif`
- *Example 5:* `jakobshavn_ice_velocity_2022.tif`

### Processing Output Naming Convention:
Outputs inside `data/outputs/<domain>/<run_id>/`:
- Classification raster: `classification.tif`
- Discrepancy / difference raster: `change_difference.tif`
- Color-mapped PNG overlay: `<analysis_type>_overlay.png`
- Validation agreement PNG: `validation_agreement.png`
- Spatial asset exposure PNG: `exposure_overlay.png`

---

## 4. Historical Storage Directory Mapping & Non-Destructive Preservation

During early prototype development, raw data directories were organized by historical ingestion numbering:
- `data/raw/domain3/`: Contains Jakobshavn Glacier datasets (scientifically assigned to D5 Glaciers & Snow/Ice).
- `data/raw/domain4/`: Contains Tyrnavos InSAR earthquake displacement and Central Valley deformation datasets (scientifically assigned to D3 Earthquakes & Deformation).
- `data/raw/domain5/`: Contains Dadia/Evros and Park Fire wildfire disturbance datasets (scientifically assigned to D2 Forests & Wildfires).

**Preservation Invariant:** In accordance with repository architecture rules, physical raw dataset files on disk are **never moved or renamed** to preserve path references, hash stability, and existing tests. Backend routers and processors cleanly resolve datasets across physical storage locations without requiring filesystem mutations.
