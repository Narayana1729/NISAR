import React, { useState } from 'react';

/**
 * StudyAreaDock — Bottom command dock for study area selection and fast navigation
 * Derived from NASA1 (#command-dock, #location-bar, .location-pills, .location-city-row)
 */
export default function StudyAreaDock({
  activeStudyAreaId,
  onSelectStudyArea,
  searchQuery,
  onSearchChange,
  onSearchSubmit,
}) {
  const [trayExpanded, setTrayExpanded] = useState(false);

  const STUDY_AREAS = [
    {
      id: 'lake-karla',
      domainId: 'domain1',
      label: 'Lake Karla, Greece',
      domain: 'Domain 1: Floods',
      badge: 'Flood Inundation',
      bbox: [22.7966, 39.4475, 22.9537, 39.5824],
      icon: '🌊',
    },
    {
      id: 'para-br163',
      domainId: 'domain2',
      label: 'Pará BR-163, Brazil',
      domain: 'Domain 2: Forests',
      badge: 'Canopy Loss',
      bbox: [-55.2311, -6.6989, -55.2044, -6.6722],
      icon: '🌲',
    },
    {
      id: 'tyrnavos',
      domainId: 'domain3',
      label: 'Tyrnavos Basin, Greece',
      domain: 'Domain 3: Earthquakes',
      badge: 'Mw 6.3 InSAR',
      bbox: [22.02, 39.62, 22.32, 39.84],
      icon: '⚡',
    },
    {
      id: 'thessaly-plains',
      domainId: 'domain4',
      label: 'Thessaly Plains, Greece',
      domain: 'Domain 4: Agriculture',
      badge: 'Crop Dynamics',
      bbox: [22.1, 39.4, 22.6, 39.8],
      icon: '🌾',
    },
    {
      id: 'jakobshavn',
      domainId: 'domain5',
      label: 'Jakobshavn Isbræ, Greenland',
      domain: 'Domain 5: Glaciers',
      badge: 'Outlet Velocity',
      bbox: [-49.92, 69.13, -49.62, 69.23],
      icon: '❄️',
    },
  ];

  return (
    <div className="gev-command-dock">
      {/* Location / Study Area Selector Button */}
      <button
        type="button"
        onClick={() => setTrayExpanded(!trayExpanded)}
        className={`gev-dock-btn ${trayExpanded ? 'active' : ''}`}
        title="Toggle Study Area & Place Navigator"
      >
        <img src="/location.svg" alt="" className="w-3.5 h-3.5 opacity-80" />
        <span>STUDY REGIONS</span>
        <span className="text-[10px] text-cyan-400">{trayExpanded ? '▼' : '▲'}</span>
      </button>

      {/* Popover Tray with Quick Study Area Pills */}
      {trayExpanded && (
        <div className="absolute bottom-14 left-1/2 -translate-x-1/2 w-[92vw] max-w-[680px] bg-[#0c0c14]/95 backdrop-blur-xl border border-white/10 rounded-2xl p-3 shadow-2xl flex flex-col gap-2.5 z-50">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-cyan-400 tracking-wider">
                VERIFIED STUDY LOCATIONS
              </span>
              <span className="text-[9px] font-mono text-gray-400 bg-white/5 px-2 py-0.5 rounded">
                REAL SATELLITE TILES
              </span>
            </div>
            <button
              type="button"
              onClick={() => setTrayExpanded(false)}
              className="text-gray-400 hover:text-white text-xs font-mono px-1.5 py-0.5"
            >
              ✕
            </button>
          </div>

          {/* Quick study area buttons */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
            {STUDY_AREAS.map((sa) => {
              const isSelected = activeStudyAreaId === sa.id;
              return (
                <button
                  key={sa.id}
                  type="button"
                  onClick={() => {
                    onSelectStudyArea(sa);
                    setTrayExpanded(false);
                  }}
                  className={`flex flex-col text-left p-2.5 rounded-lg border transition-all ${
                    isSelected
                      ? 'bg-cyan-500/20 border-cyan-500/50 text-white shadow-[0_0_12px_rgba(0,212,255,0.2)]'
                      : 'bg-white/5 border-white/5 text-gray-300 hover:bg-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="font-mono text-xs font-semibold flex items-center gap-1.5">
                      <span>{sa.icon}</span>
                      <span>{sa.label}</span>
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-1 text-[9.5px] font-mono text-gray-400">
                    <span>{sa.domain}</span>
                    <span className="text-cyan-400">{sa.badge}</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Global Search Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (onSearchSubmit) onSearchSubmit();
            }}
            className="flex items-center gap-2 mt-1 pt-2 border-t border-white/10"
          >
            <input
              type="text"
              value={searchQuery || ''}
              onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
              placeholder="Search any coordinate or location (e.g. 'Lake Karla', 'Thessaly')..."
              className="flex-1 bg-black/50 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-500 font-mono focus:outline-none focus:border-cyan-500"
            />
            <button
              type="submit"
              className="bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 px-3 py-1.5 rounded-lg text-xs font-mono transition-all"
            >
              FLY TO
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
