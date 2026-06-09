import { useCallback, useMemo, useState } from 'react';
import {
  Check,
  ChevronDown,
  ChevronRight,
  Filter,
  Search,
  Settings,
  X,
} from 'lucide-react';
import ProjectBrandMark from '@/features/projects/components/ProjectBrandMark.jsx';
import { groupProjectsForScope, statusTone } from '@/lib/projectScopeGroups.js';
import './ProjectScopeSelector.css';

const FILTER_TABS = [
  { id: 'all', label: 'All' },
  { id: 'active', label: 'Active only' },
  { id: 'selected', label: 'Selected' },
];

function ScopeProjectRow({ project, isChecked, onToggle }) {
  return (
    <label
      className={`pss-row${isChecked ? ' is-selected' : ''}`}
      title={project.name}
    >
      <input
        type="checkbox"
        className="pss-row-check"
        checked={isChecked}
        onChange={() => onToggle(project.code)}
        aria-label={`Include ${project.name} in Copilot scope`}
      />
      <span className={`pss-row-checkbox${isChecked ? ' is-checked' : ''}`} aria-hidden>
        {isChecked ? <Check size={12} strokeWidth={3} /> : null}
      </span>
      <div className="pss-row-main">
        <div className="pss-row-title-line">
          <span className="pss-row-index">#{project.index}</span>
          <span className="pss-row-name">{project.name}</span>
        </div>
        <div className="pss-row-meta">
          <ProjectBrandMark code={project.code} variant="compact" className="pss-row-code" />
          {project.diseaseFocus ? (
            <span className="pss-row-focus">{project.diseaseFocus}</span>
          ) : null}
          {project.lead ? <span className="pss-row-lead">{project.lead}</span> : null}
        </div>
      </div>
      {project.categoryLabel ? (
        <span className="pss-row-category">{project.categoryLabel}</span>
      ) : null}
    </label>
  );
}

export default function ProjectScopeSelector({
  projects,
  projectCodes,
  setProjectCodes,
}) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [collapsedStatus, setCollapsedStatus] = useState(() => new Set(['completed', 'discontinued', 'archived']));
  const [collapsedCategories, setCollapsedCategories] = useState(() => new Set());

  const selectedCodes = useMemo(
    () => new Set((Array.isArray(projectCodes) ? projectCodes : []).map(String)),
    [projectCodes],
  );

  const activeProjects = useMemo(
    () => projects.filter((project) => project.status === 'active'),
    [projects],
  );

  const selectedCount = projects.filter((project) => selectedCodes.has(project.code)).length;

  const grouped = useMemo(
    () => groupProjectsForScope(projects, { query, filter, selectedCodes }),
    [projects, query, filter, selectedCodes],
  );

  const visibleCount = useMemo(
    () => grouped.reduce((sum, group) => sum + group.projectCount, 0),
    [grouped],
  );

  const toggleProject = useCallback(
    (code) => {
      if (typeof setProjectCodes !== 'function') return;
      setProjectCodes((currentValue) => {
        const current = (Array.isArray(currentValue) ? currentValue : []).map(String);
        return current.includes(code)
          ? current.filter((item) => item !== code)
          : [...current, code];
      });
    },
    [setProjectCodes],
  );

  const toggleMany = useCallback(
    (codes, select) => {
      if (typeof setProjectCodes !== 'function') return;
      setProjectCodes((currentValue) => {
        const current = new Set((Array.isArray(currentValue) ? currentValue : []).map(String));
        codes.forEach((code) => {
          if (select) current.add(code);
          else current.delete(code);
        });
        return [...current];
      });
    },
    [setProjectCodes],
  );

  const selectActive = useCallback(() => {
    if (typeof setProjectCodes !== 'function') return;
    setProjectCodes(activeProjects.map((project) => project.code));
  }, [activeProjects, setProjectCodes]);

  const clearSelection = useCallback(() => {
    if (typeof setProjectCodes !== 'function') return;
    setProjectCodes([]);
  }, [setProjectCodes]);

  const toggleStatusCollapsed = useCallback((status) => {
    setCollapsedStatus((prev) => {
      const next = new Set(prev);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      return next;
    });
  }, []);

  const toggleCategoryCollapsed = useCallback((key) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  return (
    <section className="panel dashboard-scope-panel pss-root">
      <div className="dashboard-panel-heading pss-heading">
        <div>
          <p className="text-caption">Copilot context</p>
          <h3 className="panel-title">
            <Settings size={18} aria-hidden /> Project Scope Selector
          </h3>
        </div>
        <div className="pss-selection-badge" aria-live="polite">
          <span className="pss-selection-count">{selectedCount}</span>
          <span className="pss-selection-label">
            of {projects.length} in scope
          </span>
        </div>
      </div>

      <p className="panel-lead pss-lead">
        Choose which research projects ground Copilot queries, summaries, document
        retrieval, and dashboard metrics.
      </p>

      <div className="pss-toolbar">
        <label className="pss-search">
          <Search size={15} aria-hidden />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search name, code, disease, lead, category…"
            aria-label="Filter projects"
          />
        </label>

        <div className="pss-filter-tabs" role="tablist" aria-label="Project filters">
          {FILTER_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={filter === tab.id}
              className={`pss-filter-tab${filter === tab.id ? ' is-active' : ''}`}
              onClick={() => setFilter(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="pss-toolbar-actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={selectActive}>
            Select active
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={clearSelection}>
            <X size={14} aria-hidden /> Clear
          </button>
        </div>
      </div>

      {projects.length === 0 ? (
        <div className="obp-empty pss-empty">
          <p className="text-caption">No projects</p>
          <h4 className="text-title-3">No project catalog loaded</h4>
          <p className="text-body-secondary">
            Project rows will appear once the database returns the portfolio catalog.
          </p>
        </div>
      ) : visibleCount === 0 ? (
        <div className="obp-empty pss-empty">
          <Filter size={20} aria-hidden />
          <h4 className="text-title-3">No projects match this filter</h4>
          <p className="text-body-secondary">Try clearing search or switching to All.</p>
        </div>
      ) : (
        <div className="pss-groups feed-scroll">
          {grouped.map((statusGroup) => {
            const statusCollapsed = collapsedStatus.has(statusGroup.status);
            const statusKey = statusGroup.status;
            const allCodesInStatus = statusGroup.categories.flatMap((cat) =>
              cat.projects.map((p) => p.code),
            );
            const allSelected = allCodesInStatus.every((code) => selectedCodes.has(code));

            return (
              <section
                key={statusKey}
                className={`pss-status-group pss-status-group--${statusTone(statusGroup.status)}`}
              >
                <header className="pss-status-header">
                  <button
                    type="button"
                    className="pss-status-toggle"
                    onClick={() => toggleStatusCollapsed(statusKey)}
                    aria-expanded={!statusCollapsed}
                  >
                    {statusCollapsed ? (
                      <ChevronRight size={16} aria-hidden />
                    ) : (
                      <ChevronDown size={16} aria-hidden />
                    )}
                    <span className="pss-status-title">{statusGroup.label}</span>
                    <span className="pss-status-count">
                      {statusGroup.selectedCount}/{statusGroup.projectCount}
                    </span>
                  </button>
                  <button
                    type="button"
                    className="pss-group-select"
                    onClick={() => toggleMany(allCodesInStatus, !allSelected)}
                  >
                    {allSelected ? 'Deselect all' : 'Select all'}
                  </button>
                </header>

                {!statusCollapsed ? (
                  <div className="pss-status-body">
                    {statusGroup.categories.map((category) => {
                      const categoryKey = `${statusKey}::${category.label}`;
                      const categoryCollapsed = collapsedCategories.has(categoryKey);
                      const categoryCodes = category.projects.map((p) => p.code);
                      const categoryAllSelected = categoryCodes.every((code) =>
                        selectedCodes.has(code),
                      );

                      return (
                        <div key={categoryKey} className="pss-category-group">
                          <header className="pss-category-header">
                            <button
                              type="button"
                              className="pss-category-toggle"
                              onClick={() => toggleCategoryCollapsed(categoryKey)}
                              aria-expanded={!categoryCollapsed}
                            >
                              {categoryCollapsed ? (
                                <ChevronRight size={14} aria-hidden />
                              ) : (
                                <ChevronDown size={14} aria-hidden />
                              )}
                              <span className="pss-category-title">{category.label}</span>
                              <span className="pss-category-count">
                                {category.selectedCount}/{category.projects.length}
                              </span>
                            </button>
                            <button
                              type="button"
                              className="pss-group-select pss-group-select--sub"
                              onClick={() => toggleMany(categoryCodes, !categoryAllSelected)}
                            >
                              {categoryAllSelected ? 'Clear' : 'All'}
                            </button>
                          </header>

                          {!categoryCollapsed ? (
                            <div className="pss-project-list">
                              {category.projects.map((project) => (
                                <ScopeProjectRow
                                  key={project.code}
                                  project={project}
                                  isChecked={selectedCodes.has(project.code)}
                                  onToggle={toggleProject}
                                />
                              ))}
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </section>
            );
          })}
        </div>
      )}
    </section>
  );
}
