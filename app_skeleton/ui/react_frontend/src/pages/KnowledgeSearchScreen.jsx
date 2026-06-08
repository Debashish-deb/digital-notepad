import { BookOpen, Search } from 'lucide-react';
import { groupHitsByBucket, navigateFromSearchHit } from '@/lib/searchHits.js';
import SearchAdvancedFilters from '@/features/search/components/SearchAdvancedFilters.jsx';
import SearchBucketGroup from '@/features/search/components/SearchBucketGroup.jsx';
import SearchFilterMetadata from '@/features/search/components/SearchFilterMetadata.jsx';
import SearchFilters from '@/features/search/components/SearchFilters.jsx';
import useUnifiedSearch from '@/features/search/hooks/useUnifiedSearch.js';
import '@/features/search/components/UnifiedSearch.css';

export default function KnowledgeSearchScreen({ title, description, onNavigate, onSelectProject }) {
  const {
    query,
    setQuery,
    mode,
    setMode,
    scopes,
    setScopes,
    hits,
    error,
    loading,
    advancedFilters,
    setAdvancedFilters,
    filtersApplied,
    unsupportedFilters,
    cacheHit,
    runSearch,
  } = useUnifiedSearch({ trigger: 'manual' });

  const handleSearch = () => runSearch();

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
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button type="button" className="btn btn-primary btn-sm" onClick={handleSearch} disabled={loading}>
            <Search size={14} /> {loading ? 'Searching…' : 'Search'}
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
