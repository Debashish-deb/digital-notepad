import { FolderOpen, Library } from 'lucide-react';

export default function AssistantScopeBar({
  projectCodes = [],
  selectedProjects = [],
  onToggleProject,
  libraryScopeLabel = null,
  statusLabel = null,
  statusTone = 'neutral',
}) {
  const toggleProject = (code) => {
    if (!onToggleProject) return;
    const set = new Set(selectedProjects);
    if (set.has(code)) {
      if (set.size > 1) set.delete(code);
    } else {
      set.add(code);
    }
    onToggleProject([...set]);
  };

  return (
    <div className="assistant-scope-bar" role="region" aria-label="Copilot scope">
      <div className="assistant-scope-bar__group">
        <span className="assistant-scope-bar__label">
          <FolderOpen size={13} aria-hidden />
          Projects
        </span>
        <div className="assistant-scope-bar__chips" role="list">
          {projectCodes.slice(0, 12).map((code) => {
            const active = selectedProjects.includes(code);
            return (
              <button
                key={code}
                type="button"
                role="listitem"
                className={`assistant-scope-bar__chip${active ? ' is-active' : ''}`}
                aria-pressed={active}
                onClick={() => toggleProject(code)}
              >
                {code}
              </button>
            );
          })}
        </div>
      </div>
      {libraryScopeLabel ? (
        <div className="assistant-scope-bar__group assistant-scope-bar__group--library">
          <span className="assistant-scope-bar__label">
            <Library size={13} aria-hidden />
            Library
          </span>
          <span className="assistant-scope-bar__library-pill" title={libraryScopeLabel}>
            {libraryScopeLabel}
          </span>
        </div>
      ) : null}
      {statusLabel ? (
        <span className={`assistant-scope-bar__status is-${statusTone}`}>{statusLabel}</span>
      ) : null}
    </div>
  );
}
