import React from 'react';
import { NavLink } from 'react-router-dom';
import { DOMAINS, PLATFORM_FEATURES } from '../config/domains';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">Navigation</div>
      <ul className="sidebar-nav">
        <li>
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'active' : '')}>
            Overview Dashboard
          </NavLink>
        </li>
      </ul>

      <div className="sidebar-header">Platform Tools</div>
      <ul className="sidebar-nav">
        {PLATFORM_FEATURES.map((feature) => (
          <li key={feature.id}>
            <NavLink to={feature.route} className={({ isActive }) => (isActive ? 'active' : '')}>
              {feature.name}
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="sidebar-header">Scientific Domains</div>
      <ul className="sidebar-nav">
        {DOMAINS.map((domain) => (
          <li key={domain.id}>
            <NavLink to={domain.route} className={({ isActive }) => (isActive ? 'active' : '')}>
              {domain.name}
            </NavLink>
          </li>
        ))}
      </ul>
    </aside>
  );
}
