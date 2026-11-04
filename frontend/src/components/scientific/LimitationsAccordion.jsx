import React, { useState } from 'react';

/**
 * LimitationsAccordion — Progressive disclosure of scientific limitations,
 * methodology details, and dataset citations.
 * Derived from NASA1 (#earthtrend-accordion)
 */
export default function LimitationsAccordion({
  limitations = [],
  citation = null,
  methodologyText = null,
  title = 'METHODOLOGY, DATA QUALITY FILTERING & SCIENTIFIC LIMITATIONS',
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="gev-accordion">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="gev-accordion-header"
        aria-expanded={expanded}
      >
        <span className="flex items-center gap-2 font-mono text-[10.5px]">
          <span className="text-cyan-400">⚡</span>
          <span>{title}</span>
        </span>
        <span className="text-cyan-400 font-mono text-xs">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="gev-accordion-content space-y-3">
          {methodologyText && (
            <div className="text-gray-300">
              <strong className="text-white block font-mono text-[10px] uppercase mb-1">
                Processing Logic:
              </strong>
              <p className="text-xs text-gray-300 leading-relaxed font-sans">{methodologyText}</p>
            </div>
          )}

          {limitations.length > 0 && (
            <div>
              <strong className="text-white block font-mono text-[10px] uppercase mb-1.5">
                Physical Limitations & Assumptions:
              </strong>
              <ul className="list-disc list-inside space-y-1 text-xs text-gray-300 font-sans">
                {limitations.map((item, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {citation && (
            <div className="bg-black/40 border border-white/5 rounded p-2 text-[10.5px] font-mono text-gray-400">
              <span className="text-cyan-400 font-semibold block uppercase text-[9px] mb-0.5">
                Authoritative Dataset Citation:
              </span>
              <span>{citation}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
