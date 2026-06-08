import { inferExtension } from './fileTypeMeta.js';
import { getMediaPreviewKind } from './mediaPreviewKind.js';
import { getFilePreviewKind } from './filePreviewKind.js';

/** @typedef {'image'|'video'|'model'|'spreadsheet'|'code'|'text'|'document'} FileContentKind */

/** @typedef {'gallery'|'media'|'split'|'mixed'} BrowserLayoutMode */

const DOMINANCE_THRESHOLD = 0.65;

/**
 * Classify a document for adaptive browser layout.
 * @param {object} doc
 * @returns {FileContentKind}
 */
export function classifyFileContentKind(doc) {
  const ext = inferExtension(doc?.name, doc?.extension);
  const mediaKind = getMediaPreviewKind(ext);
  if (mediaKind === 'image') return 'image';
  if (mediaKind === 'video') return 'video';
  if (mediaKind === 'model3d') return 'model';

  const previewKind = getFilePreviewKind(ext, doc?.path);
  if (previewKind === 'spreadsheet') return 'spreadsheet';
  if (previewKind === 'code' || previewKind === 'json') return 'code';
  if (previewKind === 'text' || previewKind === 'markup') return 'text';
  return 'document';
}

/**
 * Filter files to image/video/model assets for gallery layouts.
 * @param {object[]} files
 * @param {'image'|'video'|'media'} scope
 */
export function filterMediaFiles(files, scope = 'media') {
  return (files || []).filter((doc) => {
    const kind = classifyFileContentKind(doc);
    if (scope === 'image') return kind === 'image';
    if (scope === 'video') return kind === 'video';
    return kind === 'image' || kind === 'video' || kind === 'model';
  });
}

/**
 * Derive adaptive layout mode from visible files in the current category.
 * @param {object[]} files
 * @param {{ userOverride?: 'gallery'|'split'|null }} [options]
 * @returns {{ mode: BrowserLayoutMode, dominantKind: FileContentKind|null, counts: Record<string, number>, mediaScope: 'image'|'video'|'media'|null }}
 */
export function deriveBrowserLayoutMode(files, options = {}) {
  const { userOverride = null } = options;
  const list = files || [];
  const counts = {
    image: 0,
    video: 0,
    model: 0,
    spreadsheet: 0,
    code: 0,
    text: 0,
    document: 0,
  };

  for (const doc of list) {
    const kind = classifyFileContentKind(doc);
    counts[kind] = (counts[kind] || 0) + 1;
  }

  const total = list.length;
  if (!total) {
    return { mode: 'split', dominantKind: null, counts, mediaScope: null };
  }

  if (userOverride === 'gallery') {
    const scope = counts.video > counts.image ? 'video' : 'image';
    return {
      mode: counts.image || counts.video || counts.model ? 'gallery' : 'split',
      dominantKind: scope === 'video' ? 'video' : 'image',
      counts,
      mediaScope: counts.video > counts.image && !counts.image ? 'video' : 'media',
    };
  }

  if (userOverride === 'split') {
    return { mode: 'split', dominantKind: 'document', counts, mediaScope: null };
  }

  const imageShare = counts.image / total;
  const videoShare = counts.video / total;
  const mediaShare = (counts.image + counts.video + counts.model) / total;
  const officeShare =
    (counts.document + counts.spreadsheet + counts.code + counts.text) / total;

  if (counts.image === total) {
    return { mode: 'gallery', dominantKind: 'image', counts, mediaScope: 'image' };
  }

  if (counts.video === total) {
    return { mode: 'media', dominantKind: 'video', counts, mediaScope: 'video' };
  }

  if (mediaShare === 1) {
    return {
      mode: 'gallery',
      dominantKind: counts.video > counts.image ? 'video' : 'image',
      counts,
      mediaScope: 'media',
    };
  }

  if (imageShare >= DOMINANCE_THRESHOLD) {
    return { mode: 'gallery', dominantKind: 'image', counts, mediaScope: 'image' };
  }

  if (videoShare >= DOMINANCE_THRESHOLD) {
    return { mode: 'media', dominantKind: 'video', counts, mediaScope: 'video' };
  }

  if (mediaShare >= DOMINANCE_THRESHOLD) {
    return {
      mode: 'gallery',
      dominantKind: counts.image >= counts.video ? 'image' : 'video',
      counts,
      mediaScope: 'media',
    };
  }

  if (officeShare >= DOMINANCE_THRESHOLD) {
    return { mode: 'split', dominantKind: 'document', counts, mediaScope: null };
  }

  return {
    mode: 'mixed',
    dominantKind: imageShare >= videoShare && imageShare >= officeShare
      ? 'image'
      : videoShare >= officeShare
        ? 'video'
        : 'document',
    counts,
    mediaScope: null,
  };
}

export function isGalleryLayoutMode(mode) {
  return mode === 'gallery' || mode === 'media';
}
