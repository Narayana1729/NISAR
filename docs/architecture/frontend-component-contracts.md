# NISAR Shared Frontend Component Contracts & Component Ownership

**Project:** NASA Space Apps — Dancing with the SARs (NISAR)
**Document:** `docs/architecture/frontend-component-contracts.md`
**Location:** `frontend/src/components/`
**Status:** Approved Standard

---

## 1. Shared Component Ownership Matrix

| Component | File Path | Primary Owner | Description & Contract |
| :--- | :--- | :--- | :--- |
| **Domain Workspace** | `frontend/src/components/DomainWorkspace.jsx` | Member 1 (Lead) | Orchestrates the 8 investigative sections: Header, Parameter Drawer, Primary Finding Card, Before/After Viewer, 3D/2D Viewport, Evidence Tab, Dossier Tab, and Export Bar. |
| **Dataset Selector** | `frontend/src/components/DatasetSelector.jsx` | Member 6 (Data QA) | Filters available datasets by `product_types`, displays sensor/polarization pills, and provides auto-selection for pre/post event pairs. |
| **Before/After Viewer** | `frontend/src/components/BeforeAfterViewer.jsx` | Member 1 (Lead) | Synchronized curtain swipe and side-by-side comparison with interactive pixel coordinate inspector (Lon, Lat, Pixel Row/Col, Baseline dB, Event dB, Delta dB). |
| **Shared Map Switcher** | `frontend/src/components/map/SharedMap.jsx` | Member 1 (Lead) | High-level switcher toggling between Cesium 3D Globe and 2D planar projection while maintaining consistent overlay bounds and camera states. |
| **Cesium 3D Globe** | `frontend/src/components/map/CesiumGlobe.jsx` | Member 1 (Lead) | React-wrapped Cesium viewer with photorealistic terrain, camera flyTo transitions, and dynamic raster imagery layer management. |
| **Interactive 2D Map** | `frontend/src/components/InteractiveWorldMap.jsx` | Member 1 (Lead) | Fast SVG/Canvas 2D projection map with real-time bounding box selection, pan/zoom, raster draping, and pin clustering. |
| **Metrics Panel** | `frontend/src/components/MetricsPanel.jsx` | Member 1 (Lead) | Responsive card grid displaying quantitative physical measurements (`label`, `value`, `unit`, `description`) with calibrated status colors. |
| **Primary Finding Card** | `frontend/src/components/scientific/PrimaryFindingCard.jsx` | Member 1 (Lead) | Scientific header displaying operational verdict, observation dates, CRS, bounds, and top 4 quantitative KPIs. |
| **Limitations Accordion** | `frontend/src/components/scientific/LimitationsAccordion.jsx` | Member 1 (Lead) | Progressive disclosure drawer explaining physical methodology, dielectric assumptions, caveats, and literature citations. |
| **Dataset Upload Modal** | `frontend/src/components/DatasetUploadModal.jsx` | Member 6 (Data QA) | Drag-and-drop file uploader accepting GeoTIFF and GeoJSON files with client-side bounding box validation. |

---

## 2. Component Interface Protocols

### `BeforeAfterViewer.jsx` Props:
```typescript
interface BeforeAfterViewerProps {
  beforeUrl: string | null;           // Pre-event preview PNG URL
  afterUrl: string | null;            // Post-event / Result preview PNG URL
  overlayUrl: string | null;          // Detected change overlay PNG URL
  changeMapUrl?: string | null;       // Continuous difference raster URL
  validationOverlayUrl?: string | null; // Discrepancy map URL
  exposureOverlayUrl?: string | null; // Intersected asset overlay URL
  beforeLabel?: string;               // e.g. "Pre-Flood Baseline (2023-09-01)"
  afterLabel?: string;                // e.g. "Post-Flood Observation (2023-09-13)"
  boundsWgs84?: [number, number, number, number]; // [min_lon, min_lat, max_lon, max_lat]
  legend?: Array<{ label: string; color: string }>;
  inspector?: {
    bounds_wgs84: [number, number, number, number];
    raster_width: number;
    raster_height: number;
    layers: Record<string, number[][]>;
  };
}
```

### `SharedMap.jsx` Props:
```typescript
interface MapLayerDescriptor {
  id?: string;
  key?: string;
  name?: string;
  label?: string;
  url: string;
  bounds?: [number, number, number, number];
  bounds_wgs84?: [number, number, number, number];
  opacity?: number;
  visible?: boolean;
}

interface SharedMapProps {
  events?: Array<any>;
  selectedEventId?: string | null;
  onSelectEvent?: (evtId: string) => void;
  datasets?: Array<any>;
  selectedBbox?: [number, number, number, number] | null;
  onChangeBbox?: (bbox: [number, number, number, number]) => void;
  rasterOverlays?: MapLayerDescriptor[];
  onLocationInspect?: (info: any) => void;
  height?: number | string;
  defaultMode?: '3d' | '2d';
}
```
