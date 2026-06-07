import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Search, X, Sparkles, Loader2, AlertCircle, ExternalLink } from 'lucide-react';
import { fetchSearchSuggestions, fetchUnifiedSearch, SEARCH_DEBOUNCE_MS } from '../api/searchApi.js';
import {
  BUCKET_LABELS,
  groupHitsByBucket,
  navigateFromSearchHit,
  pushRecentSearchQuery,
  readRecentSearchQueries,
  stashSearchQuery,
  consumeOmniboxPrefill,
} from '../utils/searchHits.js';
import SearchAdvancedFilters, { advancedFiltersToSearchParams, emptyAdvancedFilters } from './search/SearchAdvancedFilters.jsx';
import SearchBucketGroup from './search/SearchBucketGroup.jsx';
import SearchFilterMetadata from './search/SearchFilterMetadata.jsx';
import SearchFilters, { SCOPE_OPTIONS } from './search/SearchFilters.jsx';
import SearchSuggestions from './search/SearchSuggestions.jsx';
import './search/UnifiedSearch.css';

export default function GlobalSearchOverlay({
  isOpen,
  onClose,
  onNavigate,
  onSelectProject,
  onAskAi,
  projectCode,
}) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [scopes, setScopes] = useState(() => SCOPE_OPTIONS.map((s) => s.id));
  const [hits, setHits] = useState([]);
  const [buckets, setBuckets] = useState({});
  const [suggestions, setSuggestions] = useState([]);
  const [synonymHints, setSynonymHints] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [recentQueries, setRecentQueries] = useState(() => readRecentSearchQueries());
  const [advancedFilters, setAdvancedFilters] = useState(emptyAdvancedFilters);
  const [filtersApplied, setFiltersApplied] = useState({});
  const [unsupportedFilters, setUnsupportedFilters] = useState([]);
  const [cacheHit, setCacheHit] = useState(false);
  const inputRef = useRef(null);
  const abortRef = useRef(null);
  const suggestAbortRef = useRef(null);

  const flatHits = useMemo(() => hits, [hits]);
  const grouped = useMemo(() => groupHitsByBucket(hits), [hits]);
  const scopesParam = scopes.join(',');

  useEffect(() => {
    if (isOpen) {
      const prefill = consumeOmniboxPrefill();
      setTimeout(() => inputRef.current?.focus(), 80);
      setQuery(prefill || '');
      setHits([]);
      setBuckets({});
      setSuggestions([]);
      setSynonymHints([]);
      setError(null);
      setActiveIndex(-1);
      setFiltersApplied({});
      setUnsupportedFilters([]);
      setCacheHit(false);
      setRecentQueries(readRecentSearchQueries());
    }
  }, [isOpen]);

  const openHit = useCallback(
    (hit) => {
      if (!hit?.nav || !onNavigate) return;
      navigateFromSearchHit(hit.nav, onNavigate, onSelectProject);
      onClose();
    },
    [onNavigate, onSelectProject, onClose],
  );

  useEffect(() => {
    if (!isOpen) return undefined;

    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }
      if (!flatHits.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, flatHits.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && activeIndex >= 0) {
        e.preventDefault();
        openHit(flatHits[activeIndex]);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, flatHits, activeIndex, onClose, openHit]);

  useEffect(() => {
    if (!isOpen || query.trim().length >= 2) return undefined;

    const timer = setTimeout(() => {
      suggestAbortRef.current?.abort();
      const controller = new AbortController();
      suggestAbortRef.current = controller;

      fetchSearchSuggestions({ query: query.trim(), signal: controller.signal })
        .then((data) => {
          if (controller.signal.aborted) return;
          if (Array.isArray(data?.suggestions)) setSuggestions(data.suggestions);
          if (Array.isArray(data?.synonym_hints)) setSynonymHints(data.synonym_hints);
          if (Array.isArray(data?.recent_queries) && data.recent_queries.length) {
            setRecentQueries(data.recent_queries);
          }
        })
        .catch(() => {
          /* optional endpoint — local recent still shown */
        });
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      suggestAbortRef.current?.abort();
    };
  }, [isOpen, query]);

  useEffect(() => {
    if (!query.trim() || query.trim().length < 2) {
      setHits([]);
      setBuckets({});
      setError(null);
      setLoading(false);
      return undefined;
    }

    const timer = setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      setError(null);
      try {
        const data = await fetchUnifiedSearch({
          query,
          mode,
          scopes: scopesParam,
          projectCode,
          limit: 30,
          signal: controller.signal,
          ...advancedFiltersToSearchParams(advancedFilters),
        });
        if (controller.signal.aborted) return;
        setHits(Array.isArray(data?.hits) ? data.hits : []);
        setBuckets(data?.buckets || {});
        setSuggestions(Array.isArray(data?.suggestions) ? data.suggestions : []);
        setSynonymHints(Array.isArray(data?.synonym_hints) ? data.synonym_hints : []);
        setFiltersApplied(data?.filters_applied || {});
        setUnsupportedFilters(Array.isArray(data?.unsupported_filters) ? data.unsupported_filters : []);
        setCacheHit(Boolean(data?.metadata?.cache_hit));
        setActiveIndex(data?.hits?.length ? 0 : -1);
        pushRecentSearchQuery(query);
        setRecentQueries(readRecentSearchQueries());
      } catch (err) {
        if (err?.name === 'AbortError') return;
        setError(err?.message || 'Search failed. Check API connection and try again.');
        setHits([]);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      abortRef.current?.abort();
    };
  }, [query, mode, scopesParam, projectCode, advancedFilters]);

  const handleAskAi = useCallback(
    (text) => {
      const q = String(text || query).trim();
      if (!q) return;
      stashSearchQuery(q);
      onAskAi?.(q);
      onClose();
    },
    [query, onAskAi, onClose],
  );

  const handleAskAiAboutHit = useCallback(
    (hit) => {
      const q = hit?.title
        ? `Tell me about “${hit.title}”${hit.snippet ? `: ${hit.snippet.slice(0, 120)}` : ''}`
        : query;
      handleAskAi(q);
    },
    [handleAskAi, query],
  );

  if (!isOpen) return null;

  let rowOffset = 0;

  return (
    <div className="search-overlay-backdrop" onClick={onClose} role="presentation">
      <div
        className="search-overlay-card search-overlay-card--unified"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Platform search"
      >
        <div className="search-input-container">
          <Search size={22} className="text-muted" aria-hidden />
          <input
            ref={inputRef}
            type="search"
            className="search-input-field"
            placeholder="Search lab documents, protocols, notebook, wiki, tasks, projects…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <SearchFilters mode={mode} onModeChange={setMode} compact showScopes={false} />
          <button type="button" className="search-close-btn" onClick={onClose} aria-label="Close search">
            <X size={20} />
          </button>
        </div>

        <SearchFilters
          mode={mode}
          onModeChange={setMode}
          scopes={scopes}
          onScopesChange={setScopes}
          showModes={false}
        />

        <SearchAdvancedFilters value={advancedFilters} onChange={setAdvancedFilters} compact />

        <SearchFilterMetadata
          filtersApplied={filtersApplied}
          unsupportedFilters={unsupportedFilters}
          cacheHit={cacheHit}
          compact
        />

        <div className="search-toolbar">
          <span className="search-toolbar-hint">
            <kbd>↑</kbd><kbd>↓</kbd> navigate · <kbd>Enter</kbd> open · <kbd>Esc</kbd> close
          </span>
          {query.trim().length >= 2 && onAskAi ? (
            <button type="button" className="search-ask-ai-btn" onClick={() => handleAskAi(query)}>
              <Sparkles size={14} aria-hidden />
              Ask AI about this
            </button>
          ) : null}
        </div>

        <div className="search-results-container">
          {loading ? (
            <div className="search-empty">
              <Loader2 size={18} className="spin" aria-hidden />
              Searching across lab corpus, vault, and registry…
            </div>
          ) : null}

          {error ? (
            <div className="search-error" role="alert">
              <AlertCircle size={16} aria-hidden />
              {error}
            </div>
          ) : null}

          {!loading && !error && query.trim().length < 2 && (
            <div className="search-recent-wrap">
              <SearchSuggestions
                recentQueries={recentQueries}
                suggestions={suggestions}
                synonymHints={synonymHints}
                onSelect={setQuery}
              />
            </div>
          )}

          {!loading && !error && query.trim().length >= 2 && hits.length === 0 && (
            <div className="search-empty">No matching results. Try hybrid mode or refine your query.</div>
          )}

          {!loading && !error && grouped.length > 0 ? (
            <>
              <div className="search-bucket-summary">
                {Object.entries(buckets).map(([bucket, count]) => (
                  <span key={bucket} className={`search-bucket-chip search-bucket-chip--${bucket}`}>
                    {BUCKET_LABELS[bucket] || bucket}: {count}
                  </span>
                ))}
              </div>
              {grouped.map((group) => {
                const offset = rowOffset;
                rowOffset += group.items.length;
                return (
                  <SearchBucketGroup
                    key={group.bucket}
                    group={group}
                    query={query}
                    activeIndex={activeIndex}
                    activeIndexOffset={offset}
                    onOpenHit={openHit}
                    onAskAiAboutHit={onAskAi ? handleAskAiAboutHit : null}
                    onHoverIndex={setActiveIndex}
                  />
                );
              })}
            </>
          ) : null}
        </div>

        <div className="search-overlay-footer">
          <ExternalLink size={12} aria-hidden />
          <span>Unified search · lab + vault + registry</span>
        </div>
      </div>
    </div>
  );
}
