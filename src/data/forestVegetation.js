/**
 * @module forestVegetation
 * @description Core multispectral vegetation indices and canopy classification algorithms.
 * Implements NDVI, NDMI, and NBR with rigorous division-by-zero, NaN, and boundary safeguards.
 */

/**
 * Clamps a normalized index value to [-1.0, 1.0].
 * Returns 0 if value is not finite.
 * @param {number} value
 * @returns {number}
 */
export function clampIndex(value) {
  if (!Number.isFinite(value)) return 0;
  if (value > 1.0) return 1.0;
  if (value < -1.0) return -1.0;
  return Math.round(value * 10000) / 10000;
}

/**
 * Validates a spectral band reflectance value.
 * Reflectance must be a finite number >= 0.
 * @param {*} val
 * @returns {boolean}
 */
function isValidBand(val) {
  return val !== null && val !== undefined && typeof val === 'number' && Number.isFinite(val) && val >= 0;
}

/**
 * Computes Normalized Difference Vegetation Index (NDVI).
 * Formula: (NIR - RED) / (NIR + RED)
 * Sentinel-2: (B8 - B4) / (B8 + B4)
 * Landsat 8/9: (B5 - B4) / (B5 + B4)
 *
 * @param {number} nir - Near-infrared surface reflectance [0, 1]
 * @param {number} red - Red surface reflectance [0, 1]
 * @returns {number} NDVI clamped to [-1.0, 1.0]
 */
export function computeNdvi(nir, red) {
  if (!isValidBand(nir) || !isValidBand(red)) return 0;
  const denominator = nir + red;
  if (denominator <= 1e-6) return 0; // Guard against divide-by-zero & extreme darkness
  return clampIndex((nir - red) / denominator);
}

/**
 * Computes Normalized Difference Moisture Index (NDMI).
 * Formula: (NIR - SWIR1) / (NIR + SWIR1)
 * Useful for assessing canopy liquid water content and drought/canopy stress.
 * Sentinel-2: (B8 - B11) / (B8 + B11)
 * Landsat 8/9: (B5 - B6) / (B5 + B6)
 *
 * @param {number} nir - Near-infrared surface reflectance [0, 1]
 * @param {number} swir1 - Shortwave infrared-1 reflectance [0, 1]
 * @returns {number} NDMI clamped to [-1.0, 1.0]
 */
export function computeNdmi(nir, swir1) {
  if (!isValidBand(nir) || !isValidBand(swir1)) return 0;
  const denominator = nir + swir1;
  if (denominator <= 1e-6) return 0;
  return clampIndex((nir - swir1) / denominator);
}

/**
 * Computes Normalized Burn Ratio (NBR).
 * Formula: (NIR - SWIR2) / (NIR + SWIR2)
 * Highlights burned areas and fire scar severity.
 * Sentinel-2: (B8 - B12) / (B8 + B12)
 * Landsat 8/9: (B5 - B7) / (B5 + B7)
 *
 * @param {number} nir - Near-infrared surface reflectance [0, 1]
 * @param {number} swir2 - Shortwave infrared-2 reflectance [0, 1]
 * @returns {number} NBR clamped to [-1.0, 1.0]
 */
export function computeNbr(nir, swir2) {
  if (!isValidBand(nir) || !isValidBand(swir2)) return 0;
  const denominator = nir + swir2;
  if (denominator <= 1e-6) return 0;
  return clampIndex((nir - swir2) / denominator);
}

/**
 * Canopy classification categories based on NDVI thresholds.
 */
export const VEGETATION_CLASSES = Object.freeze({
  DENSE_FOREST: {
    id: 'DENSE_FOREST',
    label: 'Dense Forest Canopy',
    minNdvi: 0.60,
    color: '#2ecc71', // Lush Green
  },
  HEALTHY_VEGETATION: {
    id: 'HEALTHY_VEGETATION',
    label: 'Healthy Vegetation / Secondary Growth',
    minNdvi: 0.40,
    color: '#a8e6cf', // Light Green
  },
  SPARSE_VEGETATION: {
    id: 'SPARSE_VEGETATION',
    label: 'Sparse Vegetation / Shrubland',
    minNdvi: 0.20,
    color: '#f1c40f', // Yellow
  },
  DEGRADED_BARREN: {
    id: 'DEGRADED_BARREN',
    label: 'Degraded / Cleared / Bare Soil',
    minNdvi: -1.0,
    color: '#e74c3c', // Red
  },
});

/**
 * Classifies a single NDVI value into a vegetation class.
 * @param {number} ndvi
 * @returns {object} Vegetation class metadata
 */
export function classifyVegetation(ndvi) {
  const val = clampIndex(ndvi);
  if (val >= VEGETATION_CLASSES.DENSE_FOREST.minNdvi) return VEGETATION_CLASSES.DENSE_FOREST;
  if (val >= VEGETATION_CLASSES.HEALTHY_VEGETATION.minNdvi) return VEGETATION_CLASSES.HEALTHY_VEGETATION;
  if (val >= VEGETATION_CLASSES.SPARSE_VEGETATION.minNdvi) return VEGETATION_CLASSES.SPARSE_VEGETATION;
  return VEGETATION_CLASSES.DEGRADED_BARREN;
}

/**
 * Classifies multi-temporal spectral change between baseline (T1) and current (T2).
 *
 * @param {number} t1Ndvi - Baseline NDVI
 * @param {number} t2Ndvi - Current observation NDVI
 * @param {number} [nbrDelta=0] - Difference in NBR (T2 - T1). Severe burn scars show delta < -0.2
 * @returns {{ changeType: string, deltaNdvi: number, severity: string, description: string }}
 */
export function classifyCanopyChange(t1Ndvi, t2Ndvi, nbrDelta = 0) {
  const v1 = clampIndex(t1Ndvi);
  const v2 = clampIndex(t2Ndvi);
  const delta = Math.round((v2 - v1) * 10000) / 10000;
  const burn = Number(nbrDelta) || 0;

  // Significant burn scar (NDVI drop accompanied by severe NBR loss)
  if (delta <= -0.15 && burn <= -0.20) {
    return {
      changeType: 'BURN_RELATED_LOSS',
      deltaNdvi: delta,
      severity: 'CRITICAL',
      description: 'Severe canopy drop accompanied by acute burn scar spectral signature',
    };
  }

  // Sudden catastrophic clearing (clear-cut or slash-and-burn)
  if (delta <= -0.25) {
    return {
      changeType: 'SUDDEN_CLEARING',
      deltaNdvi: delta,
      severity: 'CRITICAL',
      description: 'Acute canopy collapse indicating mechanical clearing or rapid deforestation',
    };
  }

  // Gradual degradation / selective logging / drought stress
  if (delta <= -0.12) {
    return {
      changeType: 'GRADUAL_DEGRADATION',
      deltaNdvi: delta,
      severity: 'HIGH',
      description: 'Moderate canopy decline consistent with selective thinning or environmental stress',
    };
  }

  // Minor variation / seasonal fluctuation
  if (delta < -0.05) {
    return {
      changeType: 'MINOR_VEGETATION_CHANGE',
      deltaNdvi: delta,
      severity: 'MODERATE',
      description: 'Minor vegetation dip, potentially attributable to seasonal senescence or phenology',
    };
  }

  // Stable canopy
  if (delta >= -0.05 && delta <= 0.05) {
    return {
      changeType: 'STABLE_CANOPY',
      deltaNdvi: delta,
      severity: 'LOW',
      description: 'Canopy density within stable historical equilibrium',
    };
  }

  // Canopy recovery / afforestation
  return {
    changeType: 'CANOPY_RECOVERY',
    deltaNdvi: delta,
    severity: 'POSITIVE',
    description: 'Measurable canopy density gain or secondary forest regeneration',
  };
}

// Aliases for compatibility with proxy and remote sensing pipelines
export const calculateNDVI = computeNdvi;
export const calculateNDMI = computeNdmi;
export const calculateNBR = computeNbr;
export const classifySpectralChange = classifyCanopyChange;
