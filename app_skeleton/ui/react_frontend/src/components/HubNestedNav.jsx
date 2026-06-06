import React from 'react';

/**
 * Level-2 navigation: vertical section rail beside hub content.
 * Visually distinct from ModuleShell horizontal top tabs.
 */
export function HubSectionFrame({ sections, active, onChange, children, ariaLabel = 'Sections' }) {
  return (
    <div className="hub-section-frame">
      <nav className="hub-section-rail" aria-label={ariaLabel}>
        <ul className="hub-section-rail-list" role="tablist">
          {sections.map((item) => {
            const isActive = active === item.id;
            return (
              <li key={item.id} role="presentation">
                <button
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`hub-section-rail-item${isActive ? ' hub-section-rail-item--active' : ''}`}
                  onClick={() => onChange(item.id)}
                  title={item.description || item.label}
                >
                  {item.icon ? <span className="hub-rail-icon" aria-hidden>{item.icon}</span> : null}
                  <span className="hub-rail-label">{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="hub-section-body" role="tabpanel">
        {children}
      </div>
    </div>
  );
}

/**
 * Level-3 navigation: compact vertical detail rail inside a section.
 */
export function HubDetailFrame({ sections, active, onChange, children, ariaLabel = 'Views' }) {
  if (!sections?.length) return <div className="hub-detail-body">{children}</div>;

  return (
    <div className="hub-detail-frame">
      <nav className="hub-detail-rail" aria-label={ariaLabel}>
        <ul className="hub-detail-rail-list" role="tablist">
          {sections.map((item) => {
            const isActive = active === item.id;
            return (
              <li key={item.id} role="presentation">
                <button
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`hub-detail-rail-item${isActive ? ' hub-detail-rail-item--active' : ''}`}
                  onClick={() => onChange(item.id)}
                  title={item.description || item.label}
                >
                  <span className="hub-rail-label">{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="hub-detail-body" role="tabpanel">
        {children}
      </div>
    </div>
  );
}
