import React from 'react';
import { Dna, Sun, Moon, Search } from 'lucide-react';
import { MAIN_NAV } from '../config/navigation';

const THEME_CYCLE = ['dark', 'light'];

export default function Sidebar({
  navMain,
  navSub,
  onNavChange,
  onResetProject,
  theme,
  setTheme,
  apiHealth,
  apiUrl,
  onOpenSearch,
}) {
  const activeMain = navMain;

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <Dna size={32} color="var(--color-primary)" />
        <span className="sidebar-title">Farkki Digital Research NotePad</span>
      </div>

      <div style={{ padding: '0 1rem', marginBottom: '1rem' }}>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onOpenSearch}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            justifyContent: 'center',
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-secondary)',
          }}
        >
          <Search size={16} />
          <span>Search Registry...</span>
        </button>
      </div>

      <nav className="sidebar-menu" aria-label="Main lab sections">
        {MAIN_NAV.map((item) => {
          const Icon = item.icon;
          const isActive = activeMain === item.id;
          return (
            <div
              key={item.id}
              className={`sidebar-item sidebar-item-main ${isActive ? 'active' : ''}`}
              role="button"
              tabIndex={0}
              onClick={() => onNavChange(item.id, item.defaultSub)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onNavChange(item.id, item.defaultSub);
                }
              }}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer stack-md">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            User: <strong>debdeba</strong>
          </div>
          <button
            type="button"
            onClick={() => {
              const idx = THEME_CYCLE.indexOf(theme);
              const next = THEME_CYCLE[(idx + 1) % THEME_CYCLE.length];
              setTheme(next);
            }}
            className="theme-toggle-btn"
            title={`Theme: ${theme}. Click to cycle.`}
          >
            {theme === 'dark' ? <Moon size={16} /> : <Sun size={16} />}
          </button>
        </div>
        <div className="text-footnote">
          API:{' '}
          <span
            style={{
              color: apiHealth?.status === 'ok' ? 'var(--color-success)' : 'var(--color-warning)',
            }}
          >
            {apiHealth?.status === 'ok'
              ? 'Connected'
              : apiHealth?.status === 'unreachable'
                ? 'Unreachable'
                : apiHealth?.status || 'Checking…'}
          </span>
          {apiHealth?.status === 'ok' && apiHealth?.database_connected === false && (
            <span className="muted"> · DB offline</span>
          )}
        </div>
      </div>
    </div>
  );
}
