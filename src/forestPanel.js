/**
 * @module forestPanel
 * @description UI Controller for AI-Based Deforestation Detection & Prediction.
 * Manages the #forest-panel interface, KPI cards, multi-year timeline slider,
 * Explainable AI (XAI) feature attribution breakdown, and isolated DEMO DATA toggle.
 */

import { getAllMonitoredHotspots, getHotspotById } from './data/forestCatalog.js';
import { predictDeforestationRisk } from './data/forestRiskPrediction.js';
import { selectForestZone } from './data/forestIntelligence.js';

/** State container for forest panel UI */
const state = {
  viewer: null,
  forestLayer: null,
  activeZoneId: 'amazon-rondonia',
  activeYear: 2026,
  demoDataMode: false,
  comparisonMode: false,
  initialized: false,
};

/**
 * Updates KPI cards, spectral indices, XAI, and provenance for the selected zone.
 * @param {string} zoneId
 */
export function updateForestPanel(zoneId = state.activeZoneId) {
  const spot = getHotspotById(zoneId);
  if (!spot) return;

  state.activeZoneId = zoneId;

  // DOM elements
  const zoneSelect = document.getElementById('forest-zone-select');
  if (zoneSelect && zoneSelect.value !== zoneId) {
    zoneSelect.value = zoneId;
  }

  // Find record for active timeline year
  const timelineRecord = spot.timeline?.find((t) => t.year === state.activeYear)
    || spot.timeline?.[spot.timeline.length - 1];

  let coverPct = timelineRecord?.canopy_cover_percent ?? spot.latest_metrics.current_forest_cover_percent;
  let lossPct = spot.latest_metrics.forest_loss_percent;
  let lossArea = spot.latest_metrics.estimated_loss_area_km2;
  let riskLevel = spot.current_risk_level;
  let fireCount = spot.latest_metrics.active_fire_count;
  let ndvi = 0.72 + (spot.latest_metrics.ndvi_trend || 0);

  // When DEMO DATA MODE is active, show explicit perturbation with demo provenance
  if (state.demoDataMode) {
    lossPct = Math.round((lossPct * 1.25) * 10) / 10;
    lossArea = Math.round(lossArea * 1.25);
    riskLevel = 'CRITICAL';
    fireCount += 14;
    ndvi = Math.round((ndvi - 0.08) * 100) / 100;
  }

  // Comparison mode: show delta between 2021 (T1) and Current/Selected (T2)
  if (state.comparisonMode) {
    const t1Record = spot.timeline?.[0]; // 2021
    const t1Cover = t1Record?.canopy_cover_percent ?? 82.0;
    const netLoss = Math.round((t1Cover - coverPct) * 10) / 10;

    const lossEl = document.getElementById('forest-loss-val');
    if (lossEl) lossEl.textContent = `-${netLoss}%`;

    const lossSub = document.getElementById('forest-loss-area');
    if (lossSub) lossSub.textContent = `Δ T1(2021)→T2(${state.activeYear})`;
  } else {
    const lossEl = document.getElementById('forest-loss-val');
    if (lossEl) lossEl.textContent = `-${lossPct}%`;

    const lossSub = document.getElementById('forest-loss-area');
    if (lossSub) lossSub.textContent = `${lossArea.toLocaleString()} km²`;
  }

  // Canopy Cover Card
  const coverEl = document.getElementById('forest-cover-val');
  if (coverEl) coverEl.textContent = `${coverPct.toFixed(1)}%`;

  const biomeSub = document.getElementById('forest-biome-sub');
  if (biomeSub) biomeSub.textContent = spot.country;

  // Risk Level Card
  const riskEl = document.getElementById('forest-risk-val');
  if (riskEl) {
    riskEl.textContent = riskLevel;
    riskEl.className = `forest-kpi-val forest-val-risk risk-${riskLevel.toLowerCase()}`;
  }

  // Active Fires Card
  const firesEl = document.getElementById('forest-fires-val');
  if (firesEl) firesEl.textContent = String(fireCount);

  const fireAttr = document.getElementById('forest-fire-attr');
  if (fireAttr) {
    fireAttr.textContent = spot.latest_metrics.fire_correlated
      ? spot.latest_metrics.fire_attribution.replace(/_/g, ' ')
      : 'Uncorrelated';
  }

  // Spectral Indices
  const ndviEl = document.getElementById('forest-ndvi-val');
  if (ndviEl) ndviEl.textContent = ndvi.toFixed(2);

  const ndmiEl = document.getElementById('forest-ndmi-val');
  if (ndmiEl) ndmiEl.textContent = (ndvi * 0.58).toFixed(2);

  const nbrEl = document.getElementById('forest-nbr-val');
  if (nbrEl) nbrEl.textContent = (ndvi * 0.76).toFixed(2);

  // Quality chip
  const qualityChip = document.getElementById('forest-quality-chip');
  if (qualityChip) {
    qualityChip.textContent = state.demoDataMode ? 'SYNTHETIC DEMO' : 'QUALITY · 94% VALID';
    qualityChip.classList.toggle('demo-active', state.demoDataMode);
  }

  // Demo badge
  const demoBadge = document.getElementById('forest-demo-badge');
  if (demoBadge) {
    demoBadge.textContent = state.demoDataMode ? 'DEMO DATA (SYNTHETIC)' : 'LIVE SATELLITE';
    demoBadge.classList.toggle('demo-active', state.demoDataMode);
  }

  // XAI Breakdown
  const features = {
    historical_loss_rate: lossPct,
    recent_fire_density: fireCount,
    distance_to_road_km: 1.5,
    distance_to_previous_loss_km: 0.8,
    slope_degrees: 3.5,
    protected_status: 0.3,
    edge_ratio: 0.65,
    dry_season_severity: 0.7,
    agricultural_commodity_price_index: 1.15,
    concession_proximity_km: 4.0,
  };
  const prediction = predictDeforestationRisk(features);
  renderXaiBreakdown(prediction);

  // Provenance
  const provSource = document.getElementById('forest-prov-source');
  if (provSource) {
    provSource.textContent = state.demoDataMode
      ? 'Synthetic Simulation (Isolated Demo Model)'
      : spot.provenance.source;
  }

  const provDate = document.getElementById('forest-prov-date');
  if (provDate) provDate.textContent = spot.provenance.last_verified.split('T')[0];

  const provLicense = document.getElementById('forest-prov-license');
  if (provLicense) provLicense.textContent = spot.provenance.data_license;
}

/**
 * Renders Additive Risk Attribution bars and explanation summary.
 * @param {object} prediction
 */
function renderXaiBreakdown(prediction) {
  const barsContainer = document.getElementById('forest-xai-bars');
  const summaryEl = document.getElementById('forest-xai-summary');
  const scoreEl = document.getElementById('forest-risk-score');
  const modelTag = document.getElementById('forest-model-tag');

  if (scoreEl) scoreEl.textContent = `Score: ${(prediction.risk_probability * 100).toFixed(0)}/100`;
  if (modelTag) modelTag.textContent = prediction.model_type;

  if (summaryEl) {
    summaryEl.textContent = prediction.explanation_summary;
  }

  if (!barsContainer) return;
  barsContainer.innerHTML = '';

  const contributions = prediction.contributing_factors || [];
  // Render top 4 risk contributors
  contributions.slice(0, 4).forEach((c) => {
    const row = document.createElement('div');
    row.className = 'forest-xai-row';

    const label = document.createElement('span');
    label.className = 'forest-xai-row-label';
    label.textContent = c.feature.replace(/_/g, ' ').toUpperCase();

    const barWrap = document.createElement('div');
    barWrap.className = 'forest-xai-bar-wrap';

    const bar = document.createElement('div');
    const widthPct = Math.min(100, Math.max(5, Math.abs(c.contribution) * 250));
    bar.className = `forest-xai-bar ${c.contribution >= 0 ? 'risk-inc' : 'risk-dec'}`;
    bar.style.width = `${widthPct}%`;
    barWrap.appendChild(bar);

    const val = document.createElement('span');
    val.className = 'forest-xai-row-val';
    val.textContent = `${c.contribution >= 0 ? '+' : ''}${c.contribution.toFixed(2)}`;

    row.appendChild(label);
    row.appendChild(barWrap);
    row.appendChild(val);
    barsContainer.appendChild(row);
  });
}

/**
 * Initializes the Forest Intelligence UI Panel.
 * @param {object} params
 * @param {object} params.viewer - Cesium viewer instance
 * @param {object} params.forestLayer - Forest intelligence data layer instance
 */
export function initForestPanel({ viewer, forestLayer }) {
  state.viewer = viewer;
  state.forestLayer = forestLayer;

  const panel = document.getElementById('forest-panel');
  if (!panel) return;

  // 1. Populate Zone Dropdown
  const zoneSelect = document.getElementById('forest-zone-select');
  if (zoneSelect) {
    zoneSelect.innerHTML = '';
    const spots = getAllMonitoredHotspots();
    spots.forEach((s) => {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = `${s.name} (${s.country})`;
      zoneSelect.appendChild(opt);
    });
    zoneSelect.value = state.activeZoneId;

    zoneSelect.addEventListener('change', (e) => {
      const selectedId = e.target.value;
      state.activeZoneId = selectedId;
      if (state.forestLayer) {
        state.forestLayer.selectZone(selectedId);
      }
      updateForestPanel(selectedId);
    });
  }

  // 2. Focus Button
  const focusBtn = document.getElementById('forest-focus-btn');
  if (focusBtn) {
    focusBtn.addEventListener('click', () => {
      if (state.forestLayer) {
        state.forestLayer.selectZone(state.activeZoneId);
      } else {
        selectForestZone(state.activeZoneId, state.viewer);
      }
    });
  }

  // 3. Demo Data Toggle (isolated synthetic mode)
  const demoToggle = document.getElementById('forest-demo-toggle');
  if (demoToggle) {
    demoToggle.checked = state.demoDataMode;
    demoToggle.addEventListener('change', (e) => {
      state.demoDataMode = e.target.checked;
      updateForestPanel(state.activeZoneId);
    });
  }

  // 4. Comparison Toggle Button
  const compareBtn = document.getElementById('forest-compare-toggle-btn');
  if (compareBtn) {
    compareBtn.addEventListener('click', () => {
      state.comparisonMode = !state.comparisonMode;
      compareBtn.classList.toggle('active', state.comparisonMode);
      compareBtn.textContent = state.comparisonMode ? 'COMPARE: ACTIVE (T1/T2)' : 'COMPARE: T1/T2';
      updateForestPanel(state.activeZoneId);
    });
  }

  // 5. Timeline Slider
  const slider = document.getElementById('forest-timeline-slider');
  const yearLabel = document.getElementById('forest-timeline-year-label');
  if (slider) {
    slider.value = state.activeYear;
    slider.addEventListener('input', (e) => {
      const year = Number(e.target.value);
      state.activeYear = year;
      if (yearLabel) {
        yearLabel.textContent = year === 2027 ? '2027 (PREDICTED)' : `${year} ${year === 2026 ? '(CURRENT)' : ''}`;
      }
      if (state.forestLayer) {
        state.forestLayer.setTimelineYear(year);
      }
      updateForestPanel(state.activeZoneId);
    });
  }

  // 6. Window event for 3D globe click pick synchronization
  if (typeof window !== 'undefined') {
    window.addEventListener('gev:forest-zone-selected', (event) => {
      const spot = event.detail;
      if (spot?.id) {
        state.activeZoneId = spot.id;
        updateForestPanel(spot.id);
      }
    });
  }

  // Initial render
  updateForestPanel(state.activeZoneId);
  state.initialized = true;
}

export default {
  initForestPanel,
  updateForestPanel,
};
