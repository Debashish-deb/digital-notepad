import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Sidebar from './components/Sidebar';
import ModuleShell from './components/ModuleShell';
import ErrorBoundary from './components/ErrorBoundary';
import DashboardScreen from './screens/DashboardScreen';
import GlobalSearchOverlay from './components/GlobalSearchOverlay';
import ProjectsScreen from './screens/ProjectsScreen';
import NotebookWikiScreen from './screens/NotebookWikiScreen';
import DecisionsScreen from './screens/DecisionsScreen';
import TasksScreen from './screens/TasksScreen';
import BioinformaticsHubScreen from './screens/BioinformaticsHubScreen';
import AiLabAssistantScreen from './screens/AiLabAssistantScreen';
import FeatureClinicalScreen from './screens/FeatureClinicalScreen';
import LabKnowledgeScreen from './screens/LabKnowledgeScreen';
import DataStorageScreen from './screens/DataStorageScreen';
import AdministrationScreen from './screens/AdministrationScreen';
import IngestionDashboard from './screens/IngestionDashboard';
import DigitalizationDashboard from './screens/DigitalizationDashboard';
import KnowledgeSearchScreen from './screens/KnowledgeSearchScreen';
import LabCorpusBrowser from './components/LabCorpusBrowser.jsx';
import { getApiUrl, apiFetch } from './api/client.js';
import { useApiContext } from './api/ApiContext.jsx';
import ComputationalToolsScreen from './screens/ComputationalToolsScreen';
import CycifScreen from './screens/CycifScreen';
import { TaskpadProvider } from './contexts/TaskpadContext.jsx';

import {
  OrdersTasksPanel,
  OrdersRegisterPanel,
  OrdersRelatedPanel,
  OrdersBillingPanel,
} from './screens/OrdersHubScreen';
import {
  WetLabProtocolsPanel,
  WetLabTasksPanel,
  WetLabInventoryPanel,
} from './screens/WetLabScreen';
import { projectsCatalog } from './data/projectsCatalog.js';
import { teamDirectory } from './data/teamDirectory.js';
import { activityLogs } from './data/activityLogs.js';
import { platformStats } from './data/platformStats.js';
import { mergeProjectRecord } from './utils/projectUtils.js';
import {
  MAIN_NAV,
  findMainNav,
  findSubNav,
  sectionTitle,
  parseNavFromStorage,
} from './config/navigation';
import { initFirebaseAnalytics } from './config/firebase.js';
import './App.css';

const DEFAULT_PROJECT_CODES = Object.freeze(['SPACE', 'EyeMT', 'KRAS']);
const DEFAULT_STATS = Object.freeze({
  patient_count: 0,
  sample_count: 0,
  project_samples: {},
});

const NAV_STORAGE_KEY = 'farkki_nav_v2';

const API_URL = getApiUrl();

function safeStorageGet(key, fallback) {
  try {
    return window.localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function safeStorageSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

function migrateLegacyNav(stored) {
  const legacy = parseNavFromStorage(stored);
  if (legacy) return legacy;
  const map = {
    dashboard: { main: 'overview', sub: 'get_started' },
    projects: { main: 'projects_data', sub: 'portfolio' },
    notebook: { main: 'projects_data', sub: 'notebook' },
    chat: { main: 'ai_assistant', sub: 'copilot' },
    decisions: { main: 'projects_data', sub: 'decisions' },
    tasks: { main: 'projects_data', sub: 'portfolio' },
    bioinformatics: { main: 'computational', sub: 'onboarding' },
    features: { main: 'projects_data', sub: 'features' },
    ai_assistant: { main: 'ai_assistant', sub: 'prompts' },
  };
  return map[stored] || { main: 'overview', sub: 'dashboard' };
}

function normalizeProjectCodes(value) {
  const list = Array.isArray(value) ? value : DEFAULT_PROJECT_CODES;
  const seen = new Set();
  return list
    .map((code) => String(code || '').trim())
    .filter(Boolean)
    .filter((code) => {
      const key = code.toUpperCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

async function fetchJson(path, { signal, timeoutMs = 12_000, params } = {}) {
  return apiFetch(path, { signal, timeoutMs, params });
}

function mergeProjectsWithCatalog(remoteProjects = []) {
  const remote = Array.isArray(remoteProjects) ? remoteProjects : [];
  const merged = remote.map((project) => mergeProjectRecord(project));
  const seen = new Set(merged.map((project) => project.project_code));
  for (const catalogProject of projectsCatalog) {
    if (!seen.has(catalogProject.project_code)) {
      merged.push(mergeProjectRecord(catalogProject));
    }
  }
  return merged.sort((a, b) => (a.project_index || 999) - (b.project_index || 999));
}

function App() {
  const { API_URL: contextApiUrl } = useApiContext();
  const resolvedApiUrl = contextApiUrl || API_URL;
  const initialNav = migrateLegacyNav(safeStorageGet(NAV_STORAGE_KEY, ''));
  const [navMain, setNavMain] = useState(initialNav.main);
  const [navSub, setNavSub] = useState(initialNav.sub);
  const [selectedProject, setSelectedProject] = useState(null);
  const [dbProjects, setDbProjects] = useState(() => mergeProjectsWithCatalog(projectsCatalog));
  const [projectCodes, setProjectCodesState] = useState(DEFAULT_PROJECT_CODES);
  const [stats, setStats] = useState(platformStats || DEFAULT_STATS);
  const [team, setTeam] = useState(teamDirectory || []);
  const [auditLogs, setAuditLogs] = useState(activityLogs || []);
  const [loadState, setLoadState] = useState({ phase: 'idle', message: 'Ready' });
  const [theme, setTheme] = useState(() => safeStorageGet('theme', 'dark'));
  const [apiHealth, setApiHealth] = useState(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const activeTitle = sectionTitle(navMain, navSub);
  const isLoading = loadState.phase === 'loading' || loadState.phase === 'refreshing';
  const subNav = findSubNav(navMain, navSub);

  const setProjectCodes = useCallback((nextValue) => {
    setProjectCodesState((previous) => {
      const resolved = typeof nextValue === 'function' ? nextValue(previous) : nextValue;
      const normalized = normalizeProjectCodes(resolved);
      return normalized.length ? normalized : [...DEFAULT_PROJECT_CODES];
    });
  }, []);

  const resetProject = useCallback(() => setSelectedProject(null), []);

  const handleNavChange = useCallback((main, sub) => {
    const mainItem = findMainNav(main);
    const subId = sub || mainItem.defaultSub;
    setNavMain(mainItem.id);
    setNavSub(subId);
    if (!mainItem.keepsProject) setSelectedProject(null);
  }, []);

  const commonProps = useMemo(() => ({ dbProjects, API_URL: resolvedApiUrl }), [dbProjects, resolvedApiUrl]);

  const fetchProjects = useCallback(async (signal) => {
    const data = await fetchJson('/projects', { signal, timeoutMs: 14_000 });
    if (Array.isArray(data) && data.length > 0) {
      setDbProjects(mergeProjectsWithCatalog(data));
    } else {
      setDbProjects(mergeProjectsWithCatalog(projectsCatalog));
    }
  }, []);

  const refreshReferenceData = useCallback(async (signal, phase = 'refreshing') => {
    setLoadState({ phase, message: 'Syncing project list…' });
    try {
      await fetchProjects(signal);
      setLoadState({ phase: 'ready', message: 'Projects synced' });
    } catch (err) {
      setLoadState({
        phase: 'warning',
        message: 'Using cached project list where the API was unavailable.',
      });
    }
  }, [fetchProjects]);

  const renderScreenBody = () => {
    const screen = subNav.screen;

    switch (screen) {
      case 'dashboard':
        return (
          <DashboardScreen
            stats={stats}
            team={team}
            auditLogs={auditLogs}
            projectCodes={projectCodes}
            setProjectCodes={setProjectCodes}
            dbProjects={dbProjects}
            API_URL={resolvedApiUrl}
            hideHeader
            onNavigate={handleNavChange}
          />
        );
      case 'lab_knowledge':
        return (
          <LabKnowledgeScreen
            subId={navSub}
            navSub={subNav}
            API_URL={resolvedApiUrl}
            title={subNav.label}
            description={subNav.description}
          />
        );
      case 'data_storage':
        return (
          <DataStorageScreen
            title={subNav.label}
            description={subNav.description}
            section={subNav.dataSection || 'all'}
          />
        );
      case 'digitalization':
        return (
          <DigitalizationDashboard title={subNav.label} description={subNav.description} />
        );
      case 'ingestion_dashboard':
        return (
          <IngestionDashboard title={subNav.label} description={subNav.description} />
        );
      case 'knowledge_search':
        return (
          <KnowledgeSearchScreen title={subNav.label} description={subNav.description} />
        );
      case 'lab_corpus':
        return (
          <LabCorpusBrowser title={subNav.label} description={subNav.description} />
        );
      case 'administration':
        return (
          <AdministrationScreen
            title={subNav.label}
            description={subNav.description}
            onNavigate={handleNavChange}
          />
        );
      case 'tasks':
        return <OrdersTasksPanel {...commonProps} hideHeader />;
      case 'orders_billing':
        return <OrdersBillingPanel API_URL={resolvedApiUrl} />;
      case 'orders_register':
        return <OrdersRegisterPanel />;
      case 'orders_related':
        return <OrdersRelatedPanel auditLogs={auditLogs} />;
      case 'projects':
        return (
          <ProjectsScreen
            dbProjects={dbProjects}
            selectedProject={selectedProject}
            setSelectedProject={setSelectedProject}
            fetchProjects={() => refreshReferenceData(new AbortController().signal)}
            API_URL={API_URL}
          />
        );
      case 'notebook':
        return <NotebookWikiScreen {...commonProps} hideHeader />;
      case 'decisions':
        return <DecisionsScreen {...commonProps} hideHeader />;
      case 'features':
        return <FeatureClinicalScreen {...commonProps} hideHeader />;
      case 'wet_protocols':
        return <WetLabProtocolsPanel API_URL={resolvedApiUrl} />;
      case 'wet_tasks':
        return <WetLabTasksPanel {...commonProps} hideHeader categoryFilter="Wet_Lab" />;
      case 'wet_inventory':
        return <WetLabInventoryPanel />;
      case 'cycif_pipeline':
        return <CycifScreen {...commonProps} variant="pipeline" embedded />;
      case 'cycif_install':
        return <CycifScreen {...commonProps} variant="install" embedded />;
      case 'cycif_structure':
        return <CycifScreen {...commonProps} variant="structure" embedded />;
      case 'cycif_knowledge':
        return <CycifScreen {...commonProps} variant="knowledge" embedded />;
      case 'bioinformatics':
        return (
          <BioinformaticsHubScreen
            {...commonProps}
            activeSubTab={subNav.bioSub || navSub}
            hideChrome
          />
        );
      case 'computational_tools':
        return <ComputationalToolsScreen />;
      case 'chat':
        return (
          <AiLabAssistantScreen
            {...commonProps}
            activeSubTab="copilot"
            hideChrome
          />
        );
      case 'ai_assistant':
        return (
          <AiLabAssistantScreen
            {...commonProps}
            activeSubTab={subNav.aiSub || navSub}
            hideChrome
          />
        );
      default:
        return null;
    }
  };

  const handleManualRefresh = useCallback(() => {
    refreshReferenceData(new AbortController().signal, 'refreshing');
  }, [refreshReferenceData]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    safeStorageSet('theme', theme);
  }, [theme]);

  useEffect(() => {
    initFirebaseAnalytics();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch('/health', { signal: controller.signal, timeoutMs: 8_000 })
      .then((data) => {
        if (data?.status === 'ok') {
          setApiHealth(data);
        } else {
          setApiHealth({ status: 'unreachable', database_connected: false });
        }
      })
      .catch(() => setApiHealth({ status: 'unreachable', database_connected: false }));
    return () => controller.abort();
  }, [resolvedApiUrl]);

  useEffect(() => {
    document.title = `${activeTitle} · Farkki Lab Assistant`;
  }, [activeTitle]);

  useEffect(() => {
    safeStorageSet(NAV_STORAGE_KEY, `${navMain}:${navSub}`);
  }, [navMain, navSub]);

  useEffect(() => {
    const controller = new AbortController();
    refreshReferenceData(controller.signal, 'loading');
    return () => controller.abort();
  }, [refreshReferenceData]);



  const useModuleShell = navMain !== 'projects_data' || navSub !== 'portfolio' || !selectedProject;

  const activeScreen = useModuleShell ? (
    <ModuleShell mainId={navMain} subId={navSub} onSubChange={(sub) => handleNavChange(navMain, sub)}>
      {renderScreenBody()}
    </ModuleShell>
  ) : (
    renderScreenBody()
  );

  return (
    <TaskpadProvider>
      <div className="app-container" data-loading={isLoading ? 'true' : 'false'}>
        <a className="skip-link" href="#main-content">
          Skip to workspace
        </a>

      <Sidebar
        navMain={navMain}
        navSub={navSub}
        onNavChange={handleNavChange}
        onResetProject={resetProject}
        theme={theme}
        setTheme={setTheme}
        apiHealth={apiHealth}
        apiUrl={resolvedApiUrl}
        onOpenSearch={() => setIsSearchOpen(true)}
      />

      <main
        id="main-content"
        className="main-content"
        tabIndex={-1}
        aria-busy={isLoading}
        aria-labelledby="app-current-section"
      >
        <div className="app-content-shell">
          <div className="app-topline" role="status" aria-live="polite">
            <div className="app-topline-copy">
              <span className="app-topline-eyebrow">Farkki research platform</span>
              <strong id="app-current-section">{activeTitle}</strong>
              <span className="app-topline-status" data-phase={loadState.phase}>
                {loadState.message}
              </span>
            </div>
            <button
              className="btn btn-secondary app-refresh-btn"
              type="button"
              onClick={handleManualRefresh}
              disabled={isLoading}
              aria-label="Refresh project, team and audit data"
            >
              {isLoading ? 'Syncing…' : 'Refresh'}
            </button>
          </div>

          <ErrorBoundary>{activeScreen}</ErrorBoundary>
        </div>
      </main>

        <GlobalSearchOverlay
          isOpen={isSearchOpen}
          onClose={() => setIsSearchOpen(false)}
          API_URL={resolvedApiUrl}
        />
      </div>
    </TaskpadProvider>
  );
}

export default App;
