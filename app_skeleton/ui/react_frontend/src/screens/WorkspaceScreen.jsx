
import React, { useState, useEffect, useMemo } from 'react';
import { useGuiT } from '../i18n/useGuiT.js';
import { 
  ArrowLeft, 
  BookOpen, 
  FileText, 
  Edit, 
  BookMarked,
  Calendar,
  LayoutDashboard,
  Database
} from 'lucide-react';

import ProjectIntroHeader from '../components/ProjectIntroHeader';
import ProjectTwinStats from '../components/ProjectTwinStats';
import ProjectWorkspaceTaskbar from '../components/ProjectWorkspaceTaskbar';
import ProjectDocumentsBrowser from '../components/ProjectDocumentsBrowser';
import ProjectLogPanel from '../components/ProjectLogPanel';
import WorkspaceSectionDataPad from '../components/WorkspaceSectionDataPad.jsx';
import { useDigitalTwin } from '../hooks/useDigitalTwin.js';
import { ProjectTaskpadScope, useTaskpad } from '../contexts/TaskpadContext.jsx';
import { resolveProject, fetchWithTimeout } from '../utils/projectUtils.js';

export default function WorkspaceScreen({ projectCode, onBack, API_URL, dbProjects = [] }) {
  const [projectData, setProjectData] = useState(() => resolveProject(projectCode, dbProjects));
  const [projectFolders, setProjectFolders] = useState([]);
  const [workspaceMenu, setWorkspaceMenu] = useState('overview');
  const [activeSub, setActiveSub] = useState({});
  const [loadError, setLoadError] = useState(null);
  const [sectionSelectedFile, setSectionSelectedFile] = useState(null);
  
  const {
    twin,
    loading: twinLoading,
    saving: twinSaving,
    error: twinError,
    refresh: refreshTwin,
    save: saveTwin,
  } = useDigitalTwin(projectCode, API_URL);
  const { setTargetSection } = useTaskpad();
  const { t } = useGuiT();
  const menuItems = useMemo(
    () => [
      { id: 'overview', label: t('workspace.overview'), icon: LayoutDashboard },
      { id: 'plan', label: t('workspace.plan'), icon: Calendar },
      { id: 'data', label: t('workspace.data'), icon: Database },
      { id: 'methods', label: t('workspace.methods'), icon: FileText },
      { id: 'writing', label: t('workspace.writing'), icon: Edit },
      { id: 'archive', label: t('workspace.archive'), icon: BookMarked },
      { id: 'log', label: t('workspace.log'), icon: BookOpen },
    ],
    [t]
  );

  useEffect(() => {
    setProjectData(resolveProject(projectCode, dbProjects));
    fetchProjectDetails();
    fetchProjectFolders();
  }, [projectCode, dbProjects]);

  useEffect(() => {
    setTargetSection(workspaceMenu);
  }, [workspaceMenu, setTargetSection]);

  useEffect(() => {
    setSectionSelectedFile(null);
  }, [workspaceMenu, projectCode]);

  const fetchProjectFolders = async () => {
    try {
      const res = await fetch(`${API_URL}/documents/${projectCode}`);
      if (res.ok) {
        const docs = await res.json();
        const folders = new Set();
        docs.forEach(d => {
          if (d.folder_path && d.folder_path !== '.') {
            folders.add(d.folder_path.split('/')[0]);
          }
        });
        setProjectFolders(Array.from(folders).sort());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchProjectDetails = async () => {
    setLoadError(null);
    const localProject = resolveProject(projectCode, dbProjects);
    if (localProject) setProjectData(localProject);

    try {
      const res = await fetchWithTimeout(`${API_URL}/projects`);
      if (res.ok) {
        const data = await res.json();
        const resolved = resolveProject(projectCode, data);
        if (resolved) {
          setProjectData(resolved);
          return;
        }
      }
    } catch (e) {
      console.error(e);
    }

    if (!localProject) {
      setLoadError(`Project "${projectCode}" was not found in the catalog or API.`);
    }
  };

  if (!projectData) {
    return (
      <div className="panel panel-danger">
        <h3 className="text-title-3" style={{ color: 'var(--color-danger)' }}>Project not found</h3>
        <p className="text-body-secondary" style={{ marginBottom: '1rem' }}>{loadError || 'Unable to load project details.'}</p>
        <button className="btn btn-secondary" onClick={onBack}>Back to Portfolio</button>
      </div>
    );
  }

  const currentMenu = menuItems.find(m => m.id === workspaceMenu) || menuItems[0];

  const renderSectionDataPad = (tabId, { lockFile = false } = {}) =>
    twin ? (
      <WorkspaceSectionDataPad
        twin={twin}
        projectCode={projectCode}
        API_URL={API_URL}
        workspaceTab={tabId}
        lockFile={lockFile}
        preferredPath={sectionSelectedFile}
      />
    ) : null;

  const renderDocBrowser = (tabId, extra = {}) =>
    twin ? (
      <ProjectDocumentsBrowser
        twin={twin}
        projectCode={projectCode}
        API_URL={API_URL}
        workspaceTab={tabId}
        taskpadMenuItems={menuItems}
        onSelectedPathChange={setSectionSelectedFile}
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
          {twin ? <ProjectTwinStats twin={twin} /> : null}
          {renderSectionDataPad('overview')}
        </div>
      );
    } 
    else if (workspaceMenu === 'plan') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('plan') || (
            <div className="panel text-empty"><p>Scan the project folder to load plan files.</p></div>
          )}
          {renderSectionDataPad('plan')}
        </div>
      );
    }
    else if (workspaceMenu === 'data') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('data') || (
            <div className="panel text-empty"><p>Scan the project folder to load data files.</p></div>
          )}
          {renderSectionDataPad('data')}
        </div>
      );
    }
    else if (workspaceMenu === 'methods') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('methods') || (
            <div className="panel text-empty"><p>Scan the project folder to load methods files.</p></div>
          )}
          {renderSectionDataPad('methods')}
        </div>
      );
    }
    else if (workspaceMenu === 'writing') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('writing') || (
            <div className="panel text-empty"><p>Scan the project folder to load writing files.</p></div>
          )}
          {renderSectionDataPad('writing')}
        </div>
      );
    }
    else if (workspaceMenu === 'archive') {
      return (
        <div className="stack-lg">
          {renderDocBrowser('archive') || (
            <div className="panel text-empty"><p>Scan the project folder to load archive files.</p></div>
          )}
          {renderSectionDataPad('archive')}
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
          {renderSectionDataPad('log', { lockFile: true })}
        </div>
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

