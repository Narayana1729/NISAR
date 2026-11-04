import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { DOMAINS } from '../config/domains';

/**
 * Navbar — High-tech dark aerospace navigation bar
 * Derived from NASA1 (#title-bar, #app-profile-switcher, .title-logo, .brand-logo)
 */
export default function Navbar() {
  const location = useLocation();

  return (
    <header className="gev-title-bar">
      {/* Brand & Logo */}
      <div className="gev-title-brand">
        <div className="gev-title-logo">
          <img src="/logo.svg" alt="NISAR Logo" className="w-5 h-5" />
        </div>
        <div className="gev-title-heading">
          <h1>
            <span>NISAR</span>
            <span className="title-accent">RADAR CONSOLE</span>
          </h1>
          <span className="gev-title-sub">DANCING WITH THE SARS · EARTH OBSERVATION</span>
        </div>
      </div>

      {/* Domain Profile Switcher (NASA1 .app-profile-switcher) */}
      <nav className="gev-profile-switcher" aria-label="Domain Profile Switcher">
        <Link
          to="/earth-event-explorer"
          className={`gev-profile-btn ${
            location.pathname === '/' || location.pathname === '/earth-event-explorer'
              ? 'active'
              : ''
          }`}
          title="Global Earth Event Explorer"
        >
          <span className="text-xs">🌐</span>
          <span>EXPLORER</span>
        </Link>

        {DOMAINS.map((d) => {
          const isActive = location.pathname.startsWith(d.route);
          return (
            <Link
              key={d.id}
              to={d.route}
              className={`gev-profile-btn ${isActive ? 'active' : ''}`}
              title={d.description}
            >
              <span>{d.id.toUpperCase()}</span>
            </Link>
          );
        })}
      </nav>

      {/* Right Telemetry Chips */}
      <div className="hidden lg:flex items-center gap-2 font-mono text-[10px]">
        <div className="flex items-center gap-1.5 bg-black/40 border border-white/10 px-2.5 py-1 rounded-full text-emerald-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>API ONLINE</span>
        </div>
        <div className="flex items-center gap-1 bg-black/40 border border-white/10 px-2.5 py-1 rounded-full text-cyan-400">
          <span>60 DATASETS</span>
        </div>
      </div>
    </header>
  );
}
