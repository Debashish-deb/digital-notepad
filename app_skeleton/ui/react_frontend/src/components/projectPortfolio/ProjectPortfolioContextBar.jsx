import { ArrowRight, FolderOpen } from 'lucide-react';

export default function ProjectPortfolioContextBar({
  dbProjects = [],
  focusProject = '',
  onFocusProjectChange,
  onOpenWorkspace,
  onBrowsePortfolio,
  viewLabel = 'Research records',
}) {
  return (
    <div className="portfolio-context-bar panel">
      <div className="portfolio-context-bar__copy">
        <h4 className="portfolio-context-bar__title">{viewLabel}</h4>
        <p className="text-footnote muted">
          Scoped to a project inside the workspace, or browse all projects here. Open a project from the portfolio for documents, log file, notebook, and decisions together.
        </p>
      </div>
      <div className="portfolio-context-bar__actions">
        <label className="portfolio-context-bar__field">
          <span className="form-label">Focus project</span>
          <select
            className="form-select"
            value={focusProject}
            onChange={(e) => onFocusProjectChange?.(e.target.value)}
          >
            <option value="">All projects</option>
            {dbProjects.map((p) => (
              <option key={p.project_code} value={p.project_code}>
                {p.project_code} — {p.project_name || p.title || 'Project'}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={!focusProject}
          onClick={() => focusProject && onOpenWorkspace?.(focusProject)}
        >
          Open workspace <ArrowRight size={14} />
        </button>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onBrowsePortfolio}>
          <FolderOpen size={14} /> Portfolio
        </button>
      </div>
    </div>
  );
}
