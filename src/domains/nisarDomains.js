import * as Cesium from 'cesium';

/**
 * NISAR 5 Scientific Domains Specification & Workspace Controller.
 * Manages domain metadata, API dataset synchronization, camera study-area navigation,
 * and scientific execution workflows.
 */
export const NISAR_DOMAINS = [
  {
    id: 'domain1',
    code: 'D1',
    title: 'FLOODS & WETLANDS',
    icon: '◈',
    studyArea: 'Thessaly, Greece',
    expectedCount: 11,
    statusText: '11 DATASETS',
    isDemonstration: false,
    camera: {
      lat: 39.51,
      lon: 22.88,
      height: 42000,
      pitch: -38,
      heading: 15,
    },
    studies: [
      { id: 'flood_extent', label: 'Flood Extent & Water Dynamics', default: true },
      { id: 'water_veg_interaction', label: 'Standing Water & Emergent Crops' },
      { id: 'slope_drainage', label: 'Topographic Slope Inundation Mask' },
    ],
    defaultInputs: {
      baseline: '5c351e81-1dfc-4d6b-9eec-9aed124eee8a',
      event: '15a8d70a-999e-4575-a2b7-b7b502f0dad8',
      reference_flood: 'ds-bench-thessaly-ref-flood',
      dem: 'ds-dem-thessaly-basin',
    },
    aoi: [21.8, 39.2, 23.1, 40.0],
  },
  {
    id: 'domain2',
    code: 'D2',
    title: 'FORESTS & WILDFIRES',
    icon: '◈',
    studyArea: 'Pará · Greece · California',
    expectedCount: 26,
    statusText: '26 DATASETS',
    isDemonstration: false,
    camera: {
      lat: -7.14,
      lon: -55.43,
      height: 48000,
      pitch: -35,
      heading: 0,
    },
    studies: [
      { id: 'canopy_disturbance', label: 'C-Band Canopy Disturbance (VH)', default: true },
      { id: 'wildfire_burn_scar', label: 'Burn Scar Severity & Crown Damage' },
      { id: 'thermal_corroboration', label: 'FIRMS Thermal Hotspot Corroboration' },
    ],
    defaultInputs: {
      baseline: 'ds-demo-d2-base',
      event: 'ds-demo-d2-event',
      forest_mask: 'ds-demo-d2-mask',
    },
    aoi: [-55.6, -7.5, -54.8, -6.8],
  },
  {
    id: 'domain3',
    code: 'D3',
    title: 'EARTHQUAKES & DEFORMATION',
    icon: '◈',
    studyArea: 'Tyrnavos, Greece',
    expectedCount: 6,
    statusText: '6 DATASETS',
    isDemonstration: false,
    camera: {
      lat: 39.76,
      lon: 22.28,
      height: 36000,
      pitch: -36,
      heading: 345,
    },
    studies: [
      { id: 'coseismic_displacement', label: 'Coseismic Surface Motion (LOS)', default: true },
      { id: 'coherence_filter', label: 'Interferometric Coherence Mask (>0.3)' },
      { id: 'strain_gradient', label: 'Deformation Gradient & Fault Trace' },
    ],
    defaultInputs: {
      displacement: 'ds-real-d4-disp',
      coherence: 'ds-real-d4-coh',
      reference_displacement: 'ds-real-d4-ref',
    },
    aoi: [22.0, 39.6, 22.4, 39.9],
  },
  {
    id: 'domain4',
    code: 'D4',
    title: 'AGRICULTURE & SOIL',
    icon: '◈',
    studyArea: 'Central Valley, California',
    expectedCount: 0,
    statusText: 'DEMONSTRATION',
    isDemonstration: true,
    camera: {
      lat: 36.65,
      lon: -119.85,
      height: 75000,
      pitch: -42,
      heading: 320,
    },
    studies: [
      { id: 'crop_phenology', label: 'Crop Phenology & Canopy Dynamics', default: true },
      { id: 'soil_roughness_proxy', label: 'Soil Moisture & Dielectric Proxy' },
      { id: 'parcel_masking', label: 'Agricultural Field Boundary Segmentation' },
    ],
    defaultInputs: {
      baseline: 'ds-demo-d2-base',
      monitoring: 'ds-demo-d2-event',
    },
    aoi: [-120.5, 36.2, -119.2, 37.1],
  },
  {
    id: 'domain5',
    code: 'D5',
    title: 'GLACIERS & SNOW/ICE',
    icon: '◈',
    studyArea: 'Jakobshavn, Greenland',
    expectedCount: 13,
    statusText: '13 DATASETS',
    isDemonstration: false,
    camera: {
      lat: 69.17,
      lon: -49.83,
      height: 50000,
      pitch: -42,
      heading: 280,
    },
    studies: [
      { id: 'ice_velocity', label: 'Ice Stream Velocity Dynamics', default: true },
      { id: 'terminus_calving', label: 'Terminus Calving Front Migration' },
      { id: 'interannual_anomaly', label: 'Velocity Anomaly vs Climatological Baseline' },
    ],
    defaultInputs: {
      velocity: 'ds-demo-d3-vel',
      reference_velocity: 'ds-demo-d3-ref',
    },
    aoi: [-50.5, 69.0, -49.2, 69.4],
  },
];

export class NisarDomainController {
  constructor(viewer, { container, onDomainActivated = null } = {}) {
    this.viewer = viewer;
    this.container = container;
    this.onDomainActivated = onDomainActivated;
    this.activeDomainId = null;
    this.datasetsByDomain = new Map();
    this.isRunningAnalysis = false;
    this.lastResult = null;

    this._initDom();
    this._fetchDatasets();
  }

  _initDom() {
    if (!this.container) return;
    this.container.innerHTML = '';
    this.container.classList.add('nisar-domains-container');

    // List View Container
    this.listView = document.createElement('div');
    this.listView.className = 'nisar-domain-list';
    this.container.appendChild(this.listView);

    // Workspace View Container (hidden by default)
    this.workspaceView = document.createElement('div');
    this.workspaceView.className = 'nisar-domain-workspace';
    this.workspaceView.hidden = true;
    this.container.appendChild(this.workspaceView);

    this.renderDomainList();
  }

  renderDomainList() {
    if (!this.listView) return;
    this.listView.innerHTML = '';

    for (const domain of NISAR_DOMAINS) {
      const card = document.createElement('div');
      card.className = `nisar-domain-card${this.activeDomainId === domain.id ? ' active' : ''}`;
      card.dataset.domainId = domain.id;

      // Header: Icon + Title
      const header = document.createElement('div');
      header.className = 'nisar-domain-header';
      header.innerHTML = `
        <span class="nisar-domain-icon">${domain.icon}</span>
        <span class="nisar-domain-title">${domain.title}</span>
      `;

      // Area subtitle
      const area = document.createElement('div');
      area.className = 'nisar-domain-area';
      area.textContent = domain.studyArea;

      // Footer: Count badge + OPEN button
      const footer = document.createElement('div');
      footer.className = 'nisar-domain-footer';

      const badge = document.createElement('span');
      badge.className = `nisar-domain-badge${domain.isDemonstration ? ' demo-badge' : ''}`;
      badge.id = `nisar-badge-${domain.id}`;
      badge.textContent = this._getBadgeText(domain);

      const openBtn = document.createElement('button');
      openBtn.className = `nisar-open-btn${this.activeDomainId === domain.id ? ' active' : ''}`;
      openBtn.type = 'button';
      openBtn.textContent = this.activeDomainId === domain.id ? 'ACTIVE' : 'OPEN';
      openBtn.title = `Open ${domain.title} scientific workspace`;

      openBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.openDomain(domain.id);
      });

      card.addEventListener('click', () => {
        this.openDomain(domain.id);
      });

      footer.appendChild(badge);
      footer.appendChild(openBtn);

      card.appendChild(header);
      card.appendChild(area);
      card.appendChild(footer);

      this.listView.appendChild(card);
    }
  }

  _getBadgeText(domain) {
    if (domain.isDemonstration) return 'DEMONSTRATION';
    const fetched = this.datasetsByDomain.get(domain.id);
    if (fetched && Array.isArray(fetched)) {
      return `${fetched.length} DATASETS`;
    }
    return domain.statusText;
  }

  async _fetchDatasets() {
    for (const domain of NISAR_DOMAINS) {
      try {
        const response = await fetch(`/api/datasets?domain=${domain.id}`);
        if (response.ok) {
          const datasets = await response.json();
          this.datasetsByDomain.set(domain.id, datasets);
          const badgeEl = document.getElementById(`nisar-badge-${domain.id}`);
          if (badgeEl && !domain.isDemonstration) {
            badgeEl.textContent = `${datasets.length} DATASETS`;
          }
        }
      } catch {
        // Fallback to static expected counts on offline / preview mode
        this.datasetsByDomain.set(domain.id, []);
      }
    }
  }

  openDomain(domainId) {
    const domain = NISAR_DOMAINS.find((d) => d.id === domainId);
    if (!domain) return;

    this.activeDomainId = domainId;
    this.renderDomainList();

    // Fly camera smoothly to domain study area
    this.flyToDomain(domain);

    // Render the scientific workspace view
    this.renderWorkspace(domain);

    // Notify listeners & right context rail
    if (typeof this.onDomainActivated === 'function') {
      this.onDomainActivated(domain);
    }
    window.dispatchEvent(
      new CustomEvent('gev:nisar-domain-activated', {
        detail: { domainId: domain.id, domain },
      })
    );
  }

  flyToDomain(domain) {
    if (!this.viewer?.camera || !domain.camera) return;
    const { lat, lon, height, pitch, heading } = domain.camera;

    this.viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lon, lat, height),
      orientation: {
        heading: Cesium.Math.toRadians(heading || 0),
        pitch: Cesium.Math.toRadians(pitch || -35),
        roll: 0.0,
      },
      duration: 2.8,
      easingFunction: Cesium.EasingFunction.CUBIC_IN_OUT,
    });
  }

  closeWorkspace() {
    this.activeDomainId = null;
    this.lastResult = null;
    if (this.workspaceView) this.workspaceView.hidden = true;
    if (this.listView) this.listView.hidden = false;
    this.renderDomainList();

    window.dispatchEvent(
      new CustomEvent('gev:nisar-domain-closed', {
        detail: {},
      })
    );
  }

  renderWorkspace(domain) {
    if (!this.workspaceView || !this.listView) return;

    this.listView.hidden = true;
    this.workspaceView.hidden = false;
    this.workspaceView.innerHTML = '';

    const datasets = this.datasetsByDomain.get(domain.id) || [];

    // Header & Back navigation
    const navBar = document.createElement('div');
    navBar.className = 'nisar-ws-nav';

    const backBtn = document.createElement('button');
    backBtn.className = 'nisar-ws-back-btn';
    backBtn.type = 'button';
    backBtn.innerHTML = `◀ ALL DOMAINS`;
    backBtn.addEventListener('click', () => this.closeWorkspace());

    const badge = document.createElement('span');
    badge.className = `nisar-domain-badge${domain.isDemonstration ? ' demo-badge' : ''}`;
    badge.textContent = domain.isDemonstration ? 'DEMO' : `${datasets.length || domain.expectedCount} DATASETS`;

    navBar.appendChild(backBtn);
    navBar.appendChild(badge);
    this.workspaceView.appendChild(navBar);

    // Domain Title Block
    const titleBlock = document.createElement('div');
    titleBlock.className = 'nisar-ws-title-block';
    titleBlock.innerHTML = `
      <div class="nisar-ws-code">${domain.code} · SCIENTIFIC WORKSPACE</div>
      <h3 class="nisar-ws-title">${domain.title}</h3>
      <div class="nisar-ws-area">📍 ${domain.studyArea}</div>
    `;
    this.workspaceView.appendChild(titleBlock);

    // Study selection section
    const studySection = document.createElement('div');
    studySection.className = 'nisar-ws-section';
    studySection.innerHTML = `<span class="nisar-ws-section-label">STUDY FOCUS</span>`;

    const studySelect = document.createElement('select');
    studySelect.className = 'nisar-ws-select';
    for (const study of domain.studies) {
      const opt = document.createElement('option');
      opt.value = study.id;
      opt.textContent = study.label;
      if (study.default) opt.selected = true;
      studySelect.appendChild(opt);
    }
    studySection.appendChild(studySelect);
    this.workspaceView.appendChild(studySection);

    // Available Datasets Section
    const dsSection = document.createElement('div');
    dsSection.className = 'nisar-ws-section';
    dsSection.innerHTML = `
      <div class="nisar-ws-section-header">
        <span class="nisar-ws-section-label">AVAILABLE DATASETS</span>
        <span class="nisar-ws-count">${datasets.length}</span>
      </div>
    `;

    const dsList = document.createElement('div');
    dsList.className = 'nisar-ws-dataset-list';
    if (datasets.length === 0) {
      dsList.innerHTML = `<div class="nisar-ws-empty">No direct datasets found in catalog. Using demonstration fixtures.</div>`;
    } else {
      datasets.slice(0, 5).forEach((d) => {
        const item = document.createElement('div');
        item.className = 'nisar-ws-dataset-item';
        const isReal = !d.is_synthetic;
        item.innerHTML = `
          <div class="nisar-ws-ds-top">
            <span class="nisar-ws-ds-name" title="${d.name}">${d.name}</span>
            <span class="nisar-ws-ds-type ${isReal ? 'real' : 'synth'}">${isReal ? 'REAL' : 'BENCHMARK'}</span>
          </div>
          <div class="nisar-ws-ds-meta">${d.product_type} · ${d.acquisition_date || 'Baseline'}</div>
        `;
        dsList.appendChild(item);
      });
      if (datasets.length > 5) {
        const more = document.createElement('div');
        more.className = 'nisar-ws-more';
        more.textContent = `+ ${datasets.length - 5} more observations in catalog`;
        dsList.appendChild(more);
      }
    }
    dsSection.appendChild(dsList);
    this.workspaceView.appendChild(dsSection);

    // Analysis Action Section
    const actionSection = document.createElement('div');
    actionSection.className = 'nisar-ws-action-section';

    const runBtn = document.createElement('button');
    runBtn.className = 'nisar-ws-run-btn';
    runBtn.type = 'button';
    runBtn.innerHTML = `<span>▶ RUN SCIENTIFIC PIPELINE</span>`;
    runBtn.disabled = this.isRunningAnalysis;

    const statusBanner = document.createElement('div');
    statusBanner.className = 'nisar-ws-status-banner';
    statusBanner.hidden = true;

    runBtn.addEventListener('click', async () => {
      await this._executePipeline(domain, runBtn, statusBanner);
    });

    actionSection.appendChild(runBtn);
    actionSection.appendChild(statusBanner);
    this.workspaceView.appendChild(actionSection);

    // Results container (populated after run or if previous result exists)
    this.resultsContainer = document.createElement('div');
    this.resultsContainer.className = 'nisar-ws-results';
    this.workspaceView.appendChild(this.resultsContainer);

    if (this.lastResult && this.lastResult.domainId === domain.id) {
      this._renderPipelineResults(this.lastResult.data);
    }
  }

  async _executePipeline(domain, runBtn, statusBanner) {
    if (this.isRunningAnalysis) return;
    this.isRunningAnalysis = true;
    runBtn.disabled = true;
    runBtn.innerHTML = `<span class="nisar-spin">◌</span> COMPUTING SAR PHYSICS...`;

    statusBanner.hidden = false;
    statusBanner.className = 'nisar-ws-status-banner info';
    statusBanner.textContent = 'Submitting pipeline execution request to backend...';

    try {
      const response = await fetch(`/api/domains/${domain.id}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          inputs: domain.defaultInputs || {},
          parameters: {},
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Pipeline error HTTP ${response.status}`);
      }

      const result = await response.json();
      this.lastResult = { domainId: domain.id, data: result };

      statusBanner.className = 'nisar-ws-status-banner success';
      statusBanner.textContent = `✓ Execution complete (${result.execution_time_ms ? result.execution_time_ms.toFixed(0) : '--'} ms)`;

      this._renderPipelineResults(result);

      window.dispatchEvent(
        new CustomEvent('gev:nisar-pipeline-completed', {
          detail: { domainId: domain.id, domain, result },
        })
      );
    } catch (error) {
      console.warn('[NISAR] Execution error:', error);
      statusBanner.className = 'nisar-ws-status-banner error';
      statusBanner.textContent = `Execution notice: ${error.message}`;
    } finally {
      this.isRunningAnalysis = false;
      runBtn.disabled = false;
      runBtn.innerHTML = `<span>▶ RE-RUN SCIENTIFIC PIPELINE</span>`;
    }
  }

  _renderPipelineResults(result) {
    if (!this.resultsContainer) return;
    this.resultsContainer.innerHTML = '';

    const heading = document.createElement('div');
    heading.className = 'nisar-ws-results-heading';
    heading.textContent = 'ANALYSIS RESULTS & METRICS';
    this.resultsContainer.appendChild(heading);

    // KPI Metrics Grid
    if (result.summary_metrics && Array.isArray(result.summary_metrics)) {
      const grid = document.createElement('div');
      grid.className = 'nisar-ws-metrics-grid';

      result.summary_metrics.forEach((metric) => {
        const card = document.createElement('div');
        card.className = 'nisar-metric-card';
        card.innerHTML = `
          <div class="nisar-metric-label">${metric.label}</div>
          <div class="nisar-metric-val">${metric.value} <small>${metric.unit || ''}</small></div>
          <div class="nisar-metric-desc">${metric.description || ''}</div>
        `;
        grid.appendChild(card);
      });
      this.resultsContainer.appendChild(grid);
    }

    // 4-Tier Explainability Card
    if (result.explanation) {
      const expBox = document.createElement('div');
      expBox.className = 'nisar-ws-explain-card';
      expBox.innerHTML = `
        <div class="nisar-explain-row"><strong>Visual Detection:</strong> ${result.explanation.level1_visual || 'N/A'}</div>
        <div class="nisar-explain-row"><strong>Applied Method:</strong> ${result.explanation.level2_method || 'N/A'}</div>
        <div class="nisar-explain-row"><strong>Evidence:</strong> ${result.explanation.level3_evidence || 'N/A'}</div>
        <div class="nisar-explain-row"><strong>Uncertainty:</strong> ${result.explanation.level4_uncertainty || 'N/A'}</div>
      `;
      this.resultsContainer.appendChild(expBox);
    }

    // Validation Status
    if (result.validation) {
      const valBox = document.createElement('div');
      valBox.className = 'nisar-ws-val-badge';
      valBox.innerHTML = `Validation: <strong>${result.validation.validation_category || result.validation.status}</strong> (${result.validation.reference_independence || 'Standard'})`;
      this.resultsContainer.appendChild(valBox);
    }
  }
}
