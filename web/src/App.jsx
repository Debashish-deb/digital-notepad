import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import Sidebar from '@/shared/layout/Sidebar';
import ModuleShell from '@/shared/layout/ModuleShell';
import ScreenCache from '@/shared/layout/ScreenCache';
import ErrorBoundary from '@/shared/layout/ErrorBoundary';
import DashboardScreen from '@/pages/DashboardScreen';
import LoginScreen from '@/pages/LoginScreen.jsx';
import { getApiUrl, apiFetch } from '@/services/client.js';
import { useApiContext } from '@/services/ApiContext.jsx';
import { TaskpadProvider } from './contexts/TaskpadContext.jsx';
import CentralTaskpadBackground from '@/shared/layout/CentralTaskpadBackground.jsx';
import { getSectionDocumentsConfig } from '@/lib/sectionDocumentsConfig.js';
import { projectsCatalog } from './data/projectsCatalog.js';
import { teamDirectory } from './data/teamDirectory.js';
import { activityLogs } from './data/activityLogs.js';
import { platformStats } from './data/platformStats.js';
import { mergeProjectRecord } from '@/lib/projectUtils.js';
import {
  COMPUTATIONAL_LEGACY_NESTED,
  findMainNav,
  findSubNav,
  getDefaultSocialSub,
  normalizeLegacyNavPair,
  parseNavFromStorage,
  resolveCycifLegacyNav,
  resolveSectionSub,
  resolveSocialInnerSub,
  resolveSocialLegacyNav,
} from './config/navigation';
import { isDocumentExplorerRoute } from '@/lib/documentExplorerPresets.js';
import { parseViewerHash } from '@/services/imageAssetsClient.js';
import { useGuiT } from './i18n/useGuiT.js';
import { initFirebaseAnalytics } from './config/firebase.js';
import { stashOmniboxPrefill } from '@/lib/searchHits.js';
import { userProfilesData } from './data/userProfilesData.js';
import { getModulePageMeta } from './data/moduleCoverContent.js';
import { applyPageMeta } from '@/lib/pageMeta.js';
import './App.css';
import {
  AdministrationScreen,
  AiLabAssistantScreen,
  BioinformaticsHubScreen,
  CycifScreen,
  DataStorageScreen,
  DigitalizationDashboard,
  DocumentLibraryScreen,
  FeatureClinicalScreen,
  GlobalSearchOverlay,
  ImageStreamingAdminScreen,
  ImageViewerPlaceholderScreen,
  IngestionDashboard,
  KnowledgeSearchScreen,
  LabCorpusBrowser,
  LabKnowledgeScreen,
  MeetingScreen,
  OrdersArchivePanel,
  OrdersBillingPanel,
  OrdersRegisterPanel,
  OrdersRelatedPanel,
  OrdersTasksPanel,
  OverviewDocumentsScreen,
  ProjectsScreen,
  ResearchKnowledgeAdminScreen,
  SectionDocumentsScreen,
  UserProfileScreen,
  WetLabInventoryPanel,
  WetLabProtocolsPanel,
  WetLabTasksPanel,
} from '@/app/screenRegistry.js';

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
const PROJECT_STORAGE_KEY = 'farkki_selected_project';

function readStoredProject() {
  try {
    const value = window.localStorage.getItem(PROJECT_STORAGE_KEY);
    return value && value.trim() ? value.trim() : null;
  } catch {
    return null;
  }
}

function writeStoredProject(code) {
  try {
    if (code) window.localStorage.setItem(PROJECT_STORAGE_KEY, code);
    else window.localStorage.removeItem(PROJECT_STORAGE_KEY);
  } catch {
    // ignore
  }
}

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

function resolveStoredNav(raw) {
  if (raw.hubNested) {
    return { main: raw.main, sub: raw.sub, hubNested: raw.hubNested };
  }
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
    dashboard: { main: 'workbench', sub: 'home' },
    projects: { main: 'projects_data', sub: 'portfolio' },
    notebook: { main: 'projects_data', sub: 'notebook' },
    chat: { main: 'ai_assistant', sub: 'copilot' },
    decisions: { main: 'projects_data', sub: 'decisions' },
    tasks: { main: 'projects_data', sub: 'portfolio' },
    bioinformatics: { main: 'computational', sub: 'onboarding' },
    features: { main: 'projects_data', sub: 'features' },
    ai_assistant: { main: 'ai_assistant', sub: 'prompts' },
  };
  if (map[stored]) return map[stored];
  if (stored && stored.includes(':')) {
    const [main, sub] = stored.split(':');
    return normalizeLegacyNavPair(main, sub);
  }
  return { main: 'workbench', sub: 'home' };
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
    authToken,
    userProfile,
    signOut,
  } = useApiContext();
  const { locale, t, nav } = useGuiT();
  const resolvedApiUrl = contextApiUrl || API_URL;
  const initialResolved = resolveStoredNav(migrateLegacyNav(safeStorageGet(NAV_STORAGE_KEY, '')));
  const [navMain, setNavMain] = useState(initialResolved.main);
  const [navSub, setNavSub] = useState(initialResolved.sub);
  const [sidebarExpandedMain, setSidebarExpandedMain] = useState(null);
  const [hubNestedSection, setHubNestedSection] = useState(initialResolved.hubNested);
  const [overviewSocialSub, setOverviewSocialSub] = useState(
    initialResolved.socialSub || getDefaultSocialSub()
  );
  const [selectedProject, setSelectedProject] = useState(readStoredProject);
  const [dbProjects, setDbProjects] = useState(() => mergeProjectsWithCatalog(projectsCatalog));
  const [projectCodes, setProjectCodesState] = useState(DEFAULT_PROJECT_CODES);
  const stats = platformStats || DEFAULT_STATS;
  const team = teamDirectory || [];
  const auditLogs = activityLogs || [];
  const [loadState, setLoadState] = useState({ phase: 'idle' });
  const [apiHealth, setApiHealth] = useState(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [viewerAssetId, setViewerAssetId] = useState(() => parseViewerHash(window.location.hash));

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

  const resetProject = useCallback(() => {
    setSelectedProject(null);
    writeStoredProject(null);
  }, []);

  const handleSelectProject = useCallback((code) => {
    setSelectedProject(code);
    writeStoredProject(code);
  }, []);

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

    const cycifResolved = resolveCycifLegacyNav(main, sub);
    if (cycifResolved) {
      setNavMain(cycifResolved.main);
      setNavSub(cycifResolved.sub);
      setHubNestedSection(cycifResolved.hubNested);
      setSidebarExpandedMain(cycifResolved.main);
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

    if (!mainItem.keepsProject) {
      setSelectedProject(null);
      writeStoredProject(null);
    }
  }, []);

  const handleProfileClick = useCallback(() => {
    handleNavChange('profile', 'user_profile');
    setSidebarExpandedMain(null);
  }, [handleNavChange]);

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

  const commonProps = useMemo(() => ({ dbProjects, API_URL: resolvedApiUrl }), [dbProjects, resolvedApiUrl]);

  const fetchProjects = useCallback(async (signal) => {
    const data = await fetchJson('/projects', { signal, timeoutMs: 14_000 });
    if (Array.isArray(data) && data.length > 0) {
      setDbProjects(mergeProjectsWithCatalog(data));
    } else {
      setDbProjects(mergeProjectsWithCatalog(projectsCatalog));
    }
  }, []);

  const refreshReferenceData = useCallback(async (signal, phase = 'idle') => {
    if (phase === 'refreshing') {
      setLoadState({ phase: 'refreshing' });
    }
    try {
      await fetchProjects(signal);
      setLoadState({ phase: 'ready' });
    } catch (err) {
      if (phase === 'refreshing') {
        setLoadState({ phase: 'warning' });
      }
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
      case 'document_library':
        return (
          <DocumentLibraryScreen
            title={localizedSub.label}
            description={localizedSub.description}
            mainId={subNav.libraryMain || navMain}
            subId={subNav.librarySub || navSub}
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
            onSelectProject={handleSelectProject}
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
      case 'image_streaming_admin':
        return (
          <ImageStreamingAdminScreen
            onBack={() => handleNavChange('profile', 'admin')}
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
            setSelectedProject={handleSelectProject}
            fetchProjects={() => refreshReferenceData(new AbortController().signal)}
            API_URL={resolvedApiUrl}
            portfolioSub="portfolio"
            onNavigate={handleNavChange}
          />
        );
      case 'notebook':
        return (
          <ProjectsScreen
            dbProjects={dbProjects}
            selectedProject={selectedProject}
            setSelectedProject={handleSelectProject}
            fetchProjects={() => refreshReferenceData(new AbortController().signal)}
            API_URL={resolvedApiUrl}
            portfolioSub="notebook"
            onNavigate={handleNavChange}
          />
        );
      case 'decisions':
        return (
          <ProjectsScreen
            dbProjects={dbProjects}
            selectedProject={selectedProject}
            setSelectedProject={handleSelectProject}
            fetchProjects={() => refreshReferenceData(new AbortController().signal)}
            API_URL={resolvedApiUrl}
            portfolioSub="decisions"
            onNavigate={handleNavChange}
          />
        );
      case 'features':
        return <FeatureClinicalScreen {...commonProps} hideHeader />;
      case 'wet_protocols':
        return <WetLabProtocolsPanel API_URL={resolvedApiUrl} />;
      case 'wet_tasks':
        return <WetLabTasksPanel {...commonProps} hideHeader categoryFilter="Wet_Lab" />;
      case 'wet_inventory':
        return <WetLabInventoryPanel />;
      case 'cycif_pipeline':
        return (
          <CycifScreen
            {...commonProps}
            variant="pipeline"
            embedded
            dbProjects={dbProjects}
            API_URL={resolvedApiUrl}
          />
        );
      case 'cycif_install':
        return (
          <BioinformaticsHubScreen
            key="bio-cycif-install-legacy"
            {...commonProps}
            activeSubTab="lumi"
            hubNestedSection="install"
            hideChrome
            onNavigate={handleNavChange}
          />
        );
      case 'cycif_structure':
        return (
          <BioinformaticsHubScreen
            key="bio-cycif-structure-legacy"
            {...commonProps}
            activeSubTab="troubleshoot"
            hubNestedSection="diagnostics"
            hideChrome
            onNavigate={handleNavChange}
          />
        );
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
            onSelectProject={handleSelectProject}
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
            onSelectProject={handleSelectProject}
            onOpenSearch={handleOpenSearch}
          />
        );
      default:
        return null;
    }
  };

  useEffect(() => {
    const syncViewerFromHash = () => setViewerAssetId(parseViewerHash(window.location.hash));
    syncViewerFromHash();
    window.addEventListener('hashchange', syncViewerFromHash);
    return () => window.removeEventListener('hashchange', syncViewerFromHash);
  }, []);

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
    if (!authReady) return undefined;
    const canFetchProjects =
      !firebaseAuthEnabled || authDisabled || Boolean(authToken) || isAuthenticated;
    if (!canFetchProjects) return undefined;

    const controller = new AbortController();
    refreshReferenceData(controller.signal, 'idle');
    return () => controller.abort();
  }, [
    authReady,
    firebaseAuthEnabled,
    authDisabled,
    authToken,
    isAuthenticated,
    refreshReferenceData,
  ]);

  useEffect(() => {
    if (!authReady) return;
    import('@/pages/ProjectsScreen');
  }, [authReady]);

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
    dbProjects,
    subNav?.screen,
    subNav?.bioSub,
    subNav?.aiSub,
    subNav?.dataSection,
    localizedSub?.label,
    localizedSub?.description,
  ]);

  const screenCacheKey = useMemo(() => {
    let key = `${navMain}:${navSub}`;
    if (hubNestedSection) key += `:${hubNestedSection}`;
    if (navMain === 'overview' && navSub === 'social') key += `:${overviewSocialSub}`;
    if (
      navMain === 'projects_data' &&
      selectedProject &&
      ['portfolio', 'notebook', 'decisions'].includes(navSub)
    ) {
      key += `:${selectedProject}`;
    }
    return key;
  }, [navMain, navSub, hubNestedSection, overviewSocialSub, selectedProject]);

  const cachedScreenBody = (
    <ScreenCache cacheKey={screenCacheKey} isActive>
      <Suspense fallback={<ScreenFallback />}>{screenBody}</Suspense>
    </ScreenCache>
  );

  const requireLogin = firebaseAuthEnabled && !authDisabled;
  const hasFirebaseSession = Boolean(authUser || authToken);
  const showSignOut = firebaseAuthEnabled && hasFirebaseSession;

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

  const profileByEmail = authUser?.email
    ? Object.values(userProfilesData).find(
        (p) => p.email?.toLowerCase() === authUser.email.toLowerCase(),
      )
    : null;
  const displayUser =
    authUser?.displayName ||
    userProfile?.name ||
    profileByEmail?.full_name ||
    (authUser?.email ? authUser.email.split('@')[0] : null) ||
    'Guest';

  const isProjectWorkspace =
    navMain === 'projects_data' &&
    selectedProject &&
    ['portfolio', 'notebook', 'decisions'].includes(navSub);
  const useModuleShell = !isProjectWorkspace;
  const useWideContentShell = isDocumentExplorerRoute(navMain, navSub, subNav?.screen);

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
      {cachedScreenBody}
    </ModuleShell>
  ) : (
    cachedScreenBody
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
        onSignOut={showSignOut ? signOut : null}
        onSignIn={firebaseAuthEnabled && !hasFirebaseSession ? handleProfileClick : null}
        onProfileClick={handleProfileClick}
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

          {viewerAssetId ? (
            <Suspense fallback={<ScreenFallback label="Loading image viewer…" />}>
              <div className="image-viewer-overlay" role="dialog" aria-modal="true" aria-label="Image viewer">
                <ImageViewerPlaceholderScreen
                  assetId={viewerAssetId}
                  onClose={() => {
                    window.location.hash = '';
                    setViewerAssetId(null);
                  }}
                />
              </div>
            </Suspense>
          ) : null}
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

        <CentralTaskpadBackground />
      </div>
    </TaskpadProvider>
  );
}

export default App;
