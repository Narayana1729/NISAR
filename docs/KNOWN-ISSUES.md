# Known Issues & Technical Constraints

Updated: November 2, 2026

## Active Runtime Constraints

### 1. Large Vector Layer Entity Density on Global Zooms
* **Status**: Open (documented constraint)
* **Context**: Enabling all local infrastructure layers simultaneously (`local-dams`, `local-datacenters`, `telegeography-submarine-cables`) loads over 5,500 vector entities. When zoomed out to a full-Earth view, this can cause frame rate dips on low-powered GPUs.
* **Mitigation**: Screen-space clustering and distance-based LOD culling are active. Future domain builds should defer dense local entities until the camera reaches regional altitudes (< 3,000 km).

### 2. Upstream Terrain Height Fallback
* **Status**: Mitigated
* **Context**: The `/api/terrain/heights` proxy queries the Re:Earth Mapterhorn quantized-mesh endpoint. During upstream network timeouts or rate limits, the client gracefully falls back to local EGM96 geoid undulations.

### 3. Headless WebGL Mock Environment in Node Tests
* **Status**: Handled
* **Context**: Unit tests that require full WebGL context are executed with isolated headless stubs or verified through Chromium puppeteer harnesses (`scripts/qa-perf.mjs`, `scripts/qa-overlay-baseline.mjs`). One mock environment fixture is marked skipped in Node CLI runs.
