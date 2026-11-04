export const ENDPOINTS = {
  HEALTH: '/api/health',
  DATASETS: '/api/datasets',
  DATASET_UPLOAD: '/api/datasets/upload',
  DATASET_REGISTER: '/api/datasets/register',
  DOMAIN_INFO: (domainId) => `/api/domains/${domainId}/info`,
  DOMAIN_PROCESS: (domainId) => `/api/domains/${domainId}/process`,
  DOMAIN_RUNS: (domainId) => `/api/domains/${domainId}/runs`,
  EXPLORER_EVENTS: '/api/explorer/events',
  EXPLORER_EVENT: (eventId) => `/api/explorer/events/${eventId}`,
  EXPLORER_PLACES: (query = '') => `/api/explorer/places?q=${encodeURIComponent(query)}`,
  EXPLORER_DISCOVER: ({ bbox = '', domain = '', startDate = '', endDate = '', includeExternal = false } = {}) => {
    const params = new URLSearchParams();
    if (bbox) params.set('bbox', Array.isArray(bbox) ? bbox.join(',') : bbox);
    if (domain) params.set('domain', domain);
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    if (includeExternal) params.set('include_external', 'true');
    return `/api/explorer/discover?${params.toString()}`;
  },
  EXPLORER_RETRIEVE: '/api/explorer/retrieve',
  EXPLORER_RUNS: (domain = '') => (domain ? `/api/explorer/runs?domain=${encodeURIComponent(domain)}` : '/api/explorer/runs'),
  EXPLORER_RUN_DETAIL: (runId) => `/api/explorer/runs/${runId}`,
  RUN_EXPORT: (runId, format = 'json') => `/api/explorer/runs/${runId}/export?format=${format}`
};
