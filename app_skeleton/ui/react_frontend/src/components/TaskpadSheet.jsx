import { useEffect, useId, useLayoutEffect, useMemo, useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp, GitBranch, Plus } from 'lucide-react';
import LazyDataPadEditor from './LazyDataPadEditor.jsx';
import {
  useTaskpad,
  useTaskpadWorkerRegistration,
} from '../contexts/TaskpadContext.jsx';
import { useGuiT } from '../i18n/useGuiT.js';
import { inferExtension } from '../utils/fileTypeMeta.js';
import {
  TASKPAD_SCOPES,
  centralMenuItems,
  isManagerScope,
  projectsHubMenuItems,
  resolveWorkerIdFromContext,
  sectionMenuItems,
} from '../utils/taskpadRegistry.js';

const EDITABLE_LOG_EXTS = new Set(['.md', '.txt', '.html', '.rtf']);
const TASKPAD_EDITOR_HEIGHT = 'calc(20vh - 3.25rem)';

const taskpadSlotStack = [];
const taskpadSlotListeners = new Set();

function notifyTaskpadSlots() {
  taskpadSlotListeners.forEach((listener) => listener());
}

function useTaskpadSlotActive() {
  const slotId = useId();
  const [active, setActive] = useState(false);

  useLayoutEffect(() => {
    const sync = () => {
      setActive(taskpadSlotStack[taskpadSlotStack.length - 1] === slotId);
    };
    taskpadSlotListeners.add(sync);
    taskpadSlotStack.push(slotId);
    notifyTaskpadSlots();
    sync();
    return () => {
      taskpadSlotListeners.delete(sync);
      const index = taskpadSlotStack.lastIndexOf(slotId);
      if (index !== -1) taskpadSlotStack.splice(index, 1);
      notifyTaskpadSlots();
    };
  }, [slotId]);

  return active;
}

export default function TaskpadSheet({
  mainId,
  subId,
  scope: scopeProp,
  projectCode: projectCodeProp,
  projectName: projectNameProp,
  workerId: workerIdProp,
  menuItems: menuItemsProp = [],
  alwaysShow = false,
}) {
  const slotActive = useTaskpadSlotActive();
  const { t } = useGuiT();
  const {
    isOpen,
    mode,
    taskContent,
    setTaskContent,
    projectLogFile,
    taskMeta,
    activeWorkerId,
    managerPanelOpen,
    setManagerPanelOpen,
    projectCode: ctxProjectCode,
    projectName: ctxProjectName,
    scopeMenuItems,
    defaultSection,
    openWorkerTaskpad,
    closeTaskpad,
    getWorker,
    getManagerView,
    addWorkerTask,
  } = useTaskpad();

  const projectCode = projectCodeProp || ctxProjectCode;
  const projectName = projectNameProp || ctxProjectName;

  const resolvedWorkerId = useMemo(
    () =>
      workerIdProp ||
      resolveWorkerIdFromContext({
        mainId,
        subId,
        projectCode,
        scope: scopeProp,
      }),
    [workerIdProp, mainId, subId, projectCode, scopeProp]
  );

  const worker = getWorker(resolvedWorkerId);
  const workerScope = worker?.scope || scopeProp || TASKPAD_SCOPES.SECTION;
  const isProjectScope = workerScope === TASKPAD_SCOPES.PROJECT;
  const isManager = isManagerScope(workerScope);
  const managerView = isManager ? getManagerView(resolvedWorkerId) : null;
  const parentWorker = worker?.parentWorkerId ? getWorker(worker.parentWorkerId) : null;

  useTaskpadWorkerRegistration({
    workerId: resolvedWorkerId,
    scope: workerScope,
    sectionId: worker?.sectionId || mainId || null,
    projectCode: worker?.projectCode || projectCode || null,
    label:
      worker?.label ||
      (isProjectScope ? projectName || projectCode : null) ||
      undefined,
  });

  const [targetSection, setTargetSection] = useState('general');
  const [showManagerPanel, setShowManagerPanel] = useState(false);

  const targetItems = useMemo(() => {
    if (menuItemsProp.length) {
      return menuItemsProp.map((item) => ({
        ...item,
        label: isProjectScope
          ? t(`workspace.${item.id}`, item.label)
          : item.label,
      }));
    }

    if (isProjectScope) {
      const items = scopeMenuItems?.length
        ? scopeMenuItems
        : [{ id: 'log', label: t('taskpad.projectLog') }];
      return items.map((item) => ({
        ...item,
        label: t(`workspace.${item.id}`, item.label),
      }));
    }

    if (workerScope === TASKPAD_SCOPES.CENTRAL) {
      return centralMenuItems().map((item) => ({
        ...item,
        label:
          item.id === 'coordination' || item.id === 'priorities'
            ? t(`taskpad.central.${item.id}`, item.label)
            : t(`navMain.${item.id}.label`, item.label),
      }));
    }

    if (workerScope === TASKPAD_SCOPES.PROJECTS_HUB) {
      return projectsHubMenuItems().map((item) => ({
        ...item,
        label: t(`taskpad.projectsHub.${item.id}`, item.label),
      }));
    }

    const sectionId = worker?.sectionId || mainId;
    return sectionMenuItems(sectionId).map((item) => ({
      ...item,
      label: t(`navMain.${sectionId}.children.${item.id}`, item.label),
    }));
  }, [
    menuItemsProp,
    isProjectScope,
    scopeMenuItems,
    workerScope,
    worker?.sectionId,
    mainId,
    t,
  ]);

  useEffect(() => {
    if (!isOpen || mode !== 'quick') return;
    if (activeWorkerId !== resolvedWorkerId) return;
    const preferred =
      taskMeta?.section || defaultSection || targetItems[0]?.id || 'general';
    if (targetItems.some((item) => item.id === preferred)) {
      setTargetSection(preferred);
    } else {
      setTargetSection(targetItems[0]?.id || 'general');
    }
  }, [
    isOpen,
    mode,
    activeWorkerId,
    resolvedWorkerId,
    taskMeta?.section,
    defaultSection,
    targetItems,
  ]);

  useEffect(() => {
    setShowManagerPanel(managerPanelOpen && isManager);
  }, [managerPanelOpen, isManager]);

  const isProjectLog = isOpen && mode === 'project_log' && projectLogFile;
  const logExt = isProjectLog
    ? inferExtension(projectLogFile.name, projectLogFile.extension)
    : '';
  const logEditable = EDITABLE_LOG_EXTS.has(logExt);

  const scopeBadge = useMemo(() => {
    if (workerScope === TASKPAD_SCOPES.CENTRAL) return t('taskpad.scope.central');
    if (workerScope === TASKPAD_SCOPES.PROJECTS_HUB) return t('taskpad.scope.projectsHub');
    if (isProjectScope) return projectCode;
    return worker?.sectionId || mainId || t('taskpad.scope.section');
  }, [workerScope, isProjectScope, projectCode, worker?.sectionId, mainId, t]);

  const scopeLabel = useMemo(() => {
    if (workerScope === TASKPAD_SCOPES.CENTRAL) return t('taskpad.centralTitle');
    if (workerScope === TASKPAD_SCOPES.PROJECTS_HUB) return t('taskpad.projectsHubTitle');
    if (isProjectScope) {
      return `${t('taskpad.projectWorkspace')} · ${projectName || projectCode}`;
    }
    return `${t('taskpad.sectionTitle')} · ${worker?.label || mainId || ''}`;
  }, [workerScope, isProjectScope, projectName, projectCode, worker?.label, mainId, t]);

  const parentLabel = useMemo(() => {
    if (!parentWorker) return null;
    if (parentWorker.scope === TASKPAD_SCOPES.CENTRAL) return t('taskpad.managedByCentral');
    if (parentWorker.scope === TASKPAD_SCOPES.PROJECTS_HUB) {
      return t('taskpad.managedByProjectsHub');
    }
    return null;
  }, [parentWorker, t]);

  const workerTasks = worker?.tasks || [];

  const handleOpen = () => {
    openWorkerTaskpad(resolvedWorkerId);
    if (isManager) setShowManagerPanel(true);
  };

  const handleSave = () => {
    addWorkerTask(resolvedWorkerId, {
      section: targetSection,
      text: taskContent,
      filePath: taskMeta?.filePath,
      fileName: taskMeta?.fileName,
    });
    closeTaskpad();
  };

  const handleOpenChild = (childWorkerId) => {
    setShowManagerPanel(false);
    setManagerPanelOpen(false);
    openWorkerTaskpad(childWorkerId);
  };

  const handleOpenParent = () => {
    if (!parentWorker) return;
    setShowManagerPanel(isManagerScope(parentWorker.scope));
    openWorkerTaskpad(parentWorker.workerId);
  };

  const isThisWorker = activeWorkerId === resolvedWorkerId;
  const showCollapsed = (alwaysShow || slotActive) && !isOpen;
  const showOpen = isOpen && isThisWorker;

  if (!showCollapsed && !showOpen) return null;

  return (
    <div className={`taskpad-dock${showOpen ? ' taskpad-dock--open' : ''}`}>
      {!showOpen ? (
        <div className="taskpad-dock-collapsed">
          <button
            type="button"
            className="taskpad-dock-toggle"
            onClick={handleOpen}
            aria-expanded={false}
            title={scopeLabel}
          >
            <Plus size={14} aria-hidden />
            <span>{t('taskpad.title')}</span>
            <span
              className={`taskpad-dock-scope-badge${
                workerScope === TASKPAD_SCOPES.CENTRAL
                  ? ' taskpad-dock-scope-badge--global'
                  : ''
              }`}
            >
              {scopeBadge}
            </span>
            <ChevronDown size={14} className="taskpad-dock-chevron" aria-hidden />
          </button>
        </div>
      ) : (
        <div
          className={`taskpad-dock-panel${isProjectLog ? ' taskpad-dock-panel--project-log' : ''}${
            showManagerPanel ? ' taskpad-dock-panel--manager' : ''
          }`}
          role="dialog"
          aria-label={isProjectLog ? t('taskpad.projectLog') : t('taskpad.quickCapture')}
        >
          <div className="taskpad-dock-header">
            <div className="taskpad-dock-heading">
              <h3 className="taskpad-dock-title">
                {isProjectLog ? (
                  <>
                    <BookOpen size={16} aria-hidden /> {t('taskpad.projectLog')}
                  </>
                ) : showManagerPanel && isManager ? (
                  <>
                    <GitBranch size={16} aria-hidden /> {t('taskpad.managerMode')}
                  </>
                ) : (
                  <>
                    <Plus size={16} aria-hidden /> {t('taskpad.quickCapture')}
                  </>
                )}
              </h3>
              <p className="taskpad-dock-scope text-caption muted">{scopeLabel}</p>
              {parentLabel ? (
                <button
                  type="button"
                  className="taskpad-dock-parent-link text-caption"
                  onClick={handleOpenParent}
                >
                  {parentLabel}
                </button>
              ) : null}
            </div>
            <div className="taskpad-dock-header-actions">
              {isManager ? (
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={() => setShowManagerPanel((v) => !v)}
                >
                  {showManagerPanel ? t('taskpad.workerView') : t('taskpad.managerView')}
                </button>
              ) : null}
              <button
                type="button"
                className="btn btn-sm btn-secondary taskpad-dock-close"
                onClick={closeTaskpad}
                aria-label={t('taskpad.close')}
              >
                <ChevronUp size={14} aria-hidden />
                <span>{t('taskpad.collapse')}</span>
              </button>
            </div>
          </div>

          <div className="taskpad-dock-body">
            {isProjectLog ? (
              <div className="taskpad-dock-editor">
                <p className="text-caption muted taskpad-dock-path">
                  {projectLogFile.name}
                  <span> · {projectLogFile.path}</span>
                </p>
                {logEditable ? (
                  <LazyDataPadEditor
                    projectCode={projectLogFile.projectCode}
                    relativePath={projectLogFile.path}
                    fileName={projectLogFile.name}
                    sectionLabel={t('taskpad.projectLog')}
                    initialContent={projectLogFile.excerpt || ''}
                    defaultEditMode
                    editorHeight={TASKPAD_EDITOR_HEIGHT}
                    onClose={closeTaskpad}
                  />
                ) : (
                  <div className="panel taskpad-dock-note">
                    <p className="text-footnote" style={{ margin: 0 }}>
                      {t('taskpad.binaryFileHint', '', { ext: logExt || 'binary' })}
                    </p>
                  </div>
                )}
              </div>
            ) : showManagerPanel && isManager && managerView ? (
              <div className="taskpad-dock-manager">
                <p className="text-caption muted">{t('taskpad.managerHint')}</p>
                <ul className="taskpad-dock-worker-list">
                  {managerView.children.map((child) => (
                    <li key={child.workerId}>
                      <button
                        type="button"
                        className="taskpad-dock-worker-item"
                        onClick={() => handleOpenChild(child.workerId)}
                      >
                        <span className="taskpad-dock-worker-label">{child.label}</span>
                        <span className="taskpad-dock-worker-meta text-caption muted">
                          {child.tasks.length} {t('taskpad.taskCount')}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
                {managerView.children.length === 0 ? (
                  <p className="text-footnote muted">{t('taskpad.noWorkers')}</p>
                ) : null}
              </div>
            ) : (
              <div className="taskpad-dock-capture">
                {taskMeta?.filePath ? (
                  <p className="text-caption muted taskpad-dock-path">
                    {taskMeta.fileName || taskMeta.filePath}
                    <span> · {taskMeta.filePath}</span>
                    {taskMeta.projectCode ? (
                      <span> · {taskMeta.projectCode}</span>
                    ) : null}
                  </p>
                ) : null}
                {workerTasks.length > 0 ? (
                  <div className="taskpad-dock-task-list">
                    <p className="text-caption muted">{t('taskpad.recentTasks')}</p>
                    <ul>
                      {workerTasks.slice(0, 5).map((task) => (
                        <li key={task.id} className="taskpad-dock-task-item text-footnote">
                          <span className="taskpad-dock-task-section">{task.section}</span>
                          {task.text}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <div className="taskpad-dock-capture-row">
                  <div className="form-group taskpad-dock-field">
                    <label className="form-label" htmlFor={`taskpad-target-${resolvedWorkerId}`}>
                      {t('taskpad.targetArea')}
                    </label>
                    <select
                      id={`taskpad-target-${resolvedWorkerId}`}
                      className="form-select"
                      value={targetSection}
                      onChange={(e) => setTargetSection(e.target.value)}
                    >
                      {targetItems.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group taskpad-dock-field taskpad-dock-field--grow">
                    <label className="form-label" htmlFor={`taskpad-note-${resolvedWorkerId}`}>
                      {t('taskpad.noteLabel')}
                    </label>
                    <textarea
                      id={`taskpad-note-${resolvedWorkerId}`}
                      className="form-textarea taskpad-dock-textarea"
                      placeholder={t('taskpad.notePlaceholder')}
                      value={taskContent}
                      onChange={(e) => setTaskContent(e.target.value)}
                    />
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary taskpad-dock-save"
                    onClick={handleSave}
                    disabled={!taskContent.trim()}
                  >
                    {t('taskpad.save')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
