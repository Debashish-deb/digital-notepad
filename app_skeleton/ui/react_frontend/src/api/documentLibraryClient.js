/**
 * Document library API client.
 */
import { apiFetch } from './client.js';

function buildParams(params = {}) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      sp.set(key, String(value));
    }
  });
  return sp;
}

export async function fetchDocumentLibraryStats() {
  return apiFetch('/api/document-library/stats');
}

export async function searchDocumentLibrary(params = {}) {
  const sp = buildParams(params);
  return apiFetch(`/api/document-library/search?${sp}`);
}

export async function fetchDocumentLibraryFacets(params = {}) {
  const sp = buildParams(params);
  return apiFetch(`/api/document-library/facets?${sp}`);
}

export async function fetchDocumentPreview(assetId) {
  return apiFetch(`/api/document-library/preview/${encodeURIComponent(assetId)}`);
}

export async function fetchCategoryTrees() {
  return apiFetch('/api/document-library/category-trees');
}

export async function fetchDocumentLibraryTaxonomy() {
  return apiFetch('/api/document-library/taxonomy');
}

export const DOMAIN_TABS = [
  { id: 'overview', label: 'Lab Administration', description: 'Onboarding, guidelines, permits, personnel' },
  { id: 'wet_lab', label: 'Lab Operations', description: 'Protocols, wet-lab files, CyCIF resources' },
  { id: 'orders', label: 'Orders & Procurement', description: 'Billing, shipping, archives, yearly orders' },
  { id: 'all_files', label: 'Full Library', description: 'Search all indexed lab documents' },
];

export const SYSTEM_VIEWS = [
  { id: 'all_files', label: 'All files' },
  { id: 'recently_opened', label: 'Recently opened', clientOnly: true },
  { id: 'pinned', label: 'Pinned', clientOnly: true },
  { id: 'not_indexed', label: 'Not indexed' },
  { id: 'needs_redigitalization', label: 'Needs redigitalization' },
  { id: 'unknown_type', label: 'Unknown type' },
  { id: 'duplicates', label: 'Duplicates' },
  { id: 'large_files', label: 'Large files' },
  { id: 'wet_lab', label: 'Wet lab' },
  { id: 'project_files', label: 'Project files' },
  { id: 'orders_billing', label: 'Orders & billing' },
];

export const STATUS_BADGE_CLASS = {
  indexed: 'sfe-badge--indexed',
  not_started: 'sfe-badge--not-indexed',
  metadata_only: 'sfe-badge--partial',
  needs_redigitalization: 'sfe-badge--warn',
  duplicate: 'sfe-badge--duplicate',
  unknown: 'sfe-badge--unknown',
  needs_review: 'sfe-badge--review',
  warn: 'sfe-badge--warn',
};

const RECENT_KEY = 'omeia_doclib_recent';
const PINNED_KEY = 'omeia_doclib_pinned';

export function loadRecentIds() {
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function pushRecentId(assetId) {
  if (!assetId) return;
  const ids = loadRecentIds().filter((id) => id !== assetId);
  ids.unshift(assetId);
  window.localStorage.setItem(RECENT_KEY, JSON.stringify(ids.slice(0, 50)));
}

export function loadPinnedIds() {
  try {
    const raw = window.localStorage.getItem(PINNED_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function togglePinnedId(assetId) {
  const ids = loadPinnedIds();
  const next = ids.includes(assetId) ? ids.filter((id) => id !== assetId) : [...ids, assetId];
  window.localStorage.setItem(PINNED_KEY, JSON.stringify(next));
  return next;
}

export function formatBytes(n) {
  const v = Number(n) || 0;
  if (v < 1024) return `${v} B`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`;
  if (v < 1024 * 1024 * 1024) return `${(v / (1024 * 1024)).toFixed(1)} MB`;
  return `${(v / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
