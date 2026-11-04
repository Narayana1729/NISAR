# Dataset Inventory & Organization

This inventory describes the organization, file formats, and storage layout of the NISAR project data tier.

## 1. Storage Hierarchy

The `data/` root directory is partitioned into functional stages:

```
data/
├── raw/               <-- Immutable source SAR acquisitions per domain (L1/L2 products)
│   ├── domain1/
│   ├── domain2/
│   ├── domain3/
│   ├── domain4/
│   └── domain5/
├── staging/           <-- Temporary staging area
│   ├── uploads/       <-- Raw incoming user uploads prior to verification
│   └── validated/     <-- Cleaned, format-verified files ready for pipeline ingestion
├── processed/         <-- Standardized, co-registered, and calibrated rasters
│   ├── domain1/
│   ├── domain2/
│   ├── domain3/
│   ├── domain4/
│   └── domain5/
├── intermediate/      <-- Working products (temporary interferograms, unwrapped phase cache)
│   ├── domain1/
│   ├── domain2/
│   ├── domain3/
│   ├── domain4/
│   └── domain5/
├── outputs/           <-- Deliverables (final GeoTIFFs, displacement maps, preview PNGs)
│   ├── domain1/
│   ├── domain2/
│   ├── domain3/
│   ├── domain4/
│   └── domain5/
└── manifests/         <-- Machine-readable catalogs and run summaries
    ├── datasets.json
    └── processing_runs.json
```

## 2. Supported Data Formats
- **HDF5 / NetCDF4 (`.h5`, `.nc`):** Native NISAR Level 1 & Level 2 scientific data products.
- **GeoTIFF (`.tif`, `.tiff`):** Geocoded imagery, displacement maps, coherence grids.
- **Compressed Archives (`.zip`):** Batch observation packages.

## 3. Data Governance Rules
- Never commit binary rasters or large datasets to the Git repository.
- Each directory maintains a `.gitkeep` file so directory structures persist in version control.
- Dataset metadata must be tracked in SQLite or recorded in `manifests/datasets.json`.
