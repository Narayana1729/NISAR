import * as Cesium from 'cesium';

/**
 * NISAR Control Center (Right Panel Controller).
 * Manages display presets, context-sensitive scientific visualizations,
 * layer opacity, before/after comparison curtain, and scientific data legends.
 */

export const DOMAIN_VISUALIZATIONS = {
  domain1: [
    { id: 'sar_backscatter', label: 'SAR Backscatter (VV)', unit: 'dB', min: -25, max: 0, gradient: 'linear-gradient(to right, #050b14, #0077b6, #00f0ff, #ffffff)' },
    { id: 'inundation', label: 'Inundation Extent Mask', unit: 'Class', values: ['Open Water', 'Flooded Crops', 'Dry Land'], colors: ['#0077b6', '#00f0ff', 'transparent'] },
    { id: 'permanent_water', label: 'Permanent Water Delta', unit: 'Status', values: ['Permanent', 'Flood Dynamic', 'Dry'], colors: ['#03045e', '#00b4d8', 'transparent'] },
  ],
  domain2: [
    { id: 'sar_backscatter', label: 'Cross-Pol Backscatter (VH)', unit: 'dB', min: -28, max: -5, gradient: 'linear-gradient(to right, #001219, #005f73, #0a9396, #94d2bd)' },
    { id: 'canopy_disturbance', label: 'Canopy Disturbance (ΔVH)', unit: 'Loss %', min: 0, max: 100, gradient: 'linear-gradient(to right, #38b000, #ffb703, #e63946)' },
    { id: 'burn_severity', label: 'Burn Scar Severity', unit: 'Severity', values: ['Low', 'Moderate', 'High Crown'], colors: ['#ffb703', '#fb8500', '#d90429'] },
    { id: 'firms_thermal', label: 'FIRMS Thermal Spots', unit: 'FRP (MW)', min: 5, max: 150, gradient: 'linear-gradient(to right, #ffee38, #ff5400, #d00000)' },
  ],
  domain3: [
    { id: 'interferometric', label: 'Interferometric Phase', unit: 'rad', min: -3.14, max: 3.14, gradient: 'linear-gradient(to right, #ff0000, #ffff00, #00ff00, #00ffff, #0000ff, #ff00ff, #ff0000)' },
    { id: 'displacement', label: 'Surface Motion (LOS)', unit: 'mm', min: -350, max: 100, gradient: 'linear-gradient(to right, #7209b7, #3a0ca3, #4361ee, #4cc9f0, #ffffff)' },
    { id: 'coherence', label: 'Coherence Quality Mask', unit: 'γ (0-1)', min: 0.3, max: 1.0, gradient: 'linear-gradient(to right, #333333, #70e000, #00f0ff)' },
  ],
  domain4: [
    { id: 'sar_backscatter', label: 'Dual-Pol Backscatter (VV/VH)', unit: 'Ratio', min: 2, max: 10, gradient: 'linear-gradient(to right, #2b2d42, #8d99ae, #edf2f4)' },
    { id: 'crop_phenology', label: 'Crop Phenology Index', unit: 'Index', values: ['Bare Soil', 'Emergence', 'Peak Canopy', 'Senescence'], colors: ['#d4a373', '#ccd5ae', '#2d6a4f', '#bc6c25'] },
    { id: 'soil_moisture', label: 'Soil Dielectric Proxy', unit: 'εr', min: 5, max: 35, gradient: 'linear-gradient(to right, #e9c46a, #2a9d8f, #264653)' },
  ],
  domain5: [
    { id: 'velocity', label: 'Ice Stream Velocity', unit: 'm/yr', min: 0, max: 14000, gradient: 'linear-gradient(to right, #03045e, #0077b6, #00b4d8, #90e0ef, #caf0f8, #ffffff)' },
    { id: 'calving_front', label: 'Calving Front Edge', unit: 'Edge', values: ['Ice Tongue', 'Melange Ice', 'Open Fjord'], colors: ['#caf0f8', '#0077b6', '#03045e'] },
    { id: 'velocity_anomaly', label: 'Velocity Anomaly', unit: 'Δ m/yr', min: -2000, max: 2000, gradient: 'linear-gradient(to right, #0077b6, #ffffff, #d90429)' },
  ],
  default: [
    { id: 'sar_backscatter', label: 'SAR Backscatter', unit: 'dB', min: -30, max: 0, gradient: 'linear-gradient(to right, #0a0a0f, #0077b6, #00f0ff)' },
    { id: 'interferometric', label: 'Interferometric Phase', unit: 'rad', min: -3.14, max: 3.14, gradient: 'linear-gradient(to right, #ff0000, #00ff00, #0000ff)' },
    { id: 'displacement', label: 'Surface Motion', unit: 'mm', min: -100, max: 100, gradient: 'linear-gradient(to right, #7209b7, #4cc9f0, #ffffff)' },
    { id: 'classification', label: 'Classification', unit: 'Class', values: ['Background', 'Target', 'Anomaly'], colors: ['#333333', '#00f0ff', '#ffb703'] },
  ],
};

export class NisarControlCenter {
  constructor(viewer, { container = null, styleManager = null } = {}) {
    this.viewer = viewer;
    this.container = container || document.getElementById('pp-toggles');
    this.styleManager = styleManager;
    this.activeDomainId = null;
    this.activeDomain = null;
    this.activeResult = null;
    this.activeVizId = 'sar_backscatter';
    this.opacity = 0.75;
    this.layerVisible = true;
    this.comparisonMode = 'live'; // 'live', 'before', 'after', 'swipe'
    this.showReference = true;
    this.showBoundaries = true;
    this.showLegend = true;
    this.splitPosition = 0.5;
    this.sarLayers = new Map();
    this.aoiEntity = null;

    this._initDom();
    this._wireDomainEvents();
  }

  _initDom() {
    if (!this.container) return;

    // Render the NISAR Control Center inside #pp-toggles
    this.container.innerHTML = `
      <div class="compact pp-header-row">
        <span class="pp-header-label">NISAR CONTROL CENTER</span>
        <span class="panel-divider" aria-hidden="true"></span>
        <button class="panel-collapse-btn pp-collapse-btn" data-collapse-target="pp-toggles" title="Collapse panel">&#x25C0;</button>
      </div>

      <!-- 1. DISPLAY -->
      <div class="nisar-cc-group">
        <div class="nisar-cc-heading">DISPLAY</div>
        <div class="nisar-cc-seg" role="radiogroup" aria-label="HUD Display Mode">
          <button type="button" class="nisar-cc-seg-btn active" id="nisar-hud-sci" data-layout="tactical">◉ Scientific HUD</button>
          <button type="button" class="nisar-cc-seg-btn" id="nisar-hud-min" data-layout="minimal">○ Minimal</button>
        </div>
      </div>

      <!-- 2. VISUALIZATION (Context-Sensitive) -->
      <div class="nisar-cc-group">
        <div class="nisar-cc-heading">
          <span>VISUALIZATION</span>
          <span class="nisar-cc-sub" id="nisar-viz-domain-tag">GLOBAL</span>
        </div>
        <div class="nisar-cc-radio-list" id="nisar-viz-options">
          <!-- Dynamically populated based on active domain -->
        </div>
      </div>

      <!-- 3. MAP SETTINGS -->
      <div class="nisar-cc-group">
        <div class="nisar-cc-heading">MAP SETTINGS</div>
        <div class="nisar-cc-slider-row">
          <label class="nisar-cc-slider-label" for="nisar-opacity-slider">Opacity</label>
          <input type="range" class="nisar-cc-slider" id="nisar-opacity-slider" min="0" max="100" step="5" value="75" />
          <span class="nisar-cc-slider-val" id="nisar-opacity-val">75%</span>
        </div>
        <div class="nisar-cc-row-between">
          <span class="nisar-cc-label">Layer Visibility</span>
          <button type="button" class="nisar-cc-toggle-btn active" id="nisar-layer-vis-btn">ON</button>
        </div>
      </div>

      <!-- 4. COMPARISON -->
      <div class="nisar-cc-group">
        <div class="nisar-cc-heading">COMPARISON</div>
        <div class="nisar-cc-btn-row">
          <button type="button" class="nisar-cc-action-btn active" id="nisar-comp-live" title="Show current monitoring SAR observation">Live</button>
          <button type="button" class="nisar-cc-action-btn" id="nisar-comp-before" title="Show baseline SAR acquisition">Before (T1)</button>
          <button type="button" class="nisar-cc-action-btn" id="nisar-comp-after" title="Show event/post SAR acquisition">After (T2)</button>
        </div>
        <button type="button" class="nisar-cc-swipe-btn" id="nisar-comp-swipe">
          <span class="material-symbols-outlined" style="font-size: 14px;">compare</span>
          <span>Toggle Swipe Comparison</span>
        </button>
      </div>

      <!-- 5. DATA DISPLAY & SCIENTIFIC LEGEND -->
      <div class="nisar-cc-group">
        <div class="nisar-cc-heading">DATA DISPLAY</div>
        <div class="nisar-cc-checkbox-list">
          <label class="nisar-cc-checkbox-label">
            <input type="checkbox" id="nisar-toggle-ref" checked />
            <span>Reference Ground Truth</span>
          </label>
          <label class="nisar-cc-checkbox-label">
            <input type="checkbox" id="nisar-toggle-bound" checked />
            <span>AOI / Basin Boundaries</span>
          </label>
          <label class="nisar-cc-checkbox-label">
            <input type="checkbox" id="nisar-toggle-legend" checked />
            <span>Scientific Legend</span>
          </label>
        </div>
        <div class="nisar-cc-legend-box" id="nisar-scientific-legend">
          <!-- Dynamic gradient and value ticks -->
        </div>
      </div>

      <!-- 6. OPTICAL SHADERS & EFFECTS (Secondary Collapsible) -->
      <div class="nisar-cc-group nisar-cc-subgroup">
        <details class="nisar-cc-details">
          <summary class="nisar-cc-details-summary">SCIENTIFIC VISUAL EFFECTS</summary>
          <div class="nisar-cc-effects-body">
            <div class="nisar-cc-slider-row">
              <label class="nisar-cc-slider-label">Bloom</label>
              <input type="range" class="nisar-cc-slider" id="nisar-bloom-slider" min="0" max="200" value="0" />
              <span class="nisar-cc-slider-val" id="nisar-bloom-val">0%</span>
            </div>
            <div class="nisar-cc-slider-row">
              <label class="nisar-cc-slider-label">Sharpen</label>
              <input type="range" class="nisar-cc-slider" id="nisar-sharpen-slider" min="0" max="100" value="49" />
              <span class="nisar-cc-slider-val" id="nisar-sharpen-val">49%</span>
            </div>
          </div>
        </details>
      </div>
    `;

    // Render interactive swipe divider on globe
    this._initSwipeDivider();

    // Wire listeners
    this._wireControls();
    this.updateVisualizationOptions(null);
  }

  _wireDomainEvents() {
    window.addEventListener('gev:nisar-domain-activated', (e) => {
      const { domainId, domain } = e.detail;
      this.activeDomainId = domainId;
      this.activeDomain = domain;
      this.updateVisualizationOptions(domain);
      this.setAoiBoundary(domain);
      this.clearSarLayers();
    });

    window.addEventListener('gev:nisar-domain-closed', () => {
      this.activeDomainId = null;
      this.activeDomain = null;
      this.updateVisualizationOptions(null);
      this.setAoiBoundary(null);
      this.clearSarLayers();
    });

    window.addEventListener('gev:nisar-pipeline-completed', async (e) => {
      const { domainId, domain, result } = e.detail;
      if (domain) {
        this.activeDomainId = domainId;
        this.activeDomain = domain;
      }
      await this.loadResultLayers(result);
    });
  }

  updateVisualizationOptions(domain) {
    const listEl = document.getElementById('nisar-viz-options');
    const tagEl = document.getElementById('nisar-viz-domain-tag');
    if (!listEl) return;

    listEl.innerHTML = '';
    const vizList = domain ? (DOMAIN_VISUALIZATIONS[domain.id] || DOMAIN_VISUALIZATIONS.default) : DOMAIN_VISUALIZATIONS.default;

    if (tagEl) {
      tagEl.textContent = domain ? `${domain.code} · ${domain.title}` : 'GLOBAL';
    }

    vizList.forEach((viz, index) => {
      const label = document.createElement('label');
      label.className = `nisar-viz-radio-label${index === 0 ? ' selected' : ''}`;
      label.innerHTML = `
        <input type="radio" name="nisar-viz-mode" value="${viz.id}" ${index === 0 ? 'checked' : ''} />
        <span class="nisar-viz-radio-text">${viz.label}</span>
      `;

      label.querySelector('input').addEventListener('change', () => {
        listEl.querySelectorAll('.nisar-viz-radio-label').forEach((el) => el.classList.remove('selected'));
        label.classList.add('selected');
        this.activeVizId = viz.id;
        this.renderLegend(viz);
      });

      listEl.appendChild(label);
    });

    // Render legend for first visualization
    if (vizList.length > 0) {
      this.activeVizId = vizList[0].id;
      this.renderLegend(vizList[0]);
    }
  }

  renderLegend(viz) {
    const legendEl = document.getElementById('nisar-scientific-legend');
    if (!legendEl || !this.showLegend) {
      if (legendEl) legendEl.hidden = true;
      return;
    }
    legendEl.hidden = false;
    legendEl.innerHTML = '';

    const titleRow = document.createElement('div');
    titleRow.className = 'nisar-legend-title';
    titleRow.innerHTML = `<span>${viz.label}</span><small>${viz.unit || ''}</small>`;
    legendEl.appendChild(titleRow);

    if (viz.gradient) {
      const bar = document.createElement('div');
      bar.className = 'nisar-legend-bar';
      bar.style.background = viz.gradient;
      legendEl.appendChild(bar);

      const ticks = document.createElement('div');
      ticks.className = 'nisar-legend-ticks';
      ticks.innerHTML = `
        <span>${viz.min != null ? viz.min : ''}</span>
        <span>${viz.min != null && viz.max != null ? ((viz.min + viz.max) / 2).toFixed(1) : ''}</span>
        <span>${viz.max != null ? viz.max : ''}</span>
      `;
      legendEl.appendChild(ticks);
    } else if (viz.values && viz.colors) {
      const classList = document.createElement('div');
      classList.className = 'nisar-legend-classes';
      viz.values.forEach((val, i) => {
        const item = document.createElement('div');
        item.className = 'nisar-legend-class-item';
        item.innerHTML = `
          <span class="nisar-legend-swatch" style="background:${viz.colors[i] || '#ccc'}"></span>
          <span>${val}</span>
        `;
        classList.appendChild(item);
      });
      legendEl.appendChild(classList);
    }
  }

  _initSwipeDivider() {
    let curtain = document.getElementById('cesium-split-curtain');
    if (!curtain) {
      curtain = document.createElement('div');
      curtain.id = 'cesium-split-curtain';
      curtain.className = 'cesium-split-curtain';
      curtain.hidden = true;
      curtain.innerHTML = `
        <div class="cesium-split-line"></div>
        <div class="cesium-split-handle">◀ || ▶</div>
      `;
      document.body.appendChild(curtain);

      // Drag listener for swipe curtain
      let isDragging = false;
      const onMove = (clientX) => {
        const width = window.innerWidth;
        const pos = Math.max(0.05, Math.min(0.95, clientX / width));
        this.splitPosition = pos;
        curtain.style.left = `${pos * 100}%`;
        if (this.viewer?.scene) {
          this.viewer.scene.splitPosition = pos;
          this.viewer.scene.requestRender();
        }
      };

      curtain.addEventListener('mousedown', (e) => {
        isDragging = true;
        e.preventDefault();
      });

      window.addEventListener('mousemove', (e) => {
        if (isDragging) onMove(e.clientX);
      });

      window.addEventListener('mouseup', () => {
        isDragging = false;
      });

      window.addEventListener('touchmove', (e) => {
        if (isDragging && e.touches[0]) onMove(e.touches[0].clientX);
      });
      window.addEventListener('touchend', () => {
        isDragging = false;
      });
    }
    this.splitCurtain = curtain;
  }

  _wireControls() {
    // 0. Panel collapse button
    const collapseBtn = this.container?.querySelector('.pp-collapse-btn');
    if (collapseBtn) {
      collapseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (this.styleManager?.setPanelCollapsed) {
          const nextCollapsed = !this.container.classList.contains('collapsed');
          this.styleManager.setPanelCollapsed('pp-toggles', nextCollapsed, { explicit: true });
        } else {
          this.container.classList.toggle('collapsed');
        }
      });
    }

    // 1. Display Mode (Scientific HUD vs Minimal)
    const sciBtn = document.getElementById('nisar-hud-sci');
    const minBtn = document.getElementById('nisar-hud-min');

    if (sciBtn && minBtn) {
      sciBtn.addEventListener('click', () => {
        sciBtn.classList.add('active');
        minBtn.classList.remove('active');
        if (this.styleManager?._setHudVariant) {
          this.styleManager._setHudVariant('tactical');
        }
      });
      minBtn.addEventListener('click', () => {
        minBtn.classList.add('active');
        sciBtn.classList.remove('active');
        if (this.styleManager?._setHudVariant) {
          this.styleManager._setHudVariant('minimal');
        }
      });
    }

    // 2. Opacity Slider
    const opacitySlider = document.getElementById('nisar-opacity-slider');
    const opacityVal = document.getElementById('nisar-opacity-val');
    if (opacitySlider && opacityVal) {
      opacitySlider.addEventListener('input', (e) => {
        this.opacity = parseInt(e.target.value, 10) / 100;
        opacityVal.textContent = `${e.target.value}%`;
        this.applyLayerSettings();
      });
    }

    // 3. Layer Visibility Toggle
    const visBtn = document.getElementById('nisar-layer-vis-btn');
    if (visBtn) {
      visBtn.addEventListener('click', () => {
        this.layerVisible = !this.layerVisible;
        visBtn.textContent = this.layerVisible ? 'ON' : 'OFF';
        visBtn.classList.toggle('active', this.layerVisible);
        this.applyLayerSettings();
      });
    }

    // 4. Comparison Buttons
    const liveBtn = document.getElementById('nisar-comp-live');
    const beforeBtn = document.getElementById('nisar-comp-before');
    const afterBtn = document.getElementById('nisar-comp-after');
    const swipeBtn = document.getElementById('nisar-comp-swipe');

    const setComp = (mode, btn) => {
      this.comparisonMode = mode;
      [liveBtn, beforeBtn, afterBtn].forEach((b) => b?.classList.remove('active'));
      btn?.classList.add('active');
      if (mode !== 'swipe' && this.splitCurtain) {
        this.splitCurtain.hidden = true;
        swipeBtn?.classList.remove('active');
      }
      this.applyComparisonMode();
    };

    liveBtn?.addEventListener('click', () => setComp('live', liveBtn));
    beforeBtn?.addEventListener('click', () => setComp('before', beforeBtn));
    afterBtn?.addEventListener('click', () => setComp('after', afterBtn));

    swipeBtn?.addEventListener('click', () => {
      const isNowSwipe = this.comparisonMode !== 'swipe';
      if (isNowSwipe) {
        this.comparisonMode = 'swipe';
        [liveBtn, beforeBtn, afterBtn].forEach((b) => b?.classList.remove('active'));
        swipeBtn.classList.add('active');
        if (this.splitCurtain) {
          this.splitCurtain.hidden = false;
          this.splitCurtain.style.left = `${this.splitPosition * 100}%`;
          if (this.viewer?.scene) {
            this.viewer.scene.splitPosition = this.splitPosition;
          }
        }
      } else {
        setComp('live', liveBtn);
      }
      this.applyComparisonMode();
    });

    // 5. Data Display checkboxes
    const refToggle = document.getElementById('nisar-toggle-ref');
    refToggle?.addEventListener('change', (e) => {
      this.showReference = e.target.checked;
      this.applyLayerSettings();
    });

    const boundToggle = document.getElementById('nisar-toggle-bound');
    boundToggle?.addEventListener('change', (e) => {
      this.showBoundaries = e.target.checked;
      if (this.aoiEntity) {
        this.aoiEntity.show = this.showBoundaries;
        this.viewer?.scene?.requestRender();
      }
    });

    const legendToggle = document.getElementById('nisar-toggle-legend');
    legendToggle?.addEventListener('change', (e) => {
      this.showLegend = e.target.checked;
      const vizList = this.activeDomain ? (DOMAIN_VISUALIZATIONS[this.activeDomain.id] || DOMAIN_VISUALIZATIONS.default) : DOMAIN_VISUALIZATIONS.default;
      const currentViz = vizList.find((v) => v.id === this.activeVizId) || vizList[0];
      if (currentViz) this.renderLegend(currentViz);
    });

    // 6. Effects Sliders
    const bloomSlider = document.getElementById('nisar-bloom-slider');
    const bloomVal = document.getElementById('nisar-bloom-val');
    if (bloomSlider) {
      bloomSlider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        if (bloomVal) bloomVal.textContent = `${val}%`;
        if (this.styleManager?._setBloomIntensity) {
          this.styleManager._setBloomIntensity(val);
        }
      });
    }

    const sharpenSlider = document.getElementById('nisar-sharpen-slider');
    const sharpenVal = document.getElementById('nisar-sharpen-val');
    if (sharpenSlider) {
      sharpenSlider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        if (sharpenVal) sharpenVal.textContent = `${val}%`;
        if (this.styleManager?._setSharpenIntensity) {
          this.styleManager._setSharpenIntensity(val);
        }
      });
    }
  }

  async loadResultLayers(result) {
    this.clearSarLayers();
    if (!result?.layers || !this.viewer?.imageryLayers) return;
    this.activeResult = result;

    for (const layerDef of result.layers) {
      if (layerDef.kind !== 'preview' || !layerDef.url || !layerDef.bounds_wgs84) continue;
      const [west, south, east, north] = layerDef.bounds_wgs84;
      try {
        const provider = await Cesium.SingleTileImageryProvider.fromUrl(layerDef.url, {
          rectangle: Cesium.Rectangle.fromDegrees(west, south, east, north),
        });
        const layer = new Cesium.ImageryLayer(provider, {
          alpha: this.opacity,
          show: this.layerVisible,
        });
        this.viewer.imageryLayers.add(layer);
        this.sarLayers.set(layerDef.key, { layer, def: layerDef });
      } catch (err) {
        console.warn('[NISAR CC] Could not load raster overlay:', layerDef.key, err);
      }
    }
    this.applyComparisonMode();
  }

  clearSarLayers() {
    if (!this.viewer?.imageryLayers) return;
    for (const { layer } of this.sarLayers.values()) {
      try {
        this.viewer.imageryLayers.remove(layer, true);
      } catch { /* ignored */ }
    }
    this.sarLayers.clear();
    if (this.splitCurtain) this.splitCurtain.hidden = true;
    this.viewer?.scene?.requestRender();
  }

  setAoiBoundary(domain) {
    if (this.aoiEntity && this.viewer?.entities) {
      this.viewer.entities.remove(this.aoiEntity);
      this.aoiEntity = null;
    }
    if (domain?.aoi && this.viewer?.entities) {
      const [west, south, east, north] = domain.aoi;
      this.aoiEntity = this.viewer.entities.add({
        name: `${domain.title} AOI Boundary`,
        rectangle: {
          coordinates: Cesium.Rectangle.fromDegrees(west, south, east, north),
          fill: false,
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString('#00d4ff'),
          outlineWidth: 2,
        },
        show: this.showBoundaries,
      });
    }
    this.viewer?.scene?.requestRender();
  }

  applyLayerSettings() {
    if (!this.viewer?.scene) return;
    for (const [key, { layer }] of this.sarLayers.entries()) {
      layer.alpha = this.opacity;
    }
    this.applyComparisonMode();
  }

  applyComparisonMode() {
    if (!this.viewer?.scene) return;
    const isSwipe = this.comparisonMode === 'swipe';
    const isBefore = this.comparisonMode === 'before';
    const isAfter = this.comparisonMode === 'after';
    const isLive = this.comparisonMode === 'live';

    for (const [key, { layer, def }] of this.sarLayers.entries()) {
      const isBaseline = key.includes('baseline') || key === 'sar_backscatter';
      const isValidation = key.includes('validation') || key.includes('ref');

      if (isValidation && !this.showReference) {
        layer.show = false;
        continue;
      }

      if (!this.layerVisible) {
        layer.show = false;
        continue;
      }

      if (isSwipe) {
        layer.show = true;
        if (isBaseline) {
          layer.splitDirection = Cesium.SplitDirection.LEFT;
        } else {
          layer.splitDirection = Cesium.SplitDirection.RIGHT;
        }
      } else if (isBefore) {
        layer.splitDirection = Cesium.SplitDirection.NONE;
        layer.show = isBaseline;
      } else if (isAfter || isLive) {
        layer.splitDirection = Cesium.SplitDirection.NONE;
        layer.show = !isBaseline;
      }
    }

    if (isSwipe && this.splitCurtain) {
      this.splitCurtain.hidden = false;
      this.viewer.scene.splitPosition = this.splitPosition;
    } else if (this.splitCurtain) {
      this.splitCurtain.hidden = true;
    }

    this.viewer.scene.requestRender();
  }
}
