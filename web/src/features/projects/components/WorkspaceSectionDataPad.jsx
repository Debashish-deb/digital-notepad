import { useEffect, useMemo, useState } from 'react';
import { HardDrive, Lock } from 'lucide-react';
import LazyDataPadEditor from './LazyDataPadEditor.jsx';
import {
  listWorkspaceTabEditableFiles,
  resolveWorkspaceTabPrimaryFile,
  workspaceTabSectionLabel,
} from '@/lib/workspaceDatapadUtils.js';
import { getProjectLogContentFromTwin } from '@/lib/projectLogContent.js';
import { isProjectLogFile } from '@/lib/projectLogUtils.js';
import { isProjectReadmePath } from '@/lib/projectReadmeUtils.js';
import { useGuiT } from '@/i18n/useGuiT.js';

export default function WorkspaceSectionDataPad({
  twin,
  projectCode,
  API_URL,
  workspaceTab,
  lockFile = false,
  preferredPath = null,
  onReadmeSaved,
}) {
  const { t } = useGuiT();
  const editableFiles = useMemo(
    () => listWorkspaceTabEditableFiles(twin, workspaceTab, projectCode),
    [twin, workspaceTab, projectCode, twin?.processed_at],
  );

  const defaultFile = useMemo(
    () => resolveWorkspaceTabPrimaryFile(twin, workspaceTab, projectCode, preferredPath),
    [twin, workspaceTab, projectCode, preferredPath, twin?.processed_at],
  );

  const [activePath, setActivePath] = useState(defaultFile?.path || null);

  useEffect(() => {
    if (lockFile && defaultFile?.path) {
      setActivePath(defaultFile.path);
      return;
    }
    if (preferredPath && editableFiles.some((f) => f.path === preferredPath)) {
      setActivePath(preferredPath);
      return;
    }
    if (defaultFile?.path) setActivePath(defaultFile.path);
    else setActivePath(editableFiles[0]?.path || null);
  }, [lockFile, defaultFile?.path, preferredPath, editableFiles, workspaceTab, twin?.processed_at]);

  const activeFile = editableFiles.find((f) => f.path === activePath) || defaultFile;
  const sectionLabel = workspaceTabSectionLabel(workspaceTab);

  const initialLogContent = useMemo(() => {
    if (!activeFile?.path || !twin) return '';
    if (workspaceTab === 'log' || isProjectLogFile(activeFile.path)) {
      return getProjectLogContentFromTwin(twin, activeFile)?.content || '';
    }
    const doc = twin.document_index?.find(
      (d) => (d.path || d.relative_path) === activeFile.path,
    );
    return doc?.excerpt || activeFile.excerpt || '';
  }, [activeFile?.path, twin, workspaceTab]);

  if (!twin) {
    return (
      <section className="panel workspace-section-datapad">
        <p className="text-footnote muted">Scan the project folder to enable the Data Pad editor.</p>
      </section>
    );
  }

  if (!activeFile?.path) {
    return (
      <section className="panel workspace-section-datapad">
        <header className="workspace-section-datapad__header">
          <h3 className="workspace-subpanel-title">
            <HardDrive size={16} aria-hidden /> Data Pad editor
          </h3>
        </header>
        <p className="text-footnote muted">
          {workspaceTab === 'log'
            ? 'No project log file found. Add a file named like Project_log.md at the project root, then rescan.'
            : `No editable files in the ${sectionLabel} section yet.`}
        </p>
      </section>
    );
  }

  return (
    <section className="panel workspace-section-datapad">
      <header className="workspace-section-datapad__header">
        <div>
          <h3 className="workspace-subpanel-title">
            <HardDrive size={16} aria-hidden /> Data Pad editor
          </h3>
          <p className="text-caption muted workspace-section-datapad__hint">
            {lockFile ? (
              <>
                <Lock size={12} aria-hidden /> Locked to {sectionLabel} —{' '}
                <code>{activeFile.name || activeFile.path}</code>
              </>
            ) : (
              <>Editing files in the {sectionLabel} section only.</>
            )}
          </p>
        </div>

        {!lockFile && editableFiles.length > 1 ? (
          <div className="form-group workspace-section-datapad__picker">
            <label className="form-label" htmlFor={`datapad-file-${workspaceTab}`}>
              {t('docs.sectionFile', 'Section file')}
            </label>
            <select
              id={`datapad-file-${workspaceTab}`}
              className="form-select"
              value={activePath || ''}
              onChange={(e) => setActivePath(e.target.value)}
            >
              {editableFiles.map((f) => (
                <option key={f.path} value={f.path}>
                  {f.display_title || f.name || f.path}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <span className="workspace-section-datapad__locked-name text-caption">
            <code>{activeFile.name || activeFile.path}</code>
          </span>
        )}
      </header>

      <LazyDataPadEditor
        key={`${projectCode}:${activeFile.path}:${twin?.processed_at || ''}`}
        projectCode={projectCode}
        relativePath={activeFile.path}
        fileName={activeFile.name || activeFile.path.split('/').pop()}
        sectionLabel={sectionLabel}
        initialContent={initialLogContent}
        defaultEditMode
        editorHeight="min(52vh, 520px)"
        onSaved={
          isProjectReadmePath(activeFile.path) && onReadmeSaved
            ? onReadmeSaved
            : undefined
        }
      />
    </section>
  );
}
