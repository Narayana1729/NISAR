import test from 'node:test';
import assert from 'node:assert/strict';
import {
  computeGeodesicBBoxAreaKm2,
  ndviToCanopyCoverPercent,
  analyzeForestChange,
} from './forestChangeDetection.js';

test('computeGeodesicBBoxAreaKm2 computes accurate geodesic surface area', () => {
  // A 1x1 degree box at equator: width ~111km, height ~111km => ~12,300 km²
  const area = computeGeodesicBBoxAreaKm2([0, 0, 1, 1]);
  assert.ok(area > 12000 && area < 12500, `Area was ${area}`);

  // Invalid bbox returns 0
  assert.equal(computeGeodesicBBoxAreaKm2(null), 0);
  assert.equal(computeGeodesicBBoxAreaKm2([0, 0]), 0);
});

test('ndviToCanopyCoverPercent scales canopy cover reliably', () => {
  assert.equal(ndviToCanopyCoverPercent(0.85), 96.0);
  assert.equal(ndviToCanopyCoverPercent(0.10), 0);
  const mid = ndviToCanopyCoverPercent(0.475);
  assert.ok(mid > 40 && mid < 60);
});

test('analyzeForestChange detects significant forest loss between T1 and T2', () => {
  const res = analyzeForestChange({
    bbox: [-62.0, -10.0, -61.5, -9.5],
    timeRange: { start: '2023-01-01', end: '2024-01-01' },
    t1Data: { computed_indices: { NDVI: 0.80, NBR: 0.70 } },
    t2Data: { computed_indices: { NDVI: 0.50, NBR: 0.55 } },
    qualityInfo: { quality_score: 0.92, status: 'ANALYSIS_ACCEPTED', valid_pixel_percent: 94 },
  });

  assert.equal(res.observation_type, 'CONFIRMED_OBSERVATION');
  assert.equal(res.previous_forest_cover_percent, 96.0);
  assert.ok(res.current_forest_cover_percent < 60.0);
  assert.ok(res.forest_loss_percent > 35.0);
  assert.ok(res.estimated_loss_area_km2 > 0);
  assert.equal(res.classification, 'SIGNIFICANT_FOREST_LOSS');
  assert.equal(res.probable_driver, 'POTENTIAL_LAND_CLEARING');
  assert.equal(res.confidence_category, 'HIGH_CONFIDENCE');
});

test('analyzeForestChange handles stable canopy with appropriate classification', () => {
  const res = analyzeForestChange({
    bbox: [-62.0, -10.0, -61.5, -9.5],
    timeRange: { start: '2023-01-01', end: '2024-01-01' },
    t1Data: { computed_indices: { NDVI: 0.78, NBR: 0.65 } },
    t2Data: { computed_indices: { NDVI: 0.77, NBR: 0.64 } },
    qualityInfo: { quality_score: 0.90, status: 'ANALYSIS_ACCEPTED', valid_pixel_percent: 95 },
  });

  assert.equal(res.classification, 'STABLE_CANOPY');
  assert.ok(res.forest_loss_percent <= 2.0);
});
