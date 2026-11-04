import React from 'react';
import { Link } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';

export default function NotFound() {
  return (
    <MainLayout>
      <div className="not-found-container">
        <h2>404 - Page Not Found</h2>
        <p>The requested route or domain does not exist.</p>
        <Link to="/dashboard" className="btn btn-primary">Return to Dashboard</Link>
      </div>
    </MainLayout>
  );
}
