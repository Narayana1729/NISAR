# NISAR Map Engine Interface Specification

**Project:** NASA Space Apps — Dancing with the SARs (NISAR)
**Document:** `docs/architecture/map-engine-contract.md`
**Locations:** `frontend/src/components/map/`, `frontend/src/components/InteractiveWorldMap.jsx`, `src/` (legacy engine)
**Status:** Approved Standard

---

## 1. Unified Map Layer Contract

All map renderers (Cesium 3D Globe, Interactive 2D Map, and legacy viewports) accept standard layer descriptors conforming to the following structure:

```typescript
interface MapLayerDescriptor {
  id?: string;                        // Unique layer identifier
  key?: string;                       // Domain output key (e.g., 'flood_overlay', 'displacement_map')
  name?: string;                      // Human-readable title
  label?: string;                     // Alternative title alias
  kind?: 'raster' | 'overlay' | 'vector' | 'reference' | 'discrepancy';
  url: string;                        // Valid HTTP URL serving PNG/GeoTIFF/GeoJSON
  bounds?: [number, number, number, number];        // [minLon, minLat, maxLon, maxLat] in WGS84
  bounds_wgs84?: [number, number, number, number];  // Direct backend field alias
  opacity?: number;                   // 0.0 to 1.0 (default: 0.85 to 0.92)
  visible?: boolean;                  // Toggle layer rendering on/off without memory leaks
  legend?: Array<{ label: string; color: string }>;
  units?: string;                     // e.g., 'dB', 'mm/yr', 'm/day'
  description?: string;
}
```

---

## 2. Supported Layer Types Across Domains

| Layer Category | Typical Formats | Roles & Use Cases | Renderer Support |
| :--- | :--- | :--- | :--- |
| **Raster Overlays** | 8-bit RGBA PNG, GeoTIFF | Inundation masks, forest loss masks, glacier calving fronts | Draped onto 3D terrain via `Cesium.SingleTileImageryProvider` and 2D planar `<image>` projection |
| **Continuous Heatmaps** | Colormapped RGBA PNG | InSAR LOS displacement fields, ITS_LIVE ice velocities | Supported with colormap ramp legends |
| **Vector Layers** | GeoJSON Features / Pins | Infrastructure assets, FIRMS hotspots, UNESCO boundary polygons | Rendered as point billboards, vector outlines, or bounding polygons |
| **Baseline vs. Event** | GeoTIFF / PNG pairs | Pre-event and post-event calibrated radar backscatter | Synchronized in `BeforeAfterViewer.jsx` curtain swipe and side-by-side modes |
| **Classified Products** | Discrete class PNG | Categorized damage, soil moisture zones, land cover change | Color-coded pixel overlays |
| **Reference / Validation** | GeoTIFF / Vector | S2 NDWI masks, JAXA FNF, GNSS stations, MODIS MCD64A1 | Validation benchmark comparison |
| **Discrepancy Layers** | Binary discrepancy PNG | Spatial confusion matrices (False Positives in red, False Negatives in yellow) | Discrepancy inspection overlay |

---

## 3. Layer Lifecycle Management

1. **Addition:** New layers are registered into the viewer's active imagery or entity stack.
2. **Dynamic Update:** Changes to `opacity` mutate layer alpha directly without reinstantiating providers.
3. **Visibility Toggling:** `visible === false` suppresses layer rendering cleanly.
4. **Disposal / Cleanup:** When runs or domains change, active raster layers are explicitly removed and memory released via `viewer.imageryLayers.remove(layer, true)`.
5. **Error Resilience:** Missing tiles or network timeouts are logged as warnings without halting the map viewport.
