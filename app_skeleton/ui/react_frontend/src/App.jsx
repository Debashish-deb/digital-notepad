import React, { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ModuleShell from './components/ModuleShell';
import ErrorBoundary from './components/ErrorBoundary';
import DashboardScreen from './screens/DashboardScreen';
import LoginScreen from './screens/LoginScreen.jsx';
import { getApiUrl, apiFetch } from './api/client.js';
import { useApiContext } from './api/ApiContext.jsx';
import { TaskpadProvider } from './contexts/TaskpadContext.jsx';
import TaskpadSheet from './components/TaskpadSheet.jsx';
import { CENTRAL_WORKER_ID, TASKPAD_SCOPES } from './utils/taskpadRegistry.js';
import { getSectionDocumentsConfig } from './utils/sectionDocumentsConfig.js';
import { projectsCatalog } from './data/projectsCatalog.js';
import { teamDirectory } from './data/teamDirectory.js';
import { activityLogs } from './data/activityLogs.js';
import { platformStats } from './data/platformStats.js';
import { mergeProjectRecord } from './utils/projectUtils.js';
import {
  COMPUTATIONAL_LEGACY_NESTED,
  findMainNav,
  findSubNav,
  getDefaultSocialSub,
  parseNavFromStorage,
  resolveSectionSub,
  resolveSocialInnerSub,
  resolveSocialLegacyNav,
} from './config/navigation';
import { useGuiT } from './i18n/useGuiT.js';
import { initFirebaseAnalytics } from './config/firebase.js';
import { stashOmniboxPrefill } from './utils/searchHits.js';
import { getModulePageMeta } from './data/moduleCoverContent.js';
import { applyPageMeta } from './utils/pageMeta.js';
import './App.css';

const GlobalSearchOverlay = lazy(() => import('./components/GlobalSearchOverlay'));
const ProjectsScreen = lazy(() => import('./screens/ProjectsScreen'));
const NotebookWikiScreen = lazy(() => import('./screens/NotebookWikiScreen'));
const DecisionsScreen = lazy(() => import('./screens/DecisionsScreen'));
const BioinformaticsHubScreen = lazy(() => import('./screens/BioinformaticsHubScreen'));
const AiLabAssistantScreen = lazy(() => import('./screens/AiLabAssistantScreen'));
const FeatureClinicalScreen = lazy(() => import('./screens/FeatureClinicalScreen'));
const LabKnowledgeScreen = lazy(() => import('./screens/LabKnowledgeScreen'));
const DataStorageScreen = lazy(() => import('./screens/DataStorageScreen'));
const AdministrationScreen = lazy(() => import('./screens/AdministrationScreen'));
const UserProfileScreen = lazy(() => import('./screens/UserProfileScreen'));
const MeetingScreen = lazy(() => import('./screens/MeetingScreen'));
const IngestionDashboard = lazy(() => import('./screens/IngestionDashboard'));
const DigitalizationDashboard = lazy(() => import('./screens/DigitalizationDashboard'));
const KnowledgeSearchScreen = lazy(() => import('./screens/KnowledgeSearchScreen'));
const ResearchKnowledgeAdminScreen = lazy(() => import('./screens/ResearchKnowledgeAdminScreen'));
const LabCorpusBrowser = lazy(() => import('./components/LabCorpusBrowser.jsx'));
const CycifScreen = lazy(() => import('./screens/CycifScreen'));
const OverviewDocumentsScreen = lazy(() => import('./screens/OverviewDocumentsScreen.jsx'));
const SectionDocumentsScreen = lazy(() => import('./screens/SectionDocumentsScreen.jsx'));
const OrdersTasksPanel = lazy(() =>
  import('./screens/OrdersHubScreen').then((m) => ({ default: m.OrdersTasksPanel })),
);
const OrdersRegisterPanel = lazy(() =>
  import('./screens/OrdersHubScreen').then((m) => ({ default: m.OrdersRegisterPanel })),
);
const OrdersRelatedPanel = lazy(() =>
  import('./screens/OrdersHubScreen').then((m) => ({ default: m.OrdersRelatedPanel })),
);
const OrdersBillingPanel = lazy(() =>
  import('./screens/OrdersHubScreen').then((m) => ({ default: m.OrdersBillingPanel })),
);
const OrdersArchivePanel = lazy(() =>
  import('./screens/OrdersHubScreen').then((m) => ({ default: m.OrdersArchivePanel })),
);
const WetLabProtocolsPanel = lazy(() =>
  import('./screens/WetLabScreen').then((m) => ({ default: m.WetLabProtocolsPanel })),
);
const WetLabTasksPanel = lazy(() =>
  import('./screens/WetLabScreen').then((m) => ({ default: m.WetLabTasksPanel })),
);
const WetLabInventoryPanel = lazy(() =>
  import('./screens/WetLabScreen').then((m) => ({ default: m.WetLabInventoryPanel })),
);

function ScreenFallback({ label = 'Loading workspace…' }) {
  return (
    <div className="panel module-loading-fallback" role="status" aria-live="polite">
      {label}
    </div>
  );
}

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

function resolveComputationalNav(raw) {
  if (raw.main === 'computational' && raw.sub === 'utilities' && raw.hubNested === 'tools') {
    return { main: raw.main, sub: 'tools', hubNested: null };
  }
  const legacy = COMPUTATIONAL_LEGACY_NESTED[raw.sub];
  if (raw.main === 'computational' && legacy) {
    return { main: raw.main, sub: legacy.tab, hubNested: legacy.section };
  }
  if (raw.main === 'computational' && raw.sub === 'tools') {
    return { main: raw.main, sub: 'tools', hubNested: null };
  }
  return { main: raw.main, sub: raw.sub, hubNested: null };
}

function migrateLegacyNav(stored) {
  const legacy = parseNavFromStorage(stored);
  if (legacy) {
    if (
      legacy.main === 'overview' &&
      (legacy.sub === 'dashboard' || legacy.sub === 'research')
    ) {
      return { main: 'overview', sub: 'get_started' };
    }
    if (legacy.socialSub) {
      return {
        main: legacy.main,
        sub: legacy.sub,
        socialSub: legacy.socialSub,
      };
    }
    return legacy;
  }
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
  return map[stored] || { main: 'overview', sub: 'get_started' };
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
  const {
    API_URL: contextApiUrl,
    authReady,
    isAuthenticated,
    authDisabled,
    firebaseAuthEnabled,
    onAuthToken,
    authUser,
    userProfile,
    signOut,
  } = useApiContext();
  const { locale, t, nav } = useGuiT();
  const resolvedApiUrl = contextApiUrl || API_URL;
  const initialResolved = resolveComputationalNav(migrateLegacyNav(safeStorageGet(NAV_STORAGE_KEY, '')));
  const [navMain, setNavMain] = useState(initialResolved.main);
  const [navSub, setNavSub] = useState(initialResolved.sub);
  const [sidebarExpandedMain, setSidebarExpandedMain] = useState(null);
  const [hubNestedSection, setHubNestedSection] = useState(initialResolved.hubNested);
  const [overviewSocialSub, setOverviewSocialSub] = useState(
    initialResolved.socialSub || getDefaultSocialSub()
  );
  const [selectedProject, setSelectedProject] = useState(null);
  const [dbProjects, setDbProjects] = useState(() => mergeProjectsWithCatalog(projectsCatalog));
  const [projectCodes, setProjectCodesState] = useState(DEFAULT_PROJECT_CODES);
  const [stats, setStats] = useState(platformStats || DEFAULT_STATS);
  const [team, setTeam] = useState(teamDirectory || []);
  const [auditLogs, setAuditLogs] = useState(activityLogs || []);
  const [loadState, setLoadState] = useState({ phase: 'idle' });
  const [apiHealth, setApiHealth] = useState(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const handleOpenSearch = useCallback((query) => {
    if (query?.trim()) stashOmniboxPrefill(query);
    setIsSearchOpen(true);
  }, []);

  const handleCloseSearch = useCallback(() => setIsSearchOpen(false), []);

  const handleOpenSearchOverlay = useCallback(() => setIsSearchOpen(true), []);

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

  const activeTitle = nav.sectionTitle(navMain, navSub);
  const isLoading = loadState.phase === 'loading' || loadState.phase === 'refreshing';
  const subNav = findSubNav(navMain, navSub);
  const localizedSub = nav.findSub(navMain, navSub);
  const loadMessage = useMemo(() => {
    if (loadState.phase === 'loading' || loadState.phase === 'refreshing') {
      return t('common.syncing');
    }
    if (loadState.phase === 'ready') return t('common.projectsSynced');
    if (loadState.phase === 'warning') return t('common.syncWarning');
    return t('common.ready');
  }, [loadState.phase, t]);

  const setProjectCodes = useCallback((nextValue) => {
    setProjectCodesState((previous) => {
      const resolved = typeof nextValue === 'function' ? nextValue(previous) : nextValue;
      const normalized = normalizeProjectCodes(resolved);
      return normalized.length ? normalized : [...DEFAULT_PROJECT_CODES];
    });
  }, []);

  const resetProject = useCallback(() => setSelectedProject(null), []);

  const handleNavChange = useCallback((main, sub, options = {}) => {
    const { fromMainNav = false } = options;
    const socialResolved = resolveSocialLegacyNav(main, sub);
    if (socialResolved) {
      setNavMain(socialResolved.main);
      setNavSub(socialResolved.sub);
      setOverviewSocialSub(
        resolveSocialInnerSub(socialResolved.socialSub, { fromMainNav, enteringSocial: true })
      );
      setHubNestedSection(null);
      setSidebarExpandedMain('overview');
      setSelectedProject(null);
      return;
    }

    const mainItem = findMainNav(main);
    let subId = resolveSectionSub(mainItem.id, sub, { fromMainNav });
    let nested = null;
    if (mainItem.id === 'computational') {
      const legacy = COMPUTATIONAL_LEGACY_NESTED[subId];
      if (legacy) {
        nested = legacy.section;
        subId = legacy.tab;
      }
    }
    const resolvedSub = subId;
    setNavMain(mainItem.id);
    setNavSub(resolvedSub);
    setHubNestedSection(nested);
    setSidebarExpandedMain(mainItem.id);

    if (mainItem.id === 'overview') {
      if (resolvedSub === 'social') {
        setOverviewSocialSub(
          resolveSocialInnerSub(sub, { fromMainNav, enteringSocial: !fromMainNav && sub === 'social' })
        );
      } else if (fromMainNav) {
        setOverviewSocialSub(getDefaultSocialSub());
      }
    } else if (fromMainNav) {
      setOverviewSocialSub(getDefaultSocialSub());
    }

    if (!mainItem.keepsProject) setSelectedProject(null);
  }, []);

  const handleMainNavClick = useCallback((main) => {
    const mainItem = findMainNav(main);
    if (main === navMain && sidebarExpandedMain === main) {
      setSidebarExpandedMain(null);
      return;
    }
    if (main === navMain) {
      setSidebarExpandedMain(main);
      handleNavChange(main, mainItem.defaultSub, { fromMainNav: true });
      return;
    }
    handleNavChange(main, mainItem.defaultSub, { fromMainNav: true });
  }, [navMain, sidebarExpandedMain, handleNavChange]);

  const handleAskAiFromSearch = useCallback((q) => {
    handleNavChange('ai_assistant', 'copilot');
    try {
      sessionStorage.setItem('farkki_search_last_query', q);
    } catch {
      /* ignore */
    }
  }, [handleNavChange]);

  const handleSelectProject = useCallback((code) => setSelectedProject(code), []);

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
    setLoadState({ phase });
    try {
      await fetchProjects(signal);
      setLoadState({ phase: 'ready' });
    } catch (err) {
      setLoadState({ phase: 'warning' });
    }
  }, [fetchProjects]);

  const handleManualRefresh = useCallback(() => {
    refreshReferenceData(new AbortController().signal, 'refreshing');
  }, [refreshReferenceData]);

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
        if (navMain === 'overview') {
          return (
            <OverviewDocumentsScreen
              subId={navSub}
              title={localizedSub.label}
              description={localizedSub.description}
              onSubChange={(sub) => handleNavChange('overview', sub)}
              onNavigate={handleNavChange}
              onRefresh={handleManualRefresh}
              isRefreshing={isLoading}
              socialSubId={overviewSocialSub}
              onSocialSubChange={setOverviewSocialSub}
            />
          );
        }
        if (getSectionDocumentsConfig(navMain, navSub)) {
          // wet_lab, cycif document-backed tabs
          return (
            <SectionDocumentsScreen
              mainId={navMain}
              subId={navSub}
              title={localizedSub.label}
              description={localizedSub.description}
            />
          );
        }
        return (
          <LabKnowledgeScreen
            subId={navSub}
            navSub={subNav}
            API_URL={resolvedApiUrl}
            title={localizedSub.label}
            description={localizedSub.description}
          />
        );
      case 'data_storage':
        return (
          <DataStorageScreen
            key={`data-storage-${navSub}`}
            title={localizedSub.label}
            description={localizedSub.description}
            section={subNav.dataSection || navSub || 'landscape'}
            onNavigate={handleNavChange}
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
          <KnowledgeSearchScreen
            title={subNav.label}
            description={subNav.description}
            onNavigate={handleNavChange}
            onSelectProject={(code) => setSelectedProject(code)}
          />
        );
      case 'research_knowledge':
        return <ResearchKnowledgeAdminScreen />;
      case 'lab_corpus':
        return (
          <LabCorpusBrowser title={subNav.label} description={subNav.description} />
        );
      case 'administration':
        return (
          <AdministrationScreen
            title={localizedSub.label}
            description={localizedSub.description}
            onNavigate={handleNavChange}
          />
        );
      case 'user_profile':
        return (
          <UserProfileScreen
            title={localizedSub.label}
            description={localizedSub.description}
          />
        );
      case 'meeting_booking':
        return (
          <MeetingScreen
            title={localizedSub.label}
            description={localizedSub.description}
          />
        );
      case 'tasks':
        return <OrdersTasksPanel {...commonProps} hideHeader />;
      case 'orders_billing':
        return <OrdersBillingPanel API_URL={resolvedApiUrl} />;
      case 'orders_archive':
        return <OrdersArchivePanel />;
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
            key={`bio-${navSub}-${hubNestedSection || 'root'}`}
            {...commonProps}
            activeSubTab={subNav.bioSub || navSub}
            hubNestedSection={hubNestedSection}
            hideChrome
            onNavigate={handleNavChange}
          />
        );
      case 'computational_tools':
        return (
          <BioinformaticsHubScreen
            {...commonProps}
            activeSubTab="tools"
            hideChrome
            onNavigate={handleNavChange}
          />
        );
      case 'chat':
        return (
          <AiLabAssistantScreen
            {...commonProps}
            activeSubTab="copilot"
            hideChrome
            onNavigate={handleNavChange}
            onSelectProject={(code) => setSelectedProject(code)}
            onOpenSearch={handleOpenSearch}
          />
        );
      case 'ai_assistant':
        return (
          <AiLabAssistantScreen
            {...commonProps}
            activeSubTab={subNav.aiSub || navSub}
            hideChrome
            onNavigate={handleNavChange}
            onSelectProject={(code) => setSelectedProject(code)}
            onOpenSearch={handleOpenSearch}
          />
        );
      default:
        return null;
    }
  };

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
    applyPageMeta(getModulePageMeta(activeTitle, navMain, navSub, t('common.documentTitleSuffix')));
  }, [activeTitle, navMain, navSub, t]);

  useEffect(() => {
    safeStorageSet(NAV_STORAGE_KEY, `${navMain}:${navSub}`);
  }, [navMain, navSub]);

  useEffect(() => {
    const controller = new AbortController();
    refreshReferenceData(controller.signal, 'loading');
    return () => controller.abort();
  }, [refreshReferenceData]);

  const handleModuleSubChange = useCallback(
    (sub) => handleNavChange(navMain, sub),
    [handleNavChange, navMain],
  );

  const screenBody = useMemo(() => renderScreenBody(), [
    navMain,
    navSub,
    hubNestedSection,
    overviewSocialSub,
    selectedProject,
    subNav?.screen,
    subNav?.bioSub,
    subNav?.aiSub,
    subNav?.dataSection,
    localizedSub?.label,
    localizedSub?.description,
  ]);

  const requireLogin = firebaseAuthEnabled && !authDisabled;

  if (firebaseAuthEnabled && !authReady) {
    return (
      <div className="auth-boot-screen" role="status" aria-live="polite">
        <p>{t('common.syncing')}</p>
      </div>
    );
  }

  if (requireLogin && authReady && !isAuthenticated) {
    return <LoginScreen onAuthenticated={onAuthToken} />;
  }

  const displayUser =
    userProfile?.name ||
    authUser?.displayName ||
    (authUser?.email ? authUser.email.split('@')[0] : null) ||
    'Guest';

  const useModuleShell = navMain !== 'projects_data' || navSub !== 'portfolio' || !selectedProject;
  const useWideContentShell = navMain === 'data_storage' && navSub === 'documents';

  const activeScreen = useModuleShell ? (
    <ModuleShell
      mainId={navMain}
      subId={navSub}
      onSubChange={handleModuleSubChange}
      onRefresh={handleManualRefresh}
      isRefreshing={isLoading}
      compact={navMain === 'computational'}
      landing
    >
      <Suspense fallback={<ScreenFallback />}>{screenBody}</Suspense>
    </ModuleShell>
  ) : (
    <Suspense fallback={<ScreenFallback />}>{screenBody}</Suspense>
  );

  return (
    <TaskpadProvider>
      <div className="app-container" data-loading={isLoading ? 'true' : 'false'}>
        <a className="skip-link" href="#main-content">
          {t('common.skipToWorkspace')}
        </a>

      <Sidebar
        navMain={navMain}
        navSub={navSub}
        sidebarExpandedMain={sidebarExpandedMain}
        onNavChange={handleNavChange}
        onMainNavClick={handleMainNavClick}
        onResetProject={resetProject}
        apiHealth={apiHealth}
        apiUrl={resolvedApiUrl}
        onOpenSearch={handleOpenSearchOverlay}
        userLabel={displayUser}
        userEmail={authUser?.email || userProfile?.email}
        onSignOut={requireLogin ? signOut : null}
      />

      <main
        id="main-content"
        className="main-content"
        tabIndex={-1}
        aria-busy={isLoading}
        aria-labelledby="app-current-section"
      >
        <div className={`app-content-shell${useWideContentShell ? ' app-content-shell--wide' : ''}`}>
          <span className="sr-only" id="app-current-section" role="status" aria-live="polite">
            {activeTitle} — {loadMessage}
          </span>
          {!useModuleShell ? (
            <button
              type="button"
              className="app-refresh-fab"
              onClick={handleManualRefresh}
              disabled={isLoading}
              aria-label={isLoading ? t('common.syncing') : t('common.refreshAria')}
              title={isLoading ? t('common.syncing') : t('common.refresh')}
            >
              <RefreshCw size={15} className={isLoading ? 'spin' : undefined} aria-hidden />
            </button>
          ) : null}

          <ErrorBoundary>{activeScreen}</ErrorBoundary>
        </div>
      </main>

        {isSearchOpen ? (
          <Suspense fallback={null}>
            <GlobalSearchOverlay
              isOpen={isSearchOpen}
              onClose={handleCloseSearch}
              onNavigate={handleNavChange}
              onSelectProject={handleSelectProject}
              onAskAi={handleAskAiFromSearch}
              projectCode={
                typeof selectedProject === 'string'
                  ? selectedProject
                  : selectedProject?.project_code || selectedProject?.code
              }
            />
          </Suspense>
        ) : null}

        <div className="app-central-taskpad-host" aria-live="polite">
          <TaskpadSheet scope={TASKPAD_SCOPES.CENTRAL} workerId={CENTRAL_WORKER_ID} />
        </div>
      </div>
    </TaskpadProvider>
  );
}

export default App;
