import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import DatasetSelector from '../components/DatasetSelector';
import DatasetUploadModal from '../components/DatasetUploadModal';
import ProcessingStatus from '../components/ProcessingStatus';
import BeforeAfterViewer from '../components/BeforeAfterViewer';
import MetricsPanel from '../components/MetricsPanel';
import LoadingSpinner from '../components/LoadingSpinner';
import PrimaryFindingCard from '../components/scientific/PrimaryFindingCard';
import LimitationsAccordion from '../components/scientific/LimitationsAccordion';
import SharedMap from '../components/map/SharedMap';
import { apiClient } from '../services/api';
import { ENDPOINTS } from '../services/endpoints';

export default function DomainWorkspace({ domain, defaultInputs = {} }) {
  const navigate = useNavigate();
  const location = useLocation();
  const presetInputs = location.state?.presetInputs || defaultInputs;
  const presetParams = location.state?.presetParams || {};
  const presetBbox = location.state?.studyAreaBbox || null;
  const presetRunId = location.state?.reopenRunId || null;

  const [pipelineInfo, setPipelineInfo] = useState(null);
  const [availableDatasets, setAvailableDatasets] = useState([]);
  const [selectedInputs, setSelectedInputs] = useState(presetInputs);
  const [parameters, setParameters] = useState({});
  const [status, setStatus] = useState('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [runResult, setRunResult] = useState(null);
  const [pastRuns, setPastRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('analysis'); // 'analysis' | 'validation' | 'exposure' | 'history'
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  const loadWorkspaceData = useCallback(async () => {
    try {
      setLoading(true);
      const [info, dsList, runsList] = await Promise.all([
        apiClient(ENDPOINTS.DOMAIN_INFO(domain.id)),
        apiClient(`${ENDPOINTS.DATASETS}?domain=${domain.id}`),
        apiClient(ENDPOINTS.DOMAIN_RUNS(domain.id)).catch(() => [])
      ]);
      setPipelineInfo(info);
      setAvailableDatasets(dsList);
      setPastRuns(runsList || []);

      // Populate default parameter values from spec, overridden by any presetParams from event launcher
      const initialParams = {};
      if (info && info.parameters) {
        info.parameters.forEach((p) => {
          initialParams[p.name] = presetParams[p.name] !== undefined ? presetParams[p.name] : p.default;
        });
      }
      setParameters((prev) => (Object.keys(prev).length > 0 ? prev : initialParams));

      // Auto-select datasets: prefer non-synthetic real datasets if available, sorted chronologically
      const autoInputs = { ...presetInputs };
      if (info && info.inputs && dsList.length > 0) {
        const usedIds = new Set(Object.values(autoInputs).filter(Boolean));
        info.inputs.forEach((inputSpec) => {
          if (!autoInputs[inputSpec.role]) {
            const candidates = dsList
              .filter(
                (d) => inputSpec.product_types.includes(d.product_type) && !usedIds.has(d.id) && d.file_available !== false
              )
              .sort((a, b) => {
                if (Boolean(a.is_synthetic) !== Boolean(b.is_synthetic)) {
                  return a.is_synthetic ? 1 : -1;
                }
                const da = a.acquisition_date || '9999-99-99';
                const db = b.acquisition_date || '9999-99-99';
                return da.localeCompare(db);
              });

            const roleLower = inputSpec.role.toLowerCase();
            let realMatch = null;
            const realPool = candidates.filter((d) => !d.is_synthetic);
            if (roleLower.includes('base') || roleLower.includes('pre')) {
              realMatch =
                realPool.find((d) => /base|pre/i.test(d.name) || /base|pre/i.test(d.id)) || realPool[0];
            } else if (roleLower.includes('event') || roleLower.includes('post') || roleLower.includes('monitor')) {
              realMatch =
                realPool.find((d) => /post|event|monitoring|repeat/i.test(d.name) || /post|event/i.test(d.id)) ||
                realPool[realPool.length - 1];
            } else {
              realMatch = realPool[0];
            }

            const demoMatch = candidates.find((d) => d.id.startsWith('ds-demo-') || d.id.startsWith('ds-bench-'));
            const chosen = realMatch || demoMatch || (inputSpec.required ? candidates[0] : null);
            if (chosen) {
              autoInputs[inputSpec.role] = chosen.id;
              usedIds.add(chosen.id);
            }
          }
        });
      }
      setSelectedInputs(autoInputs);

      if (presetRunId) {
        const reopened = await apiClient(ENDPOINTS.EXPLORER_RUN_DETAIL(presetRunId)).catch(() => null);
        if (reopened) {
          setRunResult(reopened);
          setStatus('completed');
        }
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to load domain configuration.');
    } finally {
      setLoading(false);
    }
  }, [domain.id]);

  useEffect(() => {
    loadWorkspaceData();
  }, [loadWorkspaceData]);

  const handleInputChange = (role, datasetId) => {
    setSelectedInputs((prev) => {
      const next = { ...prev };
      if (!datasetId) {
        delete next[role];
      } else {
        next[role] = datasetId;
      }
      return next;
    });
  };

  const handleParamChange = (paramName, value) => {
    setParameters((prev) => ({
      ...prev,
      [paramName]: value
    }));
  };

  const handleRunProcessing = async () => {
    setStatus('processing');
    setErrorMessage('');
    try {
      const cleanInputs = {};
      Object.entries(selectedInputs).forEach(([k, v]) => {
        if (v) cleanInputs[k] = v;
      });
      const payload = {
        inputs: cleanInputs,
        parameters: parameters,
        study_area_bbox: presetBbox
      };
      const response = await apiClient(ENDPOINTS.DOMAIN_PROCESS(domain.id), {
        method: 'POST',
        body: payload
      });
      setRunResult(response);
      setStatus('completed');
      // Refresh run history
      const updatedRuns = await apiClient(ENDPOINTS.DOMAIN_RUNS(domain.id)).catch(() => []);
      setPastRuns(updatedRuns);
    } catch (err) {
      setStatus('failed');
      setErrorMessage(err.message || 'Processing failed. Check input parameters.');
    }
  };

  const handleReopenRun = async (runId) => {
    if (!runId) return;
    try {
      setStatus('processing');
      setErrorMessage('');
      const reopened = await apiClient(ENDPOINTS.EXPLORER_RUN_DETAIL(runId));
      setRunResult(reopened);
      if (reopened?.provenance?.parameters) {
        setParameters(reopened.provenance.parameters);
      }
      if (reopened?.provenance?.inputs) {
        const restoredInputs = {};
        Object.entries(reopened.provenance.inputs).forEach(([role, info]) => {
          if (info?.dataset_id) restoredInputs[role] = info.dataset_id;
        });
        setSelectedInputs(restoredInputs);
      }
      setStatus('completed');
    } catch (err) {
      setStatus('failed');
      setErrorMessage(`Could not reopen run ${runId}: ${err.message}`);
    }
  };

  const getLayerUrl = (key) => {
    if (!runResult || !runResult.layers) return null;
    const l = runResult.layers.find((layer) => layer.key === key);
    if (!l) return null;
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    return `${baseUrl}${l.url}`;
  };

  const beforeUrl = getLayerUrl('baseline_preview') || getLayerUrl('terminus_baseline');
  const afterUrl =
    getLayerUrl('event_preview') ||
    getLayerUrl('velocity_preview') ||
    getLayerUrl('displacement_preview') ||
    getLayerUrl('terminus_event');
  const overlayUrl =
    getLayerUrl('flood_overlay') ||
    getLayerUrl('disturbance_overlay') ||
    getLayerUrl('burn_overlay') ||
    getLayerUrl('change_overlay');
  const changeMapUrl = getLayerUrl('change_preview');
  const validationOverlayUrl = getLayerUrl('validation_overlay');
  const exposureOverlayUrl = getLayerUrl('exposure_overlay');

  const requiredSpecs = pipelineInfo?.inputs?.filter((i) => i.required) || [];
  const optionalSpecs = pipelineInfo?.inputs?.filter((i) => !i.required) || [];

  // Derive active study area metadata from runResult or currently selected primary dataset
  const primaryDs = availableDatasets.find((d) => Object.values(selectedInputs).includes(d.id));
  const activeStudyBbox =
    runResult?.study_area?.bbox_wgs84 ||
    primaryDs?.bbox_wgs84 ||
    presetBbox ||
    null;

  return (
    <MainLayout>
      <div className="domain-page-container">
        {/* Header */}
        <div className="domain-page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <h1 className="domain-title" style={{ color: domain.color, margin: 0 }}>{domain.name}</h1>
              {runResult && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    padding: '0.2rem 0.6rem',
                    borderRadius: '4px',
                    backgroundColor: runResult.is_synthetic_input ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                    color: runResult.is_synthetic_input ? '#fcd34d' : '#6ee7b7',
                    border: `1px solid ${runResult.is_synthetic_input ? '#d97706' : '#059669'}`
                  }}
                >
                  {runResult.is_synthetic_input ? '⚠️ SYNTHETIC DEMO INPUTS' : '✓ VERIFIED REAL SATELLITE DATA'}
                </span>
              )}
            </div>
            <p className="domain-description">{pipelineInfo?.summary || domain.description}</p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setUploadModalOpen(true)}
            >
              ＋ Upload Dataset
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/earth-event-explorer')}
            >
              🌍 World Map Explorer
            </button>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>
            <LoadingSpinner size={36} text="Loading domain parameters & dataset registry..." />
          </div>
        ) : (
          <div className="domain-body-grid">
            {/* Left Column: Input, Provenance & Parameter Controls */}
            <section className="domain-control-panel">
              {/* Study Area & Provenance Summary Box */}
              <div style={{ backgroundColor: '#0f172a', padding: '0.75rem', borderRadius: '6px', border: '1px solid #334155', marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 'bold', color: '#38bdf8', marginBottom: '0.3rem' }}>
                  📍 Active Study Area & Provenance
                </div>
                <div style={{ fontSize: '0.73rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  <div>
                    <strong>Bounds (WGS84):</strong>{' '}
                    <code>{activeStudyBbox ? `[${activeStudyBbox.map((x) => Number(x).toFixed(3)).join(', ')}]` : 'Select dataset'}</code>
                  </div>
                  <div>
                    <strong>Native CRS:</strong>{' '}
                    <code>{runResult?.study_area?.native_crs || primaryDs?.crs || 'N/A'}</code>
                  </div>
                  {runResult?.observation_dates?.length > 0 && (
                    <div>
                      <strong>Observation Dates:</strong> {runResult.observation_dates.join(' → ')}
                    </div>
                  )}
                  {runResult?.run_id && (
                    <div>
                      <strong>Run ID:</strong> <code>{runResult.run_id.slice(0, 12)}...</code>
                    </div>
                  )}
                </div>
              </div>

              {/* Reopen Previous Run Selector */}
              {pastRuns.length > 0 && (
                <div style={{ marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '1px solid #334155' }}>
                  <label style={{ fontSize: '0.78rem', color: '#93c5fd', fontWeight: 'bold' }}>
                    ↺ Reopen Previous Analysis ({pastRuns.filter((r) => r.status === 'completed').length}):
                  </label>
                  <select
                    className="form-select"
                    value={runResult?.run_id || ''}
                    onChange={(e) => handleReopenRun(e.target.value)}
                  >
                    <option value="">-- Select a Past Run to Reopen --</option>
                    {pastRuns
                      .filter((r) => r.status === 'completed')
                      .slice(0, 12)
                      .map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.id.slice(0, 8)} • {r.is_synthetic_input ? '[SYNTH]' : '[REAL]'} •{' '}
                          {r.observation_dates?.join('→') || new Date(r.started_at).toLocaleTimeString()}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              {availableDatasets.length === 0 && (
                <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '6px', padding: '0.75rem', marginBottom: '1rem', color: '#fca5a5', fontSize: '0.8rem' }}>
                  <strong>No Staged Datasets Available:</strong> There are currently no staged datasets matching {domain.name}.
                  {domain.id === 'domain4' && ' Real agricultural SAR backscatter datasets are pending ingestion. InSAR ground deformation datasets belong to Domain 3.'}
                </div>
              )}

              <h3>1. Required Primary Observations</h3>
              {requiredSpecs.map((inputSpec) => {
                const filtered = availableDatasets.filter((d) =>
                  inputSpec.product_types.includes(d.product_type)
                );
                return (
                  <div key={inputSpec.role} style={{ marginBottom: '0.9rem' }}>
                    <DatasetSelector
                      label={`${inputSpec.label} *`}
                      datasets={filtered}
                      selectedId={selectedInputs[inputSpec.role]}
                      onSelect={(val) => handleInputChange(inputSpec.role, val)}
                    />
                    <small style={{ color: '#94a3b8', fontSize: '0.72rem' }}>
                      {inputSpec.description}
                    </small>
                  </div>
                );
              })}

              {optionalSpecs.length > 0 && (
                <div style={{ marginTop: '1rem', borderTop: '1px solid #334155', paddingTop: '0.85rem' }}>
                  <h4 style={{ fontSize: '0.88rem', color: '#93c5fd', marginBottom: '0.6rem' }}>
                    2. Reference, Validation & Exposure Layers
                  </h4>
                  {optionalSpecs.map((inputSpec) => {
                    const filtered = availableDatasets.filter((d) =>
                      inputSpec.product_types.includes(d.product_type)
                    );
                    return (
                      <div key={inputSpec.role} style={{ marginBottom: '0.85rem' }}>
                        <DatasetSelector
                          label={inputSpec.label}
                          datasets={filtered}
                          selectedId={selectedInputs[inputSpec.role]}
                          onSelect={(val) => handleInputChange(inputSpec.role, val)}
                        />
                        <small style={{ color: '#94a3b8', fontSize: '0.7rem' }}>
                          {inputSpec.description}
                        </small>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Dynamic Parameter Controls */}
              {pipelineInfo?.parameters && pipelineInfo.parameters.length > 0 && (
                <div style={{ marginTop: '1rem', borderTop: '1px solid #334155', paddingTop: '0.85rem' }}>
                  <h4 style={{ fontSize: '0.88rem', color: '#93c5fd', marginBottom: '0.5rem' }}>
                    3. Algorithm Configuration
                  </h4>
                  {pipelineInfo.parameters.map((p) => (
                    <div key={p.name} style={{ marginTop: '0.5rem' }}>
                      <label style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>{p.label}:</label>
                      {p.type === 'select' ? (
                        <select
                          className="form-select"
                          value={parameters[p.name] ?? p.default}
                          onChange={(e) => handleParamChange(p.name, e.target.value)}
                        >
                          {p.options.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      ) : p.type === 'number' || p.type === 'integer' ? (
                        <input
                          type="number"
                          className="form-select"
                          value={parameters[p.name] ?? p.default}
                          step={p.type === 'integer' ? '1' : '0.1'}
                          min={p.min}
                          max={p.max}
                          onChange={(e) => handleParamChange(p.name, Number(e.target.value))}
                        />
                      ) : null}
                      <small style={{ color: '#94a3b8', fontSize: '0.68rem' }}>{p.description}</small>
                    </div>
                  ))}
                </div>
              )}

              <button
                type="button"
                className="btn btn-primary"
                style={{ marginTop: '1.25rem', width: '100%', justifyContent: 'center', padding: '0.7rem' }}
                onClick={handleRunProcessing}
                disabled={status === 'processing'}
              >
                {status === 'processing' ? 'Executing Georeferenced SAR Pipeline...' : `▶ Run ${domain.name} Analysis`}
              </button>

              <ProcessingStatus
                status={status}
                message={
                  errorMessage ||
                  (status === 'completed'
                    ? `Completed in ${runResult?.execution_time_seconds ?? 0}s`
                    : 'Configure inputs and click Run Analysis.')
                }
              />

              {runResult?.warnings?.length > 0 && (
                <div style={{ backgroundColor: 'rgba(217, 119, 6, 0.15)', border: '1px solid #d97706', padding: '0.75rem', borderRadius: '6px', marginTop: '0.85rem' }}>
                  <strong style={{ color: '#f59e0b', fontSize: '0.78rem' }}>Notices & Data Provenance Warnings:</strong>
                  <ul style={{ fontSize: '0.73rem', color: '#fde68a', paddingLeft: '1.1rem', marginTop: '0.25rem', marginBottom: 0 }}>
                    {runResult.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>

            {/* Right Column: Multi-Tab Scientific Workspace */}
            <section className="domain-results-panel">
              {/* NASA1 Aerospace 4-Stage Stepper Navigation */}
              <div className="gev-stepper-tabs" style={{ marginBottom: '1.1rem' }}>
                <button
                  type="button"
                  className={`gev-stepper-tab ${activeTab === 'analysis' ? 'active' : ''}`}
                  onClick={() => setActiveTab('analysis')}
                >
                  <span className="gev-stepper-num">1</span>
                  <span>MONITOR</span>
                </button>
                <button
                  type="button"
                  className={`gev-stepper-tab ${activeTab === 'observe' ? 'active' : ''}`}
                  onClick={() => setActiveTab('observe')}
                >
                  <span className="gev-stepper-num">2</span>
                  <span>OBSERVE (3D/2D)</span>
                </button>
                <button
                  type="button"
                  className={`gev-stepper-tab ${activeTab === 'validation' ? 'active' : ''}`}
                  onClick={() => setActiveTab('validation')}
                >
                  <span className="gev-stepper-num">3</span>
                  <span>EVIDENCE</span>
                  {runResult?.validation?.status === 'compared_to_reference' && (
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  )}
                </button>
                <button
                  type="button"
                  className={`gev-stepper-tab ${
                    activeTab === 'dossier' || activeTab === 'exposure' || activeTab === 'history'
                      ? 'active'
                      : ''
                  }`}
                  onClick={() => setActiveTab('dossier')}
                >
                  <span className="gev-stepper-num">4</span>
                  <span>DOSSIER</span>
                  {runResult?.exposure?.status === 'evaluated' && (
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  )}
                </button>
              </div>

              {/* TAB 1: STAGE 1 — MONITOR (SWIPE COMPARISON, KPIS & PRIMARY VERDICT) */}
              {activeTab === 'analysis' && (
                <div>
                  {runResult && (
                    <div style={{ marginBottom: '1rem' }}>
                      <PrimaryFindingCard
                        verdict={`${domain.name} — Operational Evaluation`}
                        status={runResult.is_synthetic_input ? 'demo' : 'verified'}
                        statusLabel={runResult.is_synthetic_input ? '⚠️ SYNTHETIC DEMO INPUTS' : '✓ VERIFIED REAL SATELLITE DATA'}
                        footprintText={`Bounds: ${
                          activeStudyBbox
                            ? `[${activeStudyBbox.map((x) => Number(x).toFixed(3)).join(', ')}]`
                            : 'AOI Extent'
                        } • Native CRS: ${runResult?.study_area?.native_crs || primaryDs?.crs || 'EPSG:4326'}`}
                        findingText={
                          runResult?.explanation?.level1_visual ||
                          `Analysis produced calibrated backscatter outputs across the specified observation area.`
                        }
                        kpis={(runResult?.summary_metrics || []).slice(0, 4).map((m) => ({
                          label: m.label,
                          value: String(m.value),
                          unit: m.unit || ''
                        }))}
                        cautionText={runResult?.caveats?.[0] || null}
                      />
                    </div>
                  )}

                  <BeforeAfterViewer
                    beforeUrl={beforeUrl}
                    afterUrl={afterUrl}
                    overlayUrl={overlayUrl}
                    changeMapUrl={changeMapUrl}
                    validationOverlayUrl={validationOverlayUrl}
                    exposureOverlayUrl={exposureOverlayUrl}
                    beforeLabel="Pre-Event / Baseline"
                    afterLabel="Post-Event / Result"
                    overlayLabel="Detected Change Overlay"
                    boundsWgs84={activeStudyBbox}
                    legend={runResult?.domain_data?.legend || []}
                    inspector={runResult?.domain_data?.inspector || null}
                  />

                  <MetricsPanel
                    title={`${domain.name} Quantitative Measurements`}
                    metrics={
                      runResult?.summary_metrics || [
                        { label: 'Pipeline Status', value: status.toUpperCase() },
                        { label: 'Observations', value: 'Select inputs & run analysis' }
                      ]
                    }
                  />

                  {/* Export Action Bar */}
                  {runResult && status === 'completed' && (
                    <div style={{ marginTop: '1rem', display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ flex: 1, justifyContent: 'center' }}
                        onClick={() => {
                          const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                          window.open(`${baseUrl}${ENDPOINTS.RUN_EXPORT(runResult.run_id, 'json')}`, '_blank');
                        }}
                      >
                        📄 Export JSON Scientific Report (15-Section)
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ flex: 1, justifyContent: 'center' }}
                        onClick={() => {
                          const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                          window.open(`${baseUrl}${ENDPOINTS.RUN_EXPORT(runResult.run_id, 'html')}`, '_blank');
                        }}
                      >
                        🖨️ Open Printable HTML / PDF Report
                      </button>
                    </div>
                  )}

                  {/* Four-Tier Scientific Explainability */}
                  {runResult?.explanation && (
                    <div style={{ marginTop: '1rem', backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                      <h4 style={{ color: '#38bdf8', marginBottom: '0.6rem' }}>Four-Tier Scientific Explainability</h4>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                        <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
                          <strong style={{ fontSize: '0.8rem', color: '#93c5fd' }}>Level 1: What Was Observed</strong>
                          <p style={{ fontSize: '0.76rem', color: '#cbd5e1', marginTop: '0.25rem' }}>{runResult.explanation.level1_visual}</p>
                        </div>
                        <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
                          <strong style={{ fontSize: '0.8rem', color: '#93c5fd' }}>Level 2: Processing Method Applied</strong>
                          <p style={{ fontSize: '0.76rem', color: '#cbd5e1', marginTop: '0.25rem' }}>{runResult.explanation.level2_method}</p>
                        </div>
                        <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
                          <strong style={{ fontSize: '0.8rem', color: '#6ee7b7' }}>Level 3: Quantitative Physical Evidence</strong>
                          <p style={{ fontSize: '0.76rem', color: '#cbd5e1', marginTop: '0.25rem' }}>{runResult.explanation.level3_evidence}</p>
                        </div>
                        <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px', border: '1px solid rgba(248, 113, 113, 0.35)' }}>
                          <strong style={{ fontSize: '0.8rem', color: '#fca5a5' }}>Level 4: Limitations & Alternative Explanations</strong>
                          <p style={{ fontSize: '0.76rem', color: '#fca5a5', marginTop: '0.25rem' }}>{runResult.explanation.level4_uncertainty}</p>
                        </div>
                      </div>

                      {runResult.caveats?.length > 0 && (
                        <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                          <strong>Known Domain Limitations:</strong>
                          <ul style={{ paddingLeft: '1.2rem', marginTop: '0.25rem', marginBottom: 0 }}>
                            {runResult.caveats.map((c, i) => (
                              <li key={i}>{c}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: STAGE 2 — OBSERVE (GEOSPATIAL 3D CESIUM GLOBE & 2D PROJECTION) */}
              {activeTab === 'observe' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.65rem 0.95rem',
                      borderRadius: '8px',
                      background: 'rgba(12, 12, 20, 0.8)',
                      border: '1px solid rgba(255, 255, 255, 0.08)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.82rem',
                          fontWeight: 600,
                          color: '#00d4ff',
                          letterSpacing: '1px'
                        }}
                      >
                        GEOSPATIAL 3D/2D VIEWPORT • {domain.name.toUpperCase()}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                      Extent:{' '}
                      {activeStudyBbox
                        ? `[${activeStudyBbox.map((x) => Number(x).toFixed(3)).join(', ')}]`
                        : 'Global AOI'}
                    </span>
                  </div>

                  <SharedMap
                    selectedBbox={activeStudyBbox}
                    rasterOverlays={[
                      ...(overlayUrl ? [{ id: 'overlay', name: 'Detected Change Overlay', url: overlayUrl, bounds: activeStudyBbox, opacity: 0.85 }] : []),
                      ...(changeMapUrl ? [{ id: 'change', name: 'Difference Raster', url: changeMapUrl, bounds: activeStudyBbox, opacity: 0.75 }] : []),
                      ...(afterUrl ? [{ id: 'after', name: 'Post-Event SAR', url: afterUrl, bounds: activeStudyBbox, opacity: 0.9 }] : []),
                      ...(beforeUrl ? [{ id: 'before', name: 'Pre-Event SAR', url: beforeUrl, bounds: activeStudyBbox, opacity: 0.9 }] : [])
                    ]}
                    height={520}
                    defaultMode="3d"
                  />

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.76rem' }}>
                    <div
                      style={{
                        padding: '0.65rem 0.85rem',
                        borderRadius: '8px',
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid rgba(255, 255, 255, 0.08)'
                      }}
                    >
                      <strong style={{ color: '#00d4ff', display: 'block', marginBottom: '0.2rem' }}>
                        🌐 3D Photorealistic Terrain View
                      </strong>
                      <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.72rem' }}>
                        Inspect terrain slope, elevation, ridgelines, and valleys using Cesium's 3D globe. Hold right-click or scroll to tilt and rotate camera angle.
                      </p>
                    </div>
                    <div
                      style={{
                        padding: '0.65rem 0.85rem',
                        borderRadius: '8px',
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid rgba(255, 255, 255, 0.08)'
                      }}
                    >
                      <strong style={{ color: '#10b981', display: 'block', marginBottom: '0.2rem' }}>
                        🗺️ 2D Precision Cartographic Projection
                      </strong>
                      <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.72rem' }}>
                        Toggle to 2D view for pixel-accurate planar measurements, drawing custom bounding boxes, and inspecting SAR backscatter raster alignment.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: STAGE 3 — EVIDENCE, VALIDATION & ERROR EXPLORER */}
              {activeTab === 'validation' && (
                <div>
                  <h3 style={{ color: '#38bdf8', marginBottom: '0.4rem' }}>Independent Reference Validation & Error Explorer</h3>
                  {!runResult ? (
                    <div style={{ padding: '2rem', backgroundColor: '#0f172a', borderRadius: '8px', textAlign: 'center', color: '#94a3b8' }}>
                      Run an analysis first to inspect reference validation metrics and spatial disagreement maps.
                    </div>
                  ) : runResult.validation?.status !== 'compared_to_reference' ? (
                    <div style={{ padding: '1.25rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '8px' }}>
                      <strong style={{ color: '#fcd34d' }}>Validation Status: NOT VALIDATED</strong>
                      <p style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '0.4rem' }}>
                        {runResult.validation?.notes || 'No independent reference dataset was supplied for this run. NISAR never fabricates validation scores when reference labels are absent.'}
                      </p>
                      <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '0.4rem' }}>
                        To enable validation, select an independent reference dataset under <strong>&ldquo;2. Reference, Validation & Exposure Layers&rdquo;</strong> in the left panel and click <strong>Run Analysis</strong>.
                      </p>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      {/* Reference Provenance Header */}
                      <div
                        style={{
                          backgroundColor: '#0f172a',
                          padding: '0.85rem 1rem',
                          borderRadius: '8px',
                          border: runResult.validation.reference_is_synthetic
                            ? '1px solid #d97706'
                            : runResult.validation.reference_independence === 'climatological_comparative_baseline'
                            ? '1px solid #38bdf8'
                            : runResult.validation.reference_independence === 'partially_independent_cross_pair'
                            ? '1px solid #818cf8'
                            : '1px solid #059669'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem' }}>
                          <strong
                            style={{
                              color: runResult.validation.reference_is_synthetic
                                ? '#fcd34d'
                                : runResult.validation.reference_independence === 'climatological_comparative_baseline'
                                ? '#7dd3fc'
                                : runResult.validation.reference_independence === 'partially_independent_cross_pair'
                                ? '#a5b4fc'
                                : '#6ee7b7',
                              fontSize: '0.88rem'
                            }}
                          >
                            {runResult.validation.reference_independence_label
                              ? `${runResult.validation.reference_independence_label}: ${runResult.validation.reference_dataset_name}`
                              : runResult.validation.reference_is_synthetic
                              ? `⚠️ Demonstration Benchmark Evaluation: ${runResult.validation.reference_dataset_name}`
                              : `✓ Independent Real Reference Validation: ${runResult.validation.reference_dataset_name}`}
                          </strong>
                          <span
                            style={{
                              fontSize: '0.72rem',
                              padding: '0.15rem 0.5rem',
                              borderRadius: '4px',
                              backgroundColor: runResult.validation.reference_is_synthetic
                                ? 'rgba(217, 119, 6, 0.2)'
                                : runResult.validation.reference_independence === 'climatological_comparative_baseline'
                                ? 'rgba(56, 189, 248, 0.2)'
                                : runResult.validation.reference_independence === 'partially_independent_cross_pair'
                                ? 'rgba(129, 140, 248, 0.2)'
                                : 'rgba(16, 185, 129, 0.2)',
                              color: runResult.validation.reference_is_synthetic
                                ? '#fde68a'
                                : runResult.validation.reference_independence === 'climatological_comparative_baseline'
                                ? '#bae6fd'
                                : runResult.validation.reference_independence === 'partially_independent_cross_pair'
                                ? '#c7d2fe'
                                : '#a7f3d0',
                              fontWeight: 600
                            }}
                          >
                            {runResult.validation.reference_is_synthetic
                              ? 'SYNTHETIC / BENCHMARK REFERENCE'
                              : runResult.validation.reference_independence === 'climatological_comparative_baseline'
                              ? 'CLIMATOLOGICAL BASELINE COMPARISON'
                              : runResult.validation.reference_independence === 'partially_independent_cross_pair'
                              ? 'PARTIALLY INDEPENDENT CROSS-PAIR'
                              : 'INDEPENDENT REAL REFERENCE'}
                          </span>
                        </div>
                        <p style={{ fontSize: '0.78rem', color: '#cbd5e1', marginTop: '0.3rem', marginBottom: 0 }}>
                          {runResult.validation.notes} (Source: {runResult.validation.reference_source})
                        </p>
                      </div>

                      {/* Validation Metrics */}
                      <MetricsPanel
                        title="Reference Agreement Metrics"
                        metrics={runResult.validation.metrics || []}
                      />

                      {/* Spatial Agreement & Discrepancy Visual Preview */}
                      {validationOverlayUrl && (
                        <div style={{ backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                          <h4 style={{ color: '#93c5fd', marginBottom: '0.4rem' }}>Spatial Agreement & Discrepancy Map</h4>
                          <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.6rem' }}>
                            {runResult.validation.evaluation_type === 'classification'
                              ? 'Emerald Green = Agreement (True Positive) • Amber = False Positive (Commission) • Rose = Missed Detection (False Negative) • Slate = Terrain/Mask Explained'
                              : 'Diverging Residual Error Map (Blue = Negative Bias, White = Near-Zero Residual, Red = Positive Bias)'}
                          </p>
                          <div style={{ position: 'relative', height: '260px', backgroundColor: '#020617', borderRadius: '6px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {afterUrl && (
                              <img src={afterUrl} alt="Background SAR" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', opacity: 0.45 }} />
                            )}
                            <img src={validationOverlayUrl} alt="Validation Agreement Map" style={{ position: 'relative', width: '100%', height: '100%', objectFit: 'contain' }} />
                          </div>
                        </div>
                      )}

                      {/* Confusion Matrix (for Classification) */}
                      {runResult.validation.confusion_matrix && (
                        <div style={{ backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                          <h4 style={{ color: '#93c5fd', marginBottom: '0.5rem' }}>
                            Confusion Matrix & Evaluation Procedure ({runResult.validation.confusion_matrix.positive_class_definition})
                          </h4>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', color: '#e2e8f0' }}>
                            <thead>
                              <tr style={{ backgroundColor: '#1e293b', textAlign: 'left' }}>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Category</th>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Pixel Count</th>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Physical Area ({runResult.validation.confusion_matrix.area_unit})</th>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Scientific Meaning</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155', color: '#10b981', fontWeight: 'bold' }}>True Positive (Agreement)</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>{runResult.validation.confusion_matrix.true_positive_pixels.toLocaleString()}</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>{runResult.validation.confusion_matrix.true_positive_area}</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>Detected by NISAR and confirmed by reference</td>
                              </tr>
                              <tr>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155', color: '#f59e0b', fontWeight: 'bold' }}>False Positive (Commission)</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>{runResult.validation.confusion_matrix.false_positive_pixels.toLocaleString()}</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>{runResult.validation.confusion_matrix.false_positive_area}</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>Flagged by NISAR but absent in reference</td>
                              </tr>
                              <tr>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155', color: '#f43f5e', fontWeight: 'bold' }}>False Negative (Missed)</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>{runResult.validation.confusion_matrix.false_negative_pixels.toLocaleString()}</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>{runResult.validation.confusion_matrix.false_negative_area}</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>Present in reference but missed by NISAR</td>
                              </tr>
                              <tr>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155', color: '#94a3b8' }}>True Negative (Unchanged)</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>{runResult.validation.confusion_matrix.true_negative_pixels.toLocaleString()}</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>{runResult.validation.confusion_matrix.true_negative_area}</td>
                                <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>Agreed background / unchanged terrain</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Error Explorer */}
                      {runResult.validation.error_explorer && (
                        <div style={{ backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                          <h4 style={{ color: '#fcd34d', marginBottom: '0.5rem' }}>Error Explorer & Unresolved Discrepancies</h4>
                          <div style={{ fontSize: '0.78rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                            {runResult.validation.error_explorer.false_positive_summary && (
                              <div>• <strong>Commission / False Positives:</strong> {runResult.validation.error_explorer.false_positive_summary}</div>
                            )}
                            {runResult.validation.error_explorer.false_negative_summary && (
                              <div>• <strong>Omission / Missed Detections:</strong> {runResult.validation.error_explorer.false_negative_summary}</div>
                            )}
                            <div>
                              • <strong>Unresolved Discrepancies:</strong>{' '}
                              <span style={{ color: '#fca5a5' }}>{runResult.validation.error_explorer.unresolved_discrepancy_note}</span>
                            </div>
                            <div>
                              • <strong>Missing / Nodata Pixels Excluded:</strong> {runResult.validation.error_explorer.missing_data_pixels?.toLocaleString() || 0} px
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Baseline vs Physical Pipeline vs Probabilistic Classifier Benchmark */}
                      {runResult.validation.method_comparison?.length > 0 && (
                        <div style={{ backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                          <h4 style={{ color: '#38bdf8', marginBottom: '0.4rem' }}>Baseline vs. Adaptive Physical vs. Probabilistic Classifier Comparison</h4>
                          <p style={{ fontSize: '0.74rem', color: '#94a3b8', marginBottom: '0.6rem' }}>
                            Evaluated on the full held-out study scene with zero in-scene pixel training leakage.
                          </p>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem', color: '#e2e8f0' }}>
                            <thead>
                              <tr style={{ backgroundColor: '#1e293b', textAlign: 'left' }}>
                                <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Method</th>
                                <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>IoU (%)</th>
                                <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>F1 (%)</th>
                                <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Precision (%)</th>
                                <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Recall (%)</th>
                                <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Time (ms)</th>
                                <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Known Limitations</th>
                              </tr>
                            </thead>
                            <tbody>
                              {runResult.validation.method_comparison.map((mc, idx) => (
                                <tr key={idx}>
                                  <td style={{ padding: '0.45rem', border: '1px solid #334155', fontWeight: 'bold' }}>{mc.method}</td>
                                  <td style={{ padding: '0.45rem', border: '1px solid #334155', color: '#38bdf8' }}>{mc.iou_pct}%</td>
                                  <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>{mc.f1_pct}%</td>
                                  <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>{mc.precision_pct}%</td>
                                  <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>{mc.recall_pct}%</td>
                                  <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>{mc.runtime_ms}</td>
                                  <td style={{ padding: '0.45rem', border: '1px solid #334155', color: '#94a3b8' }}>{mc.limitations}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: STAGE 4 — DOSSIER (ASSET EXPOSURE, LIMITATIONS ACCORDION, PROVENANCE & EXPORT) */}
              {(activeTab === 'dossier' || activeTab === 'exposure' || activeTab === 'history') && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  {/* Part 1: Real-World Spatial Asset Exposure Analysis */}
                  <div>
                    <h3 style={{ color: '#00d4ff', fontFamily: 'var(--font-mono)', fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                      1. Real-World Spatial Asset Exposure Analysis
                    </h3>
                    {!runResult ? (
                      <div style={{ padding: '2rem', backgroundColor: '#0f172a', borderRadius: '8px', textAlign: 'center', color: '#94a3b8' }}>
                        Run an analysis first to evaluate spatial intersection with mapped infrastructure and assets.
                      </div>
                    ) : runResult.exposure?.status !== 'evaluated' ? (
                      <div style={{ padding: '1.25rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '8px' }}>
                        <strong style={{ color: '#fcd34d' }}>Exposure Status: NOT EVALUATED</strong>
                        <p style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '0.4rem' }}>
                          {runResult.exposure?.notes || 'No supporting exposure asset dataset was selected for this run.'}
                        </p>
                        <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '0.4rem' }}>
                          Select an <strong>Exposure Assets (GeoJSON)</strong> layer in the left panel and click <strong>Run Analysis</strong> to compute measured spatial intersections.
                        </p>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <div style={{ backgroundColor: '#0f172a', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid #38bdf8' }}>
                          <strong style={{ color: '#38bdf8', fontSize: '0.88rem' }}>
                            ✓ Asset Layer Intersected: {runResult.exposure.asset_dataset_name}
                          </strong>
                          <p style={{ fontSize: '0.78rem', color: '#cbd5e1', marginTop: '0.3rem', marginBottom: 0 }}>
                            {runResult.exposure.notes} (Source: {runResult.exposure.asset_source})
                          </p>
                        </div>

                        <MetricsPanel
                          title="Measured Spatial Exposure Summary"
                          metrics={runResult.exposure.metrics || []}
                        />

                        {exposureOverlayUrl && (
                          <div style={{ backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                            <h4 style={{ color: '#93c5fd', marginBottom: '0.4rem' }}>Asset Exposure Map Overlay</h4>
                            <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.6rem' }}>
                              Gold = Mapped Asset Intersecting Detected Change • Purple = Mapped Asset Outside Change Footprint
                            </p>
                            <div style={{ position: 'relative', height: '240px', backgroundColor: '#020617', borderRadius: '6px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                              {afterUrl && (
                                <img src={afterUrl} alt="Background SAR" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', opacity: 0.45 }} />
                              )}
                              <img src={exposureOverlayUrl} alt="Exposure Overlay" style={{ position: 'relative', width: '100%', height: '100%', objectFit: 'contain' }} />
                            </div>
                          </div>
                        )}

                        <div style={{ backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                          <h4 style={{ color: '#93c5fd', marginBottom: '0.5rem' }}>Intersected Asset Breakdown</h4>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', color: '#e2e8f0' }}>
                            <thead>
                              <tr style={{ backgroundColor: '#1e293b', textAlign: 'left' }}>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Asset Name</th>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Class</th>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Geometry</th>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Status</th>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Exposed / Total in AOI</th>
                                <th style={{ padding: '0.5rem', border: '1px solid #334155' }}>Basis</th>
                              </tr>
                            </thead>
                            <tbody>
                              {runResult.exposure.asset_breakdown.map((a, idx) => (
                                <tr key={idx}>
                                  <td style={{ padding: '0.5rem', border: '1px solid #334155', fontWeight: 'bold' }}>{a.asset_name}</td>
                                  <td style={{ padding: '0.5rem', border: '1px solid #334155', textTransform: 'capitalize' }}>{a.asset_class}</td>
                                  <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>{a.geometry_type}</td>
                                  <td style={{ padding: '0.5rem', border: '1px solid #334155', color: a.exposed ? '#facc15' : '#94a3b8', fontWeight: 'bold' }}>
                                    {a.exposed ? '⚠️ EXPOSED' : 'Unexposed'}
                                  </td>
                                  <td style={{ padding: '0.5rem', border: '1px solid #334155' }}>
                                    {a.exposure_measurement} {a.unit}
                                  </td>
                                  <td style={{ padding: '0.5rem', border: '1px solid #334155', color: '#94a3b8' }}>{a.measurement_basis}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        {runResult.exposure.limitations?.length > 0 && (
                          <div style={{ backgroundColor: 'rgba(245, 158, 11, 0.12)', border: '1px solid #d97706', padding: '0.75rem', borderRadius: '6px', fontSize: '0.75rem', color: '#fde68a' }}>
                            <strong>Exposure Interpretation Safeguards:</strong>
                            <ul style={{ paddingLeft: '1.2rem', marginTop: '0.25rem', marginBottom: 0 }}>
                              {runResult.exposure.limitations.map((lim, i) => (
                                <li key={i}>{lim}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Part 2: Progressive Disclosure Limitations, Quality Filtering & Citations */}
                  <div>
                    <h3 style={{ color: '#00d4ff', fontFamily: 'var(--font-mono)', fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                      2. Peer-Reviewed Methodology & Physical Assumptions
                    </h3>
                    <LimitationsAccordion
                      limitations={
                        runResult?.caveats ||
                        pipelineInfo?.caveats || [
                          'SAR backscatter is sensitive to surface roughness, dielectric permittivity, and topography.',
                          'Complex dielectric changes between wet/dry soil can modulate backscatter independently of target features.',
                          'Multi-temporal baseline decorrelation requires careful temporal window selection.'
                        ]
                      }
                      methodologyText={
                        runResult?.explanation?.level2_method ||
                        pipelineInfo?.summary ||
                        'Standardized radiometric calibration, speckle reduction, and georeferenced spatial differencing.'
                      }
                      citation={
                        runResult?.provenance?.dataset_citations?.join('; ') ||
                        'Copernicus Sentinel-1 (ESA) / NASA-ISRO SAR Mission (NISAR)'
                      }
                    />
                  </div>

                  {/* Part 3: Reproducibility, Provenance, Run History & Report Export */}
                  <div>
                    <h3 style={{ color: '#00d4ff', fontFamily: 'var(--font-mono)', fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                      3. Reproducibility, Run History & Report Export
                    </h3>

                  {runResult && (
                    <div style={{ backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
                        <h4 style={{ color: '#93c5fd', margin: 0 }}>Current Run Provenance ({runResult.run_id})</h4>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            type="button"
                            className="btn btn-primary"
                            style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
                            onClick={() => {
                              const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                              window.open(`${baseUrl}${ENDPOINTS.RUN_EXPORT(runResult.run_id, 'json')}`, '_blank');
                            }}
                          >
                            📄 Export JSON Report
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
                            onClick={() => {
                              const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                              window.open(`${baseUrl}${ENDPOINTS.RUN_EXPORT(runResult.run_id, 'html')}`, '_blank');
                            }}
                          >
                            🖨️ Printable HTML / PDF Report
                          </button>
                        </div>
                      </div>
                      <pre
                        style={{
                          backgroundColor: '#020617',
                          color: '#cbd5e1',
                          padding: '0.75rem',
                          borderRadius: '6px',
                          fontSize: '0.72rem',
                          maxHeight: '240px',
                          overflow: 'auto'
                        }}
                      >
                        {JSON.stringify(runResult.provenance, null, 2)}
                      </pre>
                    </div>
                  )}

                  <div style={{ backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                    <h4 style={{ color: '#93c5fd', marginBottom: '0.5rem' }}>Persisted Domain Run History</h4>
                    {pastRuns.length === 0 ? (
                      <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>No runs recorded for {domain.name} yet.</p>
                    ) : (
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem', color: '#e2e8f0' }}>
                        <thead>
                          <tr style={{ backgroundColor: '#1e293b', textAlign: 'left' }}>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Run ID</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Status</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Data Type</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Observation Dates</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Validation</th>
                            <th style={{ padding: '0.45rem', border: '1px solid #334155' }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {pastRuns.slice(0, 15).map((r) => (
                            <tr key={r.id}>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155', fontFamily: 'monospace' }}>{r.id.slice(0, 12)}...</td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155', color: r.status === 'completed' ? '#10b981' : '#f43f5e' }}>
                                {r.status.toUpperCase()}
                              </td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>
                                {r.is_synthetic_input === false ? 'Real EO' : r.is_synthetic_input ? 'Synthetic' : '—'}
                              </td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>
                                {r.observation_dates?.join(' → ') || new Date(r.started_at).toLocaleString()}
                              </td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>
                                {r.validation_status || '—'}
                              </td>
                              <td style={{ padding: '0.45rem', border: '1px solid #334155' }}>
                                {r.status === 'completed' && (
                                  <button
                                    type="button"
                                    className="btn btn-secondary"
                                    style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}
                                    onClick={() => {
                                      handleReopenRun(r.id);
                                      setActiveTab('analysis');
                                    }}
                                  >
                                    Reopen
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </div>
            )}
            </section>
          </div>
        )}

        <DatasetUploadModal
          isOpen={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
          defaultDomain={domain.id}
          onUploaded={() => loadWorkspaceData()}
        />
      </div>
    </MainLayout>
  );
}
