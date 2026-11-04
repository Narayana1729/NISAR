import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as Cesium from 'cesium';
import {
  createForestIntelligenceLayer,
  createForestOverlayEntry,
  FOREST_ZONE_COLORS,
  FOREST_OVERLAY_SOURCE_ID,
  FOREST_OVERLAY_COHORT_LIMIT,
  FOREST_OVERLAY_COLLISION_CAPACITY,
} from './forestIntelligence.js';
import { getHotspotById } from './forestCatalog.js';
import { isOwnedByOtherLayer } from './pickRegistry.js';
import { selectForestZone } from './forestIntelligence.js';

function createMockViewer() {
  const dataSources = [];
  return {
    dataSources: {
      add(ds) {
        dataSources.push(ds);
        return ds;
      },
      remove(ds) {
        const idx = dataSources.indexOf(ds);
        if (idx !== -1) {
          dataSources.splice(idx, 1);
          return true;
        }
        return false;
      },
      get length() {
        return dataSources.length;
      },
    },
    camera: {
      flyToCalls: [],
      flyTo(opts) {
        this.flyToCalls.push(opts);
      },
    },
    _dataSourcesList: dataSources,
  };
}

test('forestIntelligence: FOREST_ZONE_COLORS and constants are properly defined', () => {
  assert.equal(FOREST_OVERLAY_SOURCE_ID, 'forest-intelligence');
  assert.equal(FOREST_OVERLAY_COHORT_LIMIT, 32);
  assert.equal(FOREST_OVERLAY_COLLISION_CAPACITY, 16);

  const expectedColors = [
    'HEALTHY_FOREST',
    'VEGETATION_CHANGE',
    'GRADUAL_DEGRADATION',
    'CONFIRMED_FOREST_LOSS',
    'PREDICTED_HIGH_RISK',
    'BURN_RELATED_FOREST_LOSS',
  ];

  for (const key of expectedColors) {
    assert.ok(FOREST_ZONE_COLORS[key] instanceof Cesium.Color, `${key} must be a Cesium.Color`);
  }
});

test('forestIntelligence: createForestOverlayEntry builds a valid ambient card', () => {
  const spot = getHotspotById('amazon-rondonia');
  assert.ok(spot, 'amazon-rondonia exists');

  const entry = createForestOverlayEntry(spot);
  assert.equal(entry.id, 'forest:amazon-rondonia');
  assert.equal(entry.variant, 'card');
  assert.ok(entry.title.includes('RONDÔNIA') || entry.title.includes('RONDONIA'));
  assert.equal(entry.interactive, true);
  assert.equal(entry.collisionGroup, 'ambient-card');
  assert.ok(entry.position instanceof Cesium.Cartesian3);
  assert.equal(entry.sourceData, spot);
});

test('forestIntelligence: selectForestZone triggers camera flight', () => {
  const viewer = createMockViewer();
  const res = selectForestZone('amazon-rondonia', viewer);
  assert.equal(res, true);
  assert.equal(viewer.camera.flyToCalls.length, 1);
  assert.ok(viewer.camera.flyToCalls[0].destination instanceof Cesium.Cartesian3);
});

test('forestIntelligence: layer lifecycle (init, enable, disable, timeline, destroy)', async () => {
  const viewer = createMockViewer();
  const layer = createForestIntelligenceLayer();

  // 1. Initial status before init
  let stats = layer.getStats();
  assert.equal(stats.status, 'idle');
  assert.equal(stats.count, 5);

  // 2. Init
  const initSuccess = layer.init(viewer);
  assert.equal(initSuccess, true);
  assert.equal(viewer.dataSources.length, 1);
  const ds = viewer._dataSourcesList[0];
  assert.equal(ds.show, false);
  assert.equal(ds.name, 'forest-intelligence');
  assert.equal(ds.entities.values.length, 5);

  // Check entity properties
  const firstEntity = ds.entities.values[0];
  assert.ok(firstEntity.polygon, 'entities should have polygon graphics');
  assert.ok(firstEntity.properties.forestSpotId);

  // 3. Enable / Show
  await layer.enable(viewer);
  assert.equal(ds.show, true);
  stats = layer.getStats();
  assert.equal(stats.status, 'nominal');

  // Verify pick ownership when enabled
  assert.equal(isOwnedByOtherLayer('flights', 'forest-entity:amazon-rondonia'), true);
  assert.equal(isOwnedByOtherLayer('flights', 'other-entity-123'), false);

  // 4. Timeline change
  layer.setTimelineYear(2022);
  stats = layer.getStats();
  assert.equal(stats.activeYear, 2022);

  // 5. Update
  const updateRes = await layer.update();
  assert.equal(updateRes, true);

  // 6. Select zone
  layer.selectZone('amazon-rondonia');
  assert.equal(viewer.camera.flyToCalls.length, 1);

  // 7. Analyst records
  const records = layer.getAnalystRecords();
  assert.equal(records.length, 5);
  assert.ok(records[0].loss_percent !== undefined);
  assert.ok(records[0].loss_area_km2 !== undefined);
  assert.ok(records[0].provenance_source);

  // 8. Disable / Hide
  layer.disable(viewer);
  assert.equal(ds.show, false);
  stats = layer.getStats();
  assert.equal(stats.status, 'idle');
  assert.equal(isOwnedByOtherLayer('flights', 'forest-entity:hotspot-rondonia'), false);

  // 9. Destroy
  layer.destroy(viewer);
  assert.equal(viewer.dataSources.length, 0);
});
