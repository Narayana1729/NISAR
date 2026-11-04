import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DeforestationRiskModel,
  validateAndImputeFeatures,
  computeAdditiveFeatureContributions,
  getRiskLevelFromProbability,
  baselineRiskModel,
} from './forestRiskPrediction.js';

test('getRiskLevelFromProbability categorizes risk tiers correctly', () => {
  assert.equal(getRiskLevelFromProbability(0.12).id, 'VERY_LOW');
  assert.equal(getRiskLevelFromProbability(0.28).id, 'LOW');
  assert.equal(getRiskLevelFromProbability(0.50).id, 'MODERATE');
  assert.equal(getRiskLevelFromProbability(0.72).id, 'HIGH');
  assert.equal(getRiskLevelFromProbability(0.91).id, 'CRITICAL');
});

test('validateAndImputeFeatures imputes missing values and docks confidence transparently', () => {
  const complete = validateAndImputeFeatures({
    historical_forest_loss_pct: 12,
    forest_loss_velocity: 3.5,
    ndvi_trend: -0.12,
    fire_frequency: 15,
    road_proximity_km: 1.2,
    settlement_proximity_km: 14.0,
    protected_area_status: 'UNPROTECTED',
    rainfall_anomaly_pct: -30,
    temperature_anomaly_c: 1.2,
    canopy_density_baseline: 90,
  });

  assert.equal(complete.imputed.length, 0);
  assert.equal(complete.confidence, 0.95);

  const partial = validateAndImputeFeatures({});
  assert.ok(partial.imputed.length > 5);
  assert.ok(partial.confidence < 0.80);
});

test('DeforestationRiskModel produces explainable prediction with semantic demarcation', () => {
  const model = new DeforestationRiskModel();
  const prediction = model.predict({
    historical_forest_loss_pct: 14.2,
    forest_loss_velocity: 4.1,
    ndvi_trend: -0.15,
    fire_frequency: 18,
    road_proximity_km: 0.8,
    rainfall_anomaly_pct: -32,
    protected_area_status: 'UNPROTECTED',
  });

  assert.equal(prediction.observation_type, 'PREDICTED_RISK');
  assert.equal(prediction.model_type, 'RULE_BASED_BASELINE');
  assert.equal(prediction.model_version, 'baseline-v1.0');
  assert.equal(prediction.prediction_status, 'EXPERIMENTAL');
  assert.ok(prediction.risk_probability >= 0.75);
  assert.ok(prediction.risk_level === 'HIGH' || prediction.risk_level === 'CRITICAL');
  assert.ok(prediction.contributing_factors.length >= 4);

  // Check additive contributions
  const roadFactor = prediction.contributing_factors.find((f) => f.feature === 'road_proximity');
  assert.ok(roadFactor);
  assert.equal(roadFactor.impact, 'CRITICAL');
  assert.ok(roadFactor.contribution > 0.15);

  assert.ok(prediction.explanation_summary.includes('over NEXT_6_MONTHS'));
});

test('Protected area status provides defensive risk dampening', () => {
  const model = new DeforestationRiskModel();
  const unprotected = model.predict({
    road_proximity_km: 1.5,
    fire_frequency: 12,
    protected_area_status: 'UNPROTECTED',
  });

  const protectedInside = model.predict({
    road_proximity_km: 1.5,
    fire_frequency: 12,
    protected_area_status: 'INSIDE',
  });

  assert.ok(protectedInside.risk_probability < unprotected.risk_probability);
  const protFactor = protectedInside.contributing_factors.find((f) => f.feature === 'protected_area_status');
  assert.ok(protFactor);
  assert.equal(protFactor.impact, 'PROTECTIVE');
  assert.ok(protFactor.contribution < 0);
});
