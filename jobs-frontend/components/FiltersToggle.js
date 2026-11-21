'use client';

import { useState } from 'react';

export default function FiltersToggle({ activeCount = 0, children }) {
  const [open, setOpen] = useState(false);

  return (
    <aside className="filters-wrap" aria-label="Filters">
      <button
        type="button"
        className="filters-btn"
        aria-expanded={open}
        aria-controls="filters-panel"
        onClick={() => setOpen(!open)}
      >
        Filters
        {activeCount > 0 && <span className="badge-count">{activeCount}</span>}
      </button>
      <div id="filters-panel" className={open ? 'filters-panel open' : 'filters-panel'}>
        {children}
      </div>
    </aside>
  );
}
