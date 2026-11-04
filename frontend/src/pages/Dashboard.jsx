import React from 'react';
import MainLayout from '../layouts/MainLayout';
import DomainCard from '../components/DomainCard';
import { DOMAINS } from '../config/domains';

export default function Dashboard() {
  return (
    <MainLayout>
      <div className="dashboard-container">
        <header className="dashboard-header">
          <h2>Domain Modules Overview</h2>
          <p>Select a specialized domain module to view processing pipelines, analytics, and visual products.</p>
        </header>

        <div className="domain-grid">
          {DOMAINS.map((domain) => (
            <DomainCard key={domain.id} domain={domain} />
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
