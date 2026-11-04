# Performance Baseline & Render Governor

This document records the performance architecture and baseline metrics for the CesiumJS 3D globe and overlay rendering system.

## Render Governor Invariants

The platform uses an explicit render governor (`src/renderGovernor.js`) to eliminate unnecessary WebGL draw calls and prevent battery exhaustion:

1. **Demand-Driven Frames**: When the camera is stationary and no animated layers are active, the render loop sleeps.
2. **Hold / Release Semantics**: Per-frame animators (smooth camera flights, split-flap transitions, pulse shaders) register a hold with `renderGovernor.acquireHold()`. The governor renders at display refresh rate until the hold is released.
3. **Discrete Updates**: Layer toggles, data fetches, and user interactions call `governorRequestRender()` to schedule a single repaint.
4. **Background Throttling**: When the browser tab loses visibility, all rendering is suspended.

## Baseline Hardware Measurements

Captured on an isolated browser session at 1440 x 900 resolution:

| Metric | Measured Baseline |
|---|---|
| **Cold Startup to App Ready** | ~780 ms |
| **Initial Settle Time** | ~1,950 ms |
| **Memory (Heap) at Rest** | ~95 MiB |
| **Frame Rate (Active Flight / Pan)** | 60 FPS |
| **Idle GPU Utilization** | < 2% |

## Layer Optimization Gates

* **Vector decluttering**: Vector entities use distance-based alpha attenuation and screen-space collision checks.
* **Canvas overlay blending**: Scientific overlays render to dedicated 2D canvas planes with integer coordinate snapping to avoid sub-pixel blurring.
