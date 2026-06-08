import { MAIN_NAV, findMainNav } from '../config/navigation.js';

export const TASKPAD_STORAGE_KEY = 'omeia_taskpad_workers_v1';

export const TASKPAD_SCOPES = {
  CENTRAL: 'central',
  SECTION: 'section',
  PROJECTS_HUB: 'projects_hub',
  PROJECT: 'project',
};

export const CENTRAL_WORKER_ID = 'central';
export const PROJECTS_HUB_WORKER_ID = 'projects_hub';

export function makeSectionWorkerId(sectionId) {
  return `section:${sectionId}`;
}

export function makeProjectWorkerId(projectCode) {
  return `project:${String(projectCode || '').trim()}`;
}

export function parseWorkerId(workerId) {
  if (!workerId) return { scope: null };
  if (workerId === CENTRAL_WORKER_ID) return { scope: TASKPAD_SCOPES.CENTRAL };
  if (workerId === PROJECTS_HUB_WORKER_ID) return { scope: TASKPAD_SCOPES.PROJECTS_HUB };
  if (workerId.startsWith('section:')) {
    return { scope: TASKPAD_SCOPES.SECTION, sectionId: workerId.slice(8) };
  }
  if (workerId.startsWith('project:')) {
    return { scope: TASKPAD_SCOPES.PROJECT, projectCode: workerId.slice(8) };
  }
  return { scope: null };
}

export function parentWorkerIdForScope(scope) {
  if (scope === TASKPAD_SCOPES.SECTION || scope === TASKPAD_SCOPES.PROJECTS_HUB) {
    return CENTRAL_WORKER_ID;
  }
  if (scope === TASKPAD_SCOPES.PROJECT) return PROJECTS_HUB_WORKER_ID;
  return null;
}

export function defaultLabelForScope(scope, { sectionId, projectCode } = {}) {
  if (scope === TASKPAD_SCOPES.CENTRAL) return 'Central Taskpad';
  if (scope === TASKPAD_SCOPES.PROJECTS_HUB) return 'Projects hub';
  if (scope === TASKPAD_SCOPES.SECTION) {
    const main = findMainNav(sectionId);
    return main?.label || sectionId;
  }
  if (scope === TASKPAD_SCOPES.PROJECT) return projectCode || 'Project';
  return 'Taskpad';
}

export function createWorker({
  workerId,
  scope,
  sectionId = null,
  projectCode = null,
  label = null,
  parentWorkerId = null,
}) {
  const resolvedParent = parentWorkerId ?? parentWorkerIdForScope(scope);
  return {
    workerId,
    scope,
    sectionId,
    projectCode,
    label: label || defaultLabelForScope(scope, { sectionId, projectCode }),
    content: '',
    tasks: [],
    parentWorkerId: resolvedParent,
    updatedAt: Date.now(),
  };
}

export function resolveWorkerIdFromContext({
  mainId,
  subId,
  projectCode,
  scope: scopeProp,
} = {}) {
  if (scopeProp === TASKPAD_SCOPES.CENTRAL) return CENTRAL_WORKER_ID;
  if (scopeProp === TASKPAD_SCOPES.PROJECTS_HUB) return PROJECTS_HUB_WORKER_ID;
  if (scopeProp === TASKPAD_SCOPES.PROJECT || projectCode) {
    return makeProjectWorkerId(projectCode);
  }
  if (mainId === 'projects_data' && subId === 'portfolio') return PROJECTS_HUB_WORKER_ID;
  if (mainId) return makeSectionWorkerId(mainId);
  return null;
}

export function sectionMenuItems(sectionId) {
  const main = findMainNav(sectionId);
  if (!main) return [];
  return main.children.map((child) => ({ id: child.id, label: child.label }));
}

export function projectsHubMenuItems() {
  return [
    { id: 'portfolio', label: 'Portfolio & PI notes' },
    { id: 'coordination', label: 'Cross-project coordination' },
    { id: 'admin', label: 'Admin & registry' },
  ];
}

export function centralMenuItems() {
  return [
    { id: 'coordination', label: 'Lab-wide coordination' },
    { id: 'priorities', label: 'Priorities & blockers' },
    ...MAIN_NAV.map((item) => ({ id: item.id, label: item.label })),
  ];
}

export function isManagerScope(scope) {
  return scope === TASKPAD_SCOPES.CENTRAL || scope === TASKPAD_SCOPES.PROJECTS_HUB;
}

function safeParse(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function loadWorkersFromStorage() {
  try {
    const raw = window.localStorage.getItem(TASKPAD_STORAGE_KEY);
    const parsed = safeParse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    return parsed;
  } catch {
    return {};
  }
}

export function saveWorkersToStorage(workers) {
  try {
    window.localStorage.setItem(TASKPAD_STORAGE_KEY, JSON.stringify(workers));
  } catch {
    /* ignore quota errors */
  }
}

export function ensureBootstrapWorkers(workers) {
  const next = { ...workers };
  if (!next[CENTRAL_WORKER_ID]) {
    next[CENTRAL_WORKER_ID] = createWorker({
      workerId: CENTRAL_WORKER_ID,
      scope: TASKPAD_SCOPES.CENTRAL,
      parentWorkerId: null,
    });
  }
  if (!next[PROJECTS_HUB_WORKER_ID]) {
    next[PROJECTS_HUB_WORKER_ID] = createWorker({
      workerId: PROJECTS_HUB_WORKER_ID,
      scope: TASKPAD_SCOPES.PROJECTS_HUB,
    });
  }
  for (const nav of MAIN_NAV) {
    const id = makeSectionWorkerId(nav.id);
    if (!next[id]) {
      next[id] = createWorker({
        workerId: id,
        scope: TASKPAD_SCOPES.SECTION,
        sectionId: nav.id,
      });
    }
  }
  return next;
}

export function upsertWorker(workers, meta) {
  const workerId = meta.workerId;
  if (!workerId) return workers;
  const existing = workers[workerId];
  if (existing) {
    return {
      ...workers,
      [workerId]: {
        ...existing,
        label: meta.label || existing.label,
        sectionId: meta.sectionId ?? existing.sectionId,
        projectCode: meta.projectCode ?? existing.projectCode,
        updatedAt: Date.now(),
      },
    };
  }
  const parsed = parseWorkerId(workerId);
  return {
    ...workers,
    [workerId]: createWorker({
      workerId,
      scope: meta.scope || parsed.scope,
      sectionId: meta.sectionId ?? parsed.sectionId ?? null,
      projectCode: meta.projectCode ?? parsed.projectCode ?? null,
      label: meta.label,
    }),
  };
}

export function getChildWorkers(workers, managerWorkerId) {
  return Object.values(workers)
    .filter((w) => w.parentWorkerId === managerWorkerId)
    .sort((a, b) => a.label.localeCompare(b.label));
}
