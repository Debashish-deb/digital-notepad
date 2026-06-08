import { normalizeRelPath } from './folderBrowserUtils.js';
import { stripNestedProjectRoot } from './projectDocumentCategories.js';
import { isProjectLogFile } from './projectLogUtils.js';
import { apiGet } from '@/services/client.js';

function normPath(path, projectCode = '') {
  return stripNestedProjectRoot(normalizeRelPath(path), projectCode);
}

/** Try twin-relative and nested path variants when resolving on disk. */
export function buildLogPathCandidates(path, twin) {
  const code = twin?.project_code || twin?.identity?.project_code || '';
  const base = normPath(path, code);
  const candidates = new Set();
  if (base) candidates.add(base);

  const root = (twin?.content_root || '').replace(/\\/g, '/').replace(/\/$/, '');
  if (root && base && !base.startsWith(`${root}/`)) {
    candidates.add(`${root}/${base}`);
  }
  if (root && base.startsWith(`${root}/`)) {
    candidates.add(base.slice(root.length + 1));
  }

  const parts = base.split('/').filter(Boolean);
  if (parts.length > 1) {
    candidates.add(parts[parts.length - 1]);
  }

  return [...candidates];
}

function chunksTextFromTwin(twin, targetPath) {
  const parts = [];
  for (const chunk of twin?.vector_chunks || []) {
    const src = normPath(chunk.source_file || '', twin?.project_code);
    if (src !== targetPath) continue;
    parts.push([chunk.chunk_index ?? 0, chunk.text || '']);
  }
  if (!parts.length) return null;
  parts.sort((a, b) => a[0] - b[0]);
  const text = parts.map(([, t]) => t).filter(Boolean).join('\n\n').trim();
  return text || null;
}

function textFromDocumentIndex(twin, targetPath) {
  for (const doc of twin?.document_index || []) {
    const p = normPath(doc.path || doc.relative_path || '', twin?.project_code);
    if (p !== targetPath) continue;
    const excerpt = (doc.excerpt || doc.text || '').trim();
    const title = (doc.title || '').trim();
    if (!excerpt && !title) continue;
    if (title && title !== excerpt.slice(0, Math.min(200, excerpt.length))) {
      return excerpt ? `${title}\n\n${excerpt}` : title;
    }
    return excerpt || title;
  }
  return null;
}

function excerptFromLibrary(twin, logFile) {
  const target = normPath(logFile?.path, twin?.project_code);
  for (const section of twin?.content_library?.sections || []) {
    for (const key of [
      'documents',
      'figures',
      'presentations',
      'data_files',
      'text_files',
      'videos',
      'code_scripts',
    ]) {
      for (const item of section[key] || []) {
        const p = normPath(item.path, twin?.project_code);
        if (p === target && (item.excerpt || item.text)) {
          return (item.excerpt || item.text || '').trim();
        }
      }
    }
    for (const doc of section.documents || []) {
      const p = normPath(doc.path, twin?.project_code);
      if (p === target && (doc.excerpt || doc.text)) {
        return (doc.excerpt || doc.text || '').trim();
      }
    }
  }
  return null;
}

/** Reconstruct log body from processed twin without hitting the API. */
export function getProjectLogContentFromTwin(twin, logFile) {
  if (!twin || !logFile?.path) return null;

  const candidates = buildLogPathCandidates(logFile.path, twin);
  for (const path of candidates) {
    const fromChunks = chunksTextFromTwin(twin, path);
    if (fromChunks) {
      return { content: fromChunks, path, source: 'processed_chunks' };
    }
  }

  for (const path of candidates) {
    const fromIndex = textFromDocumentIndex(twin, path);
    if (fromIndex) {
      return { content: fromIndex, path, source: 'document_index' };
    }
  }

  const excerpt = excerptFromLibrary(twin, logFile);
  if (excerpt) {
    return { content: excerpt, path: logFile.path, source: 'content_library' };
  }

  return null;
}

async function fetchPreviewText(API_URL, projectCode, relativePath) {
  const params = new URLSearchParams({
    project_code: projectCode,
    relative_path: relativePath,
  });
  try {
    const data = await apiGet(`/api/project-files/preview-text?${params}`);
    const content = (data?.content || '').trim();
    if (!content) return null;
    return { content, path: data?.path || relativePath, source: data?.source || 'preview' };
  } catch {
    return null;
  }
}

async function fetchReadText(API_URL, projectCode, relativePath) {
  const params = new URLSearchParams({
    project_code: projectCode,
    relative_path: relativePath,
  });
  try {
    const data = await apiGet(`/api/project-files/read?${params}`);
    const content = (data?.content || '').trim();
    if (!content) return null;
    return { content, path: data?.path || relativePath, source: 'disk_text' };
  } catch {
    return null;
  }
}

async function fetchExtractText(API_URL, projectCode, relativePath) {
  const params = new URLSearchParams({
    project_code: projectCode,
    relative_path: relativePath,
  });
  try {
    const data = await apiGet(`/api/project-files/extract?${params}`);
    const content = (data?.content || '').trim();
    if (!content) return null;
    return { content, path: data?.path || relativePath, source: 'live_extract' };
  } catch {
    return null;
  }
}

/**
 * Load project log text with full restoration chain:
 * processed twin chunks → document index → API preview → disk read → extract.
 */
export async function fetchProjectLogContent({ projectCode, logFile, twin, API_URL }) {
  if (!logFile?.path) return { content: '', path: null, source: null };

  const offline = getProjectLogContentFromTwin(twin, logFile);
  if (offline?.content) return offline;

  if (!API_URL) return offline || { content: '', path: logFile.path, source: null };

  const candidates = buildLogPathCandidates(logFile.path, twin);
  for (const path of candidates) {
    try {
      const preview = await fetchPreviewText(API_URL, projectCode, path);
      if (preview) return preview;
    } catch {
      /* try next */
    }
    try {
      const read = await fetchReadText(API_URL, projectCode, path);
      if (read) return read;
    } catch {
      /* try next */
    }
    try {
      const extract = await fetchExtractText(API_URL, projectCode, path);
      if (extract) return extract;
    } catch {
      /* try next */
    }
  }

  return offline || { content: '', path: logFile.path, source: null };
}

/** List all project log files referenced in a twin (for diagnostics). */
export function listProjectLogFilesInTwin(twin) {
  const seen = new Set();
  const files = [];

  const add = (item, path) => {
    const p = normPath(path || item?.path, twin?.project_code);
    if (!p || seen.has(p) || !isProjectLogFile(p)) return;
    seen.add(p);
    files.push({ ...item, path: p, name: item?.name || p.split('/').pop() });
  };

  for (const section of twin?.content_library?.sections || []) {
    for (const key of ['documents', 'figures', 'presentations', 'data_files', 'text_files', 'videos', 'code_scripts']) {
      for (const item of section[key] || []) add(item, item.path);
    }
    for (const doc of section.documents || []) add(doc, doc.path);
  }
  for (const doc of twin?.document_index || []) add(doc, doc.path || doc.relative_path);
  for (const chunk of twin?.vector_chunks || []) {
    if (isProjectLogFile(chunk.source_file)) add({ name: chunk.source_file?.split('/').pop() }, chunk.source_file);
  }

  return files;
}
