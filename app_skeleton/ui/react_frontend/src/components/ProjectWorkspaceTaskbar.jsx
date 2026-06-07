import { useEffect, useMemo, useRef, useState } from 'react';
import { Edit3, RefreshCw, Save, X } from 'lucide-react';
import DigitalTwinPanel from './DigitalTwinPanel.jsx';
import ProjectRegistryEditor from './ProjectRegistryEditor.jsx';
import TaskpadSheet from './TaskpadSheet.jsx';
import { useGuiT } from '../i18n/useGuiT.js';

const EDIT_TARGETS = [
  { id: 'overview-profile', workspaceTab: 'overview', twinSection: 'overview', labelKey: 'taskbar.overviewProfile' },
  { id: 'registry', workspaceTab: 'overview', isRegistry: true, labelKey: 'taskbar.registry' },
  { id: 'plan-activity', workspaceTab: 'plan', twinSection: 'timeline', labelKey: 'taskbar.planActivity' },
  { id: 'data-catalog', workspaceTab: 'data', twinSection: 'catalog', labelKey: 'taskbar.dataCatalog' },
  { id: 'methods-protocols', workspaceTab: 'methods', twinSection: 'protocols', labelKey: 'taskbar.protocols' },
  { id: 'methods-files', workspaceTab: 'methods', twinSection: 'content', labelKey: 'taskbar.filesFigures' },
  { id: 'writing-abstracts', workspaceTab: 'writing', twinSection: 'abstracts', labelKey: 'taskbar.writingAbstracts' },
  { id: 'log-activity', workspaceTab: 'log', twinSection: 'timeline', labelKey: 'taskbar.logActivity' },
];

function defaultTargetForTab(workspaceMenu) {
  return EDIT_TARGETS.find((t) => t.workspaceTab === workspaceMenu) || EDIT_TARGETS[0];
}

export default function ProjectWorkspaceTaskbar({
  workspaceMenu,
  menuItems,
  projectCode,
  projectData,
  onRegistrySaved,
  twin,
  twinLoading,
  twinSaving,
  twinError,
  onSave,
  refreshTwin,
  API_URL,
  onWorkspaceMenuChange,
}) {
  const { t } = useGuiT();
  const panelRef = useRef(null);
  const registryRef = useRef(null);
  const [editTargetId, setEditTargetId] = useState(() => defaultTargetForTab(workspaceMenu).id);
  const [editing, setEditing] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);

  const editTarget = useMemo(
    () => EDIT_TARGETS.find((item) => item.id === editTargetId) || EDIT_TARGETS[0],
    [editTargetId],
  );

  const targetOptions = useMemo(
    () =>
      EDIT_TARGETS.map((item) => ({
        id: item.id,
        label: t(item.labelKey, item.label || item.id),
      })),
    [t],
  );

  useEffect(() => {
    const match = defaultTargetForTab(workspaceMenu);
    setEditTargetId(match.id);
    setEditing(false);
    setSaveMsg(null);
  }, [workspaceMenu, twin?.edited_at]);

  const hasEditableContent = Boolean(
    editTarget?.isRegistry ? projectData : twin && editTarget?.twinSection,
  );

  const handleStartEdit = () => {
    setEditing(true);
    setSaveMsg(null);
  };

  useEffect(() => {
    if (!editing || editTarget?.isRegistry) return;
    panelRef.current?.startEdit();
  }, [editing, editTarget?.id, twin?.edited_at]);

  const handleCancel = () => {
    if (!editTarget?.isRegistry) {
      panelRef.current?.cancelEdit();
    }
    setEditing(false);
    setSaveMsg(null);
  };

  const handleSave = async () => {
    try {
      if (editTarget?.isRegistry) {
        await registryRef.current?.save();
      } else {
        await panelRef.current?.save();
      }
      setEditing(false);
      setSaveMsg(t('taskbar.saved', 'Saved'));
    } catch {
      setSaveMsg(t('taskbar.saveFailed', 'Save failed'));
    }
  };

  const handleTargetChange = (nextId) => {
    setEditTargetId(nextId);
    setEditing(false);
    setSaveMsg(null);
    const next = EDIT_TARGETS.find((item) => item.id === nextId);
    if (next?.workspaceTab && onWorkspaceMenuChange) {
      onWorkspaceMenuChange(next.workspaceTab);
    }
  };

  return (
    <div className="project-workspace-taskbar">
      <div className="project-workspace-taskbar__row">
        <div className="project-workspace-taskbar__section-picker form-group">
          <label className="form-label" htmlFor="workspace-edit-section">
            {t('taskbar.selectSection', 'Section')}
          </label>
          <select
            id="workspace-edit-section"
            className="form-select project-workspace-taskbar__section-select"
            value={editTargetId}
            onChange={(e) => handleTargetChange(e.target.value)}
          >
            {targetOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="project-workspace-taskbar__actions">
          {hasEditableContent ? (
            !editing ? (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleStartEdit}
                disabled={twinLoading && !editTarget?.isRegistry}
              >
                <Edit3 size={14} aria-hidden />
                {t('taskbar.edit', 'Edit')}
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleSave}
                  disabled={twinSaving}
                >
                  <Save size={14} aria-hidden />
                  {twinSaving ? t('taskbar.saving', 'Saving…') : t('taskbar.save', 'Save')}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleCancel}
                  disabled={twinSaving}
                >
                  <X size={14} aria-hidden />
                  {t('taskbar.cancel', 'Cancel')}
                </button>
              </>
            )
          ) : (
            <span className="project-workspace-taskbar__section-label text-footnote muted">
              {t('taskbar.scanFirst', 'Scan the project folder to enable editing.')}
            </span>
          )}

          {refreshTwin ? (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={refreshTwin}
              disabled={twinLoading}
              title={t('taskbar.rescan', 'Rescan project folder')}
            >
              <RefreshCw size={14} className={twinLoading ? 'spin' : undefined} aria-hidden />
            </button>
          ) : null}

          {saveMsg ? <span className="project-workspace-taskbar__status">{saveMsg}</span> : null}
          {twinSaving && !saveMsg ? (
            <span className="project-workspace-taskbar__status muted">
              {t('taskbar.saving', 'Saving…')}
            </span>
          ) : null}
          {twinError && !twinLoading ? (
            <span className="project-workspace-taskbar__status project-workspace-taskbar__status--error">
              {twinError}
            </span>
          ) : null}

          <div className="project-workspace-taskbar__taskpad">
            <TaskpadSheet
              scope="project"
              projectCode={projectCode}
              projectName={projectData?.project_name}
              menuItems={menuItems}
              alwaysShow
            />
          </div>
        </div>
      </div>

      {editing && hasEditableContent ? (
        <div className="project-workspace-taskbar__editor panel">
          {editTarget?.isRegistry ? (
            <ProjectRegistryEditor
              ref={registryRef}
              projectData={projectData}
              API_URL={API_URL}
              onSaved={onRegistrySaved}
            />
          ) : (
            <DigitalTwinPanel
              ref={panelRef}
              twin={twin}
              onSave={onSave}
              saving={twinSaving}
              section={editTarget.twinSection}
              projectCode={projectCode}
              API_URL={API_URL}
              hideToolbar
              editing={editing}
              onEditingChange={setEditing}
            />
          )}
        </div>
      ) : null}
    </div>
  );
}
