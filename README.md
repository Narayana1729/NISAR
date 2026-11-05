<div align="center">

# 🛰️ NISAR SAR Scientific Analysis Platform
### Dancing with the SARs — NASA Space Apps Challenge

An interactive 3D Earth observation console and scientific processing pipeline for SAR environmental and geophysical analysis.

Built on CesiumJS & FastAPI. Features multi-temporal SAR processing across five scientific domains, GPU-accelerated visualization shaders, and calibrated change detection.

</div>

---

## 🌍 Scientific Domains Overview

The platform provides dedicated analysis workspaces, data pipelines, and interactive 3D visualizers for five core Earth observation domains:

1. **Floods & Wetlands** (*Thessaly, Greece* — Storm Daniel):
   - Dual-pol backscatter change detection, bounded Otsu thresholding, Copernicus 30m DEM slope masking, and permanent water exclusion.
   - Comprehensive technical spec: [`docs/domains/domain1-floods-wetlands.md`](docs/domains/domain1-floods-wetlands.md)

2. **Forests & Wildfires** (*Pará, Brazil & Evia, Greece*):
   - Multi-temporal canopy disturbance detection, ALOS-2 L-band Radar Forest Degradation Index (RFDI), and NASA FIRMS active fire hotspot corroboration.
   - Comprehensive technical spec: [`docs/domains/domain2-forests-wildfires.md`](docs/domains/domain2-forests-wildfires.md)

3. **Earthquakes & Ground Deformation** (*Tyrnavos, Greece*):
   - Sentinel-1 InSAR phase unwrapping, geodetic line-of-sight (LOS) displacement calculation ($\lambda = 0.055465\text{ m}$), coherence thresholding, and 3D GNSS vector projection.
   - Comprehensive technical spec: [`docs/domains/domain3-earthquakes-deformation.md`](docs/domains/domain3-earthquakes-deformation.md)

4. **Agriculture & Soil Conditions** (*Central Valley, California*):
   - Dual-polarization Radar Vegetation Index (RVI), cross-ratio backscatter dynamics, crop phenology tracking, and calibrated surface wetness proxies.
   - Comprehensive technical spec: [`docs/domains/domain4-agriculture-soil.md`](docs/domains/domain4-agriculture-soil.md)

5. **Glaciers, Snow & Ice** (*Jakobshavn Isbræ, Greenland*):
   - SAR sub-pixel offset tracking ice velocity fields ($m/\text{yr}$), calving terminus margin extraction, ITS_LIVE climatological validation, and BedMachine v5 flux-gate mass balance estimation.
   - Comprehensive technical spec: [`docs/domains/domain5-glaciers-ice.md`](docs/domains/domain5-glaciers-ice.md)

---

## 🚀 Quick Start

### Prerequisites
* **Node.js** `>= 24.11.0` and **npm**
* **Python** `>= 3.10` with `venv`

### 1. Clone the Repository

```bash
git clone https://github.com/Narayana1729/NISAR.git
cd NISAR
```

### 2. Backend Setup (FastAPI & Scientific Engine)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start backend server (http://localhost:8000)
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup (CesiumJS & 3D Globe Console)

Open a new terminal window at the repository root:

```bash
# Install frontend dependencies
npm install

# Start local development server (http://localhost:4173)
npm run dev
```

The application console will be live at `http://localhost:4173` with full backend API connectivity at `http://localhost:8000`.

---

## 🧪 Testing & Verification

Run the full automated test suites to ensure data integrity and platform health:

```bash
# Run backend pytest suite (49 domain and contract tests)
backend/venv/bin/pytest backend/tests/

# Run frontend test suite (1,189 unit tests)
npm test

# Build production client bundle
npm run build
```

---

## 👥 Team Development & Collaboration

For branch naming rules, assigned domains, pull request guidelines, and frozen architecture standards, see the [**Team Development Guide (CONTRIBUTING.md)**](CONTRIBUTING.md).

| Role | Assigned Domain | Branch |
| :--- | :--- | :--- |
| **Member 1** | Domain 5: Glaciers, Snow & Ice | `feature/domain5-glaciers-integration` |
| **Member 2** | Domain 1: Floods & Wetlands | `feature/domain1-floods` |
| **Member 3** | Domain 2: Forests & Wildfires | `feature/domain2-forests` |
| **Member 4** | Domain 3: Earthquakes & Deformation | `feature/domain3-earthquakes` |
| **Member 5** | Domain 4: Agriculture & Soil | `feature/domain4-agriculture` |
| **Member 6** | Platform QA & Event Explorer | `feature/data-qa-event-explorer` |

---

## 🔑 Configuration & API Keys

The application runs in **keyless mode** out of the box using Esri World Imagery and local cached SAR products. Optional third-party providers can be configured in `.env`:

* `GOOGLE_MAPS_API_KEY`: Enables Google Photorealistic 3D Tiles and Google Places search.
* `CESIUM_ION_TOKEN`: Enables Cesium ion cloud assets and Bing satellite imagery.
* `FIRMS_MAP_KEY`: Enables live NASA FIRMS active fire queries.

See [`.env.example`](.env.example) for reference definitions.

---

## 📄 License & Attribution

* Platform source code is licensed under the [MIT License](LICENSE).
* Datasets and satellite imagery are sourced from Copernicus Sentinel, JAXA ALOS-2, NASA/USGS Landsat, USGS Earthquakes, and NASA FIRMS. See [`DATA_SOURCES.md`](DATA_SOURCES.md) for full licensing and attribution details.
