
import { useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';

import ProjectIntroHeader from '@/features/projects/components/ProjectIntroHeader';
import ProjectWorkspaceTaskbar from '@/features/projects/components/ProjectWorkspaceTaskbar';
import ProjectDocumentsBrowser from '@/features/projects/components/ProjectDocumentsBrowser';
import ProjectLogPanel from '@/features/projects/components/ProjectLogPanel';
import { useDigitalTwin } from '@/shared/hooks/useDigitalTwin.js';
import { ProjectTaskpadScope } from '@/contexts/TaskpadContext.jsx';
import { fetchWithTimeout } from '@/lib/projectUtils.js';
import { useEnsureProjectReadme } from '@/shared/hooks/useEnsureProjectReadme.js';
import NotebookWikiPanel from '@/features/projects/components/portfolio/NotebookWikiPanel.jsx';
import DecisionsPanel from '@/features/projects/components/portfolio/DecisionsPanel.jsx';
import useWorkspaceTabs from '@/features/projects/hooks/useWorkspaceTabs.js';
import useProjectWorkspaceData from '@/features/projects/hooks/useProjectWorkspaceData.js';
import '@/features/projects/components/portfolio/ProjectPortfolioIntegrated.css';

export default function WorkspaceScreen({
  projectCode,
  onBack,
  API_URL,
  dbProjects = [],
  initialTab = 'overview',
  onNavigate,
  onSelectProject,
}) {
  const {
    projectData,
    loadError,
    fetchProjectDetails,
  } = useProjectWorkspaceData(projectCode, dbProjects, API_URL);

  const {
    workspaceMenu,
    setWorkspaceMenu,
    menuItems,
    currentMenu,
  } = useWorkspaceTabs(projectCode, initialTab);

  const {
    twin,
    loading: twinLoading,
    saving: twinSaving,
    error: twinError,
    refresh: refreshTwin,
    save: saveTwin,
    setTwin,
  } = useDigitalTwin(projectCode, API_URL);
  const { ensuring: readmeEnsuring, error: readmeEnsureError, ensureReadme } = useEnsureProjectReadme(
    projectCode,
    { twin, setTwin, refreshTwin },
  );

  useEffect(() => {
    const onReadmeUpdated = async (event) => {
      if (event.detail?.projectCode !== projectCode) return;
      try {
        const res = await fetchWithTimeout(
          `${API_URL}/api/projects/${encodeURIComponent(projectCode)}/digital-twin`
        );
        if (res.ok) {
          const data = await res.json();
          setTwin(data);
        } else {
          refreshTwin();
        }
      } catch {
        refreshTwin();
      }
    };
    window.addEventListener('project-readme-updated', onReadmeUpdated);
    return () => window.removeEventListener('project-readme-updated', onReadmeUpdated);
  }, [projectCode, API_URL, setTwin, refreshTwin]);

  if (!projectData) {
    return (
      <div className="panel panel-danger">
        <h3 className="text-title-3" style={{ color: 'var(--color-danger)' }}>Project not found</h3>
        <p className="text-body-secondary" style={{ marginBottom: '1rem' }}>{loadError || 'Unable to load project details.'}</p>
        <button className="btn btn-secondary" onClick={onBack}>Back to Portfolio</button>
      </div>
    );
  }

  const handleReadmeSaved = () => {
    refreshTwin();
  };

  const renderDocBrowser = (tabId, extra = {}) =>
    twin ? (
      <ProjectDocumentsBrowser
        twin={twin}
        projectCode={projectCode}
        API_URL={API_URL}
        workspaceTab={tabId}
        onReadmeSaved={handleReadmeSaved}
        readmeEnsuring={readmeEnsuring}
        readmeEnsureError={readmeEnsureError}
        onCreateReadme={ensureReadme}
        {...extra}
      />
    ) : null;

  const renderSubcategory = () => {
    if (workspaceMenu === 'overview') {
      return (
        <div className="stack-lg">
          {twinLoading && !twin && <div className="panel"><p className="text-loading">Loading scanned project record…</p></div>}
          {renderDocBrowser('overview') || (
            <div className="panel text-empty"><p>Scan the project folder to load overview files.</p></div>
          )}
        </div>
      );
    }
    else if (workspaceMenu === 'plan') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('plan') || (
            <div className="panel text-empty"><p>Scan the project folder to load plan files.</p></div>
          )}
        </div>
      );
    }
    else if (workspaceMenu === 'data') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('data') || (
            <div className="panel text-empty"><p>Scan the project folder to load data files.</p></div>
          )}
        </div>
      );
    }
    else if (workspaceMenu === 'methods') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('methods') || (
            <div className="panel text-empty"><p>Scan the project folder to load methods files.</p></div>
          )}
        </div>
      );
    }
    else if (workspaceMenu === 'writing') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('writing') || (
            <div className="panel text-empty"><p>Scan the project folder to load writing files.</p></div>
          )}
        </div>
      );
    }
    else if (workspaceMenu === 'archive') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('archive') || (
            <div className="panel text-empty"><p>Scan the project folder to load archive files.</p></div>
          )}
        </div>
      );
    }
    else if (workspaceMenu === 'log') {
      return (
        <div className="stack-lg workspace-log-tab">
          {twin ? (
            <ProjectLogPanel twin={twin} projectCode={projectCode} API_URL={API_URL} />
          ) : (
            <div className="panel text-empty">
              <p>Scan the project folder to load the project log.</p>
            </div>
          )}
        </div>
      );
    }
    else if (workspaceMenu === 'notebook') {
      return (
        <NotebookWikiPanel
          dbProjects={dbProjects}
          API_URL={API_URL}
          projectCode={projectCode}
          embedded
          onOpenLogTab={() => setWorkspaceMenu('log')}
          onNavigate={onNavigate}
          onSelectProject={onSelectProject}
        />
      );
    }
    else if (workspaceMenu === 'decisions') {
      return (
        <DecisionsPanel
          dbProjects={dbProjects}
          API_URL={API_URL}
          projectCode={projectCode}
          lockProject
          embedded
          onNavigate={onNavigate}
          onSelectProject={onSelectProject}
        />
      );
    }

    return (
      <div className="panel text-empty" style={{ padding: '2rem' }}>
        <p>No backend integration yet for: {currentMenu.label}</p>
      </div>
    );
  };

  return (
    <ProjectTaskpadScope
      projectCode={projectCode}
      projectName={twin?.identity?.project_name || projectData?.project_name}
      menuItems={menuItems}
    >
    <div className="workspace-layout workspace-layout--compact">
      <div className="workspace-main" style={{ position: 'relative' }}>
        <header className="workspace-chrome-minimal">
          <button
            type="button"
            className="btn btn-secondary btn-sm workspace-tab-back"
            onClick={onBack}
            title="Back to Portfolio"
          >
            <ArrowLeft size={14} />
          </button>
          <span
            className="workspace-context-badge"
            title={twin?.identity?.project_lead ? `Lead: ${twin.identity.project_lead}` : projectCode}
          >
            {projectCode}
          </span>
        </header>

        {twin ? (
          <ProjectIntroHeader twin={twin} className="workspace-intro-card" />
        ) : null}

        <nav className="workspace-tabs workspace-tabs--below-intro" aria-label="Workspace modules">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                className={`workspace-tab${workspaceMenu === item.id ? ' active' : ''}`}
                onClick={() => setWorkspaceMenu(item.id)}
                aria-current={workspaceMenu === item.id ? 'page' : undefined}
              >
                <Icon size={14} aria-hidden />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <ProjectWorkspaceTaskbar
          workspaceMenu={workspaceMenu}
          menuItems={menuItems}
          projectCode={projectCode}
          projectData={projectData}
          onRegistrySaved={fetchProjectDetails}
          onWorkspaceMenuChange={setWorkspaceMenu}
          twin={twin}
          twinLoading={twinLoading}
          twinSaving={twinSaving}
          twinError={twinError}
          onSave={saveTwin}
          refreshTwin={refreshTwin}
          API_URL={API_URL}
        />

        {renderSubcategory()}
      </div>

    </div>
    </ProjectTaskpadScope>
  );
}
