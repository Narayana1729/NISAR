# API Contracts & Interface Specification

This document details the HTTP REST API endpoints exposed by the NISAR FastAPI backend.

## Base URL
Default: `http://localhost:8000`

---

## 1. System Health

### `GET /api/health`
Checks whether the backend server is operational.

**Response `200 OK`:**
```json
{
  "status": "healthy",
  "service": "NISAR Analysis Platform Backend",
  "version": "0.1.0"
}
```

---

## 2. Dataset Management

### `GET /api/datasets`
Lists registered datasets. Supports optional filtering by domain.

**Query Parameters:**
- `domain` (optional, string): Filter datasets by domain key (e.g., `domain1`).

**Response `200 OK`:**
```json
[
  {
    "id": "c1f7a4d2-...",
    "name": "Sample SAR Observation",
    "domain": "domain1",
    "description": "L-band acquisition",
    "format": "HDF5",
    "relative_path": "raw/domain1/sample.h5",
    "file_size_bytes": 10485760,
    "created_at": "2026-10-27T10:00:00"
  }
]
```

### `GET /api/datasets/{dataset_id}`
Retrieves metadata for a single dataset.

**Response `200 OK`:**
```json
{
  "id": "c1f7a4d2-...",
  "name": "Sample SAR Observation",
  "domain": "domain1",
  "description": "L-band acquisition",
  "format": "HDF5",
  "relative_path": "raw/domain1/sample.h5",
  "file_size_bytes": 10485760,
  "created_at": "2026-10-27T10:00:00"
}
```

### `POST /api/datasets/upload`
Uploads and registers a new dataset file. Enforces file size limits and valid file extensions (`.h5`, `.tif`, `.nc`, etc.).

**Form Data:**
- `name` (string)
- `domain` (string)
- `format` (string)
- `file` (binary)

---

## 3. Domain Modules (`/api/domains/{domain_id}`)
Supported domain keys: `domain1`, `domain2`, `domain3`, `domain4`, `domain5`.

### `GET /api/domains/{domain_id}/info`
Retrieves information and capabilities for the specified domain.

**Response `200 OK`:**
```json
{
  "domain": "domain1",
  "name": "Domain1",
  "status": "active",
  "description": "Placeholder endpoints for Domain1 processing and analytics."
}
```

### `POST /api/domains/{domain_id}/process`
Initiates a processing job using the domain's pipeline orchestrator.

**Request Body:**
```json
{
  "dataset_id": "c1f7a4d2-...",
  "params": {
    "coherence_threshold": 0.35,
    "filter_window": 5
  }
}
```

**Response `200 OK`:**
```json
{
  "domain": "domain1",
  "status": "completed",
  "metrics": [
    { "label": "Sample Metric A", "value": "12.4", "unit": "m" },
    { "label": "Sample Metric B", "value": "0.94", "unit": null }
  ],
  "output_files": [
    "outputs/domain1/preview_layer.png",
    "outputs/domain1/difference_map.png"
  ]
}
```

### `GET /api/domains/{domain_id}/runs`
Retrieves execution history for the given domain.
