/**
 * @module forestIntelligence
 * @description Cesium GIS data layer for AI-based deforestation detection, risk prediction, and temporal analysis.
 * Renders color-coded 3D ground polygons, publishes WorldOverlay ambient cards, and handles entity picking.
 */

import * as Cesium from 'cesium';
import { governorRequestRender } from '../renderGovernor.js';
import { getAllMonitoredHotspots, getHotspotById } from './forestCatalog.js';
import {
  clearOverlaySource,
  setOverlayEntries,
  setOverlaySourceVisible,
} from '../overlays/worldOverlay.js';
import { registerPickOwner, unregisterPickOwner, resolvePickId } from './pickRegistry.js';
import { registerEntityContext, selectEntityContext } from './contextStore.js';

export const FOREST_OVERLAY_SOURCE_ID = 'forest-intelligence';
export const FOREST_OVERLAY_COHORT_LIMIT = 32;
export const FOREST_OVERLAY_COLLISION_CAPACITY = 16;

/** Color mapping for forest condition & risk classifications */
export const FOREST_ZONE_COLORS = Object.freeze({
  HEALTHY_FOREST: Cesium.Color.fromCssColorString('#2ecc71'),
  VEGETATION_CHANGE: Cesium.Color.fromCssColorString('#f1c40f'),
  GRADUAL_DEGRADATION: Cesium.Color.fromCssColorString('#e67e22'),
  CONFIRMED_FOREST_LOSS: Cesium.Color.fromCssColorString('#e74c3c'),
  PREDICTED_HIGH_RISK: Cesium.Color.fromCssColorString('#9b59b6'),
  BURN_RELATED_FOREST_LOSS: Cesium.Color.fromCssColorString('#e65100'),
});

/**
 * Creates an overlay entry for one forest hotspot.
 * @param {object} spot - Hotspot record
 * @returns {object} WorldOverlay card entry
 */
export function createForestOverlayEntry(spot) {
  const cartesian = Cesium.Cartesian3.fromDegrees(spot.centroid.lon, spot.centroid.lat, 150);
  const lossPct = spot.latest_metrics?.forest_loss_percent ?? 0;
  const risk = spot.current_risk_level || 'MODERATE';

  return {
    id: `forest:${spot.id}`,
    position: cartesian,
    variant: 'card',
    title: spot.name.toUpperCase(),
    primary: `${spot.country} · ${risk} RISK`,
    secondary: `-${lossPct}% CANOPY LOSS · ${spot.latest_metrics?.active_fire_count || 0} FIRES`,
    accent: spot.risk_color || '#e74c3c',
    priority: Math.round(lossPct * 100) + (risk === 'CRITICAL' ? 500 : 0),
    collisionGroup: 'ambient-card',
    paintLane: 'ambient-card',
    interactive: true,
    edgeFade: 'keyhole',
    horizonCull: true,
    terrainOcclusion: true,
    gapPx: 12,
    placement: 'above',
    sourceData: spot,
  };
}

/**
 * Selects a forest zone, flying the camera and updating context.
 * @param {string} spotId
 * @param {object} [viewer]
 */
export function selectForestZone(spotId, viewer) {
  const spot = getHotspotById(spotId);
  if (!spot) return false;

  const targetViewer = viewer;
  if (targetViewer?.camera) {
    targetViewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        spot.centroid.lon,
        spot.centroid.lat - 0.4,
        85000,
      ),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-40),
        roll: 0,
      },
      duration: 2.0,
    });
  }

  if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
    window.dispatchEvent(new CustomEvent('gev:forest-zone-selected', { detail: spot }));
  }
  return true;
}

/**
 * Factory creating the Forest Intelligence data layer.
 * @returns {object} Layer compliant with DataLayerManager
 */
export function createForestIntelligenceLayer() {
  let _viewer = null;
  let _dataSource = null;
  let _clickHandler = null;
  let _enabled = false;
  let _activeYear = 2026;
  let _lastUpdate = null;
  let _lastError = null;

  function renderEntities() {
    if (!_dataSource) return;
    _dataSource.entities.removeAll();

    const spots = getAllMonitoredHotspots();
    const overlayEntries = [];

    for (const spot of spots) {
      // Find metric for active timeline year
      const yearRecord = spot.timeline?.find((t) => t.year === _activeYear)
        || spot.timeline?.[spot.timeline.length - 1];
      const cover = yearRecord?.canopy_cover_percent ?? 60.0;

      // Color based on risk/condition
      let baseColor = FOREST_ZONE_COLORS.CONFIRMED_FOREST_LOSS;
      if (spot.classification === 'BURN_RELATED_FOREST_LOSS') {
        baseColor = FOREST_ZONE_COLORS.BURN_RELATED_FOREST_LOSS;
      } else if (spot.classification === 'GRADUAL_DEGRADATION') {
        baseColor = FOREST_ZONE_COLORS.GRADUAL_DEGRADATION;
      } else if (cover >= 80) {
        baseColor = FOREST_ZONE_COLORS.HEALTHY_FOREST;
      }

      const polygonHierarchy = Cesium.Cartesian3.fromDegreesArray(
        spot.polygon_coordinates.flat(),
      );

      const entity = _dataSource.entities.add({
        id: `forest-entity:${spot.id}`,
        name: spot.name,
        polygon: {
          hierarchy: polygonHierarchy,
          material: baseColor.withAlpha(0.35),
          outline: true,
          outlineColor: baseColor.withAlpha(0.9),
          outlineWidth: 2,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        },
        properties: {
          forestSpotId: spot.id,
          country: spot.country,
          biome: spot.biome,
          coverPercent: cover,
          riskLevel: spot.current_risk_level,
        },
      });

      if (typeof window !== 'undefined') {
        registerEntityContext(entity, {
          id: spot.id,
          layerId: 'forest-intelligence',
          name: spot.name,
          subtitle: `${spot.country} · ${spot.biome}`,
          status: spot.status,
          metrics: spot.latest_metrics,
          provenance: spot.provenance,
          timeline: spot.timeline,
        });
      }

      overlayEntries.push(createForestOverlayEntry(spot));
    }

    if (_enabled) {
      setOverlayEntries(FOREST_OVERLAY_SOURCE_ID, overlayEntries, {
        cohortLimit: FOREST_OVERLAY_COHORT_LIMIT,
        collisionCapacity: FOREST_OVERLAY_COLLISION_CAPACITY,
        moving: false,
      });
    }
  }

  const layer = {
    id: 'forest-intelligence',
    name: 'Forest Intelligence',
    icon: '🌳',
    source: 'Sentinel-2 / Landsat · AI',
    showInTogglePanel: true,

    init(viewer) {
      _viewer = viewer;
      _dataSource = new Cesium.CustomDataSource('forest-intelligence');
      _viewer.dataSources.add(_dataSource);
      _dataSource.show = false;

      if (_viewer?.scene?.canvas) {
        _clickHandler = new Cesium.ScreenSpaceEventHandler(_viewer.scene.canvas);
        _clickHandler.setInputAction((click) => {
          if (!_enabled) return;
          const picked = _viewer.scene.pick(click.position);
          const id = resolvePickId(picked);
          if (id && (id.startsWith('forest-entity:') || id.startsWith('forest:'))) {
            const spotId = id.replace('forest-entity:', '').replace('forest:', '');
            layer.selectZone(spotId);
          }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
      }

      renderEntities();
      _lastUpdate = Date.now();
      return true;
    },

    selectZone(spotId) {
      const spot = getHotspotById(spotId);
      if (spot && _viewer) {
        const entity = _dataSource?.entities?.getById(`forest-entity:${spotId}`);
        if (entity && typeof window !== 'undefined') selectEntityContext(entity);
        selectForestZone(spotId, _viewer);
      }
    },

    async show() {
      _enabled = true;
      registerPickOwner('forest-intelligence', (id) => typeof id === 'string' && (id.startsWith('forest-entity:') || id.startsWith('forest:')));
      if (_dataSource) _dataSource.show = true;
      setOverlaySourceVisible(FOREST_OVERLAY_SOURCE_ID, true);
      renderEntities();
      governorRequestRender('forest-layer-show');
      return true;
    },

    hide() {
      _enabled = false;
      unregisterPickOwner('forest-intelligence');
      if (_dataSource) _dataSource.show = false;
      clearOverlaySource(FOREST_OVERLAY_SOURCE_ID);
      setOverlaySourceVisible(FOREST_OVERLAY_SOURCE_ID, false);
      governorRequestRender('forest-layer-hide');
      return true;
    },

    async enable(viewer) {
      if (viewer && !_viewer) _viewer = viewer;
      return this.show();
    },

    disable(viewer) {
      if (viewer && !_viewer) _viewer = viewer;
      return this.hide();
    },

    async update() {
      if (_enabled) {
        renderEntities();
      }
      return true;
    },

    destroy(viewer) {
      _enabled = false;
      clearOverlaySource(FOREST_OVERLAY_SOURCE_ID);
      setOverlaySourceVisible(FOREST_OVERLAY_SOURCE_ID, false);
      unregisterPickOwner('forest-intelligence');
      if (_clickHandler) {
        _clickHandler.destroy();
        _clickHandler = null;
      }
      if (_dataSource && viewer?.dataSources) {
        viewer.dataSources.remove(_dataSource, true);
        _dataSource = null;
      }
      _viewer = null;
      _lastUpdate = null;
      _lastError = null;
    },

    setTimelineYear(year) {
      _activeYear = Number(year) || 2026;
      renderEntities();
      governorRequestRender('forest-timeline-step');
    },

    getAnalystRecords() {
      return getAllMonitoredHotspots().map((s) => ({
        id: s.id,
        name: s.name,
        country: s.country,
        loss_percent: s.latest_metrics.forest_loss_percent,
        loss_area_km2: s.latest_metrics.estimated_loss_area_km2,
        risk_level: s.current_risk_level,
        fires_detected: s.latest_metrics.active_fire_count,
        provenance_source: s.provenance.source,
      }));
    },

    getStats() {
      const spots = getAllMonitoredHotspots();
      const highRisk = spots.filter((s) => s.current_risk_level === 'CRITICAL' || s.current_risk_level === 'HIGH').length;
      return {
        count: spots.length,
        highRiskCount: highRisk,
        activeAlerts: spots.length,
        activeYear: _activeYear,
        lastUpdate: _lastUpdate,
        error: _lastError,
        status: _enabled ? 'nominal' : 'idle',
      };
    },
  };

  return layer;
}

export default createForestIntelligenceLayer();
