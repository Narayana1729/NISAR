import React, { useState, useRef, useEffect } from 'react';

// Simplified high-recognition global continental & regional coastline polygons in [lon, lat]
const WORLD_POLYGONS = [
  {
    name: 'North America',
    points: [
      [-168, 65], [-160, 71], [-140, 70], [-125, 70], [-110, 75], [-85, 74], [-78, 72], [-65, 62],
      [-55, 52], [-60, 45], [-70, 42], [-76, 35], [-81, 25], [-83, 27], [-85, 30], [-90, 29],
      [-97, 26], [-96, 19], [-88, 21], [-83, 10], [-78, 8], [-82, 8], [-92, 15], [-105, 20],
      [-110, 24], [-115, 30], [-122, 37], [-124, 48], [-135, 58], [-150, 60], [-162, 55], [-168, 65]
    ]
  },
  {
    name: 'Greenland',
    points: [
      [-72, 76], [-60, 81], [-35, 83], [-18, 76], [-22, 70], [-36, 65], [-44, 60], [-51, 64],
      [-54, 70], [-60, 75], [-72, 76]
    ]
  },
  {
    name: 'South America',
    points: [
      [-78, 9], [-72, 12], [-60, 9], [-50, 2], [-35, -6], [-38, -15], [-42, -23], [-48, -28],
      [-54, -35], [-62, -41], [-68, -54], [-74, -52], [-73, -40], [-71, -30], [-70, -18],
      [-77, -12], [-81, -5], [-79, 2], [-78, 9]
    ]
  },
  {
    name: 'Europe & Mediterranean',
    points: [
      [-10, 36], [-9, 43], [-2, 43], [-5, 48], [2, 51], [8, 54], [10, 58], [5, 62], [15, 69],
      [28, 71], [42, 68], [60, 68], [60, 50], [45, 42], [40, 42], [30, 46], [28, 41], [26, 40],
      [23.5, 40], [23, 38], [22, 37], [20, 39], [19, 42], [14, 45], [16, 40], [15, 38], [12, 42],
      [9, 44], [5, 43], [3, 42], [-2, 36], [-10, 36]
    ]
  },
  {
    name: 'UK & Ireland',
    points: [[-6, 50], [-5, 58], [-1, 58], [1, 51], [-6, 50]]
  },
  {
    name: 'Africa',
    points: [
      [-17, 15], [-13, 28], [-6, 36], [10, 37], [11, 33], [25, 32], [33, 31], [38, 22], [43, 12],
      [51, 12], [41, -2], [40, -15], [35, -25], [28, -33], [18, -35], [15, -22], [12, -6], [9, 4],
      [2, 6], [-8, 5], [-17, 15]
    ]
  },
  {
    name: 'Asia',
    points: [
      [26, 40], [36, 37], [35, 31], [48, 30], [56, 26], [60, 25], [68, 24], [73, 18], [77, 8],
      [81, 16], [88, 22], [93, 20], [98, 16], [100, 13], [104, 1], [104, 10], [109, 12], [108, 21],
      [115, 22], [122, 30], [120, 38], [126, 38], [129, 35], [131, 43], [141, 53], [160, 60],
      [178, 66], [140, 73], [105, 77], [70, 73], [60, 68], [60, 50], [45, 42], [26, 40]
    ]
  },
  {
    name: 'Japan',
    points: [[130, 31], [136, 34], [141, 41], [145, 44], [140, 40], [131, 34], [130, 31]]
  },
  {
    name: 'Indonesia & Maritime SE Asia',
    points: [[95, 5], [105, -6], [115, -8], [120, -8], [118, 4], [110, 2], [95, 5]]
  },
  {
    name: 'Australia',
    points: [
      [114, -22], [122, -17], [131, -12], [136, -12], [142, -11], [150, -22], [153, -28],
      [150, -37], [140, -38], [130, -32], [115, -34], [114, -22]
    ]
  },
  {
    name: 'Antarctica',
    points: [
      [-180, -72], [-120, -73], [-65, -64], [-58, -72], [-20, -72], [20, -70], [70, -68],
      [140, -66], [175, -72], [180, -85], [-180, -85], [-180, -72]
    ]
  }
];

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

export default function InteractiveWorldMap({
  events = [],
  selectedEventId = null,
  onSelectEvent = null,
  datasets = [],
  selectedBbox = null,
  onChangeBbox = null,
  rasterOverlays = [],
  onLocationInspect = null,
  initialView = null,
  height = 420
}) {
  // View state in degrees: center [lon, lat], spanLon (width of viewport in degrees)
  const [view, setView] = useState(() => {
    if (initialView && initialView.length === 4) {
      const [minLon, minLat, maxLon, maxLat] = initialView;
      const dLon = Math.max(maxLon - minLon, 0.05) * 1.45;
      return {
        lon: (minLon + maxLon) / 2,
        lat: (minLat + maxLat) / 2,
        spanLon: clamp(dLon, 0.04, 360)
      };
    }
    return { lon: 10, lat: 22, spanLon: 320 };
  });

  const [interactionMode, setInteractionMode] = useState('pan'); // 'pan' | 'draw_bbox'
  const [cursorCoord, setCursorCoord] = useState(null);
  const [dragStart, setDragStart] = useState(null);
  const [drawBoxStart, setDrawBoxStart] = useState(null);
  const [drawBoxCurrent, setDrawBoxCurrent] = useState(null);

  const svgRef = useRef(null);
  const aspect = 2.0; // width:height in SVG viewBox units
  const spanLon = view.spanLon;
  const spanLat = spanLon / aspect;

  // Sync view when initialView prop changes significantly
  useEffect(() => {
    if (initialView && initialView.length === 4) {
      const [minLon, minLat, maxLon, maxLat] = initialView;
      const dLon = Math.max((maxLon - minLon) * 1.5, (maxLat - minLat) * aspect * 1.5, 0.04);
      setView({
        lon: (minLon + maxLon) / 2,
        lat: (minLat + maxLat) / 2,
        spanLon: clamp(dLon, 0.03, 360)
      });
    }
  }, [initialView ? initialView.join(',') : '']);

  const fitToBbox = (bbox) => {
    if (!bbox || bbox.length !== 4) return;
    const [minLon, minLat, maxLon, maxLat] = bbox;
    const dLon = Math.max((maxLon - minLon) * 1.6, (maxLat - minLat) * aspect * 1.6, 0.04);
    setView({
      lon: (minLon + maxLon) / 2,
      lat: (minLat + maxLat) / 2,
      spanLon: clamp(dLon, 0.03, 360)
    });
  };

  const resetGlobalView = () => {
    setView({ lon: 10, lat: 20, spanLon: 330 });
  };

  const zoomBy = (factor) => {
    setView((prev) => ({
      ...prev,
      spanLon: clamp(prev.spanLon * factor, 0.02, 360)
    }));
  };

  // Convert client mouse event to [lon, lat]
  const clientToLonLat = (e) => {
    if (!svgRef.current) return [0, 0];
    const rect = svgRef.current.getBoundingClientRect();
    const fx = (e.clientX - rect.left) / rect.width;
    const fy = (e.clientY - rect.top) / rect.height;
    const lon = view.lon - spanLon / 2 + fx * spanLon;
    const lat = view.lat + spanLat / 2 - fy * spanLat;
    return [clamp(lon, -180, 180), clamp(lat, -89.9, 89.9)];
  };

  const handleMouseDown = (e) => {
    const [lon, lat] = clientToLonLat(e);
    if (interactionMode === 'draw_bbox') {
      setDrawBoxStart([lon, lat]);
      setDrawBoxCurrent([lon, lat]);
    } else {
      setDragStart({ x: e.clientX, y: e.clientY, lon: view.lon, lat: view.lat });
    }
  };

  const handleMouseMove = (e) => {
    const [lon, lat] = clientToLonLat(e);
    setCursorCoord([lon, lat]);

    if (interactionMode === 'draw_bbox' && drawBoxStart) {
      setDrawBoxCurrent([lon, lat]);
    } else if (dragStart && svgRef.current) {
      const rect = svgRef.current.getBoundingClientRect();
      const dxDeg = ((e.clientX - dragStart.x) / rect.width) * spanLon;
      const dyDeg = ((e.clientY - dragStart.y) / rect.height) * spanLat;
      setView((prev) => ({
        ...prev,
        lon: clamp(dragStart.lon - dxDeg, -180, 180),
        lat: clamp(dragStart.lat + dyDeg, -85, 85)
      }));
    }
  };

  const handleMouseUp = (e) => {
    if (interactionMode === 'draw_bbox' && drawBoxStart && drawBoxCurrent) {
      const minLon = Number(Math.min(drawBoxStart[0], drawBoxCurrent[0]).toFixed(4));
      const maxLon = Number(Math.max(drawBoxStart[0], drawBoxCurrent[0]).toFixed(4));
      const minLat = Number(Math.min(drawBoxStart[1], drawBoxCurrent[1]).toFixed(4));
      const maxLat = Number(Math.max(drawBoxStart[1], drawBoxCurrent[1]).toFixed(4));
      if (maxLon - minLon > 0.001 && maxLat - minLat > 0.001 && onChangeBbox) {
        onChangeBbox([minLon, minLat, maxLon, maxLat]);
      }
      setDrawBoxStart(null);
      setDrawBoxCurrent(null);
      setInteractionMode('pan');
    } else if (dragStart) {
      const movedPx = Math.hypot(e.clientX - dragStart.x, e.clientY - dragStart.y);
      if (movedPx < 4 && onLocationInspect && cursorCoord) {
        onLocationInspect({ lon: cursorCoord[0], lat: cursorCoord[1] });
      }
      setDragStart(null);
    }
  };

  // Compute dynamic graticule spacing based on zoom level
  const getGridStep = (span) => {
    if (span > 120) return 30;
    if (span > 40) return 10;
    if (span > 12) return 2;
    if (span > 3) return 0.5;
    if (span > 0.6) return 0.1;
    if (span > 0.15) return 0.02;
    return 0.005;
  };

  const gridStep = getGridStep(spanLon);
  const minViewLon = view.lon - spanLon / 2;
  const maxViewLon = view.lon + spanLon / 2;
  const minViewLat = view.lat - spanLat / 2;
  const maxViewLat = view.lat + spanLat / 2;

  const lonLines = [];
  for (
    let x = Math.ceil(minViewLon / gridStep) * gridStep;
    x <= maxViewLon;
    x += gridStep
  ) {
    lonLines.push(Number(x.toFixed(4)));
  }

  const latLines = [];
  for (
    let y = Math.ceil(minViewLat / gridStep) * gridStep;
    y <= maxViewLat;
    y += gridStep
  ) {
    latLines.push(Number(y.toFixed(4)));
  }

  const strokeScale = spanLon / 600;

  return (
    <div
      style={{
        backgroundColor: '#06101e',
        border: '1px solid #334155',
        borderRadius: '8px',
        overflow: 'hidden',
        position: 'relative',
        userSelect: 'none'
      }}
    >
      {/* Top Map Toolbar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.5rem 0.75rem',
          backgroundColor: '#0f172a',
          borderBottom: '1px solid #1e293b',
          flexWrap: 'wrap',
          gap: '0.5rem'
        }}
      >
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.55rem', fontSize: '0.75rem' }}
            onClick={() => zoomBy(0.6)}
            title="Zoom In"
          >
            ＋ Zoom In
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.55rem', fontSize: '0.75rem' }}
            onClick={() => zoomBy(1.65)}
            title="Zoom Out"
          >
            － Zoom Out
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '0.25rem 0.55rem', fontSize: '0.75rem' }}
            onClick={resetGlobalView}
          >
            🌍 Global View
          </button>
          {selectedBbox && (
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '0.25rem 0.55rem', fontSize: '0.75rem', color: '#38bdf8' }}
              onClick={() => fitToBbox(selectedBbox)}
            >
              🎯 Fit Study Area
            </button>
          )}
          {onChangeBbox && (
            <button
              type="button"
              className={`btn ${interactionMode === 'draw_bbox' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem' }}
              onClick={() => setInteractionMode((m) => (m === 'draw_bbox' ? 'pan' : 'draw_bbox'))}
            >
              {interactionMode === 'draw_bbox' ? '✎ Drag on Map to Draw Box...' : '⬚ Draw Study Area Box'}
            </button>
          )}
        </div>

        <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontFamily: 'monospace' }}>
          {cursorCoord
            ? `Lat: ${cursorCoord[1].toFixed(4)}° | Lon: ${cursorCoord[0].toFixed(4)}° | Span: ${spanLon.toFixed(2)}°`
            : `Center: ${view.lat.toFixed(2)}°, ${view.lon.toFixed(2)}° (EPSG:4326)`}
        </div>
      </div>

      {/* SVG Geospatial Viewport (y-axis inverted so North is up: y = -lat) */}
      <svg
        ref={svgRef}
        viewBox={`${minViewLon} ${-maxViewLat} ${spanLon} ${spanLat}`}
        style={{
          width: '100%',
          height: `${height}px`,
          display: 'block',
          cursor: interactionMode === 'draw_bbox' ? 'crosshair' : dragStart ? 'grabbing' : 'grab',
          background: 'radial-gradient(circle at 50% 50%, #0a192f 0%, #040d1a 100%)'
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={(e) => {
          e.preventDefault();
          zoomBy(e.deltaY > 0 ? 1.2 : 0.82);
        }}
      >
        {/* Graticule Grid */}
        {lonLines.map((x) => (
          <g key={`lon-${x}`}>
            <line
              x1={x}
              y1={-90}
              x2={x}
              y2={90}
              stroke="#1e293b"
              strokeWidth={strokeScale * 0.8}
            />
            <text
              x={x + strokeScale * 2}
              y={-maxViewLat + strokeScale * 12}
              fill="#475569"
              fontSize={strokeScale * 9}
              fontFamily="monospace"
            >
              {x}°
            </text>
          </g>
        ))}
        {latLines.map((y) => (
          <g key={`lat-${y}`}>
            <line
              x1={-180}
              y1={-y}
              x2={180}
              y2={-y}
              stroke={y === 0 ? '#334155' : '#1e293b'}
              strokeWidth={y === 0 ? strokeScale * 1.4 : strokeScale * 0.8}
            />
            <text
              x={minViewLon + strokeScale * 4}
              y={-y - strokeScale * 2}
              fill="#475569"
              fontSize={strokeScale * 9}
              fontFamily="monospace"
            >
              {y}°
            </text>
          </g>
        ))}

        {/* World Continental Vector Basemap */}
        {WORLD_POLYGONS.map((poly) => (
          <polygon
            key={poly.name}
            points={poly.points.map(([lon, lat]) => `${lon},${-lat}`).join(' ')}
            fill="#13263e"
            stroke="#2a4a6d"
            strokeWidth={strokeScale * 1.1}
          />
        ))}

        {/* Registered Dataset Footprints */}
        {datasets.map((ds) => {
          const b = ds.bbox_wgs84;
          if (!b || b.length !== 4) return null;
          const [minX, minY, maxX, maxY] = b;
          const isSynth = Boolean(ds.is_synthetic);
          return (
            <rect
              key={`ds-${ds.id}`}
              x={minX}
              y={-maxY}
              width={Math.max(maxX - minX, strokeScale * 3)}
              height={Math.max(maxY - minY, strokeScale * 3)}
              fill={isSynth ? 'rgba(245, 158, 11, 0.12)' : 'rgba(16, 185, 129, 0.16)'}
              stroke={isSynth ? '#f59e0b' : '#10b981'}
              strokeWidth={strokeScale * 1.4}
              strokeDasharray={isSynth ? `${strokeScale * 3},${strokeScale * 2}` : undefined}
            />
          );
        })}

        {/* Georeferenced Raster Overlays (Placed strictly at their geographic bounds_wgs84) */}
        {rasterOverlays.map((ov, idx) => {
          if (ov.visible === false) return null;
          const b = ov.bounds || ov.bounds_wgs84;
          if (!ov.url || !b || b.length !== 4) return null;
          const [minX, minY, maxX, maxY] = b;
          return (
            <image
              key={`ov-${idx}-${ov.url}`}
              href={ov.url}
              x={minX}
              y={-maxY}
              width={maxX - minX}
              height={maxY - minY}
              preserveAspectRatio="none"
              opacity={ov.opacity ?? 0.92}
            />
          );
        })}

        {/* Selected Study Area Bounding Box */}
        {selectedBbox && selectedBbox.length === 4 && (
          <rect
            x={selectedBbox[0]}
            y={-selectedBbox[3]}
            width={Math.max(selectedBbox[2] - selectedBbox[0], strokeScale * 2)}
            height={Math.max(selectedBbox[3] - selectedBbox[1], strokeScale * 2)}
            fill="rgba(56, 189, 248, 0.12)"
            stroke="#38bdf8"
            strokeWidth={strokeScale * 2.2}
          />
        )}

        {/* Active Dragged Bounding Box Preview */}
        {drawBoxStart && drawBoxCurrent && (
          <rect
            x={Math.min(drawBoxStart[0], drawBoxCurrent[0])}
            y={-Math.max(drawBoxStart[1], drawBoxCurrent[1])}
            width={Math.abs(drawBoxCurrent[0] - drawBoxStart[0])}
            height={Math.abs(drawBoxCurrent[1] - drawBoxStart[1])}
            fill="rgba(56, 189, 248, 0.25)"
            stroke="#38bdf8"
            strokeWidth={strokeScale * 2}
            strokeDasharray={`${strokeScale * 4},${strokeScale * 2}`}
          />
        )}

        {/* Curated Event Pins & Footprints */}
        {events.map((evt) => {
          if (!evt.bbox || evt.bbox.length !== 4) return null;
          const [minX, minY, maxX, maxY] = evt.bbox;
          const cx = evt.center ? evt.center[0] : (minX + maxX) / 2;
          const cy = evt.center ? evt.center[1] : (minY + maxY) / 2;
          const isSelected = evt.id === selectedEventId;
          const color =
            evt.data_readiness === 'verified_real'
              ? '#10b981'
              : evt.data_readiness === 'synthetic_demo'
              ? '#f59e0b'
              : '#64748b';

          return (
            <g
              key={evt.id}
              style={{ cursor: 'pointer' }}
              onClick={(e) => {
                e.stopPropagation();
                if (onSelectEvent) onSelectEvent(evt);
                fitToBbox(evt.bbox);
              }}
            >
              <rect
                x={minX}
                y={-maxY}
                width={Math.max(maxX - minX, strokeScale * 4)}
                height={Math.max(maxY - minY, strokeScale * 4)}
                fill={isSelected ? 'rgba(56, 189, 248, 0.2)' : 'transparent'}
                stroke={isSelected ? '#38bdf8' : color}
                strokeWidth={isSelected ? strokeScale * 2.4 : strokeScale * 1.4}
              />
              <circle
                cx={cx}
                cy={-cy}
                r={isSelected ? strokeScale * 7.5 : strokeScale * 5.5}
                fill={color}
                stroke="#0f172a"
                strokeWidth={strokeScale * 1.6}
              />
              <text
                x={cx + strokeScale * 9}
                y={-cy + strokeScale * 3}
                fill={isSelected ? '#38bdf8' : '#e2e8f0'}
                fontSize={strokeScale * 10.5}
                fontWeight={isSelected ? 'bold' : 'normal'}
                style={{ pointerEvents: 'none', textShadow: '0 1px 3px #000' }}
              >
                {evt.location || evt.name}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Bottom Legend Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.4rem 0.75rem',
          backgroundColor: '#0f172a',
          borderTop: '1px solid #1e293b',
          fontSize: '0.72rem',
          color: '#cbd5e1',
          flexWrap: 'wrap',
          gap: '0.75rem'
        }}
      >
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span>
            <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: '50%', backgroundColor: '#10b981', marginRight: 5 }} />
            Verified Real Satellite Data
          </span>
          <span>
            <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: '50%', backgroundColor: '#f59e0b', marginRight: 5 }} />
            Synthetic Demonstration Fixture
          </span>
          <span>
            <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: '50%', backgroundColor: '#64748b', marginRight: 5 }} />
            External Catalog / Unstaged AOI
          </span>
          <span>
            <span style={{ display: 'inline-block', width: 10, height: 10, border: '2px solid #38bdf8', marginRight: 5 }} />
            Selected Study Area (AOI)
          </span>
        </div>
        <span style={{ color: '#94a3b8' }}>
          Click event pins to zoom • Scroll to zoom • Use &ldquo;Draw Study Area Box&rdquo; to define custom AOI
        </span>
      </div>
    </div>
  );
}
