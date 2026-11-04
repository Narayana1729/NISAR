import React from 'react';

export default function MetricsPanel({ title = 'Domain Metrics', metrics = [] }) {
  return (
    <div className="metrics-panel">
      <h4 className="metrics-title">{title}</h4>
      <div className="metrics-grid">
        {metrics.length === 0 ? (
          <p className="no-metrics">No metrics available yet.</p>
        ) : (
          metrics.map((item, idx) => (
            <div key={idx} className="metric-item">
              <span className="metric-label">{item.label}</span>
              <span className="metric-value">{item.value}</span>
              {item.unit && <span className="metric-unit">{item.unit}</span>}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
