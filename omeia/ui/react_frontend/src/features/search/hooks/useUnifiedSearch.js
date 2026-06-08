import { useCallback, useEffect, useRef, useState } from 'react';
import {
  fetchUnifiedSearch,
  parseUnifiedSearchResponse,
  SEARCH_DEBOUNCE_MS,
} from '@/services/searchApi.js';
import { pushRecentSearchQuery, readRecentSearchQueries } from '@/lib/searchHits.js';
import { SCOPE_OPTIONS } from '@/features/search/components/SearchFilters.jsx';
import { advancedFiltersToSearchParams, emptyAdvancedFilters } from '@/features/search/components/SearchAdvancedFilters.jsx';

/**
 * Shared unified search state + execution for GlobalSearchOverlay and KnowledgeSearchScreen.
 * @param {object} options
 * @param {'manual'|'debounced'} [options.trigger='manual'] — manual submit vs debounced auto-search
 * @param {boolean} [options.enabled=true] — when false, debounced searches are suppressed
 * @param {string} [options.projectCode] — optional project scope for overlay
 * @param {number} [options.limit=30]
 */
export default function useUnifiedSearch({
  trigger = 'manual',
  enabled = true,
  projectCode,
  limit = 30,
  onResults = null,
} = {}) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [scopes, setScopes] = useState(() => SCOPE_OPTIONS.map((s) => s.id));
  const [hits, setHits] = useState([]);
  const [buckets, setBuckets] = useState({});
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [advancedFilters, setAdvancedFilters] = useState(emptyAdvancedFilters);
  const [filtersApplied, setFiltersApplied] = useState({});
  const [unsupportedFilters, setUnsupportedFilters] = useState([]);
  const [cacheHit, setCacheHit] = useState(false);
  const [recentQueries, setRecentQueries] = useState(() => readRecentSearchQueries());
  const [suggestions, setSuggestions] = useState([]);
  const [synonymHints, setSynonymHints] = useState([]);
  const abortRef = useRef(null);

  const scopesParam = scopes.join(',');

  const applySearchResult = useCallback((parsed, { trackRecent = false, q } = {}) => {
    setHits(parsed.hits);
    setBuckets(parsed.buckets);
    setFiltersApplied(parsed.filtersApplied);
    setUnsupportedFilters(parsed.unsupportedFilters);
    setCacheHit(parsed.cacheHit);
    setSuggestions(parsed.suggestions);
    setSynonymHints(parsed.synonymHints);
    if (trackRecent && q) {
      pushRecentSearchQuery(q);
      setRecentQueries(readRecentSearchQueries());
    }
    onResults?.(parsed);
    return parsed;
  }, [onResults]);

  const runSearch = useCallback(async (overrideQuery, { signal } = {}) => {
    const q = String(overrideQuery ?? query).trim();
    if (q.length < 2) {
      setHits([]);
      setBuckets({});
      setError(null);
      return null;
    }

    abortRef.current?.abort();
    const controller = signal ? null : new AbortController();
    const mergedSignal = signal || controller.signal;
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const data = await fetchUnifiedSearch({
        query: q,
        mode,
        scopes: scopesParam,
        projectCode,
        limit,
        signal: mergedSignal,
        ...advancedFiltersToSearchParams(advancedFilters),
      });
      if (mergedSignal.aborted) return null;
      const parsed = parseUnifiedSearchResponse(data);
      applySearchResult(parsed, { trackRecent: true, q });
      return parsed;
    } catch (err) {
      if (err?.name === 'AbortError') return null;
      setError(String(err?.message || err || 'Search failed. Check API connection and try again.'));
      setHits([]);
      setBuckets({});
      return null;
    } finally {
      if (!mergedSignal.aborted) setLoading(false);
    }
  }, [
    query,
    mode,
    scopesParam,
    projectCode,
    limit,
    advancedFilters,
    applySearchResult,
  ]);

  useEffect(() => {
    if (trigger !== 'debounced' || !enabled) return undefined;

    const trimmed = query.trim();
    if (!trimmed || trimmed.length < 2) {
      setHits([]);
      setBuckets({});
      setError(null);
      setLoading(false);
      return undefined;
    }

    const timer = setTimeout(() => {
      runSearch(trimmed);
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      abortRef.current?.abort();
    };
  }, [trigger, enabled, query, runSearch]);

  const resetSearchState = useCallback(() => {
    abortRef.current?.abort();
    setHits([]);
    setBuckets({});
    setError(null);
    setLoading(false);
    setFiltersApplied({});
    setUnsupportedFilters([]);
    setCacheHit(false);
    setSuggestions([]);
    setSynonymHints([]);
    setRecentQueries(readRecentSearchQueries());
  }, []);

  return {
    query,
    setQuery,
    mode,
    setMode,
    scopes,
    setScopes,
    hits,
    buckets,
    error,
    loading,
    advancedFilters,
    setAdvancedFilters,
    filtersApplied,
    unsupportedFilters,
    cacheHit,
    recentQueries,
    setRecentQueries,
    suggestions,
    setSuggestions,
    synonymHints,
    setSynonymHints,
    runSearch,
    resetSearchState,
    scopesParam,
  };
}
