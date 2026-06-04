const ASSET_KEYS = ['figures', 'documents', 'presentations', 'data_files', 'text_files', 'videos'];

/** Lifecycle order for standard project content sections (1 → archive). */
export const CONTENT_SECTION_ORDER = [
  'management',
  'methods',
  'data_figures',
  'writing',
  'meetings',
  'archive',
  'guidelines',
  'root',
];

export function formatFileSize(bytes) {
  if (bytes == null || bytes === 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatModifiedAt(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return '—';
  }
}

export function sectionSortKey(folder) {
  if (!folder) return 9999;
  if (folder.source === 'folder_tree') {
    const m = (folder.path || '').match(/^(\d+)[_.\s-]/);
    if (m) return 800 + parseInt(m[1], 10);
    return 850 + (folder.path || '').length;
  }
  const idx = CONTENT_SECTION_ORDER.indexOf(folder.id);
  if (idx >= 0) return idx;
  const labelMatch = (folder.label || '').match(/^(\d+)[_.\s-]/);
  if (labelMatch) return parseInt(labelMatch[1], 10) - 1;
  return 400 + (folder.label || folder.id || '').toLowerCase().charCodeAt(0);
}

export function sortFolderEntries(folders) {
  return [...folders].sort((a, b) => {
    const diff = sectionSortKey(a) - sectionSortKey(b);
    if (diff !== 0) return diff;
    return (a.label || '').localeCompare(b.label || '');
  });
}

export function sortProjectFiles(files, sortBy = 'name') {
  const list = [...files];
  const cmpStr = (a, b) => (a || '').localeCompare(b || '', undefined, { sensitivity: 'base' });
  switch (sortBy) {
    case 'type':
      return list.sort((a, b) => {
        const ta = (a.extension || a.document_kind || '').toLowerCase();
        const tb = (b.extension || b.document_kind || '').toLowerCase();
        const d = cmpStr(ta, tb);
        return d !== 0 ? d : cmpStr(a.name, b.name);
      });
    case 'size':
      return list.sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0) || cmpStr(a.name, b.name));
    case 'modified':
      return list.sort((a, b) => {
        const da = a.modified_at ? new Date(a.modified_at).getTime() : 0;
        const db = b.modified_at ? new Date(b.modified_at).getTime() : 0;
        return db - da || cmpStr(a.name, b.name);
      });
    case 'name':
    default:
      return list.sort((a, b) => cmpStr(a.name, b.name));
  }
}

export function getFilePreviewStatus(file, twin, normPath) {
  const ext = (file?.extension || '').toLowerCase();
  if (getChunkTextForProjectFile(twin, normPath)) {
    return { state: 'extracted', label: 'Indexed chunks', tone: 'success' };
  }
  const doc = getDocumentIndexEntry(twin, normPath);
  if (doc?.excerpt) {
    return { state: 'extracted', label: 'Document index', tone: 'success' };
  }
  if (file?.extraction_status === 'extracted' || file?.extraction_status === 'success') {
    return { state: 'extracted', label: 'Extracted', tone: 'success' };
  }
  if (file?.excerpt) {
    return { state: 'metadata', label: 'Metadata excerpt', tone: 'accent' };
  }
  if (isTextPreviewable(ext)) {
    return { state: 'readable', label: 'Plain text', tone: 'accent' };
  }
  if (file?.previewable || isExtractPreviewable(ext)) {
    return { state: 'eligible', label: 'Extractable', tone: 'warning' };
  }
  return { state: 'none', label: 'Not indexed', tone: 'muted' };
}

export function collectFolderEntries(twin) {
  const lib = twin?.content_library;
  if (lib?.sections?.length) {
    return sortFolderEntries(
      lib.sections
        .filter((s) => s.total_files > 0)
        .map((s) => ({
          id: s.id,
          label: s.label,
          path: s.id,
          file_count: s.total_files,
          section: s,
          source: 'content_library',
        }))
    );
  }

  const tree = twin?.data_assets?.folder_tree || [];
  const entries = tree
    .filter((f) => f.path && f.path !== '.')
    .map((f) => ({
      id: f.path,
      label: f.path.split('/').pop() || f.path,
      path: f.path,
      file_count: f.file_count,
      categories: f.categories,
      source: 'folder_tree',
    }));

  if (entries.length) return sortFolderEntries(entries);

  return [];
}

export function filesForFolderEntry(entry) {
  if (!entry) return [];
  if (entry.section) {
    return ASSET_KEYS.flatMap((key) =>
      (entry.section[key] || []).map((item) => ({ ...item, asset_type: item.asset_type || key }))
    );
  }
  return [];
}

export function filesUnderTreePath(twin, folderPath) {
  const lib = twin?.content_library;
  if (!lib?.sections?.length || !folderPath) return [];

  const prefix = folderPath.replace(/\/$/, '');
  const out = [];
  for (const section of lib.sections) {
    for (const key of ASSET_KEYS) {
      for (const item of section[key] || []) {
        const p = (item.path || '').replace(/\\/g, '/');
        if (p === prefix || p.startsWith(`${prefix}/`)) {
          out.push({ ...item, asset_type: item.asset_type || key, section_label: section.label });
        }
      }
    }
  }
  return out;
}

const TEXT_READABLE_EXTENSIONS = new Set([
  '.md', '.txt', '.py', '.r', '.sh', '.json', '.yaml', '.yml', '.sql', '.csv', '.tsv',
  '.html', '.xml', '.toml', '.ini', '.cfg', '.log', '.ipynb',
]);

const EXTRACT_PREVIEW_EXTENSIONS = new Set([
  '.pdf', '.docx', '.doc', '.dotx', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.rtf',
]);

const ASSET_PREVIEW_EXTENSIONS = new Set([
  '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.tif', '.tiff',
]);

export function normalizeRelPath(path) {
  return (path || '').replace(/\\/g, '/').replace(/^\/+/, '');
}

export function isTextPreviewable(ext) {
  return TEXT_READABLE_EXTENSIONS.has((ext || '').toLowerCase());
}

export function isExtractPreviewable(ext) {
  return EXTRACT_PREVIEW_EXTENSIONS.has((ext || '').toLowerCase());
}

export function isAssetPreviewable(ext) {
  return ASSET_PREVIEW_EXTENSIONS.has((ext || '').toLowerCase());
}

export function getDocumentIndexEntry(twin, relativePath) {
  if (!twin?.document_index?.length) return null;
  const norm = normalizeRelPath(relativePath);
  return twin.document_index.find((d) => normalizeRelPath(d.path) === norm) || null;
}

export function getChunkTextForProjectFile(twin, relativePath) {
  if (!twin?.vector_chunks?.length || !relativePath) return null;
  const norm = normalizeRelPath(relativePath);
  const parts = twin.vector_chunks
    .filter((c) => normalizeRelPath(c.source_file) === norm)
    .sort((a, b) => (a.chunk_index || 0) - (b.chunk_index || 0));
  if (!parts.length) return null;
  return parts.map((c) => c.text || '').filter(Boolean).join('\n\n');
}
