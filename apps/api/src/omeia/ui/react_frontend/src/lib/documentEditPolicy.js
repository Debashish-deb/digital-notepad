import { isProjectReadmePath } from './projectReadmeUtils.js';

const EDITABLE_EXTENSIONS = new Set(['.md', '.txt', '.html', '.rtf']);

const SOURCE_DOCUMENT_EXTENSIONS = new Set([
  '.pdf',
  '.doc',
  '.docx',
  '.ppt',
  '.pptx',
  '.odt',
  '.xls',
  '.xlsx',
  '.csv',
  '.png',
  '.jpg',
  '.jpeg',
  '.webp',
  '.tif',
  '.tiff',
  '.gif',
  '.mp4',
  '.mov',
]);

export function isSourceDocument(doc, extension) {
  const ext = String(extension || '').toLowerCase();
  if (doc?.isResearchMaterial) return true;
  if (SOURCE_DOCUMENT_EXTENSIONS.has(ext)) return true;
  return false;
}

/** Editable only for markdown/readme by default, or when explicitly flagged on the doc. */
export function canEditDocument(doc, extension) {
  const ext = String(extension || '').toLowerCase();
  if (!EDITABLE_EXTENSIONS.has(ext)) return false;
  if (doc?.explicitly_editable || doc?.allow_edit) return true;
  if (doc?.isResearchMaterial) return false;
  if (ext === '.md' || isProjectReadmePath(doc?.path)) return true;
  return false;
}

export function documentViewBadge(doc, extension) {
  if (!isSourceDocument(doc, extension)) return null;
  if (canEditDocument(doc, extension)) return 'Source · editable';
  return 'Source · view only';
}
