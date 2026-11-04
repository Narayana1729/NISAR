import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import InteractiveWorldMap from '../components/InteractiveWorldMap';
import SharedMap from '../components/map/SharedMap';
import StudyAreaDock from '../components/navigation/StudyAreaDock';
import DatasetUploadModal from '../components/DatasetUploadModal';
import LoadingSpinner from '../components/LoadingSpinner';
import { apiClient } from '../services/api';
import { ENDPOINTS } from '../services/endpoints';
import { DOMAINS } from '../config/domains';

const ANALYTICAL_DOMAINS = DOMAINS;

export default function EarthEventExplorer() {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [allDatasets, setAllDatasets] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedDomain, setSelectedDomain] = useState('domain1');
  const [selectedBbox, setSelectedBbox] = useState([22.7966, 39.4475, 22.9537, 39.5824]);
  const [placeQuery, setPlaceQuery] = useState('');
  const [placeResults, setPlaceResults] = useState([]);
  const [discovery, setDiscovery] = useState(null);
  const [discovering, setDiscovering] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [retrievingId, setRetrievingId] = useState(null);
  const [retrieveMessage, setRetrieveMessage] = useState(null);
  const [recentRuns, setRecentRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [activeBottomTab, setActiveBottomTab] = useState('discovery'); // 'discovery' | 'events' | 'history'

  const runDiscovery = useCallback(async (bbox, domainId, includeExt = false, sDate = '', eDate = '') => {
    try {
      setDiscovering(true);
      const data = await apiClient(
        ENDPOINTS.EXPLORER_DISCOVER({
          bbox: bbox && bbox.length === 4 ? bbox.join(',') : '',
          domain: domainId,
          startDate: sDate,
          endDate: eDate,
          includeExternal: includeExt
        })
      );
      setDiscovery(data);
    } catch (err) {
      console.error('Dataset discovery error:', err);
    } finally {
      setDiscovering(false);
    }
  }, []);

  const loadInitialCatalog = useCallback(async () => {
    try {
      setLoading(true);
      const [evts, dsList, runsList] = await Promise.all([
        apiClient(ENDPOINTS.EXPLORER_EVENTS),
        apiClient(ENDPOINTS.DATASETS),
        apiClient(ENDPOINTS.EXPLORER_RUNS()).catch(() => [])
      ]);
      setEvents(evts || []);
      setAllDatasets(dsList || []);
      setRecentRuns(runsList || []);

      if (evts && evts.length > 0) {
        const first = evts[0];
        setSelectedEvent(first);
        setSelectedBbox(first.bbox);
        const dom = first.domains_involved?.[0] || 'domain1';
        setSelectedDomain(dom);
        await runDiscovery(first.bbox, dom, false);
      }
    } catch (err) {
      console.error('Failed to load explorer catalog:', err);
    } finally {
      setLoading(false);
    }
  }, [runDiscovery]);

  useEffect(() => {
    loadInitialCatalog();
  }, [loadInitialCatalog]);

  const handleSelectEvent = (evt) => {
    setSelectedEvent(evt);
    if (evt.bbox && evt.bbox.length === 4) {
      setSelectedBbox(evt.bbox);
    }
    const dom = evt.domains_involved?.[0] || selectedDomain;
    setSelectedDomain(dom);
    runDiscovery(evt.bbox, dom, false);
  };

  const handleBboxChange = (newBbox) => {
    setSelectedBbox(newBbox);
    // Clear selectedEvent if user drew a custom bounding box
    setSelectedEvent(null);
    runDiscovery(newBbox, selectedDomain, false);
  };

  const handleDomainChange = (domId) => {
    setSelectedDomain(domId);
    runDiscovery(selectedBbox, domId, false);
  };

  const handlePlaceSearch = async (e) => {
    e.preventDefault();
    try {
      const results = await apiClient(ENDPOINTS.EXPLORER_PLACES(placeQuery));
      setPlaceResults(results || []);
      if (results && results.length > 0) {
        const top = results[0];
        setSelectedBbox(top.bbox);
        const recDom = top.recommended_domains?.[0] || selectedDomain;
        setSelectedDomain(recDom);
        setSelectedEvent(null);
        runDiscovery(top.bbox, recDom, false);
      }
    } catch (err) {
      console.error('Place search error:', err);
    }
  };

  const handleSelectPlace = (place) => {
    setSelectedBbox(place.bbox);
    const recDom = place.recommended_domains?.[0] || selectedDomain;
    setSelectedDomain(recDom);
    setSelectedEvent(null);
    setPlaceResults([]);
    runDiscovery(place.bbox, recDom, false);
  };

  const handleSelectStudyArea = (area) => {
    if (area.bbox && area.bbox.length === 4) {
      setSelectedBbox(area.bbox);
    }
    if (area.domainId) {
      setSelectedDomain(area.domainId);
    }
    const matchedEvt = events.find(
      (e) =>
        e.id === area.id ||
        (area.id === 'lake-karla' && e.id === 'thessaly-flood-2023') ||
        (area.id === 'para-br163' && e.id === 'para-wildfire-2024') ||
        (area.id === 'tyrnavos' && e.id === 'tyrnavos-earthquake-2021') ||
        (area.id === 'thessaly-plains' && e.id === 'thessaly-agriculture-2023') ||
        (area.id === 'jakobshavn' && e.id === 'jakobshavn-glacier-retreat')
    );
    if (matchedEvt) {
      setSelectedEvent(matchedEvt);
    } else {
      setSelectedEvent(null);
    }
    runDiscovery(area.bbox, area.domainId || selectedDomain, false);
  };

  const handleLaunchWorkspace = (domId, presetMap = null, presetParams = null) => {
    const domObj = DOMAINS.find((d) => d.id === domId);
    const route = domObj?.route || `/${domId}`;
    const state = {
      studyAreaBbox: selectedBbox
    };
    if (presetMap && Object.keys(presetMap).length > 0) {
      state.presetInputs = presetMap;
    } else if (selectedEvent?.dataset_ids?.[domId]) {
      state.presetInputs = selectedEvent.dataset_ids[domId];
    }
    if (presetParams && Object.keys(presetParams).length > 0) {
      state.presetParams = presetParams;
    } else if (selectedEvent?.recommended_parameters) {
      state.presetParams = selectedEvent.recommended_parameters;
    }
    navigate(route, { state });
  };

  const handleRetrieveExternalGranule = async (granule) => {
    if (!selectedBbox || selectedBbox.length !== 4) return;
    try {
      setRetrievingId(granule.granule_id);
      setRetrieveMessage(null);
      const res = await apiClient(ENDPOINTS.EXPLORER_RETRIEVE, {
        method: 'POST',
        body: {
          collection: granule.collection || 'sentinel-1-rtc',
          granule_id: granule.granule_id,
          domain: selectedDomain,
          product_type: granule.recommended_product_type || 'sar_backscatter',
          asset_key: granule.default_asset_key || null,
          bbox: selectedBbox
        }
      });
      setRetrieveMessage({
        type: 'success',
        text: res.message || `Retrieved and registered ${granule.granule_id}`
      });
      const dsList = await apiClient(ENDPOINTS.DATASETS);
      setAllDatasets(dsList || []);
      await runDiscovery(selectedBbox, selectedDomain, true, startDate, endDate);
    } catch (err) {
      setRetrieveMessage({
        type: 'error',
        text: err.message || `Failed to retrieve granule ${granule.granule_id}`
      });
    } finally {
      setRetrievingId(null);
    }
  };

  const currentDomainObj = DOMAINS.find((d) => d.id === selectedDomain);
  const realCount = discovery?.summary?.local_real_count || 0;
  const synthCount = discovery?.summary?.local_synthetic_count || 0;
  const totalReady = realCount + synthCount;

  return (
    <MainLayout>
      <div className="domain-page-container">
        {/* Top Platform Header */}
        <div className="domain-page-header" style={{ marginBottom: '1rem' }}>
          <div>
            <h1 className="domain-title" style={{ color: '#38bdf8', marginBottom: '0.2rem' }}>
              NISAR — Dancing with the SARs Earth Observation Platform
            </h1>
            <p className="domain-description">
              Explore the Earth • Select a study area or documented event • Discover verified SAR observations • Run domain analysis • Validate & assess exposure
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setUploadModalOpen(true)}
            >
              ＋ Upload GeoTIFF / GeoJSON
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/dashboard')}
            >
              Domain Overview Grid
            </button>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>
            <LoadingSpinner size={36} text="Initializing geospatial catalog & world map..." />
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Top Search & Domain Filter Bar */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1.3fr 1fr',
                gap: '1rem',
                backgroundColor: '#1e293b',
                padding: '0.85rem 1rem',
                borderRadius: '8px',
                border: '1px solid #334155',
                alignItems: 'center'
              }}
            >
              {/* Place / Coordinate Search */}
              <div style={{ position: 'relative' }}>
                <form onSubmit={handlePlaceSearch} style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type="text"
                    className="form-select"
                    style={{ marginTop: 0, flex: 1 }}
                    placeholder="Search study region (e.g. Lake Karla, Jakobshavn, San Joaquin, Pará) or Lat, Lon..."
                    value={placeQuery}
                    onChange={(e) => setPlaceQuery(e.target.value)}
                  />
                  <button type="submit" className="btn btn-primary" style={{ whiteSpace: 'nowrap' }}>
                    🔍 Locate
                  </button>
                </form>
                {placeResults.length > 0 && (
                  <div
                    style={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      backgroundColor: '#0f172a',
                      border: '1px solid #38bdf8',
                      borderRadius: '6px',
                      marginTop: '4px',
                      zIndex: 50,
                      maxHeight: '220px',
                      overflowY: 'auto'
                    }}
                  >
                    {placeResults.map((p) => (
                      <div
                        key={p.id}
                        onClick={() => handleSelectPlace(p)}
                        style={{
                          padding: '0.55rem 0.8rem',
                          borderBottom: '1px solid #1e293b',
                          cursor: 'pointer',
                          fontSize: '0.8rem'
                        }}
                      >
                        <strong style={{ color: '#38bdf8' }}>{p.name}</strong>{' '}
                        <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>({p.category})</span>
                        <div style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>{p.notes}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Domain Selector Pills */}
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                {ANALYTICAL_DOMAINS.map((dom) => (
                  <button
                    key={dom.id}
                    type="button"
                    onClick={() => handleDomainChange(dom.id)}
                    style={{
                      padding: '0.35rem 0.65rem',
                      fontSize: '0.75rem',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: selectedDomain === dom.id ? 'bold' : 'normal',
                      backgroundColor: selectedDomain === dom.id ? dom.color : '#0f172a',
                      color: '#f8fafc',
                      border: `1px solid ${dom.color}`
                    }}
                  >
                    {dom.name.split('&')[0].trim()}
                  </button>
                ))}
              </div>
            </div>

            {/* Main Map + Prepared Events Split Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.85fr 1fr', gap: '1.25rem' }}>
              {/* Left: Shared Map (3D Globe + 2D Projection) + Command Dock */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <SharedMap
                  events={events}
                  selectedEventId={selectedEvent?.id}
                  onSelectEvent={handleSelectEvent}
                  datasets={allDatasets}
                  selectedBbox={selectedBbox}
                  onChangeBbox={handleBboxChange}
                  initialView={selectedBbox}
                  height={470}
                  defaultMode="3d"
                />

                {/* NASA1-Style Command Dock for Fast Study Area Switching */}
                <StudyAreaDock
                  activeStudyAreaId={selectedEvent?.id}
                  onSelectStudyArea={handleSelectStudyArea}
                  searchQuery={placeQuery}
                  onSearchChange={setPlaceQuery}
                  onSearchSubmit={handlePlaceSearch}
                />

                {/* Study Area Bounding Box & Direct Launcher Bar */}
                <div
                  className="panel-inner"
                  style={{
                    padding: '0.65rem 0.95rem',
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '0.75rem',
                    fontSize: '0.78rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="w-2 h-2 rounded-full bg-cyan-400" />
                    <strong style={{ color: '#00d4ff', fontFamily: 'var(--font-mono)' }}>TARGET EXTENT (WGS84):</strong>{' '}
                    <code style={{ color: '#e2e8f0', fontFamily: 'var(--font-mono)' }}>
                      {selectedBbox
                        ? `[${selectedBbox.map((x) => Number(x).toFixed(4)).join(', ')}]`
                        : 'Global'}
                    </code>
                  </div>
                  <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                    <span style={{ color: '#94a3b8' }}>Domain:</span>
                    <strong style={{ color: currentDomainObj?.color || '#00d4ff' }}>{currentDomainObj?.name}</strong>
                    <button
                      type="button"
                      className="btn btn-primary"
                      style={{
                        padding: '0.35rem 0.85rem',
                        fontSize: '0.78rem',
                        background: 'linear-gradient(135deg, rgba(0,212,255,0.2) 0%, rgba(0,212,255,0.4) 100%)',
                        border: '1px solid rgba(0,212,255,0.5)',
                        boxShadow: '0 0 10px rgba(0,212,255,0.2)'
                      }}
                      onClick={() => handleLaunchWorkspace(selectedDomain)}
                    >
                      Launch {currentDomainObj?.name.split('&')[0].trim()} Workspace &rarr;
                    </button>
                  </div>
                </div>
              </div>

              {/* Right: Prepared Documented Events List in NASA1 Glassmorphic Panel */}
              <div
                className="panel-collapsible"
                style={{
                  borderRadius: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  maxHeight: '610px',
                  overflow: 'hidden'
                }}
              >
                <div className="panel-header" style={{ padding: '0.75rem 1rem' }}>
                  <div className="panel-title">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                    <span>STUDY EVENTS CATALOG</span>
                  </div>
                  <span
                    style={{
                      fontSize: '0.68rem',
                      fontFamily: 'var(--font-mono)',
                      color: '#00d4ff',
                      backgroundColor: 'rgba(0, 212, 255, 0.1)',
                      border: '1px solid rgba(0, 212, 255, 0.25)',
                      padding: '0.15rem 0.5rem',
                      borderRadius: '4px'
                    }}
                  >
                    {events.length} DOCUMENTED
                  </span>
                </div>

                <div
                  className="panel-inner"
                  style={{
                    padding: '0.85rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.65rem',
                    overflowY: 'auto'
                  }}
                >
                  <p style={{ fontSize: '0.74rem', color: '#94a3b8', margin: '0 0 0.25rem 0' }}>
                    Select a documented event to focus 3D/2D views, verify dataset readiness, or launch processing.
                  </p>

                  {events.map((evt) => {
                    const isSelected = selectedEvent?.id === evt.id;
                    const badgeBg =
                      evt.data_readiness === 'verified_real'
                        ? '#059669'
                        : evt.data_readiness === 'synthetic_demo'
                        ? '#d97706'
                        : '#475569';
                    const badgeLabel =
                      evt.data_readiness === 'verified_real'
                        ? '✓ Real Satellite Data'
                        : evt.data_readiness === 'synthetic_demo'
                        ? '⚠️ Synthetic Demo Fixture'
                        : 'External / Unstaged';

                    return (
                      <div
                        key={evt.id}
                        onClick={() => handleSelectEvent(evt)}
                        style={{
                          padding: '0.8rem',
                          borderRadius: '8px',
                          backgroundColor: isSelected ? 'rgba(0, 212, 255, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                          border: isSelected ? '1px solid #00d4ff' : '1px solid rgba(255, 255, 255, 0.08)',
                          boxShadow: isSelected ? '0 0 14px rgba(0, 212, 255, 0.18)' : 'none',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                          <strong style={{ fontSize: '0.84rem', color: '#f8fafc' }}>{evt.name}</strong>
                          <span
                            style={{
                              fontSize: '0.66rem',
                              padding: '0.15rem 0.45rem',
                              borderRadius: '4px',
                              backgroundColor: badgeBg,
                              color: '#fff',
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {badgeLabel}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                          📍 {evt.location} • 📅 {(evt.acquisition_dates || [evt.date]).join(' → ')} • ⚡ {evt.type}
                        </div>
                        <p style={{ fontSize: '0.73rem', color: '#cbd5e1', marginTop: '0.35rem', marginBottom: '0.4rem' }}>
                          {evt.description}
                        </p>
                        {/* Structured Live Demonstration Metadata Box */}
                        <div
                          style={{
                            fontSize: '0.69rem',
                            color: '#cbd5e1',
                            backgroundColor: 'rgba(8, 8, 14, 0.8)',
                            border: '1px solid rgba(255, 255, 255, 0.06)',
                            borderRadius: '5px',
                            padding: '0.4rem 0.55rem',
                            marginBottom: '0.5rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.15rem'
                          }}
                        >
                          <div>
                            <strong style={{ color: '#93c5fd' }}>Source & Sensor:</strong> {evt.sensor || evt.dataset_source || 'Local Registry'}
                          </div>
                          {evt.available_workflow && (
                            <div>
                              <strong style={{ color: '#93c5fd' }}>Workflow:</strong> {evt.available_workflow}
                            </div>
                          )}
                          <div>
                            <strong style={{ color: '#6ee7b7' }}>Reference & Validation:</strong>{' '}
                            {evt.reference_data_available ? '✓ Reference Available — ' : 'No Reference — '}
                            {evt.validation_status || (evt.is_synthetic ? 'Demonstration Benchmark' : 'Independent Reference Validation')}
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                          {evt.domains_involved?.map((domId) => {
                            const dom = DOMAINS.find((d) => d.id === domId);
                            const hasLocal = Boolean(evt.dataset_ids?.[domId]);
                            return (
                              <button
                                key={domId}
                                type="button"
                                className="btn btn-secondary"
                                style={{
                                  padding: '0.25rem 0.6rem',
                                  fontSize: '0.72rem',
                                  borderLeft: `3px solid ${dom?.color || '#38bdf8'}`
                                }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleLaunchWorkspace(domId, evt.dataset_ids?.[domId], evt.recommended_parameters);
                                }}
                              >
                                Open {dom?.name.split('&')[0].trim()}{' '}
                                {hasLocal ? (evt.is_synthetic ? '(Demo Loaded)' : '(Real Data Loaded)') : '(Empty State)'} &rarr;
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Bottom Section: Live Data Discovery, External STAC Check, & Analysis History */}
            <div
              style={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                padding: '1.25rem'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #334155', paddingBottom: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    className={`btn ${activeBottomTab === 'discovery' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveBottomTab('discovery')}
                  >
                    📡 Dataset Discovery for Study Area ({totalReady} Ready)
                  </button>
                  <button
                    type="button"
                    className={`btn ${activeBottomTab === 'history' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveBottomTab('history')}
                  >
                    🕒 Platform Analysis History ({recentRuns.length})
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <input
                    type="date"
                    className="form-select"
                    style={{ marginTop: 0, width: '132px', padding: '0.3rem 0.45rem', fontSize: '0.74rem' }}
                    title="Start Date Filter (Optional)"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                  <span style={{ color: '#94a3b8', fontSize: '0.74rem' }}>to</span>
                  <input
                    type="date"
                    className="form-select"
                    style={{ marginTop: 0, width: '132px', padding: '0.3rem 0.45rem', fontSize: '0.74rem' }}
                    title="End Date Filter (Optional)"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.78rem' }}
                    onClick={() => runDiscovery(selectedBbox, selectedDomain, true, startDate, endDate)}
                    disabled={discovering}
                  >
                    {discovering ? 'Querying Catalogs...' : '🛰️ Check External Satellite Catalog (STAC)'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ fontSize: '0.78rem' }}
                    onClick={() => handleLaunchWorkspace(selectedDomain)}
                  >
                    Proceed to {currentDomainObj?.name.split('&')[0].trim()} Workspace &rarr;
                  </button>
                </div>
              </div>

              {activeBottomTab === 'discovery' && (
                <div>
                  {/* Discovery Summary Banner */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(4, 1fr)',
                      gap: '0.75rem',
                      marginBottom: '1rem'
                    }}
                  >
                    <div style={{ backgroundColor: '#0f172a', padding: '0.75rem', borderRadius: '6px', borderLeft: '4px solid #10b981' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Verified Real Datasets (Local)</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#10b981' }}>
                        {discovery?.summary?.local_real_count ?? 0}
                      </div>
                    </div>
                    <div style={{ backgroundColor: '#0f172a', padding: '0.75rem', borderRadius: '6px', borderLeft: '4px solid #f59e0b' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Synthetic Demo Fixtures (Local)</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#f59e0b' }}>
                        {discovery?.summary?.local_synthetic_count ?? 0}
                      </div>
                    </div>
                    <div style={{ backgroundColor: '#0f172a', padding: '0.75rem', borderRadius: '6px', borderLeft: '4px solid #38bdf8' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>External STAC Granules</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#38bdf8' }}>
                        {discovery?.summary?.external_discoverable_count ?? 0}
                      </div>
                    </div>
                    <div style={{ backgroundColor: '#0f172a', padding: '0.75rem', borderRadius: '6px', borderLeft: '4px solid #64748b' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Other / Incompatible Domain</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#94a3b8' }}>
                        {discovery?.summary?.unavailable_or_incompatible_count ?? 0}
                      </div>
                    </div>
                  </div>

                  {/* Honest Empty State if no datasets intersect AOI for this domain */}
                  {totalReady === 0 && (
                    <div
                      style={{
                        padding: '1.25rem',
                        backgroundColor: '#0f172a',
                        border: '1px dashed #475569',
                        borderRadius: '8px',
                        marginBottom: '1rem'
                      }}
                    >
                      <strong style={{ color: '#fcd34d', fontSize: '0.9rem' }}>
                        No Local Ready Datasets Found for {currentDomainObj?.name} in This Study Area
                      </strong>
                      <p style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.35rem' }}>
                        Selecting a region on the map does not automatically fabricate or stream satellite imagery.
                        For this bounding box and domain, no compatible rasters are currently staged on disk.
                      </p>
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.6rem', flexWrap: 'wrap' }}>
                        <button
                          type="button"
                          className="btn btn-primary"
                          style={{ fontSize: '0.75rem' }}
                          onClick={() => setUploadModalOpen(true)}
                        >
                          ＋ Upload Compatible GeoTIFF / GeoJSON
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ fontSize: '0.75rem' }}
                          onClick={() => {
                            if (events.length > 0) handleSelectEvent(events[0]);
                          }}
                        >
                          Jump to Storm Daniel (Verified Real Sentinel-1A Data)
                        </button>
                      </div>
                    </div>
                  )}

                  {/* 1. Local Verified Real Datasets Table */}
                  {discovery?.local_real_datasets?.length > 0 && (
                    <div style={{ marginBottom: '1rem' }}>
                      <h4 style={{ color: '#10b981', fontSize: '0.88rem', marginBottom: '0.4rem' }}>
                        ✓ Local Verified Real Satellite & Ancillary Datasets (Ready for Processing)
                      </h4>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem', color: '#e2e8f0' }}>
                        <thead>
                          <tr style={{ backgroundColor: '#0f172a', textAlign: 'left' }}>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Dataset Title</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Product Type</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Sensor / Pol</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Acquisition Date</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>CRS & Grid</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Source Provenance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {discovery.local_real_datasets.map((d) => (
                            <tr key={d.id}>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155', fontWeight: 'bold' }}>{d.name}</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}><code>{d.product_type}</code></td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>{d.sensor || '—'} {d.polarization ? `(${d.polarization})` : ''}</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>{d.acquisition_date || '—'}</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}><code>{d.crs}</code> ({d.width}×{d.height || 'vec'})</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155', color: '#94a3b8' }}>{d.source || 'Local Registry'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* 2. Local Synthetic Demonstration Fixtures Table */}
                  {discovery?.local_synthetic_datasets?.length > 0 && (
                    <div style={{ marginBottom: '1rem' }}>
                      <h4 style={{ color: '#f59e0b', fontSize: '0.88rem', marginBottom: '0.4rem' }}>
                        ⚠️ Local Synthetic Demonstration & Validation Fixtures (Explicitly Flagged Synthetic)
                      </h4>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem', color: '#e2e8f0' }}>
                        <thead>
                          <tr style={{ backgroundColor: '#0f172a', textAlign: 'left' }}>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Fixture Name</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Product Type</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Simulated Date</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>CRS & Grid</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Notice</th>
                          </tr>
                        </thead>
                        <tbody>
                          {discovery.local_synthetic_datasets.map((d) => (
                            <tr key={d.id}>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155', fontWeight: 'bold' }}>{d.name}</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}><code>{d.product_type}</code></td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>{d.acquisition_date || '—'}</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}><code>{d.crs}</code> ({d.width}×{d.height || 'vec'})</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155', color: '#fcd34d' }}>{d.compatibility_note}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* 3. External Satellite Archive (STAC) Discovery & On-Demand Granule Retrieval */}
                  {discovery?.external_discovery && (
                    <div
                      style={{
                        backgroundColor: '#0f172a',
                        padding: '0.85rem 1rem',
                        borderRadius: '6px',
                        border: '1px solid #334155'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem' }}>
                        <strong style={{ fontSize: '0.82rem', color: '#38bdf8' }}>
                          External Satellite Archive Discovery: {discovery.external_discovery.source}
                        </strong>
                        <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                          Status: <code>{discovery.external_discovery.status}</code>
                        </span>
                      </div>
                      <p style={{ fontSize: '0.76rem', color: '#cbd5e1', marginTop: '0.3rem', marginBottom: '0.5rem' }}>
                        {discovery.external_discovery.message}
                      </p>

                      {retrieveMessage && (
                        <div
                          style={{
                            padding: '0.5rem 0.75rem',
                            borderRadius: '4px',
                            marginBottom: '0.6rem',
                            fontSize: '0.75rem',
                            backgroundColor: retrieveMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                            border: retrieveMessage.type === 'success' ? '1px solid #10b981' : '1px solid #ef4444',
                            color: retrieveMessage.type === 'success' ? '#a7f3d0' : '#fca5a5'
                          }}
                        >
                          {retrieveMessage.text}
                        </div>
                      )}

                      {discovery.external_discovery.items?.length > 0 && (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.74rem', color: '#e2e8f0', marginTop: '0.4rem' }}>
                          <thead>
                            <tr style={{ backgroundColor: '#1e293b', textAlign: 'left' }}>
                              <th style={{ padding: '0.4rem', border: '1px solid #334155' }}>Remote Granule ID</th>
                              <th style={{ padding: '0.4rem', border: '1px solid #334155' }}>Collection / Sensor</th>
                              <th style={{ padding: '0.4rem', border: '1px solid #334155' }}>Date</th>
                              <th style={{ padding: '0.4rem', border: '1px solid #334155' }}>Polarization / Band</th>
                              <th style={{ padding: '0.4rem', border: '1px solid #334155' }}>On-Demand Retrieval</th>
                            </tr>
                          </thead>
                          <tbody>
                            {discovery.external_discovery.items.map((item) => (
                              <tr key={`${item.collection}-${item.granule_id}`}>
                                <td style={{ padding: '0.4rem', border: '1px solid #334155', fontFamily: 'monospace' }}>
                                  {item.granule_id}
                                </td>
                                <td style={{ padding: '0.4rem', border: '1px solid #334155' }}>
                                  {item.sensor || item.collection}
                                </td>
                                <td style={{ padding: '0.4rem', border: '1px solid #334155' }}>
                                  {item.acquisition_date || '—'}
                                </td>
                                <td style={{ padding: '0.4rem', border: '1px solid #334155' }}>
                                  {(item.polarizations || []).join(', ') || item.default_asset_key || '—'}
                                </td>
                                <td style={{ padding: '0.4rem', border: '1px solid #334155' }}>
                                  <button
                                    type="button"
                                    className="btn btn-primary"
                                    style={{ padding: '0.2rem 0.55rem', fontSize: '0.7rem' }}
                                    disabled={retrievingId === item.granule_id}
                                    onClick={() => handleRetrieveExternalGranule(item)}
                                  >
                                    {retrievingId === item.granule_id
                                      ? 'Streaming AOI Subset...'
                                      : '⬇ Retrieve & Register Subset for AOI'}
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}
                </div>
              )}

              {activeBottomTab === 'history' && (
                <div>
                  <h4 style={{ color: '#38bdf8', marginBottom: '0.5rem' }}>Reproducible Analysis History Across All Domains</h4>
                  {recentRuns.length === 0 ? (
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>No analysis runs have been executed yet.</p>
                  ) : (
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem', color: '#e2e8f0' }}>
                      <thead>
                        <tr style={{ backgroundColor: '#0f172a', textAlign: 'left' }}>
                          <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Run ID</th>
                          <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Domain</th>
                          <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Analysis</th>
                          <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Data Provenance</th>
                          <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Validation</th>
                          <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recentRuns.slice(0, 15).map((r) => {
                          const dom = DOMAINS.find((d) => d.id === r.domain);
                          return (
                            <tr key={r.id}>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155', fontFamily: 'monospace' }}>{r.id.slice(0, 12)}...</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155', color: dom?.color || '#38bdf8', fontWeight: 'bold' }}>
                                {dom?.name || r.domain}
                              </td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>{r.analysis || r.status}</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>
                                {r.is_synthetic_input === false ? (
                                  <span style={{ color: '#10b981' }}>✓ Real EO Data</span>
                                ) : r.is_synthetic_input ? (
                                  <span style={{ color: '#f59e0b' }}>⚠️ Synthetic Demo</span>
                                ) : (
                                  '—'
                                )}
                              </td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>{r.validation_status || '—'}</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155', display: 'flex', gap: '0.4rem' }}>
                                {r.status === 'completed' && (
                                  <>
                                    <button
                                      type="button"
                                      className="btn btn-primary"
                                      style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem' }}
                                      onClick={() => navigate(dom?.route || `/${r.domain}`, { state: { reopenRunId: r.id } })}
                                    >
                                      Reopen in Workspace
                                    </button>
                                    <button
                                      type="button"
                                      className="btn btn-secondary"
                                      style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem' }}
                                      onClick={() => {
                                        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                                        window.open(`${baseUrl}${ENDPOINTS.RUN_EXPORT(r.id, 'html')}`, '_blank');
                                      }}
                                    >
                                      HTML Report
                                    </button>
                                  </>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        <DatasetUploadModal
          isOpen={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
          defaultDomain={selectedDomain}
          onUploaded={() => loadInitialCatalog()}
        />
      </div>
    </MainLayout>
  );
}
