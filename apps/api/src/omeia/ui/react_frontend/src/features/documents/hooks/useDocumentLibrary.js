import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchDocumentLibraryFacets,
  fetchDocumentLibraryStats,
  loadPinnedIds,
  pushRecentId,
  searchDocumentLibrary,
  togglePinnedId,
} from '@/services/documentLibraryClient.js';
import { consumeSearchNavigation } from '@/lib/searchHits.js';
import { filterClientView } from '@/features/documents/documentLibraryUi.js';

/** Initial page size — keeps first open fast; API supports offset/limit up to 5000. */
const DOCUMENT_LIBRARY_PAGE_SIZE = 200;

export default function useDocumentLibrary({
  initialDomainTab = 'all_files',
  taxonomyTab = 'all_files',
  initialSystemView = 'all_files',
  initialFilters = {},
  initialQuery = '',
  hideScopeFilters = false,
  layoutMode = 'split',
  coverCtx = null,
  hideHeroText = false,
}) {
  const isReadingLayout = layoutMode === 'reading';
  const [domainTab, setDomainTab] = useState(initialDomainTab);
  const [systemView, setSystemView] = useState(initialSystemView);
  const [query, setQuery] = useState(initialQuery);
  const [debouncedQ, setDebouncedQ] = useState(initialQuery);
  const [filters, setFilters] = useState(initialFilters);
  const [loadError, setLoadError] = useState(null);
  const [facets, setFacets] = useState(null);
  const [stats, setStats] = useState(null);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selected, setSelected] = useState(null);
  const [viewMode, setViewMode] = useState('table');
  const [sort, setSort] = useState('filename');
  const [order, setOrder] = useState('asc');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [listDetailExpanded, setListDetailExpanded] = useState(false);
  const [pinnedIds, setPinnedIds] = useState(() => loadPinnedIds());

  useEffect(() => {
    const register = coverCtx?.setSubsectionSearch;
    if (!register) return undefined;
    if (!hideHeroText) {
      register(null);
      return undefined;
    }
    return () => register(null);
  }, [coverCtx?.setSubsectionSearch, hideHeroText]);

  useEffect(() => {
    const register = coverCtx?.setSubsectionSearch;
    if (!hideHeroText || !register) return;
    register({
      value: query,
      onChange: setQuery,
      placeholder: 'Search files…',
      ariaLabel: 'Search document library',
    });
  }, [coverCtx?.setSubsectionSearch, hideHeroText, query]);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(query.trim()), 280);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    fetchDocumentLibraryStats().then(setStats).catch(() => setStats(null));
  }, []);

  useEffect(() => {
    if (filters.subcategory && filters.category && facets?.facets?.subcategory) {
      const allowed = facets.facets.subcategory[filters.subcategory];
      if (allowed === undefined) {
        setFilters((prev) => ({ ...prev, subcategory: undefined }));
      }
    }
  }, [filters.category, filters.subcategory, facets]);

  const effectiveDomainTab = domainTab === 'all_files' ? undefined : (taxonomyTab || domainTab);

  const facetParams = useMemo(() => ({
    q: debouncedQ,
    domain_tab: effectiveDomainTab === 'all_files' ? undefined : effectiveDomainTab,
    system_view: ['recently_opened', 'pinned'].includes(systemView) ? undefined : (systemView === 'all_files' ? undefined : systemView),
    sort,
    order,
    ...filters,
  }), [debouncedQ, effectiveDomainTab, systemView, sort, order, filters]);

  const searchParams = useMemo(() => ({
    ...facetParams,
    offset: 0,
    limit: DOCUMENT_LIBRARY_PAGE_SIZE,
  }), [facetParams]);

  useEffect(() => {
    setOffset(0);
  }, [facetParams, systemView]);

  useEffect(() => {
    let alive = true;
    fetchDocumentLibraryFacets(facetParams)
      .then((facetRes) => {
        if (alive) setFacets(facetRes);
      })
      .catch(() => {
        if (alive) setFacets(null);
      });
    return () => { alive = false; };
  }, [facetParams]);

  useEffect(() => {
    let alive = true;
    const isInitialLoad = offset === 0;
    if (isInitialLoad) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }
    if (isInitialLoad) {
      setLoadError(null);
    }
    const params = { ...facetParams, offset, limit: DOCUMENT_LIBRARY_PAGE_SIZE };
    searchDocumentLibrary(params)
      .then((searchRes) => {
        if (!alive) return;
        let rows = searchRes.items || [];
        rows = filterClientView(rows, systemView);
        setItems((prev) => (offset === 0 ? rows : [...prev, ...rows]));
        setTotal(systemView === 'recently_opened' || systemView === 'pinned' ? rows.length : searchRes.total || 0);
      })
      .catch((err) => {
        if (!alive) return;
        if (offset === 0) {
          setItems([]);
          setTotal(0);
          setLoadError(err?.message || 'Could not load document library.');
        }
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
        setIsRefreshing(false);
        setLoadingMore(false);
      });
    return () => { alive = false; };
  }, [facetParams, systemView, offset]);

  useEffect(() => {
    if (loading || !items.length) return;
    const pending = consumeSearchNavigation();
    if (!pending) return;
    const targetPath = String(pending.relative_path || pending.query || '')
      .trim()
      .replace(/^\/+/, '');
    if (targetPath) {
      const basename = targetPath.split('/').pop();
      if (basename && basename !== targetPath) {
        setQuery(basename);
      } else if (pending.query && pending.main !== 'document_library') {
        setQuery(String(pending.query));
      }
      const match = items.find((item) => {
        const logical = String(item.logical_path || '').replace(/^\/+/, '');
        return logical === targetPath
          || logical.endsWith(`/${targetPath}`)
          || targetPath.endsWith(logical);
      });
      if (match) setSelected(match);
    } else if (pending.query) {
      setQuery(String(pending.query));
    }
  }, [loading, items]);

  const handleSelect = useCallback((item) => {
    setSelected(item);
    pushRecentId(item.asset_id);
  }, []);

  useEffect(() => {
    if (!isReadingLayout || selected || loading || !items.length) return;
    setSelected(items[0]);
  }, [isReadingLayout, items, selected, loading]);

  const handleSortChange = useCallback((value) => {
    const [s, o] = value.split(':');
    setSort(s);
    setOrder(o);
  }, []);

  const handleTogglePin = useCallback(() => {
    if (!selected) return;
    const next = togglePinnedId(selected.asset_id);
    setPinnedIds(next);
  }, [selected]);

  const handleClearFilters = useCallback(() => {
    setFilters(
      hideScopeFilters
        ? Object.fromEntries(Object.entries(initialFilters).filter(([, v]) => v != null && v !== ''))
        : {},
    );
  }, [hideScopeFilters, initialFilters]);

  const hasMore = useMemo(() => {
    if (systemView === 'recently_opened' || systemView === 'pinned') return false;
    return items.length < total;
  }, [items.length, total, systemView]);

  const loadMore = useCallback(() => {
    if (loadingMore || loading || !hasMore) return;
    setIsRefreshing(true);
    setOffset((prev) => prev + DOCUMENT_LIBRARY_PAGE_SIZE);
  }, [hasMore, loading, loadingMore]);

  const scopedStats = facets?.scoped_stats;
  const scopeChips = facets?.scope_chips || [];
  const scopedAudit = scopedStats?.audit_counts;
  const displayTotal = scopedStats?.total_files ?? stats?.total_files;
  const audit = scopedAudit || stats?.audit_counts || {};

  return {
    isReadingLayout,
    domainTab,
    setDomainTab,
    systemView,
    setSystemView,
    query,
    setQuery,
    filters,
    setFilters,
    loadError,
    facets,
    stats,
    items,
    total,
    loading,
    isRefreshing,
    loadingMore,
    hasMore,
    loadMore,
    selected,
    viewMode,
    setViewMode,
    sort,
    order,
    advancedOpen,
    setAdvancedOpen,
    listDetailExpanded,
    setListDetailExpanded,
    pinnedIds,
    handleSelect,
    handleSortChange,
    handleTogglePin,
    handleClearFilters,
    scopedStats,
    scopeChips,
    displayTotal,
    audit,
  };
}
