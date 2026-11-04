# NISAR Processing Request & Response Contract Specification

**Project:** NASA Space Apps — Dancing with the SARs (NISAR)
**Document:** `docs/architecture/processing-contract.md`
**Endpoint:** `POST /api/domains/{domain_id}/process` and `POST /api/{domain_id}/process`
**Schema Source:** `app/schemas/results.py`
**Status:** Approved Standard

---

## 1. Processing Request Contract (`ProcessingRequest`)

```json
{
  "inputs": {
    "<role_name>": "<dataset_id>"
  },
  "parameters": {
    "<param_name>": "<value>"
  },
  "study_area_bbox": [min_lon, min_lat, max_lon, max_lat]
}
```

### Fields:
- **`inputs`** *(dict[str, str], required)*: Key-value map from the domain's declared `InputSpec.role` to a registered dataset UUID or ID.
- **`parameters`** *(dict[str, Any], optional)*: Key-value map of algorithm thresholds and options matching `ParamSpec.name`. Defaults are injected automatically if omitted.
- **`study_area_bbox`** *(list[float], optional)*: `[west, south, east, north]` coordinates in WGS84 (`EPSG:4326`) defining custom spatial cropping boundaries.

---

## 2. Standard Domain Response Contract (`StandardDomainResponse`)

```json
{
  "run_id": "82cbb3d3-6acc-43e1-bc07-d8e49c7b8230",
  "domain": "domain1",
  "status": "completed",
  "analysis": "Floods & Wetlands Inundation Analysis",
  "execution_time_seconds": 1.42,
  "implementation_status": "implemented",
  "is_synthetic_input": false,
  "study_area": {
    "bbox_wgs84": [22.7966, 39.4476, 22.9537, 39.5824],
    "native_crs": "EPSG:32634",
    "native_bbox": [654440.0, 4368140.0, 667640.0, 4382840.0],
    "width": 1320,
    "height": 1470
  },
  "summary_metrics": [
    { "label": "New Flood Inundation", "value": "5.74", "unit": "km²" },
    { "label": "Permanent Water Extent", "value": "29.35", "unit": "km²" },
    { "label": "Total Surface Water", "value": "35.09", "unit": "km²" },
    { "label": "Water Threshold", "value": "-15.1", "unit": "dB" }
  ],
  "layers": [
    {
      "key": "classification_geotiff",
      "label": "Classified Flood Map (GeoTIFF)",
      "kind": "raster",
      "path": "outputs/domain1/82cbb3d3.../classification.tif",
      "url": "/api/outputs/domain1/82cbb3d3.../classification.tif",
      "bounds_wgs84": [22.7966, 39.4476, 22.9537, 39.5824]
    },
    {
      "key": "flood_overlay",
      "label": "Flood Inundation Overlay (RGBA)",
      "kind": "overlay",
      "path": "outputs/domain1/82cbb3d3.../flood_overlay.png",
      "url": "/api/outputs/domain1/82cbb3d3.../flood_overlay.png",
      "bounds_wgs84": [22.7966, 39.4476, 22.9537, 39.5824]
    }
  ],
  "explanation": {
    "operational": "Rapid response flood extent map covering Lake Karla basin.",
    "scientific": "Calibrated dual-temporal Sentinel-1A C-band SAR backscatter processed with bounded Otsu thresholding.",
    "public": "Map showing newly submerged land and standing water after Storm Daniel."
  },
  "caveats": [
    "Vegetation canopies may obscure standing water in flooded wetlands."
  ],
  "warnings": [],
  "observation_dates": ["2023-09-01", "2023-09-13"],
  "provenance": {
    "algorithm": "Floods & Wetlands Inundation Analysis",
    "algorithm_version": "2.0.0",
    "software_version": "NISAR-DancingWithTheSARs/2.0.0"
  },
  "validation": {
    "status": "evaluated",
    "reference_dataset_id": "...",
    "metrics": [
      { "label": "Critical Success Index (IoU)", "value": "0.84", "unit": "fraction" }
    ]
  },
  "exposure": {
    "status": "evaluated",
    "metrics": [
      { "label": "Submerged Agricultural Land", "value": "412.5", "unit": "ha" }
    ]
  }
}
```

---

## 3. Pre-Execution Validation Gates

In `ProcessingService._resolve_inputs()` and `_validate_dataset_compatibility()`:
1. **Catalog & Storage Presence:** Validates existence in SQLite database and physical readability of files on disk.
2. **Product Type Matching:** Verifies dataset `product_type` satisfies `InputSpec.product_types`.
3. **Role Uniqueness:** Enforces distinct datasets for each input role.
4. **Implementation Status Gate:** If `pipeline.implementation_status == "planned"`, halts execution with HTTP 422.
5. **Polarization Matching:** SAR backscatter comparison inputs must share identical polarization.
6. **Dimension Validity:** Dataset rasters must exhibit positive non-zero dimensions (`width > 0, height > 0`).
7. **Spatial Overlap:** Primary raster pairs must intersect in WGS84 geographic bounding boxes.
8. **Temporal Ordering:** Sequential inputs (pre/post) warn upon chronological inversion.
9. **Non-Empty Output:** Execution must produce $\ge 1$ layer or metric; empty outputs raise `PipelineExecutionError`.
