import NotebookWikiPanel from '@/features/projects/components/portfolio/NotebookWikiPanel.jsx';
import '@/features/projects/components/portfolio/ProjectPortfolioIntegrated.css';

export default function NotebookWikiScreen({
  dbProjects,
  API_URL,
  hideHeader = false,
  defaultSubTab = 'notebook',
  projectCode = null,
  onNavigate,
  onSelectProject,
}) {
  return (
    <div className="notebook-wiki-screen">
      {!hideHeader && (
        <div className="page-header">
          <h1 className="page-title-gradient">Living Notebook & Wiki SOPs</h1>
          <p className="page-subtitle">
            Structured lab notebook entries per project, plus shared protocol wiki — integrated with each project workspace.
          </p>
        </div>
      )}
      <NotebookWikiPanel
        dbProjects={dbProjects}
        API_URL={API_URL}
        defaultSubTab={defaultSubTab}
        projectCode={projectCode || null}
        onNavigate={onNavigate}
        onSelectProject={onSelectProject}
      />
    </div>
  );
}
