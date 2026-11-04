import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from '../pages/Home';
import Dashboard from '../pages/Dashboard';
import NotFound from '../pages/NotFound';
import Domain1Page from '../domains/domain1/Domain1Page';
import Domain2Page from '../domains/domain2/Domain2Page';
import Domain3Page from '../domains/domain3/Domain3Page';
import Domain4Page from '../domains/domain4/Domain4Page';
import Domain5Page from '../domains/domain5/Domain5Page';
import EarthEventExplorer from '../pages/EarthEventExplorer';

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/domain1" element={<Domain1Page />} />
      <Route path="/domain2" element={<Domain2Page />} />
      <Route path="/domain3" element={<Domain3Page />} />
      <Route path="/domain4" element={<Domain4Page />} />
      <Route path="/domain5" element={<Domain5Page />} />
      <Route path="/earth-event-explorer" element={<EarthEventExplorer />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
