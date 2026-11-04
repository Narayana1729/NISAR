import React, { useState } from 'react';
import { apiClient } from '../services/api';
import { ENDPOINTS } from '../services/endpoints';

const PRODUCT_TYPES = [
  { value: 'sar_backscatter', label: 'SAR Backscatter Raster (GeoTIFF)' },
  { value: 'reference_water', label: 'Permanent Water Mask (GeoTIFF)' },
  { value: 'reference_flood', label: 'Reference Flood Map — Validation (GeoTIFF)' },
  { value: 'reference_disturbance', label: 'Reference Forest/Burn Disturbance — Validation (GeoTIFF)' },
  { value: 'reference_velocity', label: 'Reference Ice Velocity — Validation (GeoTIFF)' },
  { value: 'reference_displacement', label: 'Reference Ground Displacement — Validation (GeoTIFF)' },
  { value: 'dem', label: 'Digital Elevation Model / DEM (GeoTIFF)' },
  { value: 'forest_mask', label: 'Baseline Forest Cover Mask (GeoTIFF)' },
  { value: 'ice_velocity', label: 'Glacier Surface Velocity (GeoTIFF)' },
  { value: 'insar_displacement', label: 'InSAR Unwrapped LOS Displacement (GeoTIFF)' },
  { value: 'insar_coherence', label: 'InSAR Coherence 0–1 (GeoTIFF)' },
  { value: 'fire_detections', label: 'Active Fire Thermal Detections / FIRMS (GeoJSON)' },
  { value: 'exposure_assets', label: 'Exposure Assets: Roads, Settlements, Protected Areas (GeoJSON)' }
];

export default function DatasetUploadModal({ isOpen, onClose, defaultDomain = 'domain1', onUploaded }) {
  const [name, setName] = useState('');
  const [domain, setDomain] = useState(defaultDomain);
  const [productType, setProductType] = useState('sar_backscatter');
  const [sensor, setSensor] = useState('Sentinel-1 / NISAR');
  const [polarization, setPolarization] = useState('VV');
  const [acquisitionDate, setAcquisitionDate] = useState('');
  const [valueScale, setValueScale] = useState('power');
  const [units, setUnits] = useState('');
  const [source, setSource] = useState('');
  const [isSynthetic, setIsSynthetic] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a georeferenced GeoTIFF (.tif/.tiff) or GeoJSON (.geojson/.json) file.');
      return;
    }
    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('name', name.trim() || file.name);
      formData.append('domain', domain);
      formData.append('product_type', productType);
      if (sensor) formData.append('sensor', sensor);
      if (polarization) formData.append('polarization', polarization);
      if (acquisitionDate) formData.append('acquisition_date', acquisitionDate);
      if (valueScale) formData.append('value_scale', valueScale);
      if (units) formData.append('units', units);
      if (source) formData.append('source', source);
      formData.append('is_synthetic', isSynthetic ? 'true' : 'false');
      formData.append('file', file);

      const created = await apiClient(ENDPOINTS.DATASET_UPLOAD, {
        method: 'POST',
        body: formData
      });
      if (onUploaded) onUploaded(created);
      onClose();
    } catch (err) {
      setError(err.message || 'Upload failed. Ensure the file has valid CRS and georeferencing.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 23, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem'
      }}
    >
      <div
        style={{
          backgroundColor: '#0f172a',
          border: '1px solid #334155',
          borderRadius: '10px',
          width: '100%',
          maxWidth: '580px',
          padding: '1.5rem',
          maxHeight: '90vh',
          overflowY: 'auto'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ color: '#38bdf8', margin: 0 }}>Upload & Register Georeferenced Dataset</h3>
          <button type="button" className="btn btn-secondary" onClick={onClose} style={{ padding: '0.25rem 0.6rem' }}>
            ✕
          </button>
        </div>

        <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem' }}>
          Files are inspected with <code>rasterio</code> / GeoJSON parser on upload to verify CRS, bounding box,
          dimensions, and nodata values. Ungeoreferenced images are rejected.
        </p>

        {error && (
          <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#fca5a5', padding: '0.6rem', borderRadius: '6px', fontSize: '0.8rem', marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div>
            <label style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Dataset Title *</label>
            <input
              type="text"
              required
              placeholder="e.g., Sentinel-1A RTC Post-Flood Observation"
              className="form-select"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Target Domain *</label>
              <select className="form-select" value={domain} onChange={(e) => setDomain(e.target.value)}>
                <option value="domain1">1. Floods & Wetlands</option>
                <option value="domain2">2. Forests & Wildfires</option>
                <option value="domain3">3. Earthquakes & Ground Deformation</option>
                <option value="domain4">4. Agriculture & Soil Conditions</option>
                <option value="domain5">5. Glaciers & Snow/Ice</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Product Type *</label>
              <select className="form-select" value={productType} onChange={(e) => setProductType(e.target.value)}>
                {PRODUCT_TYPES.map((pt) => (
                  <option key={pt.value} value={pt.value}>{pt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Acquisition Date</label>
              <input
                type="date"
                className="form-select"
                value={acquisitionDate}
                onChange={(e) => setAcquisitionDate(e.target.value)}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Sensor</label>
              <input
                type="text"
                className="form-select"
                placeholder="e.g. Sentinel-1A / NISAR"
                value={sensor}
                onChange={(e) => setSensor(e.target.value)}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Polarization / Band</label>
              <input
                type="text"
                className="form-select"
                placeholder="e.g. VV, HV, LOS"
                value={polarization}
                onChange={(e) => setPolarization(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Radiometric Scale</label>
              <select className="form-select" value={valueScale} onChange={(e) => setValueScale(e.target.value)}>
                <option value="power">Linear Power (gamma0 / sigma0)</option>
                <option value="db">Decibels (dB)</option>
                <option value="amplitude">Amplitude</option>
                <option value="other">Other / Geophysical Units</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Units / Citation Source</label>
              <input
                type="text"
                className="form-select"
                placeholder="e.g. Copernicus / ASF HyP3 / NASA FIRMS"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Georeferenced File (.tif, .tiff, .geojson, .json) *</label>
            <input
              type="file"
              accept=".tif,.tiff,.geojson,.json"
              className="form-select"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: '#fcd34d', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={isSynthetic}
              onChange={(e) => setIsSynthetic(e.target.checked)}
            />
            Mark this file as a Synthetic / Simulated Test Fixture (not a real Earth observation)
          </label>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={uploading}>
              {uploading ? 'Inspecting & Uploading...' : 'Upload & Register Dataset'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
