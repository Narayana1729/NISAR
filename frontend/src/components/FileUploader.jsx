import React, { useRef } from 'react';

export default function FileUploader({ onFileSelect, accept = '.h5,.tif,.tiff,.nc,.zip', label = 'Upload SAR Product' }) {
  const fileInputRef = useRef(null);

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect && onFileSelect(e.target.files[0]);
    }
  };

  return (
    <div className="file-uploader-box">
      <label className="uploader-label">{label}</label>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        className="uploader-input"
      />
      <p className="uploader-hint">Accepted formats: {accept}</p>
    </div>
  );
}
