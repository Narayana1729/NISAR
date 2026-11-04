# NISAR SAR Scientific Analysis Platform — Second-Pass Legacy Cleanup Final Report

**Date:** November 2, 2026
**Status:** Verification Complete & Green (1,189 Unit Tests Passed, 1 Skipped, 0 Failed; Production Server Passed; Build Succeeded)
**Total Active Codebase Files:** 259 files (down from ~465 initial files and 297 first-pass files)

---

## 1. Executive Summary

This second cleanup pass eliminates legacy God's Eye View (GEV) modules, surveillance assets, dead demo media, mock fixtures, and obsolete QA harnesses while preserving the core CesiumJS 3D geospatial engine, styling, render governor, and active scientific layers (`earthquakes`, `forest-intelligence`, `local-dams`, `local-datacenters`, `local-firms`, `telegeography-submarine-cables`).

All unneeded dependencies have been uninstalled, dead proxy routes pruned, dead UI controllers stubbed, and documentation updated to reflect the platform's focus on SAR Earth observation and environmental analysis.

---

## 2. Inventory of Removed Legacy Modules & Assets

### Obsolete Modules & Associated Tests Removed
* `src/contactsDetectionPolicy.js` & `src/contactsDetectionPolicy.test.mjs`
* `src/data/installationFeedback.js` & `src/data/installationFeedback.test.mjs`
* `src/data/trackedCamera.js` & `src/data/trackedCamera.test.mjs`
* `src/data/trackingClickGesture.js` & `src/data/trackingClickGesture.test.mjs`
* `scripts/track-regression.mjs`

### Obsolete Assets, Models & Fixtures Removed
* `scripts/fixtures/voice/` (removed directory and `full-globe-turn-on-radio.wav`, `README.md`)
* `public/models/` (removed all 3D vehicle/aircraft glTF models: `airplane.glb`, `atr72.glb`, `b789.glb`, `bell206.glb`, `c172.glb`, `citation2.glb`, `jet.glb`, `mq9.glb`, `ship.glb`, and `README.md`)
* `public/mic.svg`
* `src/data/fixtures/tomtom-flow-austin-12-935-1686.pbf` (retained `firms-viirs-noaa20-sample.csv`)

### Obsolete Tools & QA Harnesses Removed
* `tools/pano-pinhole.mjs`
* `tools/streetview-headings.mjs`
* `tools/streetview-panorama.mjs`
* `scripts/qa-heading-b3.mjs`
* `scripts/qa-sprites-b5.mjs`
* `scripts/qa-enrich-ambient.mjs`
* `scripts/qa-height-datum.mjs`
* `scripts/qa-failstate-b10.mjs`
* `scripts/qa-focus-evidence.mjs`
* `scripts/qa-floor-verify.mjs`

### Obsolete Demo Media Removed (from `docs/media/`)
* Deleted 16 obsolete GIFs/PNGs: `01-voice-annotate-zilker.gif`, `03-austin-cctv.gif`, `04-airport-distance.gif`, `05-traffic-to-cctv.gif`, `06-cockpit-ar.gif`, `07-helicopter-loops.gif`, `08-boneyard.gif`, `08-falcon9-replay.gif`, `12-switch-aircraft-cockpit.gif`, `14-iss-over-ukraine.gif`, `15-global-radio-layer.gif`, `hero-open-source-reveal.gif`, `open-source-survey.png`, `youtube-popular-videos.png`, `start-here/airport-ground-traffic-google-3d.gif`, `start-here/military-cockpit-dense-google-3d.gif`.
* Preserved 3 Cesium/layer assets: `01-style-sweep.gif`, `09-undersea-cables.gif`, `10-walking-route-flythrough.gif`.

---

## 3. Configuration & Dependency Pruning

1. **`package.json`**:
   - Removed obsolete npm dependencies: `@mapbox/vector-tile`, `pbf`, `satellite.js`, `ws`.
   - Removed dead npm scripts: `opensky:import`, `test:track`.
   - Updated package description to NISAR SAR Earth Observation Platform.
2. **`vite.config.js`**:
   - Pruned ~5,622 lines of dead proxy routes for removed CCTV, OpenSky, AIS, TomTom, and Pinokio endpoints using AST dead-code elimination.
   - Retained secure proxy routes for Google 3D Tiles, Re:Earth Mapterhorn terrain, USGS earthquakes, NASA FIRMS, and HUD summary.
3. **`.env.example`**:
   - Removed all credentials for OpenSky, TomTom, MarineTraffic, AISStream, RadioBrowser, and Twilio.
   - Retained active keys for Google Maps 3D Tiles, Cesium Ion, NASA FIRMS, and OpenAI HUD summary.
4. **`.github/workflows/ci.yml`**:
   - Removed references to deleted test harness files and deleted Pinokio environment checks.
5. **`Dockerfile` & `server.mjs`**:
   - Updated logging prefixes and branding from `[God's Eye View]` to `[NISAR]`.

---

## 4. UI Architecture & Stubbing

1. **`CockpitViewController` Stub in `src/ui.js`**:
   - Replaced 1,440+ lines of flight simulation and cockpit HUD manipulation with a null-object pattern controller that satisfies all caller invariants without throwing runtime exceptions.
2. **`loadingFeedback.js`**:
   - Removed military installation error-handling and retry logic while preserving live data aggregation for earthquakes and active fires.
3. **`docs/CURRENT-STATE.md`**:
   - Documented the first-run modal lifecycle and exclusive surface invariants.

---

## 5. Verification Results

| Verification Step | Command | Status | Output / Metrics |
|---|---|---|---|
| **Production Build** | `npm run build` | **PASSED** | 91 modules transformed in 1.12s; 0 bundle errors. |
| **Unit Test Suite** | `npm test` | **PASSED** | 1,189 passed, 1 skipped, 0 failed (9,283ms duration). |
| **Standalone Server** | `node scripts/verify-production-server.mjs` | **PASSED** | Security headers verified (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`); Keyless HUD summary degradation verified; Forest Intelligence sync & async jobs verified. |

---

## 6. Directory Structure Overview (259 Active Files)

```
gods-eye-view/
├── .github/workflows/ci.yml
├── docs/
│   ├── media/ (3 preserved demos: style sweep, undersea cables, camera flythrough)
│   ├── CURRENT-STATE.md
│   ├── KNOWN-ISSUES.md
│   └── PERFORMANCE.md
├── public/ (location.svg, logo.svg, pin.svg, visual-presets.svg)
├── scripts/ (23 verified QA scripts, setup doctor, production server verifier)
├── src/
│   ├── annotations/ (screen, world, hybrid annotation engines & resolvers)
│   ├── data/
│   │   ├── fixtures/ (firms-viirs-noaa20-sample.csv)
│   │   ├── local_data/ (dams, datacenters, natural earth, submarine cables)
│   │   ├── earthquakes.js
│   │   ├── firmsHeatmap.js, firmsCsv.js, firmsLabels.js
│   │   ├── forest*.js (forest intelligence analysis, risk, change detection)
│   │   ├── layerState.js, manager.js
│   │   └── terrainHeights.js, geoid.js
│   ├── overlays/ (world overlay label and bounding box rendering)
│   ├── styles/ (retro, anime, noir, snow, surveillance, thermal post-processing)
│   ├── camera.js, cameraVerbs.js, renderGovernor.js
│   ├── firstRunExperience.js, forestPanel.js, hud.js, splitFlap.js, ui.js
│   └── main.js
├── tools/ (cesium-render.html, cesium-render.mjs, sat-ortho.mjs)
├── .env.example, CHANGELOG.md, DATA_SOURCES.md, Dockerfile, index.html
├── package.json, package-lock.json, README.md, server.mjs, style.css, vite.config.js
```
