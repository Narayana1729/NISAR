/**
 * @module forestCatalog
 * @description Monitored global deforestation hotspot catalog with authoritative scientific provenance.
 * Distinguishes MONITORED_HOTSPOT boundaries from blanket active deforestation claims.
 */

export const MONITORED_FOREST_HOTSPOTS = Object.freeze([
  {
    id: 'amazon-rondonia',
    name: 'Rondônia Deforestation Arc',
    country: 'Brazil',
    biome: 'Amazonian Moist Tropical Rainforest',
    status: 'MONITORED_HOTSPOT',
    classification: 'CONFIRMED_FOREST_LOSS',
    current_risk_level: 'CRITICAL',
    risk_color: '#e74c3c',
    centroid: { lat: -9.85, lon: -61.85 },
    bbox: [-62.20, -10.15, -61.50, -9.55],
    polygon_coordinates: [
      [-62.20, -9.55],
      [-61.50, -9.55],
      [-61.50, -10.15],
      [-62.20, -10.15],
      [-62.20, -9.55],
    ],
    provenance: {
      source: 'INPE PRODES / TerraBrasilis / Global Forest Watch',
      source_url: 'http://terrabrasilis.dpi.inpe.br/app/dashboard/deforestation/biomes/amazon/increments',
      source_date: '2024-11-15',
      last_verified: '2026-06-01T00:00:00Z',
      data_license: 'Open Data / Public Domain (Brazilian Federal Law 12.527)',
      baseline_coverage_km2: 4520.0,
      sensor_constellation: 'Copernicus Sentinel-2 MSI / Landsat 8-9 OLI',
    },
    latest_metrics: {
      previous_forest_cover_percent: 78.4,
      current_forest_cover_percent: 63.8,
      forest_loss_percent: 14.6,
      estimated_loss_area_km2: 660.0,
      ndvi_trend: -0.16,
      active_fire_count: 24,
      fire_correlated: true,
      fire_attribution: 'POSSIBLE_LAND_CLEARING',
    },
    timeline: [
      { year: 2021, canopy_cover_percent: 82.1, ndvi: 0.78, fire_count: 8 },
      { year: 2022, canopy_cover_percent: 78.4, ndvi: 0.75, fire_count: 12 },
      { year: 2023, canopy_cover_percent: 73.6, ndvi: 0.71, fire_count: 18 },
      { year: 2024, canopy_cover_percent: 68.9, ndvi: 0.67, fire_count: 22 },
      { year: 2025, canopy_cover_percent: 65.2, ndvi: 0.64, fire_count: 26 },
      { year: 2026, canopy_cover_percent: 63.8, ndvi: 0.62, fire_count: 24 },
      { year: 2027, canopy_cover_percent: 60.5, ndvi: 0.59, projected: true },
    ],
  },
  {
    id: 'congo-salonga',
    name: 'Salonga National Park Buffer Corridor',
    country: 'Democratic Republic of the Congo',
    biome: 'Congo Basin Lowland Rainforest',
    status: 'MONITORED_HOTSPOT',
    classification: 'GRADUAL_DEGRADATION',
    current_risk_level: 'HIGH',
    risk_color: '#e67e22',
    centroid: { lat: -2.15, lon: 20.85 },
    bbox: [20.50, -2.45, 21.20, -1.85],
    polygon_coordinates: [
      [20.50, -1.85],
      [21.20, -1.85],
      [21.20, -2.45],
      [20.50, -2.45],
      [20.50, -1.85],
    ],
    provenance: {
      source: 'Observatoire des Forêts d’Afrique Centrale (OFAC) / Hansen GFC',
      source_url: 'https://www.observatoire-comifac.net/',
      source_date: '2024-09-30',
      last_verified: '2026-05-15T00:00:00Z',
      data_license: 'Creative Commons Attribution 4.0 International (CC BY 4.0)',
      baseline_coverage_km2: 5100.0,
      sensor_constellation: 'Copernicus Sentinel-2 MSI / Landsat 9',
    },
    latest_metrics: {
      previous_forest_cover_percent: 88.2,
      current_forest_cover_percent: 81.6,
      forest_loss_percent: 6.6,
      estimated_loss_area_km2: 336.6,
      ndvi_trend: -0.09,
      active_fire_count: 9,
      fire_correlated: true,
      fire_attribution: 'POSSIBLE_LAND_CLEARING',
    },
    timeline: [
      { year: 2021, canopy_cover_percent: 91.0, ndvi: 0.82, fire_count: 3 },
      { year: 2022, canopy_cover_percent: 88.2, ndvi: 0.80, fire_count: 5 },
      { year: 2023, canopy_cover_percent: 85.7, ndvi: 0.77, fire_count: 7 },
      { year: 2024, canopy_cover_percent: 83.9, ndvi: 0.75, fire_count: 8 },
      { year: 2025, canopy_cover_percent: 82.4, ndvi: 0.73, fire_count: 10 },
      { year: 2026, canopy_cover_percent: 81.6, ndvi: 0.72, fire_count: 9 },
      { year: 2027, canopy_cover_percent: 79.8, ndvi: 0.70, projected: true },
    ],
  },
  {
    id: 'borneo-kalimantan',
    name: 'West Kalimantan Peatland Frontier',
    country: 'Indonesia',
    biome: 'Sundaland Peat Swamp & Tropical Rainforest',
    status: 'MONITORED_HOTSPOT',
    classification: 'BURN_RELATED_FOREST_LOSS',
    current_risk_level: 'CRITICAL',
    risk_color: '#e74c3c',
    centroid: { lat: -0.85, lon: 109.85 },
    bbox: [109.50, -1.15, 110.20, -0.55],
    polygon_coordinates: [
      [109.50, -0.55],
      [110.20, -0.55],
      [110.20, -1.15],
      [109.50, -1.15],
      [109.50, -0.55],
    ],
    provenance: {
      source: 'Ministry of Environment and Forestry (KLHK) / World Resources Institute',
      source_url: 'https://menlhk.go.id/',
      source_date: '2024-10-10',
      last_verified: '2026-06-10T00:00:00Z',
      data_license: 'Open Government Data Indonesia / CC BY 4.0',
      baseline_coverage_km2: 4800.0,
      sensor_constellation: 'Copernicus Sentinel-2 / NASA VIIRS',
    },
    latest_metrics: {
      previous_forest_cover_percent: 71.0,
      current_forest_cover_percent: 54.5,
      forest_loss_percent: 16.5,
      estimated_loss_area_km2: 792.0,
      ndvi_trend: -0.19,
      active_fire_count: 38,
      fire_correlated: true,
      fire_attribution: 'POSSIBLE_LAND_CLEARING',
    },
    timeline: [
      { year: 2021, canopy_cover_percent: 76.5, ndvi: 0.76, fire_count: 14 },
      { year: 2022, canopy_cover_percent: 71.0, ndvi: 0.72, fire_count: 22 },
      { year: 2023, canopy_cover_percent: 64.2, ndvi: 0.67, fire_count: 45 },
      { year: 2024, canopy_cover_percent: 59.8, ndvi: 0.63, fire_count: 32 },
      { year: 2025, canopy_cover_percent: 56.4, ndvi: 0.60, fire_count: 41 },
      { year: 2026, canopy_cover_percent: 54.5, ndvi: 0.58, fire_count: 38 },
      { year: 2027, canopy_cover_percent: 50.8, ndvi: 0.54, projected: true },
    ],
  },
  {
    id: 'chaco-paraguay',
    name: 'Gran Chaco Agricultural Clearing Corridor',
    country: 'Paraguay',
    biome: 'Dry Chaco Xerophytic Forest',
    status: 'MONITORED_HOTSPOT',
    classification: 'CONFIRMED_FOREST_LOSS',
    current_risk_level: 'HIGH',
    risk_color: '#e67e22',
    centroid: { lat: -21.85, lon: -60.85 },
    bbox: [-61.20, -22.15, -60.50, -21.55],
    polygon_coordinates: [
      [-61.20, -21.55],
      [-60.50, -21.55],
      [-60.50, -22.15],
      [-61.20, -22.15],
      [-61.20, -21.55],
    ],
    provenance: {
      source: 'Guyra Paraguay / Hansen Global Forest Change',
      source_url: 'https://guyra.org.py/',
      source_date: '2024-08-20',
      last_verified: '2026-04-20T00:00:00Z',
      data_license: 'Creative Commons Attribution-NonCommercial 4.0',
      baseline_coverage_km2: 4400.0,
      sensor_constellation: 'Copernicus Sentinel-2 / Landsat 8',
    },
    latest_metrics: {
      previous_forest_cover_percent: 65.0,
      current_forest_cover_percent: 51.2,
      forest_loss_percent: 13.8,
      estimated_loss_area_km2: 607.2,
      ndvi_trend: -0.14,
      active_fire_count: 16,
      fire_correlated: true,
      fire_attribution: 'POSSIBLE_LAND_CLEARING',
    },
    timeline: [
      { year: 2021, canopy_cover_percent: 71.2, ndvi: 0.69, fire_count: 8 },
      { year: 2022, canopy_cover_percent: 65.0, ndvi: 0.64, fire_count: 14 },
      { year: 2023, canopy_cover_percent: 59.4, ndvi: 0.60, fire_count: 19 },
      { year: 2024, canopy_cover_percent: 55.8, ndvi: 0.57, fire_count: 21 },
      { year: 2025, canopy_cover_percent: 53.0, ndvi: 0.55, fire_count: 18 },
      { year: 2026, canopy_cover_percent: 51.2, ndvi: 0.53, fire_count: 16 },
      { year: 2027, canopy_cover_percent: 48.0, ndvi: 0.50, projected: true },
    ],
  },
  {
    id: 'sumatra-tesso-nilo',
    name: 'Tesso Nilo Buffer Encroachment Zone',
    country: 'Indonesia',
    biome: 'Sumatran Lowland Rainforest',
    status: 'MONITORED_HOTSPOT',
    classification: 'GRADUAL_DEGRADATION',
    current_risk_level: 'MODERATE',
    risk_color: '#f1c40f',
    centroid: { lat: -0.15, lon: 101.65 },
    bbox: [101.30, -0.45, 102.00, 0.15],
    polygon_coordinates: [
      [101.30, 0.15],
      [102.00, 0.15],
      [102.00, -0.45],
      [101.30, -0.45],
      [101.30, 0.15],
    ],
    provenance: {
      source: 'WWF Indonesia / Eyes on the Forest',
      source_url: 'https://eyesontheforest.or.id/',
      source_date: '2024-07-15',
      last_verified: '2026-05-01T00:00:00Z',
      data_license: 'CC BY-NC 4.0',
      baseline_coverage_km2: 4600.0,
      sensor_constellation: 'Copernicus Sentinel-2 MSI',
    },
    latest_metrics: {
      previous_forest_cover_percent: 58.0,
      current_forest_cover_percent: 49.5,
      forest_loss_percent: 8.5,
      estimated_loss_area_km2: 391.0,
      ndvi_trend: -0.11,
      active_fire_count: 7,
      fire_correlated: true,
      fire_attribution: 'POSSIBLE_LAND_CLEARING',
    },
    timeline: [
      { year: 2021, canopy_cover_percent: 63.5, ndvi: 0.71, fire_count: 5 },
      { year: 2022, canopy_cover_percent: 58.0, ndvi: 0.68, fire_count: 8 },
      { year: 2023, canopy_cover_percent: 54.2, ndvi: 0.65, fire_count: 10 },
      { year: 2024, canopy_cover_percent: 51.9, ndvi: 0.63, fire_count: 9 },
      { year: 2025, canopy_cover_percent: 50.4, ndvi: 0.61, fire_count: 11 },
      { year: 2026, canopy_cover_percent: 49.5, ndvi: 0.60, fire_count: 7 },
      { year: 2027, canopy_cover_percent: 47.1, ndvi: 0.58, projected: true },
    ],
  },
]);

/**
 * Returns all monitored forest hotspots.
 * @returns {Array<object>}
 */
export function getAllMonitoredHotspots() {
  return MONITORED_FOREST_HOTSPOTS;
}

/**
 * Finds a monitored hotspot by its unique identifier.
 * @param {string} id
 * @returns {object|null}
 */
export function getHotspotById(id) {
  if (!id) return null;
  return MONITORED_FOREST_HOTSPOTS.find((h) => h.id === id) || null;
}

/**
 * Returns the timeline timeseries for a given hotspot.
 * @param {string} id
 * @returns {Array<object>|null}
 */
export function getHotspotTimeline(id) {
  const spot = getHotspotById(id);
  return spot?.timeline || null;
}
