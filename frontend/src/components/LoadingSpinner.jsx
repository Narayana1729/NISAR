import React from 'react';

export default function LoadingSpinner({ size = 28, text = 'Loading...' }) {
  return (
    <div className="spinner-wrapper">
      <div
        className="spinner-circle"
        style={{ width: `${size}px`, height: `${size}px` }}
      />
      {text && <span className="spinner-text">{text}</span>}
    </div>
  );
}
