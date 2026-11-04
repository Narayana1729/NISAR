import React, { useState } from 'react';
import InteractiveWorldMap from './InteractiveWorldMap';

export default function BeforeAfterViewer({
  beforeUrl,
  afterUrl,
  overlayUrl,
  changeMapUrl = null,
  validationOverlayUrl = null,
  exposureOverlayUrl = null,
  beforeLabel = 'Baseline / Before',
  afterLabel = 'Observation / After',
  overlayLabel = 'Detected Change Overlay',
  boundsWgs84 = null,
  legend = [],
  inspector = null
}) {
  const [viewMode, setViewMode] = useState('swipe'); // 'swipe' | 'georef_map'
  const [sliderPos, setSliderPos] = useState(50);
  const [activeOverlay, setActiveOverlay] = useState('change'); // 'none' | 'change' | 'delta' | 'validation' | 'exposure'
  const [zoom, setZoom] = useState(1);
  const [inspectedPoint, setInspectedPoint] = useState(null);

  const resolveActiveOverlayUrl = () => {
    if (activeOverlay === 'none') return null;
    if (activeOverlay === 'change') return overlayUrl;
    if (activeOverlay === 'delta') return changeMapUrl;
    if (activeOverlay === 'validation') return validationOverlayUrl;
    if (activeOverlay === 'exposure') return exposureOverlayUrl;
    return overlayUrl;
  };

  const currentOverlayUrl = resolveActiveOverlayUrl();

  const handleViewportMouseMove = (e) => {
    if (!inspector || !inspector.layers) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const fx = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const fy = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

    const gRows = inspector.grid_rows || 24;
    const gCols = inspector.grid_cols || 24;
    const rIdx = Math.min(gRows - 1, Math.floor(fy * gRows));
    const cIdx = Math.min(gCols - 1, Math.floor(fx * gCols));

    const pixelRow = Math.round(fy * (inspector.raster_height || gRows));
    const pixelCol = Math.round(fx * (inspector.raster_width || gCols));

    let lon = null;
    let lat = null;
    const b = boundsWgs84 || inspector.bounds_wgs84;
    if (b && b.length === 4) {
      lon = b[0] + fx * (b[2] - b[0]);
      lat = b[3] - fy * (b[3] - b[1]);
    }

    const values = {};
    Object.entries(inspector.layers).forEach(([k, grid]) => {
      if (grid && grid[rIdx] && grid[rIdx][cIdx] !== undefined) {
        values[k] = grid[rIdx][cIdx];
      }
    });

    setInspectedPoint({
      pixelRow,
      pixelCol,
      lon,
      lat,
      values
    });
  };

  const effectiveBounds = boundsWgs84 || inspector?.bounds_wgs84 || null;
  const mapOverlays = [];
  if (afterUrl && effectiveBounds) {
    mapOverlays.push({ url: afterUrl, bounds: effectiveBounds, opacity: 0.9, label: afterLabel });
  } else if (beforeUrl && effectiveBounds) {
    mapOverlays.push({ url: beforeUrl, bounds: effectiveBounds, opacity: 0.9, label: beforeLabel });
  }
  if (currentOverlayUrl && effectiveBounds) {
    mapOverlays.push({ url: currentOverlayUrl, bounds: effectiveBounds, opacity: 0.92, label: overlayLabel });
  }

  return (
    <div className="before-after-container" style={{ border: '1px solid #334155', borderRadius: '8px', padding: '0.75rem', backgroundColor: '#0f172a' }}>
      {/* Top Controls Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.6rem' }}>
        <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className={`btn ${viewMode === 'swipe' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem' }}
            onClick={() => setViewMode('swipe')}
          >
            ⇆ Synchronized Swipe
          </button>
          {effectiveBounds && (
            <button
              type="button"
              className={`btn ${viewMode === 'georef_map' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem' }}
              onClick={() => setViewMode('georef_map')}
            >
              🗺️ Georeferenced Map View
            </button>
          )}
          {viewMode === 'swipe' && (
            <>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}
                onClick={() => setZoom((z) => Math.min(3, Number((z + 0.5).toFixed(1))))}
              >
                🔍+ ({zoom}x)
              </button>
              {zoom > 1 && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}
                  onClick={() => setZoom(1)}
                >
                  Reset 1x
                </button>
              )}
            </>
          )}
        </div>

        {/* Overlay Selector */}
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap', fontSize: '0.75rem' }}>
          <span style={{ color: '#94a3b8' }}>Overlay Layer:</span>
          <select
            className="form-select"
            style={{ width: 'auto', padding: '0.2rem 0.5rem', fontSize: '0.75rem', marginTop: 0 }}
            value={activeOverlay}
            onChange={(e) => setActiveOverlay(e.target.value)}
          >
            {overlayUrl && <option value="change">{overlayLabel}</option>}
            {changeMapUrl && <option value="delta">Backscatter Difference Map (ΔdB)</option>}
            {validationOverlayUrl && <option value="validation">Validation Agreement & Error Map</option>}
            {exposureOverlayUrl && <option value="exposure">Exposed Infrastructure & Assets</option>}
            <option value="none">None (Raw Imagery Only)</option>
          </select>
        </div>
      </div>

      {/* Labels Row */}
      <div className="viewer-labels" style={{ marginBottom: '0.35rem' }}>
        <span>◀ {beforeLabel}</span>
        {effectiveBounds && (
          <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>
            Bounds: [{effectiveBounds.map((n) => Number(n).toFixed(3)).join(', ')}] WGS84
          </span>
        )}
        <span>{afterLabel} ▶</span>
      </div>

      {/* Main Viewport */}
      {viewMode === 'georef_map' && effectiveBounds ? (
        <InteractiveWorldMap
          selectedBbox={effectiveBounds}
          initialView={effectiveBounds}
          rasterOverlays={mapOverlays}
          height={360}
          onLocationInspect={({ lon, lat }) => {
            if (!inspector || !effectiveBounds) return;
            const fx = Math.max(0, Math.min(1, (lon - effectiveBounds[0]) / (effectiveBounds[2] - effectiveBounds[0])));
            const fy = Math.max(0, Math.min(1, (effectiveBounds[3] - lat) / (effectiveBounds[3] - effectiveBounds[1])));
            const rIdx = Math.min((inspector.grid_rows || 24) - 1, Math.floor(fy * (inspector.grid_rows || 24)));
            const cIdx = Math.min((inspector.grid_cols || 24) - 1, Math.floor(fx * (inspector.grid_cols || 24)));
            const values = {};
            Object.entries(inspector.layers || {}).forEach(([k, g]) => {
              if (g?.[rIdx]?.[cIdx] !== undefined) values[k] = g[rIdx][cIdx];
            });
            setInspectedPoint({
              pixelRow: Math.round(fy * (inspector.raster_height || 24)),
              pixelCol: Math.round(fx * (inspector.raster_width || 24)),
              lon,
              lat,
              values
            });
          }}
        />
      ) : (
        <div
          className="viewer-viewport"
          onMouseMove={handleViewportMouseMove}
          style={{ overflow: 'hidden', cursor: 'crosshair' }}
        >
          <div style={{ width: '100%', height: '100%', transform: `scale(${zoom})`, transformOrigin: 'center center', position: 'relative' }}>
            {/* Layer 1: Left / Baseline */}
            <div className="viewport-placeholder before-layer">
              {beforeUrl ? (
                <img src={beforeUrl} alt={beforeLabel} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              ) : afterUrl ? (
                <img src={afterUrl} alt={afterLabel} style={{ width: '100%', height: '100%', objectFit: 'contain', filter: 'grayscale(70%)' }} />
              ) : (
                <div className="placeholder-content">Run analysis to render georeferenced SAR imagery</div>
              )}
            </div>

            {/* Layer 2: Right / Event (clipped by slider) */}
            <div
              className="viewport-placeholder after-layer"
              style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
            >
              {afterUrl ? (
                <img src={afterUrl} alt={afterLabel} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              ) : (
                <div className="placeholder-content">Observation Imagery / Layer B</div>
              )}
            </div>

            {/* Layer 3: Classified / Validation / Exposure Overlay */}
            {currentOverlayUrl && (
              <div
                className="viewport-placeholder overlay-layer"
                style={{ pointerEvents: 'none', clipPath: `inset(0 0 0 ${sliderPos}%)` }}
              >
                <img src={currentOverlayUrl} alt={overlayLabel} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
            )}
          </div>

          <input
            type="range"
            min="0"
            max="100"
            value={sliderPos}
            onChange={(e) => setSliderPos(Number(e.target.value))}
            className="viewer-slider"
          />
        </div>
      )}

      {/* Interactive Pixel / Location Inspector Readout */}
      {inspectedPoint && (
        <div
          style={{
            marginTop: '0.5rem',
            padding: '0.45rem 0.75rem',
            backgroundColor: '#1e293b',
            borderRadius: '6px',
            fontSize: '0.75rem',
            fontFamily: 'monospace',
            color: '#e2e8f0',
            display: 'flex',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.5rem'
          }}
        >
          <span>
            📍 <strong>Location Inspector:</strong>{' '}
            {inspectedPoint.lat !== null && inspectedPoint.lon !== null
              ? `${inspectedPoint.lat.toFixed(4)}°N, ${inspectedPoint.lon.toFixed(4)}°E`
              : ''}{' '}
            (Row {inspectedPoint.pixelRow}, Col {inspectedPoint.pixelCol})
          </span>
          <span style={{ color: '#38bdf8' }}>
            {Object.entries(inspectedPoint.values).map(([k, v]) => (
              <span key={k} style={{ marginLeft: '0.75rem' }}>
                {k}: <strong>{v !== null ? v : 'nodata'}</strong>
              </span>
            ))}
          </span>
        </div>
      )}

      {/* Scientific Legend */}
      {legend && legend.length > 0 && (
        <div
          style={{
            marginTop: '0.5rem',
            padding: '0.45rem 0.75rem',
            backgroundColor: '#091326',
            border: '1px solid #1e293b',
            borderRadius: '6px',
            display: 'flex',
            gap: '1rem',
            flexWrap: 'wrap',
            alignItems: 'center',
            fontSize: '0.75rem'
          }}
        >
          <strong style={{ color: '#94a3b8' }}>Legend:</strong>
          {legend.map((item, idx) => (
            <span key={idx} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#e2e8f0' }}>
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: '3px',
                  backgroundColor: item.color,
                  display: 'inline-block',
                  border: '1px solid rgba(255,255,255,0.25)'
                }}
              />
              {item.label} <span style={{ color: '#94a3b8' }}>({item.unit})</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
