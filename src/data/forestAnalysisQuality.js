/**
 * @module forestAnalysisQuality
 * @description Scientific quality assurance and cloud masking pipeline for satellite deforestation analysis.
 * Centralizes cloud detection, shadow masking, valid pixel filtering, sensor consistency, and phenological comparability.
 */

/** Minimum required valid (cloud-free, shadow-free) pixel percentage to accept analysis */
export const MIN_VALID_PIXEL_THRESHOLD = 70.0;

/** Recommended maximum cloud cover percentage for standard confidence analysis */
export const MAX_ACCEPTABLE_CLOUD_COVER = 20.0;

/**
 * Evaluates seasonal / phenological comparability between two observation dates.
 * Tropical dry/wet season shifts can alter deciduous canopy NDVI by up to 0.15 without real tree loss.
 *
 * @param {string|Date} date1 - Baseline date
 * @param {string|Date} date2 - Current observation date
 * @returns {{ comparable: boolean, status: string, monthDiff: number, description: string }}
 */
export function evaluateSeasonalComparability(date1, date2) {
  const d1 = new Date(date1);
  const d2 = new Date(date2);
  if (Number.isNaN(d1.getTime()) || Number.isNaN(d2.getTime())) {
    return {
      comparable: false,
      status: 'INVALID_DATES',
      monthDiff: -1,
      description: 'Unable to evaluate seasonal comparability due to malformed date timestamps',
    };
  }

  const m1 = d1.getUTCMonth();
  const m2 = d2.getUTCMonth();
  // Absolute cyclic month difference (0 to 6)
  const diff = Math.min(Math.abs(m1 - m2), 12 - Math.abs(m1 - m2));

  if (diff <= 1) {
    return {
      comparable: true,
      status: 'EXCELLENT',
      monthDiff: diff,
      description: 'Observations acquired within the same seasonal phenology window (<= 1 month calendar alignment)',
    };
  }

  if (diff <= 2) {
    return {
      comparable: true,
      status: 'GOOD',
      monthDiff: diff,
      description: 'Observations acquired within acceptable seasonal window (<= 2 months calendar alignment)',
    };
  }

  if (diff <= 3) {
    return {
      comparable: true,
      status: 'MODERATE',
      monthDiff: diff,
      description: 'Moderate seasonal gap (3 months); minor phenological canopy fluctuation may be present',
    };
  }

  return {
    comparable: false,
    status: 'SEASONAL_MISMATCH',
    monthDiff: diff,
    description: 'Significant seasonal mismatch (opposing wet/dry seasons); risk of false-positive deciduous leaf loss',
  };
}

/**
 * Evaluates the scientific quality of a satellite analysis scene.
 *
 * @param {object} input
 * @param {number} [input.cloudCoveragePercent=0] - Estimated cloud cover percentage [0, 100]
 * @param {number} [input.shadowCoveragePercent=0] - Cloud shadow percentage [0, 100]
 * @param {string} [input.sensorQuality='HIGH'] - 'HIGH' | 'MEDIUM' | 'DEGRADED'
 * @param {string} [input.sensorType='SENTINEL_2'] - 'SENTINEL_2' | 'LANDSAT_8' | 'LANDSAT_9' | 'SYNTHETIC'
 * @param {string} [input.t1Date] - ISO date for baseline
 * @param {string} [input.t2Date] - ISO date for comparison
 * @returns {object} Quality assessment payload
 */
export function evaluateAnalysisQuality({
  cloudCoveragePercent = 0,
  shadowCoveragePercent = 0,
  sensorQuality = 'HIGH',
  sensorType = 'SENTINEL_2',
  t1Date,
  t2Date,
} = {}) {
  const clouds = Math.max(0, Math.min(100, Number(cloudCoveragePercent) || 0));
  const shadows = Math.max(0, Math.min(100, Number(shadowCoveragePercent) || 0));
  const validPixels = Math.max(0, Math.min(100, Math.round((100 - (clouds + shadows)) * 10) / 10));

  const reasons = [];
  let score = 1.0;

  // Cloud contamination deduction
  if (clouds > 5) {
    score -= (clouds / 100) * 0.4;
  }
  if (clouds > MAX_ACCEPTABLE_CLOUD_COVER) {
    reasons.push('HIGH_CLOUD_COVER');
  }

  // Shadow penalty
  if (shadows > 3) {
    score -= (shadows / 100) * 0.3;
    reasons.push('CLOUD_SHADOW_CONTAMINATION');
  }

  // Sensor quality penalty
  const sq = String(sensorQuality).toUpperCase();
  if (sq === 'DEGRADED') {
    score -= 0.3;
    reasons.push('DEGRADED_SENSOR_QUALITY');
  } else if (sq === 'MEDIUM') {
    score -= 0.1;
  }

  // Seasonal comparability
  let seasonal = { comparable: true, status: 'EXCELLENT', monthDiff: 0, description: 'Single date or aligned dates' };
  if (t1Date && t2Date) {
    seasonal = evaluateSeasonalComparability(t1Date, t2Date);
    if (!seasonal.comparable) {
      score -= 0.25;
      reasons.push('SEASONAL_MISMATCH');
    } else if (seasonal.status === 'MODERATE') {
      score -= 0.1;
    }
  }

  // Clamp final quality score
  const finalScore = Math.max(0, Math.min(1.0, Math.round(score * 100) / 100));

  // Determine overall status
  let status = 'ANALYSIS_ACCEPTED';
  if (validPixels < MIN_VALID_PIXEL_THRESHOLD) {
    status = 'ANALYSIS_REJECTED';
    reasons.push('INSUFFICIENT_VALID_PIXELS');
  } else if (finalScore < 0.65 || reasons.length > 0) {
    status = 'REQUIRES_HUMAN_REVIEW';
  }

  return {
    quality_score: finalScore,
    valid_pixel_percent: validPixels,
    cloud_coverage_percent: clouds,
    shadow_coverage_percent: shadows,
    sensor_quality: sq,
    sensor_type: sensorType,
    seasonal_comparability: seasonal.status,
    status,
    reasons,
    accepted: status === 'ANALYSIS_ACCEPTED',
  };
}
