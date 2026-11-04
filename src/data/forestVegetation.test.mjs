import test from 'node:test';
import assert from 'node:assert/strict';
import {
  clampIndex,
  computeNdvi,
  computeNdmi,
  computeNbr,
  classifyVegetation,
  classifyCanopyChange,
  VEGETATION_CLASSES,
} from './forestVegetation.js';

test('clampIndex properly bounds values and handles non-finite numbers', () => {
  assert.equal(clampIndex(0.55556), 0.5556);
  assert.equal(clampIndex(1.5), 1.0);
  assert.equal(clampIndex(-2.0), -1.0);
  assert.equal(clampIndex(NaN), 0);
  assert.equal(clampIndex(Infinity), 0);
  assert.equal(clampIndex(-Infinity), 0);
  assert.equal(clampIndex(undefined), 0);
});

test('computeNdvi computes accurate Normalized Difference Vegetation Index', () => {
  // Dense forest: NIR=0.8, RED=0.1 => (0.8 - 0.1) / (0.8 + 0.1) = 0.7 / 0.9 = 0.7778
  const dense = computeNdvi(0.8, 0.1);
  assert.ok(Math.abs(dense - 0.7778) < 0.001);

  // Cleared soil: NIR=0.2, RED=0.25 => (0.2 - 0.25) / (0.2 + 0.25) = -0.05 / 0.45 = -0.1111
  const bare = computeNdvi(0.2, 0.25);
  assert.ok(Math.abs(bare - (-0.1111)) < 0.001);

  // Water/shadow: NIR=0.02, RED=0.05 => negative
  assert.ok(computeNdvi(0.02, 0.05) < 0);
});

test('computeNdvi handles boundary conditions safely (divide-by-zero, negative, NaN)', () => {
  assert.equal(computeNdvi(0, 0), 0);
  assert.equal(computeNdvi(0.0000001, 0.0000001), 0);
  assert.equal(computeNdvi(-0.5, 0.5), 0);
  assert.equal(computeNdvi(NaN, 0.5), 0);
  assert.equal(computeNdvi(0.5, null), 0);
  assert.equal(computeNdvi(undefined, 0.5), 0);
});

test('computeNdmi and computeNbr compute valid normalized difference indices', () => {
  // NDMI: NIR=0.7, SWIR1=0.3 => (0.7 - 0.3) / (0.7 + 0.3) = 0.4 / 1.0 = 0.4
  assert.equal(computeNdmi(0.7, 0.3), 0.4);
  assert.equal(computeNdmi(0, 0), 0);

  // NBR: NIR=0.8, SWIR2=0.2 => (0.8 - 0.2) / (0.8 + 0.2) = 0.6 / 1.0 = 0.6
  assert.equal(computeNbr(0.8, 0.2), 0.6);
  assert.equal(computeNbr(0, 0), 0);
});

test('classifyVegetation classifies NDVI thresholds correctly', () => {
  assert.equal(classifyVegetation(0.85).id, VEGETATION_CLASSES.DENSE_FOREST.id);
  assert.equal(classifyVegetation(0.60).id, VEGETATION_CLASSES.DENSE_FOREST.id);
  assert.equal(classifyVegetation(0.50).id, VEGETATION_CLASSES.HEALTHY_VEGETATION.id);
  assert.equal(classifyVegetation(0.30).id, VEGETATION_CLASSES.SPARSE_VEGETATION.id);
  assert.equal(classifyVegetation(0.10).id, VEGETATION_CLASSES.DEGRADED_BARREN.id);
  assert.equal(classifyVegetation(-0.2).id, VEGETATION_CLASSES.DEGRADED_BARREN.id);
});

test('classifyCanopyChange differentiates burn scars, clear-cuts, degradation, and recovery', () => {
  // Burn scar: NDVI drops from 0.75 to 0.45 (-0.30) with acute NBR drop (-0.25)
  const burn = classifyCanopyChange(0.75, 0.45, -0.25);
  assert.equal(burn.changeType, 'BURN_RELATED_LOSS');
  assert.equal(burn.severity, 'CRITICAL');

  // Sudden mechanical clearing: NDVI drops from 0.80 to 0.35 (-0.45)
  const clear = classifyCanopyChange(0.80, 0.35, 0);
  assert.equal(clear.changeType, 'SUDDEN_CLEARING');
  assert.equal(clear.severity, 'CRITICAL');

  // Gradual degradation: NDVI drops from 0.75 to 0.60 (-0.15)
  const grad = classifyCanopyChange(0.75, 0.60, 0);
  assert.equal(grad.changeType, 'GRADUAL_DEGRADATION');
  assert.equal(grad.severity, 'HIGH');

  // Minor seasonal fluctuation: NDVI drops from 0.75 to 0.68 (-0.07)
  const minor = classifyCanopyChange(0.75, 0.68, 0);
  assert.equal(minor.changeType, 'MINOR_VEGETATION_CHANGE');

  // Stable: NDVI fluctuates within +-0.05
  const stable = classifyCanopyChange(0.75, 0.76, 0);
  assert.equal(stable.changeType, 'STABLE_CANOPY');

  // Recovery: NDVI increases
  const rec = classifyCanopyChange(0.50, 0.65, 0);
  assert.equal(rec.changeType, 'CANOPY_RECOVERY');
});
