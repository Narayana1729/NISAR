import React from 'react';

export default function ProcessingStatus({ status = 'idle', progress = 0, message = '' }) {
  const statusColorMap = {
    idle: '#6b7280',
    pending: '#d97706',
    processing: '#2563eb',
    completed: '#059669',
    failed: '#dc2626'
  };

  return (
    <div className="processing-status-card">
      <div className="status-header">
        <span className="status-label">Status:</span>
        <span
          className="status-badge"
          style={{ backgroundColor: statusColorMap[status] || '#6b7280' }}
        >
          {status.toUpperCase()}
        </span>
      </div>
      {status === 'processing' && (
        <div className="progress-container">
          <div className="progress-bar" style={{ width: `${progress}%` }}></div>
          <span className="progress-text">{progress}%</span>
        </div>
      )}
      {message && <p className="status-message">{message}</p>}
    </div>
  );
}
