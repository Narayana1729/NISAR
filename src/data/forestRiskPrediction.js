/**
 * @module forestRiskPrediction
 * @description Future deforestation risk prediction engine with Additive Risk Attribution (XAI).
 * Supports explicit model typing (RULE_BASED_BASELINE vs TRAINED_ML_MODEL),
 * standardized feature schema validation, missing-data imputation, and semantic demarcation.
 */

export const RISK_LEVELS = Object.freeze({
  VERY_LOW: { id: 'VERY_LOW', label: 'Very Low Risk', minProb: 0.00, maxProb: 0.19, color: '#2ecc71' },
  LOW: { id: 'LOW', label: 'Low Risk', minProb: 0.20, maxProb: 0.39, color: '#a8e6cf' },
  MODERATE: { id: 'MODERATE', label: 'Moderate Risk', minProb: 0.40, maxProb: 0.59, color: '#f1c40f' },
  HIGH: { id: 'HIGH', label: 'High Risk', minProb: 0.60, maxProb: 0.79, color: '#e67e22' },
  CRITICAL: { id: 'CRITICAL', label: 'Critical Risk', minProb: 0.80, maxProb: 1.00, color: '#e74c3c' },
});

export function getRiskLevelFromProbability(prob) {
  const p = Math.max(0, Math.min(1.0, Number(prob) || 0));
  if (p >= RISK_LEVELS.CRITICAL.minProb) return RISK_LEVELS.CRITICAL;
  if (p >= RISK_LEVELS.HIGH.minProb) return RISK_LEVELS.HIGH;
  if (p >= RISK_LEVELS.MODERATE.minProb) return RISK_LEVELS.MODERATE;
  if (p >= RISK_LEVELS.LOW.minProb) return RISK_LEVELS.LOW;
  return RISK_LEVELS.VERY_LOW;
}

/**
 * Standardized Deforestation Risk Model Interface.
 */
export class DeforestationRiskModel {
  constructor({
    modelType = 'RULE_BASED_BASELINE',
    modelVersion = 'baseline-v1.0',
    predictionStatus = 'EXPERIMENTAL',
  } = {}) {
    this.modelType = modelType;
    this.modelVersion = modelVersion;
    this.predictionStatus = predictionStatus;
  }

  /**
   * Predicts future deforestation risk and computes additive feature contributions.
   * @param {object} features
   * @param {string} [horizon='NEXT_6_MONTHS']
   * @returns {object} Standardized prediction payload
   */
  predict(features = {}, horizon = 'NEXT_6_MONTHS') {
    const validated = validateAndImputeFeatures(features);
    const contributions = computeAdditiveFeatureContributions(validated.features);

    // Sum base prior (0.10) + feature contributions
    let rawProb = 0.10;
    for (const item of contributions) {
      rawProb += item.contribution;
    }
    const riskProbability = Math.max(0.02, Math.min(0.98, Math.round(rawProb * 100) / 100));
    const riskLevel = getRiskLevelFromProbability(riskProbability);

    // Formulate human-readable explanation
    const topDrivers = contributions.filter((c) => c.impact === 'HIGH' || c.impact === 'CRITICAL');
    const protectiveDrivers = contributions.filter((c) => c.impact === 'PROTECTIVE');

    let summaryText = `${riskLevel.label} (${Math.round(riskProbability * 100)}%) over ${horizon}.`;
    if (topDrivers.length > 0) {
      const driverDesc = topDrivers.map((d) => d.feature.replace(/_/g, ' ')).join(', ');
      summaryText += ` Primary risk drivers: ${driverDesc}.`;
    }
    if (protectiveDrivers.length > 0) {
      summaryText += ` Mitigated by designated protected status.`;
    }

    return {
      observation_type: 'PREDICTED_RISK',
      model_type: this.modelType,
      model_version: this.modelVersion,
      prediction_status: this.predictionStatus,
      prediction_horizon: horizon,
      risk_probability: riskProbability,
      risk_level: riskLevel.id,
      risk_color: riskLevel.color,
      confidence: validated.confidence,
      contributing_factors: contributions,
      explanation_summary: summaryText,
      missing_features_imputed: validated.imputed,
    };
  }
}

/**
 * Validates feature dictionary and imputes missing fields with regional medians.
 * @param {object} input
 * @returns {{ features: object, confidence: number, imputed: string[] }}
 */
export function validateAndImputeFeatures(input = {}) {
  const imputed = [];
  let penalty = 0;

  function resolve(val, fallback, name, deduction = 0.05) {
    if (val !== undefined && val !== null && Number.isFinite(Number(val))) {
      return Number(val);
    }
    imputed.push(name);
    penalty += deduction;
    return fallback;
  }

  const features = {
    historical_forest_loss_pct: Math.max(0, Math.min(100, resolve(input.historical_forest_loss_pct, 4.5, 'historical_forest_loss_pct'))),
    forest_loss_velocity: Math.max(0, Math.min(50, resolve(input.forest_loss_velocity, 1.2, 'forest_loss_velocity'))),
    ndvi_trend: Math.max(-1.0, Math.min(1.0, resolve(input.ndvi_trend, -0.04, 'ndvi_trend'))),
    fire_frequency: Math.max(0, Math.min(200, resolve(input.fire_frequency, 2, 'fire_frequency'))),
    road_proximity_km: Math.max(0.1, Math.min(100, resolve(input.road_proximity_km, 8.0, 'road_proximity_km'))),
    settlement_proximity_km: Math.max(0.5, Math.min(200, resolve(input.settlement_proximity_km, 25.0, 'settlement_proximity_km'))),
    protected_area_status: ['INSIDE', 'BUFFER_10KM', 'UNPROTECTED'].includes(input.protected_area_status)
      ? input.protected_area_status
      : 'UNPROTECTED',
    rainfall_anomaly_pct: Math.max(-100, Math.min(100, resolve(input.rainfall_anomaly_pct, 0, 'rainfall_anomaly_pct'))),
    temperature_anomaly_c: Math.max(-5, Math.min(5, resolve(input.temperature_anomaly_c, 0, 'temperature_anomaly_c'))),
    canopy_density_baseline: Math.max(0, Math.min(100, resolve(input.canopy_density_baseline, 85.0, 'canopy_density_baseline'))),
  };

  const confidence = Math.max(0.40, Math.round((0.95 - penalty) * 100) / 100);
  return { features, confidence, imputed };
}

/**
 * Computes Additive Risk Attribution (Feature Contribution Analysis).
 * @param {object} f - Normalized features
 * @returns {Array<{ feature: string, contribution: number, impact: string, value: any, description: string }>}
 */
export function computeAdditiveFeatureContributions(f) {
  const factors = [];

  // 1. Road Proximity (Empirically the strongest physical predictor of new deforestation fronts)
  if (f.road_proximity_km <= 2.0) {
    factors.push({
      feature: 'road_proximity',
      contribution: 0.22,
      impact: 'CRITICAL',
      value: `${f.road_proximity_km.toFixed(1)} km`,
      description: 'Acute proximity to road network (< 2.0 km) provides direct physical access for clearing machinery',
    });
  } else if (f.road_proximity_km <= 5.0) {
    factors.push({
      feature: 'road_proximity',
      contribution: 0.14,
      impact: 'HIGH',
      value: `${f.road_proximity_km.toFixed(1)} km`,
      description: 'Proximity to secondary access route (< 5.0 km) correlates with frontier expansion',
    });
  } else if (f.road_proximity_km > 20.0) {
    factors.push({
      feature: 'road_proximity',
      contribution: -0.08,
      impact: 'PROTECTIVE',
      value: `${f.road_proximity_km.toFixed(1)} km`,
      description: 'Remoteness from road network (> 20 km) provides natural logistical friction',
    });
  }

  // 2. Fire Frequency / Thermal Anomalies
  if (f.fire_frequency >= 10) {
    factors.push({
      feature: 'fire_frequency',
      contribution: 0.20,
      impact: 'CRITICAL',
      value: `${f.fire_frequency} detections`,
      description: 'Dense concentration of active thermal anomalies indicates ongoing slash-and-burn clearing',
    });
  } else if (f.fire_frequency >= 3) {
    factors.push({
      feature: 'fire_frequency',
      contribution: 0.12,
      impact: 'HIGH',
      value: `${f.fire_frequency} detections`,
      description: 'Clustered thermal anomalies observed in adjacent canopy buffers',
    });
  }

  // 3. Historical Forest Loss & Velocity
  if (f.historical_forest_loss_pct >= 10.0 || f.forest_loss_velocity >= 3.0) {
    factors.push({
      feature: 'historical_forest_loss_rate',
      contribution: 0.18,
      impact: 'HIGH',
      value: `${f.forest_loss_velocity.toFixed(1)}%/yr`,
      description: 'Accelerated historical clearing velocity establishes active deforestation momentum',
    });
  } else if (f.historical_forest_loss_pct >= 4.0) {
    factors.push({
      feature: 'historical_forest_loss_rate',
      contribution: 0.08,
      impact: 'MEDIUM',
      value: `${f.historical_forest_loss_pct.toFixed(1)}%`,
      description: 'Moderate prior clearing within the 3-year surveillance baseline',
    });
  }

  // 4. Downward NDVI Trajectory
  if (f.ndvi_trend <= -0.10) {
    factors.push({
      feature: 'ndvi_canopy_trend',
      contribution: 0.15,
      impact: 'HIGH',
      value: `${f.ndvi_trend.toFixed(2)} ΔNDVI`,
      description: 'Persistent 12-month vegetation index decline confirms ongoing structural degradation',
    });
  } else if (f.ndvi_trend <= -0.04) {
    factors.push({
      feature: 'ndvi_canopy_trend',
      contribution: 0.07,
      impact: 'MEDIUM',
      value: `${f.ndvi_trend.toFixed(2)} ΔNDVI`,
      description: 'Subtle downward vegetation trend across seasonal cycles',
    });
  }

  // 5. Climate / Rainfall Deficit (Drought amplifies fire susceptibility)
  if (f.rainfall_anomaly_pct <= -25) {
    factors.push({
      feature: 'rainfall_anomaly',
      contribution: 0.12,
      impact: 'MEDIUM',
      value: `${f.rainfall_anomaly_pct}%`,
      description: 'Severe precipitation deficit creates dry fuel conditions and increases fire vulnerability',
    });
  }

  // 6. Protected Area Status
  if (f.protected_area_status === 'INSIDE') {
    factors.push({
      feature: 'protected_area_status',
      contribution: -0.16,
      impact: 'PROTECTIVE',
      value: 'National Park / Reserve',
      description: 'Statutory conservation designation historically deters industrial-scale concessions',
    });
  } else if (f.protected_area_status === 'BUFFER_10KM') {
    factors.push({
      feature: 'protected_area_status',
      contribution: 0.06,
      impact: 'LOW',
      value: 'Protected Buffer (< 10 km)',
      description: 'Buffer zone immediately adjoining conservation boundary experiences frontier pressure',
    });
  }

  return factors;
}

/** Default singleton instance */
export const baselineRiskModel = new DeforestationRiskModel();

/**
 * Convenience prediction helper using the default baseline model.
 * @param {object} features
 * @param {string} [horizon='NEXT_6_MONTHS']
 * @returns {object} Standardized prediction
 */
export function predictDeforestationRisk(features = {}, horizon = 'NEXT_6_MONTHS') {
  return baselineRiskModel.predict(features, horizon);
}
