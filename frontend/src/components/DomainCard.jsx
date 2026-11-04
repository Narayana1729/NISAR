import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function DomainCard({ domain }) {
  const navigate = useNavigate();

  return (
    <div className="domain-card" style={{ borderTop: `4px solid ${domain.color || '#3b82f6'}` }}>
      <h3 className="domain-card-title">{domain.name}</h3>
      <p className="domain-card-desc">{domain.description}</p>
      <button
        type="button"
        className="btn btn-primary"
        onClick={() => navigate(domain.route)}
      >
        Open {domain.name} &rarr;
      </button>
    </div>
  );
}
