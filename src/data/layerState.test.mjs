import test from 'node:test';
import assert from 'node:assert/strict';

import { DataLayerManager } from './manager.js';
import {
  LAYER_STATE_REGISTRY,
  LAYER_STATE_STORAGE_KEY,
  LayerStateCoordinator,
  REGISTERED_LAYER_IDS,
  createDefaultLayerState,
  decodeLayerStateParams,
  encodeLayerStateParams,
  normalizeLayerState,
  parseStoredLayerState,
  serializeStoredLayerState,
  validateLayerStateRegistry,
} from './layerState.js';

function fakeLayer(id, hooks = {}) {
  return {
    id,
    name: id,
    async init() { return hooks.init ? hooks.init() : true; },
    async enable() { return hooks.enable ? hooks.enable() : true; },
    async update() { return hooks.update ? hooks.update() : true; },
    async disable() { return hooks.disable ? hooks.disable() : true; },
  };
}

function productionManager(hooksById = {}) {
  const manager = new DataLayerManager({});
  for (const id of REGISTERED_LAYER_IDS) manager.register(fakeLayer(id, hooksById[id] || {}));
  manager.finalizeRegistrations(LAYER_STATE_REGISTRY);
  return manager;
}

function memoryStorage(initial = null) {
  const values = new Map();
  if (initial !== null) values.set(LAYER_STATE_STORAGE_KEY, initial);
  return {
    getItem: (key) => (values.has(key) ? values.get(key) : null),
    setItem: (key, val) => { values.set(key, String(val)); },
    removeItem: (key) => { values.delete(key); },
  };
}

function encode(state) {
  const params = new URLSearchParams([['v', '2']]);
  encodeLayerStateParams(params, state);
  return params.toString();
}

test('production registry is exact, canonical, and rejects incomplete contracts', async () => {
  assert.equal(validateLayerStateRegistry(), true);
  assert.equal(REGISTERED_LAYER_IDS.length, 6);
  assert.equal(new Set(REGISTERED_LAYER_IDS).size, 6);
  assert.deepEqual(REGISTERED_LAYER_IDS, [...REGISTERED_LAYER_IDS].sort());
  assert.throws(
    () => validateLayerStateRegistry([...LAYER_STATE_REGISTRY, LAYER_STATE_REGISTRY[0]]),
    /Duplicate layer-state id/,
  );

  const manager = new DataLayerManager({});
  manager.register(fakeLayer('earthquakes'));
  assert.throws(() => manager.register(fakeLayer('earthquakes')), /Duplicate data-layer id/);
  await assert.rejects(manager.restoreLayerState('earthquakes', { enabled: true }), /finalized/);
  assert.throws(() => manager.finalizeRegistrations([]), /registry mismatch/);
  assert.throws(
    () => manager.finalizeRegistrations([{ id: 'earthquakes', disposition: 'default' }]),
    /Invalid layer serialization disposition/,
  );
  assert.equal(manager.finalizeRegistrations([
    { id: 'earthquakes', disposition: 'enabled-only' },
  ]), true);
  assert.throws(() => manager.register(fakeLayer('forest-intelligence')), /finalized/);
  assert.throws(() => manager.registerForQa(fakeLayer('forest-intelligence')), /not authorized/);
  const qaManager = new DataLayerManager({}, { allowQaRegistration: true });
  qaManager.register(fakeLayer('earthquakes'));
  qaManager.finalizeRegistrations([{ id: 'earthquakes', disposition: 'enabled-only' }]);
  qaManager.registerForQa(fakeLayer('forest-intelligence'));
  assert.equal(qaManager.layers.has('forest-intelligence'), true);
  assert.equal(await qaManager.unregisterForQa('forest-intelligence'), true);
  assert.equal(qaManager.layers.has('forest-intelligence'), false);
});

test('v2 codec distinguishes absent from empty and keeps canonical deterministic ordering', () => {
  assert.equal(decodeLayerStateParams(new URLSearchParams('lat=1&lon=2')), null);
  assert.equal(decodeLayerStateParams(new URLSearchParams('v=1&l=e')), null);
  assert.equal(decodeLayerStateParams(new URLSearchParams('v=3&l=e')), null);
  assert.equal(decodeLayerStateParams(new URLSearchParams('v=2')), null);

  const empty = decodeLayerStateParams(new URLSearchParams('v=2&l='));
  assert.deepEqual(empty.enabledLayerIds, []);

  const first = normalizeLayerState({
    enabledLayerIds: ['local-firms', 'earthquakes', 'local-firms'],
  });
  const second = normalizeLayerState({
    enabledLayerIds: ['earthquakes', 'local-firms'],
  });
  assert.equal(encode(first), encode(second));
  assert.deepEqual(decodeLayerStateParams(new URLSearchParams(encode(first))), first);
});

test('forest-intelligence serialization roundtrip with token k', () => {
  const state = normalizeLayerState({
    enabledLayerIds: ['forest-intelligence', 'earthquakes'],
  });
  const encoded = encode(state);
  assert.ok(encoded.includes('l=e.k'), `expected canonical ordering with token k: ${encoded}`);
  const decoded = decodeLayerStateParams(new URLSearchParams(encoded));
  assert.deepEqual(decoded.enabledLayerIds, ['earthquakes', 'forest-intelligence']);
});

test('unknown enabled-layer tokens reject the payload instead of becoming an empty set', () => {
  assert.equal(decodeLayerStateParams(new URLSearchParams('v=2&l=z')), null);
  assert.equal(decodeLayerStateParams(new URLSearchParams('v=2&l=e.z')), null);
});

test('stored state is deterministic, rejects other versions, and stays within a tested URL bound', () => {
  const state = normalizeLayerState({
    enabledLayerIds: ['earthquakes', 'forest-intelligence', 'local-firms'],
  });
  const serialized = serializeStoredLayerState(state);
  assert.deepEqual(parseStoredLayerState(serialized), state);
  assert.equal(parseStoredLayerState('{"version":1}'), null);
  assert.equal(parseStoredLayerState('not-json'), null);
  assert.equal(parseStoredLayerState(null), null);
});

test('restore applies state after init and enables layers in coordinator', async () => {
  const manager = productionManager();
  const storage = memoryStorage();
  const coordinator = new LayerStateCoordinator(manager, null, {
    storage,
  });
  const shareLayerState = decodeLayerStateParams(new URLSearchParams('v=2&l=e.k'));
  const results = await coordinator.start({ shareLayerState });
  assert.equal(manager.isEnabled('earthquakes'), true);
  assert.equal(manager.isEnabled('forest-intelligence'), true);
  assert.equal(manager.isEnabled('local-firms'), false);
  assert.equal(results.every((r) => r.succeeded), true);
});

test('one layer failure is isolated from sibling restoration', async () => {
  const manager = productionManager({
    'local-firms': {
      enable: async () => false,
    },
  });
  const storage = memoryStorage();
  const coordinator = new LayerStateCoordinator(manager, null, {
    storage,
  });
  const shareLayerState = decodeLayerStateParams(new URLSearchParams('v=2&l=e.w'));
  const results = await coordinator.start({ shareLayerState });
  assert.equal(manager.isEnabled('earthquakes'), true);
  assert.equal(manager.isEnabled('local-firms'), false);
  const firmsResult = results.find((r) => r.layerId === 'local-firms');
  assert.equal(firmsResult.succeeded, false);
  const quakeResult = results.find((r) => r.layerId === 'earthquakes');
  assert.equal(quakeResult.succeeded, true);
});
