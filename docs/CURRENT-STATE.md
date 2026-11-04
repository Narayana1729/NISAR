# NISAR SAR Earth Observation Platform — Current State

Updated: November 2, 2026

## 1. Overview

The codebase is an interactive 3D Earth observation console built on CesiumJS, optimized for synthetic aperture radar (SAR) analysis, environmental monitoring, and geological risk assessment. The repository has completed two cleanup passes to remove all legacy flight tracking, maritime AIS, urban traffic, CCTV surveillance, cockpit simulator, and voice assistant modules.

## 2. Core Infrastructure & Lifecycle

### CesiumJS Globe Engine
* **Ellipsoid & Terrain**: Operates on the WGS84 ellipsoid with Re:Earth Mapterhorn quantized-mesh terrain provider (`/api/terrain/heights` proxy) and local EGM96 geoid undulation corrections (`src/data/geoid.js`).
* **Render Governor** (`src/renderGovernor.js`): Coordinates WebGL rendering on demand. Continuous frame animators register holds; discrete user actions and data arrivals request single-frame paints (`governorRequestRender`). Inactive browser tabs suspend the render loop to prevent GPU resource exhaustion.
* **Camera System** (`src/camera.js`, `src/cameraVerbs.js`): Smooth perspective and orthographic camera transitions, bounding-box framing for regions of interest, and coordinate conversion (`src/locationReadouts.js`).

### Layer State Coordinator
* **Registry** (`src/data/layerState.js`): Maintains the 6 verified layers:
  1. `earthquakes` — USGS global earthquake events.
  2. `forest-intelligence` — Multi-spectral canopy change, deforestation detection, and risk scoring.
  3. `local-dams` — Global Dam Watch critical infrastructure vector layer.
  4. `local-datacenters` — Worldwide datacenter infrastructure vector layer.
  5. `local-firms` — NASA FIRMS near-real-time active fire hotspots.
  6. `telegeography-submarine-cables` — TeleGeography submarine fiber optic cable network.
* **State Persistence**: Serializes layer visibility and display parameters into shareable URL hashes (`src/sharelink.js`).

### Scientific Overlays & Annotations
* **World Overlay** (`src/overlays/worldOverlay.js`, `src/overlays/worldOverlayDraw.js`): Screen-space canvas overlay rendering re-projected geographic labels, bounding boxes, and region inspection cards.
* **Annotation Engine** (`src/annotations/annotationEngine.js`, `src/annotations/annotationResolver.js`): Supports interactive drawing of points, lines, polylines, and polygons on the 3D surface, with Overpass footprint resolution and GeoJSON export.

## 3. Active Scientific & Environmental Domains

### Forest Intelligence (`src/data/forest*.js`, `src/forestPanel.js`)
* **Spectral Analysis**: Computes calibrated vegetation indices (NDVI, NDMI, NBR) from Sentinel-2 and Landsat surface reflectance.
* **Multi-temporal Change Detection**: Calculates confirmed physical canopy loss percentage and geodesic area ($\text{km}^2$) between observation dates $T_1$ and $T_2$.
* **Risk Prediction**: Implements an explainable rule-based baseline model (`RULE_BASED_BASELINE`) with additive risk factors, strictly segregated from physical loss measurements.

### Geological Activity (`src/data/earthquakes.js`)
* Real-time and historical USGS earthquake event feeds, rendering epicenter markers scaled by magnitude and colored by focal depth.
* Serves as anchor data for future InSAR surface deformation and fault rupture studies.

### Thermal Anomalies (`src/data/firmsHeatmap.js`, `src/data/firmsCsv.js`)
* Real-time NASA FIRMS active fire hotspots (VIIRS NOAA-20 / Suomi-NPP / MODIS) ingested through the secure server-side `/api/firms` proxy.
* Supports multi-temporal fire scar verification and hazard correlation.

## 4. UI Shell & Styling

* **Layout Structure**: Dual-rail architecture preserving `#left-panel-stack` (domain controls), `#right-context-rail` (display presets and HUD options), and `#command-dock` (navigation and visual preset selection).
* **Visual Post-Processing**: Hardware-accelerated WebGL post-processing shaders (`retro`, `anime`, `noir`, `snow`, `surveillance`, `thermal`) repurposed for radar polarimetry contrast enhancement.
* **Split-Flap Display** (`src/splitFlap.js`): Mechanical split-flap animation engine for telemetry bars, coordinate readouts, and job metrics.

## 5. UI Lifecycle & Modals

* **First-Run Experience** (`src/firstRunExperience.js`): Coordinates welcome modal choices (`ENVIRONMENTAL`, `EXPLORE MANUALLY`). If an exclusive surface is active at startup (e.g., during full-screen recording or modal takeover), the launcher yields. Per the platform design invariant, a surface class that never clears means no launcher for that page; the system does not force popups via arbitrary timers.
