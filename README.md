<div align="center">

# 🛰️ NISAR SAR Scientific Analysis Platform

### An interactive 3D Earth observation console for SAR environmental and geological analysis.

Built on CesiumJS. Integrates multi-spectral canopy monitoring, global seismic activity, active fire tracking, critical infrastructure overlays, and GPU-accelerated visual analysis shaders.

</div>

---

## 🌍 Platform Overview

The NISAR platform provides high-precision geospatial visualization and scientific Earth observation tools running directly in the browser:

* **Interactive 3D Globe**: WGS84 ellipsoid rendering with quantized-mesh terrain and geoid height corrections.
* **Forest Intelligence & Change Detection**: Multi-spectral vegetation index analysis (NDVI, NDMI, NBR) from Sentinel-2 and Landsat surface reflectance, with multi-temporal canopy disturbance detection.
* **Global Seismic Activity**: Real-time and historical USGS earthquake catalog integration with magnitude scaling and depth profiling.
* **Active Fire Hotspots**: NASA FIRMS near-real-time thermal anomaly footprints (VIIRS NOAA-20 / Suomi-NPP / MODIS).
* **Critical Infrastructure**: Global vector datasets for world dams, datacenters, and submarine fiber optic cables.
* **Geospatial Annotations**: Interactive point, path, and polygon drawing with Overpass footprint resolution and GeoJSON export.
* **Post-Processing Shaders**: Hardware-accelerated visual shaders (`surveillance`, `thermal`, `retro`, `noir`, `snow`) for imagery contrast enhancement.

---

## 🚀 Quick Start

### Prerequisites
* Node.js `>= 24.11.0`
* npm

### Installation & Launch

```bash
# Clone the repository
git clone https://github.com/bilawalsidhu/gods-eye-view.git
cd gods-eye-view

# Install dependencies
npm install

# Start local development server
npm run dev
```

The application will start on `http://localhost:4173`.

---

## 🔑 Configuration & API Keys

The application runs in a keyless mode out of the box using **Esri World Imagery** and public data feeds. To enable optional high-resolution services, configure keys via `.env` or the in-app settings panel:

* `GOOGLE_MAPS_API_KEY`: Enables Google Photorealistic 3D Tiles and Google Places search.
* `CESIUM_ION_TOKEN`: Enables Cesium ion assets and Bing satellite imagery.
* `FIRMS_MAP_KEY`: Enables live NASA FIRMS active fire queries via the server-side proxy.

See [`.env.example`](.env.example) for reference variable definitions.

---

## 🧪 Testing & Verification

```bash
# Run unit tests
npm test

# Production build
npm run build

# Start production preview server
npm run preview
```

---

## 📄 License & Attribution

* Platform source code is licensed under the [MIT License](LICENSE).
* Third-party data sources maintain their respective open-access and provider terms. See [`DATA_SOURCES.md`](DATA_SOURCES.md) for full licensing and attribution details.
