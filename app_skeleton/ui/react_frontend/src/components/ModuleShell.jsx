import React from 'react';
import { findMainNav, findSubNav } from '../config/navigation';

/**
 * Section layout: category header + horizontal sub-nav + page body.
 */
export default function ModuleShell({ mainId, subId, onSubChange, children }) {
  const main = findMainNav(mainId);
  const sub = findSubNav(mainId, subId);

  return (
    <div className="module-shell">
      <header className="module-shell-header">
        <div className="module-shell-heading">
          <h1 className="module-shell-title">{main.label}</h1>
          <p className="module-shell-lead">{sub.description || ''}</p>
        </div>
      </header>

      <nav className="module-subnav" aria-label={`${main.label} sections`}>
        {main.children.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`module-subnav-item ${subId === item.id ? 'active' : ''}`}
            onClick={() => onSubChange(item.id)}
            aria-current={subId === item.id ? 'page' : undefined}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="module-shell-body">{children}</div>
    </div>
  );
}
