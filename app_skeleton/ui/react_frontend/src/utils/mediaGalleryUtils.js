import { inferExtension } from './fileTypeMeta.js';
import { getMediaPreviewKind } from './mediaPreviewKind.js';

function parentFolder(path) {
  const norm = (path || '').replace(/\\/g, '/');
  const idx = norm.lastIndexOf('/');
  return idx >= 0 ? norm.slice(0, idx) : '';
}

/**
 * Build a gallery of sibling image/video/3D files in the same folder.
 * @param {object|null} selectedDoc
 * @param {object[]} allDocs
 * @param {(doc: object) => string|null} resolveUrl
 * @param {(doc: object) => string} resolveTitle
 */
export function buildMediaGallery(selectedDoc, allDocs, resolveUrl, resolveTitle) {
  if (!selectedDoc?.path) return [];

  const selectedExt = inferExtension(selectedDoc.name, selectedDoc.extension);
  const selectedKind = getMediaPreviewKind(selectedExt);
  if (!selectedKind) return [];

  const folder = parentFolder(selectedDoc.path);

  return allDocs
    .filter((doc) => {
      if (!doc?.path || doc.path === selectedDoc.path) return false;
      if (parentFolder(doc.path) !== folder) return false;
      const ext = inferExtension(doc.name, doc.extension);
      return Boolean(getMediaPreviewKind(ext));
    })
    .map((doc) => {
      const ext = inferExtension(doc.name, doc.extension);
      return {
        path: doc.path,
        url: resolveUrl(doc),
        title: resolveTitle(doc),
        kind: getMediaPreviewKind(ext),
        extension: ext,
      };
    })
    .filter((item) => Boolean(item.url));
}

export function mergeGalleryItem(selectedDoc, gallery, resolveUrl, resolveTitle) {
  if (!selectedDoc?.path) return gallery;
  const ext = inferExtension(selectedDoc.name, selectedDoc.extension);
  const kind = getMediaPreviewKind(ext);
  if (!kind) return gallery;

  const current = {
    path: selectedDoc.path,
    url: resolveUrl(selectedDoc),
    title: resolveTitle(selectedDoc),
    kind,
    extension: ext,
  };

  const siblings = gallery.filter((g) => g.path !== selectedDoc.path);
  const combined = [current, ...siblings].sort((a, b) =>
    a.path.localeCompare(b.path, undefined, { numeric: true, sensitivity: 'base' })
  );
  return combined;
}
