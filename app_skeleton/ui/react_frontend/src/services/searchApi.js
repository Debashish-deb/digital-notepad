import { apiGet, createAbortCoordinator, SEARCH_DEBOUNCE_MS } from './client.js';
import { buildUnifiedSearchParams } from '@/lib/searchHits.js';

const unifiedSearchCoordinator = createAbortCoordinator();
const suggestionsCoordinator = createAbortCoordinator();

export { SEARCH_DEBOUNCE_MS };

/** Normalize unified-search API payload for UI consumers. */
export function parseUnifiedSearchResponse(data) {
  return {
    hits: Array.isArray(data?.hits) ? data.hits : [],
    buckets: data?.buckets || {},
    suggestions: Array.isArray(data?.suggestions) ? data.suggestions : [],
    synonymHints: Array.isArray(data?.synonym_hints) ? data.synonym_hints : [],
    filtersApplied: data?.filters_applied || {},
    unsupportedFilters: Array.isArray(data?.unsupported_filters) ? data.unsupported_filters : [],
    cacheHit: Boolean(data?.metadata?.cache_hit),
  };
}

/**
 * Canonical platform search — GET /api/platform/unified-search
 * @param {object} options
 * @param {AbortSignal} [options.signal]
 */
export async function fetchUnifiedSearch({
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
  signal,
}) {
  const params = buildUnifiedSearchParams({
    query,
    mode,
    scopes,
    projectCode,
    sectionId,
    limit,
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
  });
  const { signal: mergedSignal, release } = unifiedSearchCoordinator.next(signal);
  try {
    return await apiGet('/api/platform/unified-search', { params, signal: mergedSignal });
  } finally {
    release();
  }
}

/**
 * Query suggestions + synonym hints — GET /api/platform/search-suggestions
 */
export async function fetchSearchSuggestions({ query = '', limit = 8, signal } = {}) {
  const params = new URLSearchParams();
  if (query?.trim()) params.set('q', query.trim());
  params.set('limit', String(limit));
  const { signal: mergedSignal, release } = suggestionsCoordinator.next(signal);
  try {
    return await apiGet('/api/platform/search-suggestions', { params, signal: mergedSignal });
  } finally {
    release();
  }
}
