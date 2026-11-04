import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MIN_VALID_PIXEL_THRESHOLD,
  evaluateSeasonalComparability,
  evaluateAnalysisQuality,
} from './forestAnalysisQuality.js';

test('evaluateSeasonalComparability correctly scores aligned months vs opposing seasons', () => {
  // June 2024 vs July 2025 (diff = 1 month) => EXCELLENT
  const res1 = evaluateSeasonalComparability('2024-06-15', '2025-07-20');
  assert.equal(res1.status, 'EXCELLENT');
  assert.equal(res1.comparable, true);

  // January 2024 vs December 2024 (diff = 1 month across year boundary) => EXCELLENT
  const resDecJan = evaluateSeasonalComparability('2024-01-10', '2024-12-28');
  assert.equal(resDecJan.status, 'EXCELLENT');
  assert.equal(resDecJan.comparable, true);

  // February 2024 vs August 2025 (diff = 6 months, opposite seasons) => SEASONAL_MISMATCH
  const resOpp = evaluateSeasonalComparability('2024-02-15', '2025-08-15');
  assert.equal(resOpp.status, 'SEASONAL_MISMATCH');
  assert.equal(resOpp.comparable, false);

  // Invalid dates
  const resInvalid = evaluateSeasonalComparability('not-a-date', '2025-08-15');
  assert.equal(resInvalid.status, 'INVALID_DATES');
  assert.equal(resInvalid.comparable, false);
});

test('evaluateAnalysisQuality accepts clear, high-quality satellite acquisitions', () => {
  const q = evaluateAnalysisQuality({
    cloudCoveragePercent: 2.5,
    shadowCoveragePercent: 1.0,
    sensorQuality: 'HIGH',
    t1Date: '2024-07-01',
    t2Date: '2025-07-15',
  });

  assert.equal(q.status, 'ANALYSIS_ACCEPTED');
  assert.equal(q.accepted, true);
  assert.ok(q.quality_score >= 0.90);
  assert.equal(q.valid_pixel_percent, 96.5);
  assert.equal(q.reasons.length, 0);
});

test('evaluateAnalysisQuality rejects scenes with cloud contamination exceeding threshold', () => {
  // 35% clouds + 5% shadow => 60% valid pixels (< 70% threshold)
  const q = evaluateAnalysisQuality({
    cloudCoveragePercent: 35.0,
    shadowCoveragePercent: 5.0,
    sensorQuality: 'HIGH',
    t1Date: '2024-07-01',
    t2Date: '2025-07-15',
  });

  assert.equal(q.status, 'ANALYSIS_REJECTED');
  assert.equal(q.accepted, false);
  assert.ok(q.valid_pixel_percent < MIN_VALID_PIXEL_THRESHOLD);
  assert.ok(q.reasons.includes('INSUFFICIENT_VALID_PIXELS'));
  assert.ok(q.reasons.includes('HIGH_CLOUD_COVER'));
});

test('evaluateAnalysisQuality flags moderate cloud or seasonal mismatch for human review', () => {
  // 15% clouds, but opposing seasons (Jan vs July)
  const q = evaluateAnalysisQuality({
    cloudCoveragePercent: 15.0,
    shadowCoveragePercent: 2.0,
    sensorQuality: 'HIGH',
    t1Date: '2024-01-15',
    t2Date: '2024-07-15',
  });

  assert.equal(q.status, 'REQUIRES_HUMAN_REVIEW');
  assert.equal(q.accepted, false);
  assert.ok(q.reasons.includes('SEASONAL_MISMATCH'));
});
