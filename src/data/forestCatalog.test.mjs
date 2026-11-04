import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MONITORED_FOREST_HOTSPOTS,
  getAllMonitoredHotspots,
  getHotspotById,
  getHotspotTimeline,
} from './forestCatalog.js';

test('MONITORED_FOREST_HOTSPOTS contains verified records with scientific provenance', () => {
  const spots = getAllMonitoredHotspots();
  assert.equal(spots.length, 5);

  for (const s of spots) {
    assert.ok(s.id, 'Hotspot must have id');
    assert.ok(s.name, 'Hotspot must have name');
    assert.ok(s.country, 'Hotspot must have country');
    assert.equal(s.status, 'MONITORED_HOTSPOT', 'Must be explicitly labeled MONITORED_HOTSPOT');
    assert.ok(s.centroid.lat >= -90 && s.centroid.lat <= 90);
    assert.ok(s.centroid.lon >= -180 && s.centroid.lon <= 180);
    assert.equal(s.bbox.length, 4);
    assert.ok(s.polygon_coordinates.length >= 4);

    // Provenance verification
    assert.ok(s.provenance.source, 'Must have authoritative source');
    assert.ok(s.provenance.source_url, 'Must have source URL');
    assert.ok(s.provenance.last_verified, 'Must have verification date');
    assert.ok(s.provenance.data_license, 'Must specify data license');
    assert.ok(s.provenance.baseline_coverage_km2 > 0);

    // Timeline verification
    assert.ok(Array.isArray(s.timeline) && s.timeline.length >= 6);
  }
});

test('getHotspotById retrieves correct record and null on invalid id', () => {
  const amazon = getHotspotById('amazon-rondonia');
  assert.ok(amazon);
  assert.equal(amazon.name, 'Rondônia Deforestation Arc');

  assert.equal(getHotspotById('non-existent'), null);
  assert.equal(getHotspotById(''), null);
});

test('getHotspotTimeline retrieves multi-year timeseries data', () => {
  const tl = getHotspotTimeline('borneo-kalimantan');
  assert.ok(Array.isArray(tl));
  assert.equal(tl[0].year, 2021);
  assert.equal(tl[tl.length - 1].year, 2027);
  assert.equal(tl[tl.length - 1].projected, true);
});
