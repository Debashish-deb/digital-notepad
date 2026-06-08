/**
 * Shared SearchHit contract + in-app navigation for unified platform search.
 */

export const SEARCH_NAV_STORAGE_KEY = 'farkki_search_pending_nav';
export const SEARCH_QUERY_STORAGE_KEY = 'farkki_search_last_query';
export const SEARCH_OMNIBOX_PREFILL_KEY = 'farkki_search_omnibox_prefill';
export const SEARCH_RECENT_STORAGE_KEY = 'farkki_search_recent_queries';
const RECENT_MAX = 12;

export const BUCKET_LABELS = {
  lab: 'Lab Knowledge',
  file: 'Documents',
  vault: 'Vault Asset',
  document_library: 'Document Library',
  vault_review: 'Vault Review',
  notebook: 'Notebook',
  wiki: 'Wiki / SOP',
  decision: 'Decisions',
  task: 'Tasks',
  project: 'Projects',
  research: 'Research KB',
  people: 'Lab members',
};

export const BUCKET_ORDER = [
  'research',
  'lab',
  'document_library',
  'people',
  'file',
  'vault',
  'vault_review',
  'notebook',
  'wiki',
  'decision',
  'task',
  'project',
];

export function stashSearchNavigation(nav) {
  if (!nav) return;
  try {
    sessionStorage.setItem(SEARCH_NAV_STORAGE_KEY, JSON.stringify(nav));
  } catch {
    /* ignore quota */
  }
}

export function consumeSearchNavigation() {
  try {
    const raw = sessionStorage.getItem(SEARCH_NAV_STORAGE_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(SEARCH_NAV_STORAGE_KEY);
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function stashSearchQuery(query) {
  if (!query?.trim()) return;
  try {
    sessionStorage.setItem(SEARCH_QUERY_STORAGE_KEY, query.trim());
  } catch {
    /* ignore */
  }
}

export function stashOmniboxPrefill(query) {
  if (!query?.trim()) return;
  try {
    sessionStorage.setItem(SEARCH_OMNIBOX_PREFILL_KEY, query.trim());
  } catch {
    /* ignore */
  }
}

export function consumeOmniboxPrefill() {
  try {
    const raw = sessionStorage.getItem(SEARCH_OMNIBOX_PREFILL_KEY);
    if (!raw) return '';
    sessionStorage.removeItem(SEARCH_OMNIBOX_PREFILL_KEY);
    return raw;
  } catch {
    return '';
  }
}

export function readStashedSearchQuery() {
  try {
    return sessionStorage.getItem(SEARCH_QUERY_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

export function pushRecentSearchQuery(query) {
  const q = String(query || '').trim();
  if (q.length < 2) return;
  try {
    const raw = localStorage.getItem(SEARCH_RECENT_STORAGE_KEY);
    const prev = raw ? JSON.parse(raw) : [];
    const next = [q, ...(Array.isArray(prev) ? prev : []).filter((item) => item !== q)].slice(0, RECENT_MAX);
    localStorage.setItem(SEARCH_RECENT_STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
}

export function readRecentSearchQueries() {
  try {
    const raw = localStorage.getItem(SEARCH_RECENT_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * Navigate from a SearchHit.nav action.
 * @param {object} nav
 * @param {(main: string, sub?: string) => void} onNavigate
 * @param {(code: string) => void} [onSelectProject]
 */
export function navigateFromSearchHit(nav, onNavigate, onSelectProject) {
  if (!nav?.main) return false;
  stashSearchNavigation(nav);
  if (nav.project_code && onSelectProject) {
    onSelectProject(nav.project_code);
  }
  onNavigate(nav.main, nav.sub || undefined);
  return true;
}

export function groupHitsByBucket(hits = []) {
  const groups = new Map();
  for (const hit of hits) {
    const bucket = hit.bucket || 'lab';
    if (!groups.has(bucket)) groups.set(bucket, []);
    groups.get(bucket).push(hit);
  }
  return BUCKET_ORDER.filter((b) => groups.has(b)).map((bucket) => ({
    bucket,
    label: BUCKET_LABELS[bucket] || bucket,
    items: groups.get(bucket),
  }));
}

export function buildUnifiedSearchParams({
  query,
  mode = 'hybrid',
  scopes,
  projectCode,
  sectionId,
  limit = 25,
  category,
  smartChip,
  domainTab,
  systemView,
  fileType,
  dateFrom,
  dateTo,
  indexedStatus,
  filterProjectCodes,
  filterSectionId,
  sourceBuckets,
}) {
  const params = new URLSearchParams();
  params.set('q', query.trim());
  params.set('mode', mode);
  params.set('limit', String(limit));
  if (scopes) params.set('scopes', scopes);
  if (projectCode) params.set('project_code', projectCode);
  if (sectionId) params.set('section_id', sectionId);
  if (category) params.set('category', category);
  if (smartChip) params.set('smart_chip', smartChip);
  if (domainTab) params.set('domain_tab', domainTab);
  if (systemView) params.set('system_view', systemView);
  if (fileType) params.set('file_type', fileType);
  if (dateFrom) params.set('date_from', dateFrom);
  if (dateTo) params.set('date_to', dateTo);
  if (indexedStatus) params.set('indexed_status', indexedStatus);
  if (filterProjectCodes) params.set('filter_project_codes', filterProjectCodes);
  if (filterSectionId) params.set('filter_section_id', filterSectionId);
  if (sourceBuckets) params.set('source_buckets', sourceBuckets);
  return params;
}
