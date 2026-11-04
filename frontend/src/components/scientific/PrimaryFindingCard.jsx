import React from 'react';

/**
 * PrimaryFindingCard — High-visibility scientific finding display
 * Adapted from NASA1 (#earthtrend-panel finding card and #forest-panel)
 */
export default function PrimaryFindingCard({
  verdict,
  status = 'verified', // 'verified' | 'partial' | 'demo'
  statusLabel = 'VERIFIED REAL SATELLITE EVENT',
  footprintText = 'Point / Area Footprint: Sentinel-1 SAR 10m Resolution Grid',
  findingText,
  kpis = [], // [{ label, value, unit }]
  cautionText = null,
}) {
  const getBadgeClass = () => {
    if (status === 'verified') return 'badge-verified';
    if (status === 'partial') return 'badge-partial';
    return 'badge-demo';
  };

  return (
    <div className="gev-finding-card">
      <div className="gev-verdict-title">
        <span className="text-sm font-bold tracking-wide">{verdict}</span>
        <span className={`gev-badge-pill ${getBadgeClass()}`}>{statusLabel}</span>
      </div>

      <div className="flex flex-col gap-1 text-[10px] font-mono text-gray-400 mb-2">
        <span className="text-cyan-400/90">{footprintText}</span>
      </div>

      <p className="text-xs text-gray-200 leading-relaxed font-sans mb-3">
        {findingText}
      </p>

      {kpis.length > 0 && (
        <div className="gev-kpi-grid">
          {kpis.map((kpi, idx) => (
            <div key={idx} className="gev-kpi-card">
              <span className="gev-kpi-label">{kpi.label}</span>
              <div className="flex items-baseline">
                <span className="gev-kpi-val">{kpi.value}</span>
                {kpi.unit && <span className="gev-kpi-unit">{kpi.unit}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {cautionText && (
        <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5 text-[11px] text-amber-300/90 font-mono mt-2">
          <span className="text-amber-400 font-bold">ℹ</span>
          <span>{cautionText}</span>
        </div>
      )}
    </div>
  );
}
