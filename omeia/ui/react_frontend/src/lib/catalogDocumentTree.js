/** Helpers for organizing static catalog.json documents into browsable folders. */

import { inferExtension } from './fileTypeMeta.js';

export function humanizeFolderLabel(name) {
  return String(name || '')
    .replace(/[_&]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function shortenFolderLabel(name, max = 52) {
  const label = String(name || '').trim();
  if (label.length <= max) return label;
  const beforeComma = label.split(',')[0]?.trim();
  if (beforeComma && beforeComma.length >= 14 && beforeComma.length < label.length) {
    return `${beforeComma}…`;
  }
  return `${label.slice(0, max - 1)}…`;
}

export function catalogDocFileName(doc) {
  const fromPath = doc.path?.split('/').filter(Boolean).pop();
  return fromPath || doc.title || 'Untitled';
}

export function catalogDocDisplayTitle(doc) {
  const fileName = catalogDocFileName(doc);
  const title = (doc.title || '').trim();
  if (!title || title === fileName) {
    return fileName.replace(/\.[^.]+$/, '') || fileName;
  }
  return title.replace(/\.[^.]+$/, '') || title;
}

export function catalogDocBreadcrumb(path) {
  const parts = String(path || '').split('/').filter(Boolean);
  if (parts.length <= 2) return null;
  return parts
    .slice(1, -1)
    .map(humanizeFolderLabel)
    .join(' › ');
}

/** Second-level folder within a top-level catalog group. */
export function catalogSubfolderKey(path) {
  const parts = String(path || '').split('/').filter(Boolean);
  if (parts.length <= 2) return '__direct__';
  return parts[1];
}

export function catalogTopFolder(path) {
  const parts = String(path || '').split('/').filter(Boolean);
  return parts[0] || 'Root Documents';
}

export function groupCatalogDocuments(docs) {
  const topMap = new Map();

  for (const doc of docs) {
    const top = catalogTopFolder(doc.path);
    if (!topMap.has(top)) {
      topMap.set(top, new Map());
    }
    const subMap = topMap.get(top);
    const subKey = catalogSubfolderKey(doc.path);
    if (!subMap.has(subKey)) subMap.set(subKey, []);
    subMap.get(subKey).push(doc);
  }

  return [...topMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([topFolder, subMap]) => {
      const subfolders = [...subMap.entries()]
        .sort(([a], [b]) => {
          if (a === '__direct__') return -1;
          if (b === '__direct__') return 1;
          return a.localeCompare(b);
        })
        .map(([subKey, files]) => ({
          id: subKey,
          label: subKey === '__direct__' ? 'Main folder' : humanizeFolderLabel(subKey),
          files: files.sort((a, b) => catalogDocDisplayTitle(a).localeCompare(catalogDocDisplayTitle(b))),
        }));

      return {
        id: topFolder,
        label: topFolder,
        shortLabel: shortenFolderLabel(topFolder),
        count: subfolders.reduce((sum, sub) => sum + sub.files.length, 0),
        subfolders,
      };
    });
}

export function filterCatalogDocuments(docs, query) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return docs;
  return docs.filter((doc) => {
    const title = catalogDocDisplayTitle(doc).toLowerCase();
    const path = String(doc.path || '').toLowerCase();
    const fileName = catalogDocFileName(doc).toLowerCase();
    return title.includes(q) || path.includes(q) || fileName.includes(q);
  });
}

export function catalogDocTypeLabel(doc) {
  const ext = inferExtension(catalogDocFileName(doc));
  return ext ? ext.replace('.', '').toUpperCase() : 'FILE';
}
