import React from 'react';
import { useNavigate } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import DatasetSelector from '../components/DatasetSelector';
import FileUploader from '../components/FileUploader';
import ProcessingStatus from '../components/ProcessingStatus';
import BeforeAfterViewer from '../components/BeforeAfterViewer';
import MetricsPanel from '../components/MetricsPanel';

export default function DomainLayout({ domain, children }) {
  const navigate = useNavigate();

  return (
    <MainLayout>
      <div className="domain-page-container">
        <div className="domain-page-header">
          <div>
            <h1 className="domain-title">{domain.name}</h1>
            <p className="domain-description">{domain.description}</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate('/dashboard')}
          >
            &larr; Back to Dashboard
          </button>
        </div>

        <div className="domain-body-grid">
          <section className="domain-control-panel">
            <h3>Configuration & Controls</h3>
            <DatasetSelector label={`Select ${domain.name} Dataset`} />
            <FileUploader label="Upload SAR Product / Data File" />
            <ProcessingStatus status="idle" message="Ready for execution." />
          </section>

          <section className="domain-results-panel">
            <h3>Visualizations & Comparison</h3>
            <BeforeAfterViewer
              beforeLabel="Pre-event / Reference"
              afterLabel="Post-event / Processing Result"
            />
            <MetricsPanel
              title={`${domain.name} Analytics`}
              metrics={[
                { label: 'Sample Metric A', value: '0.00', unit: 'm' },
                { label: 'Sample Metric B', value: 'N/A' }
              ]}
            />
          </section>
        </div>

        {children && <div className="domain-custom-content">{children}</div>}
      </div>
    </MainLayout>
  );
}
