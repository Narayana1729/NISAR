import test from 'node:test';
import assert from 'node:assert/strict';
import {
  haversineDistanceKm,
  correlateFiresWithForestLoss,
} from './forestFireCorrelation.js';

test('haversineDistanceKm computes accurate great-circle distances', () => {
  // Distance between London (51.5074, -0.1278) and Paris (48.8566, 2.3522) is ~344 km
  const d = haversineDistanceKm(51.5074, -0.1278, 48.8566, 2.3522);
  assert.ok(d > 340 && d < 350, `Distance was ${d}`);

  // Same point is 0
  assert.equal(haversineDistanceKm(10, 20, 10, 20), 0);
});

test('correlateFiresWithForestLoss detects concentrated agricultural clearing fires', () => {
  const bbox = [-62.0, -10.0, -61.5, -9.5];
  const timeRange = { start: '2024-06-01', end: '2024-09-01' };

  // 4 fires directly inside the clearing zone
  const mockFires = [
    { lat: -9.75, lon: -61.75, frp: 45, acqDate: '2024-07-15' },
    { lat: -9.76, lon: -61.76, frp: 30, acqDate: '2024-07-16' },
    { lat: -9.74, lon: -61.74, frp: 60, acqDate: '2024-07-20' },
  ];

  const res = correlateFiresWithForestLoss({ bbox, timeRange, fireDetections: mockFires });
  assert.equal(res.fire_correlated, true);
  assert.equal(res.correlated_fire_count, 3);
  assert.equal(res.attribution, 'POSSIBLE_LAND_CLEARING');
  assert.ok(res.attribution_confidence >= 0.70);
});

test('correlateFiresWithForestLoss classifies large thermal cluster as possible wildfire', () => {
  const bbox = [-62.0, -10.0, -61.5, -9.5];
  const timeRange = { start: '2024-06-01', end: '2024-09-01' };

  // 12 high-intensity fires
  const mockFires = Array.from({ length: 12 }, (_, i) => ({
    lat: -9.75 + i * 0.01,
    lon: -61.75 + i * 0.01,
    frp: 35,
    acqDate: '2024-08-01',
  }));

  const res = correlateFiresWithForestLoss({ bbox, timeRange, fireDetections: mockFires });
  assert.equal(res.fire_correlated, true);
  assert.equal(res.attribution, 'POSSIBLE_WILDFIRE');
  assert.ok(res.total_radiative_power_mw >= 400);
});

test('correlateFiresWithForestLoss returns unexplained when zero fires are detected', () => {
  const bbox = [-62.0, -10.0, -61.5, -9.5];
  const timeRange = { start: '2024-06-01', end: '2024-09-01' };

  const res = correlateFiresWithForestLoss({ bbox, timeRange, fireDetections: [] });
  assert.equal(res.fire_correlated, false);
  assert.equal(res.correlated_fire_count, 0);
  assert.equal(res.attribution, 'UNEXPLAINED_BY_FIRE');
});
