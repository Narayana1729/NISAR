import React, { useState } from 'react';
import CesiumGlobe from './CesiumGlobe';
import InteractiveWorldMap from '../InteractiveWorldMap';

/**
 * SharedMap — Unified geospatial viewport for Dancing with the SARs
 * Supports seamless switching between a photorealistic 3D Globe (Cesium)
 * and the 2D projection map (InteractiveWorldMap with raster overlays).
 */
export default function SharedMap({
  events = [],
  selectedEventId = null,
  onSelectEvent = null,
  datasets = [],
  selectedBbox = null,
  onChangeBbox = null,
  rasterOverlays = [],
  onLocationInspect = null,
  height = 500,
  defaultMode = '3d', // '3d' | '2d'
}) {
  const [mapMode, setMapMode] = useState(defaultMode);

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-white/10 bg-[#0a0a0f] shadow-2xl">
      {/* Top Floating View Switcher & Map Controls */}
      <div className="absolute top-3 right-3 z-30 flex items-center gap-2 bg-[#0c0c14]/85 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 shadow-lg">
        <span className="text-[10px] font-mono text-gray-400 tracking-wider uppercase mr-1">
          VIEWPORT:
        </span>
        <button
          type="button"
          onClick={() => setMapMode('3d')}
          className={`px-2.5 py-1 text-xs font-mono rounded transition-all flex items-center gap-1.5 ${
            mapMode === '3d'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_8px_rgba(0,212,255,0.25)]'
              : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent'
          }`}
          title="Switch to 3D Photorealistic Globe"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          3D GLOBE
        </button>
        <button
          type="button"
          onClick={() => setMapMode('2d')}
          className={`px-2.5 py-1 text-xs font-mono rounded transition-all flex items-center gap-1.5 ${
            mapMode === '2d'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_8px_rgba(0,212,255,0.25)]'
              : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent'
          }`}
          title="Switch to 2D Projection Map"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          2D MAP
        </button>
      </div>

      {/* Render 3D Globe or 2D Map */}
      {mapMode === '3d' ? (
        <CesiumGlobe
          bbox={selectedBbox}
          events={events}
          selectedEventId={selectedEventId}
          onSelectEvent={onSelectEvent}
          rasterOverlays={rasterOverlays}
          height={height}
        />
      ) : (
        <InteractiveWorldMap
          events={events}
          selectedEventId={selectedEventId}
          onSelectEvent={onSelectEvent}
          datasets={datasets}
          selectedBbox={selectedBbox}
          onChangeBbox={onChangeBbox}
          rasterOverlays={rasterOverlays}
          onLocationInspect={onLocationInspect}
          height={height}
        />
      )}
    </div>
  );
}
