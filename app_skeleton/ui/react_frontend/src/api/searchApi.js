import { apiGet } from './client.js';
import { buildUnifiedSearchParams } from '../utils/searchHits.js';

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
  signal,
}) {
  const params = buildUnifiedSearchParams({
    query,
    mode,
    scopes,
    projectCode,
    sectionId,
    limit,
  });
  return apiGet('/api/platform/unified-search', { params, signal });
}

/**
 * Query suggestions + synonym hints — GET /api/platform/search-suggestions
 */
export async function fetchSearchSuggestions({ query = '', limit = 8, signal } = {}) {
  const params = new URLSearchParams();
  if (query?.trim()) params.set('q', query.trim());
  params.set('limit', String(limit));
  return apiGet('/api/platform/search-suggestions', { params, signal });
}
