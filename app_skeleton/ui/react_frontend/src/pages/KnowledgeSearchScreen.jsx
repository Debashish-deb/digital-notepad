import { useState } from 'react';
import { BookOpen, Search } from 'lucide-react';
import { fetchUnifiedSearch } from '@/services/searchApi.js';
import { groupHitsByBucket, navigateFromSearchHit } from '@/lib/searchHits.js';
import SearchAdvancedFilters, { advancedFiltersToSearchParams, emptyAdvancedFilters } from '@/features/search/components/SearchAdvancedFilters.jsx';
import SearchBucketGroup from '@/features/search/components/SearchBucketGroup.jsx';
import SearchFilterMetadata from '@/features/search/components/SearchFilterMetadata.jsx';
import SearchFilters, { SCOPE_OPTIONS } from '@/features/search/components/SearchFilters.jsx';
import '@/features/search/components/UnifiedSearch.css';

export default function KnowledgeSearchScreen({ title, description, onNavigate, onSelectProject }) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [scopes, setScopes] = useState(() => SCOPE_OPTIONS.map((s) => s.id));
  const [hits, setHits] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [advancedFilters, setAdvancedFilters] = useState(emptyAdvancedFilters);
  const [filtersApplied, setFiltersApplied] = useState({});
  const [unsupportedFilters, setUnsupportedFilters] = useState([]);
  const [cacheHit, setCacheHit] = useState(false);

  const runSearch = async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setBusy(true);
    setError(null);
    try {
      const data = await fetchUnifiedSearch({
        query: q,
        mode,
        scopes: scopes.join(','),
        limit: 30,
        ...advancedFiltersToSearchParams(advancedFilters),
      });
      setHits(Array.isArray(data?.hits) ? data.hits : []);
      setFiltersApplied(data?.filters_applied || {});
      setUnsupportedFilters(Array.isArray(data?.unsupported_filters) ? data.unsupported_filters : []);
      setCacheHit(Boolean(data?.metadata?.cache_hit));
    } catch (e) {
      setError(String(e.message || e));
      setHits([]);
    } finally {
      setBusy(false);
    }
  };

  const grouped = groupHitsByBucket(hits);

  return (
    <div className="stack-md">
      <div className="panel">
        <h3 className="panel-title">
          <BookOpen size={18} /> {title || 'Knowledge search'}
        </h3>
        <p className="panel-lead prose-block">
          {description || 'Unified platform search via /api/platform/unified-search.'}
        </p>
        <div className="disk-pad-toolbar" style={{ marginTop: '0.75rem' }}>
          <input
            type="search"
            className="input"
            placeholder="Query protocols, documents, vault metadata…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runSearch()}
          />
          <button type="button" className="btn btn-primary btn-sm" onClick={runSearch} disabled={busy}>
            <Search size={14} /> {busy ? 'Searching…' : 'Search'}
          </button>
        </div>
        <SearchFilters mode={mode} onModeChange={setMode} scopes={scopes} onScopesChange={setScopes} />
        <SearchAdvancedFilters value={advancedFilters} onChange={setAdvancedFilters} />
        <SearchFilterMetadata
          filtersApplied={filtersApplied}
          unsupportedFilters={unsupportedFilters}
          cacheHit={cacheHit}
        />
        {error && <p className="text-footnote citation-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p>}
      </div>

      {grouped.map((group) => (
        <div key={group.bucket} className="panel">
          <SearchBucketGroup
            group={group}
            query={query}
            onOpenHit={(hit) => {
              if (hit?.nav && onNavigate) {
                navigateFromSearchHit(hit.nav, onNavigate, onSelectProject);
              }
            }}
          />
        </div>
      ))}
    </div>
  );
}
