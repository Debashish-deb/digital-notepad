import { loadPinnedIds, loadRecentIds } from '@/services/documentLibraryClient.js';
import { getMediaPreviewKind } from '@/lib/mediaPreviewKind.js';
import { getFilePreviewKind } from '@/lib/filePreviewKind.js';

export const ROW_HEIGHT = 60;
export const CARD_HEIGHT = 100;

export const SFE_LIST_COLUMNS = [
  { id: 'name', label: 'Name', defaultWidth: 300, minWidth: 140, maxWidth: 720 },
  { id: 'category', label: 'Category', defaultWidth: 140, minWidth: 72, maxWidth: 360 },
  { id: 'size', label: 'Size', defaultWidth: 76, minWidth: 56, maxWidth: 140 },
  { id: 'modified', label: 'Modified', defaultWidth: 100, minWidth: 80, maxWidth: 160 },
  { id: 'status', label: 'Status', defaultWidth: 128, minWidth: 96, maxWidth: 220 },
];
export const SFE_COLUMN_WIDTHS_KEY = 'sfe-file-list-column-widths';

export const MAINTENANCE_CHIP_IDS = [
  'all_files',
  'not_indexed',
  'needs_redigitalization',
  'duplicates',
  'unknown_type',
  'large_files',
];

export const SCOPE_OVERLAY_FILTER_KEYS = ['protocol_category', 'reagent_category', 'smart_chip', 'file_type'];

export function prettifyCategory(value) {
  return (value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

export function scopeChipToFilters(chip, baseFilters) {
  const next = { ...baseFilters };
  SCOPE_OVERLAY_FILTER_KEYS.forEach((key) => delete next[key]);
  const chipFilter = chip.filter || {};
  Object.entries(chipFilter).forEach(([key, value]) => {
    if (key === 'system_view') return;
    if (value === undefined || value === null || value === '') {
      delete next[key];
    } else {
      next[key] = value;
    }
  });
  return next;
}

export function extensionFromListItem(item) {
  let ext = (item?.extension || item?.metadata?.extension || '').toLowerCase();
  if (!ext && item?.filename) {
    const match = item.filename.match(/\.[^.]+$/i);
    if (match) ext = match[0].toLowerCase();
  }
  if (!ext && item?.logical_path) {
    const match = item.logical_path.match(/\.[^.]+$/i);
    if (match) ext = match[0].toLowerCase();
  }
  if (ext && !ext.startsWith('.')) ext = `.${ext}`;
  return ext;
}

export function resolveFileBulletKind(item) {
  const ext = extensionFromListItem(item);
  const fileType = item?.file_type || item?.metadata?.file_type;
  if (fileType === 'image' || getMediaPreviewKind(ext) === 'image') return 'image';
  if (fileType === 'video' || getMediaPreviewKind(ext) === 'video') return 'video';

  const previewKind = getFilePreviewKind(ext, item?.logical_path);
  if (previewKind === 'spreadsheet') return 'spreadsheet';
  if (previewKind === 'code' || previewKind === 'json') return 'code';
  if (ext === '.pdf') return 'pdf';
  if (previewKind === 'text') return 'text';
  if (['.csv', '.tsv', '.parquet'].includes(ext)) return 'data';
  return 'document';
}

export function extensionFromPreview(preview) {
  const md = preview?.metadata || {};
  let ext = (md.extension || preview?.extension || '').toLowerCase();
  if (!ext && preview?.filename) {
    const match = preview.filename.match(/\.[^.]+$/i);
    if (match) ext = match[0].toLowerCase();
  }
  if (ext && !ext.startsWith('.')) ext = `.${ext}`;
  return ext;
}

export function resolvePreviewMedia(preview) {
  if (!preview) return null;
  const md = preview.metadata || {};
  const extension = extensionFromPreview(preview);
  const kind =
    getMediaPreviewKind(extension) ||
    (md.file_type === 'image' ? 'image' : md.file_type === 'video' ? 'video' : null);
  if (!kind) return null;

  const logical = preview.logical_path || md.logical_path;
  const url =
    preview.preview_url ||
    (logical ? `/database-static/${logical.split('/').map(encodeURIComponent).join('/')}` : null);
  if (!url) return null;

  return { kind, url, extension };
}

export function filterClientView(items, systemView) {
  if (systemView === 'recently_opened') {
    const recent = new Set(loadRecentIds());
    return items.filter((i) => recent.has(i.asset_id));
  }
  if (systemView === 'pinned') {
    const pinned = new Set(loadPinnedIds());
    return items.filter((i) => pinned.has(i.asset_id));
  }
  return items;
}
