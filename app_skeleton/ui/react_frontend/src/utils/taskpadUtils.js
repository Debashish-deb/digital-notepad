/** Map content-library folder ids to workspace tab ids. */
export const FOLDER_SECTION_TO_WORKSPACE = {
  management: 'plan',
  methods: 'methods',
  data_figures: 'data',
  writing: 'writing',
  meetings: 'log',
  archive: 'archive',
  guidelines: 'overview',
  root: 'overview',
};

export function folderSectionToWorkspaceTab(folderId) {
  if (!folderId) return 'overview';
  return FOLDER_SECTION_TO_WORKSPACE[folderId] || 'overview';
}

export function normalizeTaskMeta(meta = {}) {
  const out = {};
  if (meta.workerId) out.workerId = meta.workerId;
  if (meta.projectCode) out.projectCode = meta.projectCode;
  if (meta.section) out.section = meta.section;
  if (meta.filePath) out.filePath = meta.filePath;
  if (meta.fileName) out.fileName = meta.fileName;
  return out;
}

export function mergeTaskMeta(scope, projectCode, meta = {}, workerId = null) {
  const merged = normalizeTaskMeta(meta);
  if (workerId && !merged.workerId) merged.workerId = workerId;
  if (scope === 'project' && projectCode && !merged.projectCode) {
    merged.projectCode = projectCode;
  }
  return merged;
}
