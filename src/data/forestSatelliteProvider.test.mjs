import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SatelliteProvider,
  Sentinel2Provider,
  LandsatProvider,
  createSatelliteProvider,
} from './forestSatelliteProvider.js';

test('createSatelliteProvider instantiates correct provider subclasses', () => {
  const s2 = createSatelliteProvider('SENTINEL_2');
  assert.ok(s2 instanceof Sentinel2Provider);
  assert.equal(s2.getSpatialResolution(), 10);
  assert.equal(s2.providerId, 'SENTINEL_2');

  const ls = createSatelliteProvider('LANDSAT');
  assert.ok(ls instanceof LandsatProvider);
  assert.equal(ls.getSpatialResolution(), 30);
  assert.equal(ls.providerId, 'LANDSAT_8_9');

  const auto = createSatelliteProvider('AUTO');
  assert.ok(auto instanceof Sentinel2Provider);
});

test('Sentinel2Provider extracts valid multi-spectral bands and computed indices', async () => {
  const provider = new Sentinel2Provider();
  const res = await provider.getBands({
    bbox: [-62.0, -10.0, -61.5, -9.5],
    date: '2024-07-15',
    bands: ['RED', 'NIR', 'SWIR1', 'SWIR2'],
  });

  assert.equal(res.sensor, 'SENTINEL_2');
  assert.equal(res.resolution_meters, 10);
  assert.ok(res.bands.RED > 0 && res.bands.RED < 1.0);
  assert.ok(res.bands.NIR > 0 && res.bands.NIR < 1.0);
  assert.ok(res.bands.SWIR1 > 0 && res.bands.SWIR1 < 1.0);
  assert.ok(res.bands.SWIR2 > 0 && res.bands.SWIR2 < 1.0);

  // Check indices
  assert.ok(res.computed_indices.NDVI > 0.4, 'Rainforest baseline should have high NDVI');
  assert.ok(Number.isFinite(res.computed_indices.NDMI));
  assert.ok(Number.isFinite(res.computed_indices.NBR));
});

test('Abstract SatelliteProvider throws when getBands is called directly', async () => {
  const base = new SatelliteProvider({
    providerId: 'BASE',
    name: 'Base',
    spatialResolutionMeters: 20,
    revisitDays: 5,
  });

  await assert.rejects(
    () => base.getBands({ bbox: [0, 0, 1, 1], date: '2024-01-01' }),
    /getBands\(\) must be implemented/,
  );
});
