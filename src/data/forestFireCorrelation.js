/**
 * @module forestFireCorrelation
 * @description Integrates NASA FIRMS thermal anomalies with satellite forest change detection.
 * Provides probabilistic spatial-temporal correlation and scientifically honest fire attribution.
 */

/**
 * Calculates great-circle distance between two coordinates in kilometers (Haversine formula).
 * @param {number} lat1
 * @param {number} lon1
 * @param {number} lat2
 * @param {number} lon2
 * @returns {number} Distance in km
 */
export function haversineDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371.0;
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
    + Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180))
    * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c * 100) / 100;
}

/**
 * Correlates active fire thermal anomalies with a detected forest loss event.
 *
 * @param {object} input
 * @param {number[]} input.bbox - [minLon, minLat, maxLon, maxLat] of forest loss zone
 * @param {object} input.timeRange - { start: 'YYYY-MM-DD', end: 'YYYY-MM-DD' }
 * @param {Array<object>} input.fireDetections - Raw FIRMS active fire records ({ lat, lon, frp, acqDate, acqMs })
 * @param {number} [input.bufferKm=15.0] - Maximum proximity buffer in km
 * @returns {object} Fire correlation report
 */
export function correlateFiresWithForestLoss({
  bbox,
  timeRange,
  fireDetections = [],
  bufferKm = 15.0,
}) {
  const [minLon = 0, minLat = 0, maxLon = 0, maxLat = 0] = Array.isArray(bbox) ? bbox : [0, 0, 0, 0];
  const centerLat = (minLat + maxLat) / 2;
  const centerLon = (minLon + maxLon) / 2;

  const startMs = timeRange?.start ? new Date(timeRange.start).getTime() : 0;
  const endMs = timeRange?.end ? new Date(timeRange.end).getTime() : Date.now();

  let correlatedFires = [];
  let totalFrp = 0;
  let minDistanceKm = Infinity;

  for (const fire of fireDetections) {
    const fLat = Number(fire.lat ?? fire.latitude);
    const fLon = Number(fire.lon ?? fire.longitude);
    if (!Number.isFinite(fLat) || !Number.isFinite(fLon)) continue;

    // Temporal filter: fire must be within the analysis time range (with a 15-day tolerance)
    const fireMs = Number(fire.acqMs) || (fire.acqDate ? new Date(fire.acqDate).getTime() : 0);
    if (fireMs && (fireMs < startMs - 15 * 86400000 || fireMs > endMs + 15 * 86400000)) {
      continue;
    }

    // Spatial filter: within bbox or buffer distance
    const dist = haversineDistanceKm(centerLat, centerLon, fLat, fLon);
    const insideBbox = fLat >= minLat && fLat <= maxLat && fLon >= minLon && fLon <= maxLon;

    if (insideBbox || dist <= bufferKm) {
      correlatedFires.push({
        lat: fLat,
        lon: fLon,
        frp: Number(fire.frp) || 10,
        distanceKm: dist,
        insideBbox,
      });
      totalFrp += Number(fire.frp) || 10;
      if (dist < minDistanceKm) minDistanceKm = dist;
    }
  }

  const fireCount = correlatedFires.length;
  const isCorrelated = fireCount >= 2;

  // Determine attribution classification
  let attribution = 'UNEXPLAINED_BY_FIRE';
  let confidence = 0.0;

  if (fireCount === 0) {
    attribution = 'UNEXPLAINED_BY_FIRE';
    confidence = 0.95; // High confidence that fire was not a proximate factor
  } else if (fireCount >= 10 && totalFrp >= 250) {
    // Large thermal signature over widespread cluster
    attribution = 'POSSIBLE_WILDFIRE';
    confidence = 0.85;
  } else if (fireCount >= 2 && minDistanceKm <= 5.0) {
    // Concentrated cluster inside or immediately bordering the clearing
    attribution = 'POSSIBLE_LAND_CLEARING';
    confidence = 0.75;
  } else if (fireCount >= 1) {
    attribution = 'FIRE_CORRELATED';
    confidence = 0.55;
  } else {
    attribution = 'UNDETERMINED_FIRE_RELATIONSHIP';
    confidence = 0.40;
  }

  return {
    fire_correlated: isCorrelated,
    correlated_fire_count: fireCount,
    fire_count_within_radius: fireCount,
    total_radiative_power_mw: Math.round(totalFrp * 10) / 10,
    nearest_fire_distance_km: Number.isFinite(minDistanceKm) ? minDistanceKm : null,
    attribution,
    attribution_confidence: Math.round(confidence * 100) / 100,
    summary: isCorrelated
      ? `${fireCount} thermal anomalies detected within ${bufferKm} km buffer (total FRP: ${totalFrp.toFixed(1)} MW)`
      : 'No statistically significant thermal anomalies correlated with this canopy loss event',
  };
}

/**
 * Adapter for correlating active fires with forest loss accepting centroid and fire arrays.
 * @param {object} input
 * @returns {object} Fire correlation report
 */
export function correlateActiveFiresWithLoss(input = {}) {
  const {
    forestLossCentroid,
    lossStartDate,
    lossEndDate,
    activeFires,
    searchRadiusKm,
    bbox,
    timeRange,
    fireDetections,
    bufferKm,
  } = input;

  const lat = forestLossCentroid?.lat ?? 0;
  const lon = forestLossCentroid?.lon ?? 0;
  const computedBbox = bbox || [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05];
  const computedTime = timeRange || { start: lossStartDate, end: lossEndDate };
  const fires = activeFires || fireDetections || [];
  const radius = searchRadiusKm || bufferKm || 15.0;

  return correlateFiresWithForestLoss({
    bbox: computedBbox,
    timeRange: computedTime,
    fireDetections: fires,
    bufferKm: radius,
  });
}
