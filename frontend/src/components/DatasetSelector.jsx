import React from 'react';

export default function DatasetSelector({ datasets = [], selectedId, onSelect, label = 'Select Dataset' }) {
  const selectedDs = datasets.find((d) => d.id === selectedId);

  return (
    <div className="dataset-selector-wrapper">
      <label className="input-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{label}</span>
        {selectedDs && (
          <span
            style={{
              fontSize: '0.68rem',
              padding: '0.1rem 0.45rem',
              borderRadius: '4px',
              backgroundColor: selectedDs.is_synthetic ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
              color: selectedDs.is_synthetic ? '#fcd34d' : '#6ee7b7',
              border: `1px solid ${selectedDs.is_synthetic ? '#d97706' : '#059669'}`
            }}
          >
            {selectedDs.is_synthetic ? 'SYNTHETIC FIXTURE' : 'REAL OBSERVATION'}
          </span>
        )}
      </label>
      <select
        value={selectedId || ''}
        onChange={(e) => onSelect && onSelect(e.target.value)}
        className="form-select"
      >
        <option value="">-- None / Choose a Dataset --</option>
        {datasets.map((ds) => {
          const tag = ds.is_synthetic ? '[SYNTHETIC] ' : '[REAL] ';
          const dateStr = ds.acquisition_date ? ` (${ds.acquisition_date})` : '';
          const polStr = ds.polarization ? ` [${ds.polarization}]` : '';
          return (
            <option key={ds.id} value={ds.id}>
              {tag}{ds.name || ds.id}{polStr}{dateStr}
            </option>
          );
        })}
      </select>
      {selectedDs && (
        <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '0.25rem', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <span>CRS: <code>{selectedDs.crs || 'N/A'}</code></span>
          {selectedDs.width && selectedDs.height && (
            <span>Grid: {selectedDs.width}×{selectedDs.height}px</span>
          )}
          {selectedDs.acquisition_date && (
            <span>Date: {selectedDs.acquisition_date}</span>
          )}
        </div>
      )}
    </div>
  );
}
