import React, { useState } from 'react';

/**
 * CollapsiblePanel — Reusable glassmorphic accordion panel container
 * Derived from NASA1 (.panel-collapsible, .panel-glow, .panel-inner, .panel-header)
 */
export default function CollapsiblePanel({
  title,
  badge = null,
  badgeVariant = 'verified', // 'verified' | 'partial' | 'demo'
  children,
  defaultCollapsed = false,
  className = '',
}) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  const getBadgeClass = () => {
    if (badgeVariant === 'verified') return 'badge-verified';
    if (badgeVariant === 'partial') return 'badge-partial';
    return 'badge-demo';
  };

  return (
    <div className={`panel-collapsible ${collapsed ? 'collapsed' : ''} ${className}`}>
      <div className="panel-glow" />
      <div className="relative z-10 flex flex-col">
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <span className="panel-title">{title}</span>
            {badge && (
              <span className={`gev-badge-pill ${getBadgeClass()}`}>
                {badge}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            className="panel-collapse-btn"
            title={collapsed ? 'Expand panel' : 'Collapse panel'}
          >
            {collapsed ? '+' : '−'}
          </button>
        </div>

        {!collapsed && <div className="p-3.5 flex flex-col gap-2.5">{children}</div>}
      </div>
    </div>
  );
}
