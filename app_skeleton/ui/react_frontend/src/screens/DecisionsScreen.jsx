import DecisionsPanel from '../components/projectPortfolio/DecisionsPanel.jsx';
import '../components/projectPortfolio/ProjectPortfolioIntegrated.css';

export default function DecisionsScreen({
  dbProjects,
  API_URL,
  hideHeader = false,
  projectCode = null,
  onOpenProject,
  onNavigate,
  onSelectProject,
}) {
  return (
    <div>
      {!hideHeader && (
        <div className="page-header">
          <h1 className="page-title-gradient">Research Decisions Ledger</h1>
          <p className="page-subtitle">
            Registry of project scope definitions, antibody panels, and sample exclusions — scoped per project in the workspace.
          </p>
        </div>
      )}
      <DecisionsPanel
        dbProjects={dbProjects}
        API_URL={API_URL}
        projectCode={projectCode || null}
        onOpenProject={onOpenProject}
        onNavigate={onNavigate}
        onSelectProject={onSelectProject}
      />
    </div>
  );
}
