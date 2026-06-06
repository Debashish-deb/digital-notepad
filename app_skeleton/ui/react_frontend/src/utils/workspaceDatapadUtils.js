import { collectProjectDocuments } from './documentBrowserUtils.js';
import { normalizeRelPath } from './folderBrowserUtils.js';
import { getProjectTabDocumentConfig, projectDocumentTitle } from './projectDocumentCategories.js';
import { findProjectLogFile, isProjectLogFile } from './projectLogUtils.js';
import { inferExtension } from './fileTypeMeta.js';

const EDITABLE_EXTS = new Set(['.md', '.txt', '.html', '.rtf']);

export function isEditableWorkspacePath(path) {
  const ext = inferExtension((path || '').split('/').pop(), '');
  return EDITABLE_EXTS.has(ext);
}

/** All editable files belonging to a workspace tab. */
export function listWorkspaceTabEditableFiles(twin, workspaceTab, projectCode = '') {
  if (!twin) return [];
  const config = getProjectTabDocumentConfig(workspaceTab, [], projectCode);
  const docs = collectProjectDocuments(twin, {
    categorizePath: config.categorizePath,
    documentTitle: projectDocumentTitle,
    tabFilter: config.tabFilter,
  });

  const logFile = workspaceTab === 'log' ? findProjectLogFile(twin) : null;
  const merged = [...docs];
  if (logFile?.path && !merged.some((d) => d.path === logFile.path)) {
    merged.unshift({
      ...logFile,
      path: logFile.path,
      name: logFile.name || logFile.path.split('/').pop(),
      display_title: projectDocumentTitle(logFile),
      categoryId: 'project_log',
    });
  }

  return merged
    .filter((d) => d.path && isEditableWorkspacePath(d.path))
    .sort((a, b) => (a.path || '').localeCompare(b.path || ''));
}

/** Default file to open in the section-locked Data Pad for a tab. */
export function resolveWorkspaceTabPrimaryFile(twin, workspaceTab, projectCode = '', preferredPath = null) {
  const editable = listWorkspaceTabEditableFiles(twin, workspaceTab, projectCode);
  if (preferredPath && editable.some((d) => d.path === preferredPath)) {
    return editable.find((d) => d.path === preferredPath);
  }

  if (workspaceTab === 'log') {
    return findProjectLogFile(twin) || editable.find((d) => isProjectLogFile(d.path)) || editable[0] || null;
  }

  if (workspaceTab === 'overview') {
    const readme =
      editable.find((d) => /^readme/i.test(d.name || d.path.split('/').pop() || '')) ||
      editable.find((d) => !d.path.includes('/'));
    if (readme) return readme;
  }

  return editable[0] || null;
}

export function workspaceTabSectionLabel(workspaceTab) {
  const labels = {
    overview: 'Overview',
    plan: 'Plan',
    data: 'Data',
    methods: 'Methods',
    writing: 'Writing',
    log: 'Project log',
    archive: 'Archive',
  };
  return labels[workspaceTab] || 'Section';
}
