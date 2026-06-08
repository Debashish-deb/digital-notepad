import { normalizeRelPath } from './folderBrowserUtils.js';

const ASSET_KEYS = [
  'documents',
  'figures',
  'presentations',
  'data_files',
  'text_files',
  'videos',
  'code_scripts',
];

const PROJECT_LOG_RE = /project[_\s-]?log/i;

export function isProjectLogFile(pathOrName) {
  const base = (pathOrName || '').split('/').pop() || pathOrName || '';
  return PROJECT_LOG_RE.test(base);
}

function editabilityScore(path) {
  const ext = (path.match(/(\.[^.]+)$/)?.[1] || '').toLowerCase();
  if (ext === '.md') return 0;
  if (ext === '.txt') return 1;
  if (ext === '.html' || ext === '.rtf') return 2;
  if (ext === '.docx' || ext === '.doc') return 3;
  return 4;
}

function pushCandidate(candidates, seen, item, path) {
  const norm = normalizeRelPath(path || item.path || item.relative_path);
  if (!norm || seen.has(norm) || !isProjectLogFile(norm)) return;
  seen.add(norm);
  candidates.push({
    ...item,
    path: norm,
    name: item.name || norm.split('/').pop(),
    extension: item.extension || (norm.match(/(\.[^.]+)$/)?.[1] || ''),
  });
}

/** Find the primary project log file in a digital twin (prefers .md). */
export function findProjectLogFile(twin) {
  const candidates = [];
  const seen = new Set();

  for (const section of twin?.content_library?.sections || []) {
    for (const key of ASSET_KEYS) {
      for (const item of section[key] || []) {
        pushCandidate(candidates, seen, { ...item, section_label: section.label }, item.path);
      }
    }
    for (const doc of section.documents || []) {
      pushCandidate(candidates, seen, { ...doc, section_label: section.label }, doc.path);
    }
  }

  for (const entry of twin?.document_index || []) {
    pushCandidate(candidates, seen, entry, entry.path || entry.relative_path);
  }

  for (const row of twin?.data_assets?.folder_tree || []) {
    const path = row.path || row.relative_path || row.name;
    pushCandidate(candidates, seen, row, path);
  }

  if (!candidates.length) return null;
  candidates.sort((a, b) => editabilityScore(a.path) - editabilityScore(b.path));
  return candidates[0];
}
