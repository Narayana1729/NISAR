import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SPRITE_LAYER_ORDER,
  registerSpriteCollection,
  restoreSpriteOrder,
  restoreSpriteOrderOnEnable,
  unregisterSpriteCollection,
} from './spriteOrder.js';
import { createFirmsHeatmapLayer } from './firmsHeatmap.js';

function makePrimitives(initial = []) {
  return {
    items: [...initial],
    calls: [],
    contains(collection) { return this.items.includes(collection); },
    raiseToTop(collection) {
      this.calls.push(collection.id);
      const index = this.items.indexOf(collection);
      if (index >= 0) this.items.splice(index, 1);
      this.items.push(collection);
    },
  };
}

function makeCollection(id, destroyed = false) {
  return { id, isDestroyed: () => destroyed };
}

test('SPRITE_LAYER_ORDER defines the preserved NISAR sprite order', () => {
  assert.deepEqual(SPRITE_LAYER_ORDER, ['firms']);
});

test('restoreSpriteOrder raises live collections bottom-to-top and skips destroyed entries', () => {
  const firms = makeCollection('firms');
  const destroyedFirms = makeCollection('firms', true);

  registerSpriteCollection('firms', destroyedFirms);
  const primitives = makePrimitives([destroyedFirms]);

  restoreSpriteOrder({ scene: { primitives } });
  assert.deepEqual(primitives.calls, [], 'destroyed collection is not raised');

  registerSpriteCollection('firms', firms);
  primitives.items = [firms];
  restoreSpriteOrder({ scene: { primitives } });
  assert.deepEqual(primitives.calls, ['firms'], 'live firms collection is raised');

  unregisterSpriteCollection('firms');
});

test('restoreSpriteOrder is inert for destroyed viewers and primitive collections', () => {
  const firms = makeCollection('firms');
  const primitives = makePrimitives([firms]);
  registerSpriteCollection('firms', firms);

  restoreSpriteOrder({ isDestroyed: () => true, scene: { primitives } });
  restoreSpriteOrder({ scene: { primitives: { ...primitives, isDestroyed: () => true } } });

  assert.deepEqual(primitives.calls, []);
  unregisterSpriteCollection('firms', firms);
});

test('restoreSpriteOrder never raises a registered collection absent from scene primitives', () => {
  const firms = makeCollection('firms');
  const primitives = makePrimitives([]);
  registerSpriteCollection('firms', firms);

  restoreSpriteOrder({ scene: { primitives } });

  assert.deepEqual(primitives.calls, []);
  assert.deepEqual(primitives.items, []);
  unregisterSpriteCollection('firms', firms);
});

test('FIRMS enable path is wired through the shared sprite restorer', () => {
  const viewer = { id: 'viewer' };
  const calls = [];
  const restoreSpy = (value) => calls.push(value);

  restoreSpriteOrderOnEnable('firms', viewer, restoreSpy);
  assert.deepEqual(calls, [viewer]);

  const firmsLayer = createFirmsHeatmapLayer({ id: 'firms', name: 'FIRMS' });
  assert.match(firmsLayer.enable.toString(), /restoreSpriteOrderOnEnable\('firms', viewer\)/);
  assert.match(
    createFirmsHeatmapLayer.toString(),
    /registerSpriteCollection\('firms', _billboards\);\s*restoreSpriteOrder\(_viewer\);/,
    'lazy FIRMS registration must restore order immediately',
  );
});
