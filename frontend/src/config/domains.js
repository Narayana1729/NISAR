// Configurable domain definitions for the NISAR platform
// Exactly five scientific domains are supported.

export const DOMAINS = [
  {
    id: 'domain1',
    name: 'Floods & Wetlands',
    description: 'Detect changes in inundation, flooded areas and wetland extent.',
    route: '/domain1',
    color: '#2563eb'
  },
  {
    id: 'domain2',
    name: 'Forests & Wildfires',
    description: 'Analyse changes in forest structure and fire-affected areas.',
    route: '/domain2',
    color: '#059669'
  },
  {
    id: 'domain3',
    name: 'Earthquakes & Ground Deformation',
    description: 'Investigate surface displacement and land subsidence.',
    route: '/domain3',
    color: '#7c3aed'
  },
  {
    id: 'domain4',
    name: 'Agriculture & Soil Conditions',
    description: 'Analyse agricultural surface changes and suitable radar-derived indicators.',
    route: '/domain4',
    color: '#d97706'
  },
  {
    id: 'domain5',
    name: 'Glaciers & Snow/Ice',
    description: 'Investigate glacier movement and changes in ice-related surface conditions.',
    route: '/domain5',
    color: '#0284c7'
  }
];

export const EXPLORER_FEATURE = {
  id: 'earth-event-explorer',
  name: 'Earth Event Explorer',
  description: 'Multi-hazard event integration hub, timeline scrubber, and explainable evidence chain synthesis.',
  route: '/earth-event-explorer',
  icon: '🌐',
  color: '#4f46e5'
};

export const PLATFORM_FEATURES = [
  EXPLORER_FEATURE
];

export const getDomainById = (id) => DOMAINS.find((d) => d.id === id);
