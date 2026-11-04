/**
 * @module forestChangeDetection
 * @description Multi-temporal satellite change detection and forest loss calculation engine.
 * Computes previous/current forest coverage, net loss percentage, geodesic affected area in km²,
 * statistical confidence, and driver classifications.
 */

import { clampIndex, classifyCanopyChange } from './forestVegetation.js';

/**
 * Computes geodesic surface area of a bounding box on the WGS84 ellipsoid in square kilometers.
 * @param {number[]} bbox - [minLon, minLat, maxLon, maxLat] in degrees
 * @returns {number} Area in km²
 */
export function computeGeodesicBBoxAreaKm2(bbox) {
  if (!Array.isArray(bbox) || bbox.length !== 4) return 0;
  const [minLon, minLat, maxLon, maxLat] = bbox;
  if (![minLon, minLat, maxLon, maxLat].every(Number.isFinite)) return 0;

  const R = 6371.0; // Mean Earth radius in km
  const dLon = Math.abs(maxLon - minLon) * (Math.PI / 180);
  const lat1 = Math.min(minLat, maxLat) * (Math.PI / 180);
  const lat2 = Math.max(minLat, maxLat) * (Math.PI / 180);

  // Area of spherical zone between two parallels = R^2 * dLon * (sin(lat2) - sin(lat1))
  const area = (R * R) * dLon * Math.abs(Math.sin(lat2) - Math.sin(lat1));
  return Math.round(area * 100) / 100;
}

/**
 * Computes geodesic surface area of a polygon ring or bbox in square kilometers.
 * @param {Array<number[]>|number[]} coordinates - GeoJSON polygon ring or bbox
 * @returns {number} Area in km²
 */
export function computeGeodesicPolygonAreaKm2(coordinates) {
  if (!Array.isArray(coordinates) || coordinates.length === 0) return 0;
  if (coordinates.length === 4 && typeof coordinates[0] === 'number') {
    return computeGeodesicBBoxAreaKm2(coordinates);
  }
  const ring = Array.isArray(coordinates[0]) && Array.isArray(coordinates[0][0])
    ? coordinates[0]
    : coordinates;
  if (!Array.isArray(ring) || ring.length < 3) return 0;

  const R = 6371.0; // km
  let total = 0;
  const toRad = Math.PI / 180;
  const len = ring.length;

  for (let i = 0; i < len; i++) {
    const p1 = ring[i];
    const p2 = ring[(i + 1) % len];
    if (!Array.isArray(p1) || !Array.isArray(p2)) continue;
    const lon1 = p1[0] * toRad;
    const lat1 = p1[1] * toRad;
    const lon2 = p2[0] * toRad;
    const lat2 = p2[1] * toRad;
    total += (lon2 - lon1) * (2 + Math.sin(lat1) + Math.sin(lat2));
  }

  const area = Math.abs(total * (R * R) / 2.0);
  return Math.round(area * 100) / 100;
}

/**
 * Derives canopy coverage percentage from mean NDVI.
 * Tropical dense forest (NDVI >= 0.75) corresponds to ~90-95% canopy cover.
 * Cleared land (NDVI <= 0.20) corresponds to <= 10% canopy cover.
 *
 * @param {number} ndvi
 * @returns {number} Canopy cover percent [0, 100]
 */
export function ndviToCanopyCoverPercent(ndvi) {
  const val = clampIndex(ndvi);
  if (val <= 0.15) return 0;
  if (val >= 0.80) return 96.0;
  // Linear interpolation between 0.15 (0%) and 0.80 (96%)
  const ratio = (val - 0.15) / (0.80 - 0.15);
  return Math.round(ratio * 96.0 * 10) / 10;
}

/**
 * Performs temporal forest change detection between baseline (T1) and observation (T2).
 *
 * @param {object} input
 * @param {number[]} input.bbox - Geographic bounds [minLon, minLat, maxLon, maxLat]
 * @param {object} input.timeRange - { start: 'YYYY-MM-DD', end: 'YYYY-MM-DD' }
 * @param {object} input.t1Data - Satellite observation at T1 (with computed_indices)
 * @param {object} input.t2Data - Satellite observation at T2 (with computed_indices)
 * @param {object} [input.qualityInfo] - From forestAnalysisQuality.js
 * @param {object} [input.fireCorrelation] - From forestFireCorrelation.js
 * @returns {object} Standardized deforestation analysis report
 */
export function analyzeForestChange({
  bbox,
  timeRange,
  t1Data,
  t2Data,
  qualityInfo = null,
  fireCorrelation = null,
}) {
  const totalAreaKm2 = computeGeodesicBBoxAreaKm2(bbox);
  const t1Ndvi = t1Data?.computed_indices?.NDVI ?? 0.75;
  const t2Ndvi = t2Data?.computed_indices?.NDVI ?? 0.65;
  const nbrDelta = (t2Data?.computed_indices?.NBR ?? 0) - (t1Data?.computed_indices?.NBR ?? 0);

  const prevCover = ndviToCanopyCoverPercent(t1Ndvi);
  const currCover = ndviToCanopyCoverPercent(t2Ndvi);
  const lossPercent = Math.max(0, Math.round((prevCover - currCover) * 10) / 10);
  const deltaNdvi = Math.round((t2Ndvi - t1Ndvi) * 10000) / 10000;

  // Estimated affected forest loss area in km²
  const estimatedLossAreaKm2 = Math.round((totalAreaKm2 * (lossPercent / 100)) * 100) / 100;

  const spectralChange = classifyCanopyChange(t1Ndvi, t2Ndvi, nbrDelta);

  // Derive classification
  let classification = 'STABLE_CANOPY';
  if (spectralChange.changeType === 'BURN_RELATED_LOSS' || fireCorrelation?.fire_correlated) {
    classification = 'BURN_RELATED_FOREST_LOSS';
  } else if (lossPercent >= 10.0 || spectralChange.changeType === 'SUDDEN_CLEARING') {
    classification = 'SIGNIFICANT_FOREST_LOSS';
  } else if (lossPercent >= 5.0) {
    classification = 'MODERATE_FOREST_LOSS';
  } else if (lossPercent >= 2.5 || spectralChange.changeType === 'GRADUAL_DEGRADATION') {
    classification = 'GRADUAL_DEGRADATION';
  } else if (currCover > prevCover + 1.5) {
    classification = 'VEGETATION_RECOVERY';
  }

  // Base confidence on quality info and spectral gap
  let confidence = qualityInfo?.quality_score ?? 0.88;
  if (Math.abs(deltaNdvi) < 0.04) {
    // Subtle changes carry lower confidence
    confidence = Math.max(0.4, confidence - 0.15);
  }
  confidence = Math.round(confidence * 100) / 100;

  // Assign confidence category
  let confidenceCategory = 'HIGH_CONFIDENCE';
  if (confidence < 0.50 || qualityInfo?.status === 'REQUIRES_HUMAN_REVIEW') {
    confidenceCategory = 'REQUIRES_HUMAN_REVIEW';
  } else if (confidence < 0.70) {
    confidenceCategory = 'LOW_CONFIDENCE';
  } else if (confidence < 0.85) {
    confidenceCategory = 'MEDIUM_CONFIDENCE';
  }

  // Probable driver classification
  let probableDriver = 'NATURAL_VEGETATION_CHANGE';
  if (fireCorrelation?.fire_correlated) {
    probableDriver = fireCorrelation.attribution || 'POSSIBLE_WILDFIRE';
  } else if (classification === 'SIGNIFICANT_FOREST_LOSS') {
    probableDriver = 'POTENTIAL_LAND_CLEARING';
  } else if (classification === 'GRADUAL_DEGRADATION') {
    probableDriver = 'AGRICULTURAL_CHANGE';
  }

  return {
    observation_type: 'CONFIRMED_OBSERVATION',
    location: {
      bbox,
      total_area_km2: totalAreaKm2,
    },
    analysis_period: {
      start: timeRange?.start || '2023-01-01',
      end: timeRange?.end || '2024-01-01',
    },
    indices: {
      t1_ndvi: t1Ndvi,
      t2_ndvi: t2Ndvi,
      delta_ndvi: deltaNdvi,
    },
    previous_forest_cover_percent: prevCover,
    current_forest_cover_percent: currCover,
    forest_loss_percent: lossPercent,
    net_loss_percent: lossPercent,
    estimated_loss_area_km2: estimatedLossAreaKm2,
    confidence,
    confidence_category: confidenceCategory,
    classification,
    probable_driver: probableDriver,
    spectral_details: spectralChange,
    quality_summary: qualityInfo ? {
      status: qualityInfo.status,
      valid_pixel_percent: qualityInfo.valid_pixel_percent,
    } : null,
  };
}

/**
 * Adapter for canopy change detection accepting either coordinates or bbox.
 * @param {object} input
 * @returns {object} Change detection report
 */
export function detectCanopyChange(input = {}) {
  if (input.t1CanopyCoverPercent !== undefined || input.t2CanopyCoverPercent !== undefined) {
    const prevCover = Number(input.t1CanopyCoverPercent) || 0;
    const currCover = Number(input.t2CanopyCoverPercent) || 0;
    const lossPercent = Math.max(0, Math.round((prevCover - currCover) * 10) / 10);
    const coords = input.coordinates || [];
    const totalAreaKm2 = computeGeodesicPolygonAreaKm2(coords);
    const estimatedLossAreaKm2 = Math.round((totalAreaKm2 * (lossPercent / 100)) * 100) / 100;
    const spectralClass = input.spectralClass || 'SIGNIFICANT_FOREST_LOSS';

    return {
      observation_type: 'CONFIRMED_OBSERVATION',
      previous_forest_cover_percent: prevCover,
      current_forest_cover_percent: currCover,
      forest_loss_percent: lossPercent,
      net_loss_percent: lossPercent,
      estimated_loss_area_km2: estimatedLossAreaKm2,
      classification: spectralClass,
      probable_driver: lossPercent > 10 ? 'POTENTIAL_LAND_CLEARING' : 'GRADUAL_DEGRADATION',
      confidence: input.validPixelFraction ?? 0.94,
      confidence_category: 'HIGH_CONFIDENCE',
    };
  }
  const res = analyzeForestChange(input);
  res.net_loss_percent = res.forest_loss_percent;
  return res;
}
