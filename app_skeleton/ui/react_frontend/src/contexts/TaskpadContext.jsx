import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { MAIN_NAV } from '../config/navigation.js';
import { mergeTaskMeta, normalizeTaskMeta } from '../utils/taskpadUtils.js';
import {
  CENTRAL_WORKER_ID,
  PROJECTS_HUB_WORKER_ID,
  TASKPAD_SCOPES,
  createWorker,
  ensureBootstrapWorkers,
  getChildWorkers,
  loadWorkersFromStorage,
  makeProjectWorkerId,
  makeSectionWorkerId,
  parseWorkerId,
  resolveWorkerIdFromContext,
  saveWorkersToStorage,
  upsertWorker,
} from '../utils/taskpadRegistry.js';

const TaskpadContext = createContext(null);

const INITIAL_SCOPE = {
  scope: 'section',
  workerId: null,
  sectionId: null,
  projectCode: null,
  projectName: null,
  menuItems: null,
  defaultSection: null,
};

export function useTaskpad() {
  const ctx = useContext(TaskpadContext);
  if (!ctx) {
    throw new Error('useTaskpad must be used within TaskpadProvider');
  }

  const openTaskpad = useCallback(
    (content = '', meta = {}) => {
      const workerId =
        meta.workerId ||
        ctx.activeWorkerId ||
        ctx.scopeState.workerId ||
        resolveWorkerIdFromContext({
          mainId: ctx.scopeState.sectionId,
          subId: ctx.scopeState.defaultSection,
          projectCode: ctx.scopeState.projectCode,
          scope: ctx.scopeState.scope,
        });
      ctx.openWorkerTaskpad(workerId, content, {
        section: meta.section || ctx.scopeState.defaultSection || undefined,
        ...meta,
      });
    },
    [ctx]
  );

  return {
    ...ctx,
    openTaskpad,
    scope: ctx.scopeState.scope,
    workerId: ctx.activeWorkerId || ctx.scopeState.workerId,
    projectCode: ctx.scopeState.projectCode,
    projectName: ctx.scopeState.projectName,
    scopeMenuItems: ctx.scopeState.menuItems,
    defaultSection: ctx.scopeState.defaultSection,
  };
}

/** Register a taskpad worker while a screen is mounted. */
export function useTaskpadWorkerRegistration(meta) {
  const { registerWorker, unregisterWorker } = useTaskpad();
  const workerId = meta?.workerId;

  useEffect(() => {
    if (!workerId) return undefined;
    registerWorker(meta);
    return () => unregisterWorker(workerId);
  }, [
    workerId,
    meta?.scope,
    meta?.sectionId,
    meta?.projectCode,
    meta?.label,
    registerWorker,
    unregisterWorker,
  ]);
}

/** Declarative project scope wrapper (WorkspaceScreen). */
export function ProjectTaskpadScope({
  projectCode,
  projectName,
  menuItems,
  children,
}) {
  const { setProjectScope, clearPageScope } = useTaskpad();
  const workerId = makeProjectWorkerId(projectCode);

  useEffect(() => {
    setProjectScope(projectCode, menuItems, projectName);
    return () => clearPageScope();
  }, [projectCode, projectName, menuItems, setProjectScope, clearPageScope]);

  useTaskpadWorkerRegistration({
    workerId,
    scope: TASKPAD_SCOPES.PROJECT,
    projectCode,
    label: projectName || projectCode,
  });

  return children;
}

/** @deprecated Use section-scoped workers via ModuleShell. Kept for callers expecting lab-wide menu shape. */
export function globalTaskpadMenuItems() {
  return [
    { id: 'general', label: 'General lab task' },
    ...MAIN_NAV.map((item) => ({ id: item.id, label: item.label })),
  ];
}

export function TaskpadProvider({ children }) {
  const [workers, setWorkers] = useState(() =>
    ensureBootstrapWorkers(loadWorkersFromStorage())
  );
  const [isOpen, setIsOpen] = useState(false);
  const [taskContent, setTaskContent] = useState('');
  const [mode, setMode] = useState('quick');
  const [projectLogFile, setProjectLogFile] = useState(null);
  const [taskMeta, setTaskMeta] = useState(null);
  const [scopeState, setScopeState] = useState(INITIAL_SCOPE);
  const [activeWorkerId, setActiveWorkerId] = useState(null);
  const [managerPanelOpen, setManagerPanelOpen] = useState(false);

  useEffect(() => {
    saveWorkersToStorage(workers);
  }, [workers]);

  const getWorker = useCallback(
    (workerId) => (workerId ? workers[workerId] || null : null),
    [workers]
  );

  const registerWorker = useCallback((meta = {}) => {
    if (!meta.workerId) return;
    setWorkers((prev) => upsertWorker(prev, meta));
  }, []);

  const unregisterWorker = useCallback((workerId) => {
    if (!workerId) return;
    const parsed = parseWorkerId(workerId);
    if (
      parsed.scope === TASKPAD_SCOPES.CENTRAL ||
      parsed.scope === TASKPAD_SCOPES.SECTION ||
      parsed.scope === TASKPAD_SCOPES.PROJECTS_HUB
    ) {
      return;
    }
    setWorkers((prev) => {
      if (!prev[workerId]) return prev;
      const next = { ...prev };
      delete next[workerId];
      return next;
    });
  }, []);

  const updateWorkerContent = useCallback((workerId, content) => {
    if (!workerId) return;
    setWorkers((prev) => {
      const worker = prev[workerId];
      if (!worker) return prev;
      return {
        ...prev,
        [workerId]: { ...worker, content, updatedAt: Date.now() },
      };
    });
  }, []);

  const addWorkerTask = useCallback((workerId, task) => {
    if (!workerId || !task?.text?.trim()) return;
    setWorkers((prev) => {
      const worker = prev[workerId];
      if (!worker) return prev;
      const entry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        section: task.section || 'general',
        text: task.text.trim(),
        createdAt: Date.now(),
        filePath: task.filePath || null,
        fileName: task.fileName || null,
      };
      return {
        ...prev,
        [workerId]: {
          ...worker,
          tasks: [entry, ...worker.tasks],
          content: '',
          updatedAt: Date.now(),
        },
      };
    });
  }, []);

  const setSectionScope = useCallback((mainId, subId = null, menuItems = null) => {
    const workerId = resolveWorkerIdFromContext({ mainId, subId });
    const parsed = parseWorkerId(workerId);
    setScopeState({
      scope: parsed.scope || TASKPAD_SCOPES.SECTION,
      workerId,
      sectionId: parsed.sectionId || mainId || null,
      projectCode: null,
      projectName: null,
      menuItems,
      defaultSection: subId || null,
    });
    setActiveWorkerId(workerId);
  }, []);

  const setProjectScope = useCallback((projectCode, menuItems, projectName = null) => {
    const workerId = makeProjectWorkerId(projectCode);
    setScopeState({
      scope: TASKPAD_SCOPES.PROJECT,
      workerId,
      sectionId: null,
      projectCode: projectCode || null,
      projectName: projectName || projectCode || null,
      menuItems: menuItems || null,
      defaultSection: null,
    });
    setActiveWorkerId(workerId);
  }, []);

  const clearPageScope = useCallback(() => {
    setScopeState(INITIAL_SCOPE);
    setActiveWorkerId(null);
  }, []);

  const setTargetSection = useCallback((section) => {
    setScopeState((prev) => ({ ...prev, defaultSection: section || null }));
  }, []);

  const openWorkerTaskpad = useCallback((workerId, content = '', meta = {}) => {
    if (!workerId) return;
    let draft = typeof content === 'string' && content.length > 0 ? content : '';
    setWorkers((prev) => {
      const next = upsertWorker(prev, { workerId, ...parseWorkerId(workerId), ...meta });
      if (!draft) draft = next[workerId]?.content || '';
      return next;
    });
    setActiveWorkerId(workerId);
    setMode('quick');
    setProjectLogFile(null);
    setTaskContent(draft);
    setTaskMeta(normalizeTaskMeta({ workerId, ...meta }));
    setIsOpen(true);
  }, []);

  const openCentralTaskpad = useCallback(() => {
    setWorkers((prev) =>
      upsertWorker(prev, {
        workerId: CENTRAL_WORKER_ID,
        scope: TASKPAD_SCOPES.CENTRAL,
      }),
    );
  }, []);

  const openProjectLogTaskpad = useCallback(
    (file) => {
      if (!file?.path) return;
      const workerId = makeProjectWorkerId(file.projectCode);
      setActiveWorkerId(workerId);
      setMode('project_log');
      setProjectLogFile(file);
      setTaskContent('');
      setTaskMeta(
        normalizeTaskMeta({
          workerId,
          projectCode: file.projectCode,
          section: 'log',
          filePath: file.path,
          fileName: file.name,
        })
      );
      setIsOpen(true);
    },
    []
  );

  const closeTaskpad = useCallback(() => {
    if (activeWorkerId && taskContent) {
      updateWorkerContent(activeWorkerId, taskContent);
    }
    setIsOpen(false);
    setTaskContent('');
    setMode('quick');
    setProjectLogFile(null);
    setTaskMeta(null);
    setManagerPanelOpen(false);
  }, [activeWorkerId, taskContent, updateWorkerContent]);

  const getManagerView = useCallback(
    (managerWorkerId = activeWorkerId) => {
      const manager = getWorker(managerWorkerId);
      if (!manager) return null;
      return {
        manager,
        children: getChildWorkers(workers, managerWorkerId),
      };
    },
    [activeWorkerId, getWorker, workers]
  );

  const value = useMemo(
    () => ({
      isOpen,
      taskContent,
      setTaskContent,
      mode,
      projectLogFile,
      taskMeta,
      scopeState,
      activeWorkerId,
      workers,
      managerPanelOpen,
      setManagerPanelOpen,
      registerWorker,
      unregisterWorker,
      updateWorkerContent,
      addWorkerTask,
      getWorker,
      setSectionScope,
      setProjectScope,
      clearPageScope,
      setTargetSection,
      openWorkerTaskpad,
      openCentralTaskpad,
      openProjectLogTaskpad,
      closeTaskpad,
      getManagerView,
      setGlobalScope: clearPageScope,
    }),
    [
      isOpen,
      taskContent,
      mode,
      projectLogFile,
      taskMeta,
      scopeState,
      activeWorkerId,
      workers,
      managerPanelOpen,
      registerWorker,
      unregisterWorker,
      updateWorkerContent,
      addWorkerTask,
      getWorker,
      setSectionScope,
      setProjectScope,
      clearPageScope,
      setTargetSection,
      openWorkerTaskpad,
      openCentralTaskpad,
      openProjectLogTaskpad,
      closeTaskpad,
      getManagerView,
    ]
  );

  return (
    <TaskpadContext.Provider value={value}>{children}</TaskpadContext.Provider>
  );
}
