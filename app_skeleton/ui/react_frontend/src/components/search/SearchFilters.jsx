import React from 'react';

const MODES = [
  { id: 'hybrid', label: 'Hybrid' },
  { id: 'semantic', label: 'Semantic' },
  { id: 'keyword', label: 'Keyword' },
];

const SCOPE_OPTIONS = [
  { id: 'lab', label: 'Lab' },
  { id: 'file', label: 'Files' },
  { id: 'vault', label: 'Vault' },
  { id: 'notebook', label: 'Notebook' },
  { id: 'wiki', label: 'Wiki' },
  { id: 'decision', label: 'Decisions' },
  { id: 'task', label: 'Tasks' },
  { id: 'project', label: 'Projects' },
  { id: 'research', label: 'Research KB' },
];

export default function SearchFilters({
  mode,
  onModeChange,
  scopes,
  onScopesChange,
  compact = false,
  showModes = true,
  showScopes = true,
}) {
  const activeScopes = scopes?.length ? new Set(scopes) : null;

  const toggleScope = (scopeId) => {
    if (!onScopesChange) return;
    const base = activeScopes ? [...activeScopes] : SCOPE_OPTIONS.map((s) => s.id);
    const next = base.includes(scopeId) ? base.filter((s) => s !== scopeId) : [...base, scopeId];
    onScopesChange(next.length ? next : SCOPE_OPTIONS.map((s) => s.id));
  };

  return (
    <div className={`search-filters${compact ? ' search-filters--compact' : ''}`}>
      {showModes ? (
        <div className="search-mode-tabs" role="tablist" aria-label="Search mode">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              role="tab"
              aria-selected={mode === m.id}
              className={`search-mode-tab${mode === m.id ? ' is-active' : ''}`}
              onClick={() => onModeChange?.(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>
      ) : null}
      {showScopes && onScopesChange ? (
        <div className="search-scope-chips" role="group" aria-label="Search scopes">
          {SCOPE_OPTIONS.map((scope) => {
            const on = !activeScopes || activeScopes.has(scope.id);
            return (
              <button
                key={scope.id}
                type="button"
                className={`search-scope-chip${on ? ' is-on' : ''}`}
                aria-pressed={on}
                onClick={() => toggleScope(scope.id)}
              >
                {scope.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export { MODES, SCOPE_OPTIONS };
