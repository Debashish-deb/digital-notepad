import { LayoutGrid, List, Loader2, PanelLeftClose, PanelLeftOpen, Search } from 'lucide-react';
import { DOMAIN_TABS } from '@/services/documentLibraryClient.js';
import { useModuleShellCover } from '@/contexts/ModuleShellCoverContext.jsx';
import useDocumentLibrary from '@/features/documents/hooks/useDocumentLibrary.js';
import DocumentFilterPanel from './DocumentFilterPanel.jsx';
import DocumentResultList from './DocumentResultList.jsx';
import DocumentMetadataPanel from './DocumentMetadataPanel.jsx';
import './ScientificFileExplorer.css';
import '@/features/overview/components/OverviewReadingPage.css';
import './DocumentExportMenu.css';
import './DocumentViewerExpand.css';
import './DocumentViewerToolbar.css';

export default function ScientificFileExplorer({
  title = 'Scientific File Explorer',
  subtitle = '',
  scopeLabel = '',
  initialDomainTab = 'all_files',
  taxonomyTab = 'all_files',
  initialSystemView = 'all_files',
  initialFilters = {},
  initialQuery = '',
  showDomainTabs = true,
  hideScopeFilters = false,
  scopeChipIds = null,
  layoutMode = 'split',
  className = '',
}) {
  const coverCtx = useModuleShellCover();
  const hideHeroText = Boolean(coverCtx?.showModuleCover);

  const library = useDocumentLibrary({
    initialDomainTab,
    taxonomyTab,
    initialSystemView,
    initialFilters,
    initialQuery,
    hideScopeFilters,
    layoutMode,
    coverCtx,
    hideHeroText,
  });

  const {
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
  } = library;

  const domainTabsNav = showDomainTabs ? (
    <nav className="sfe-domain-tabs" aria-label="Domain tabs">
      {DOMAIN_TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`sfe-domain-tab${domainTab === tab.id ? ' is-active' : ''}`}
          onClick={() => setDomainTab(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  ) : null;

  return (
    <div className={`sfe-root${isReadingLayout ? ' sfe-root--reading' : ''} ${className}`.trim()}>
      {!hideHeroText ? (
        <header className="sfe-hero">
          <div className="sfe-hero-text">
            <p className="sfe-hero-kicker">{scopeLabel || 'Document library'}</p>
            <h2 className="sfe-hero-title">{title}</h2>
            {subtitle ? <p className="sfe-hero-subtitle">{subtitle}</p> : null}
          </div>
          <div className="sfe-search-wrap sfe-search-wrap--hero">
            <Search size={18} aria-hidden />
            <input
              type="search"
              placeholder="Search filename, title, sample ID, tissue, assay, marker, owner, category…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Global search"
            />
          </div>
          {domainTabsNav}
        </header>
      ) : domainTabsNav ? (
        <div className="sfe-domain-tabs-bar">{domainTabsNav}</div>
      ) : null}

      <div className="sfe-workspace-controls">
        <div className="sfe-stats-bar" aria-live="polite">
          <span className="sfe-stat-pill">{displayTotal?.toLocaleString() ?? '—'} files{scopedStats ? ' in scope' : ''}</span>
          <span className="sfe-stat-pill sfe-stat-pill--warn">{audit.not_indexed ?? '—'} not indexed</span>
          <span className="sfe-stat-pill sfe-stat-pill--warn">{audit.pending_extraction ?? audit.needs_redigitalization ?? '—'} pending extraction</span>
          <span className="sfe-stat-pill">{audit.unknown_type ?? '—'} unknown type</span>
          <span className="sfe-stat-pill">{audit.duplicate_copies ?? audit.duplicate_groups ?? '—'} duplicates</span>
        </div>

        <DocumentFilterPanel
          facets={facets}
          filters={filters}
          onChange={setFilters}
          advancedOpen={advancedOpen}
          onToggleAdvanced={() => setAdvancedOpen((v) => !v)}
          onClear={handleClearFilters}
          hideScopeFilters={hideScopeFilters}
          scopeChips={scopeChips}
          scopeChipIds={scopeChipIds}
          systemView={systemView}
          onSystemView={setSystemView}
          stats={stats}
          scopedStats={scopedStats}
          initialFilters={initialFilters}
          scopeLabel={scopeLabel}
        />
      </div>

      <div
        className={[
          'sfe-body',
          isReadingLayout ? 'sfe-body--reading' : '',
          !isReadingLayout && listDetailExpanded ? 'sfe-body--list-expanded' : '',
          !isReadingLayout && !listDetailExpanded ? 'sfe-body--list-compact' : '',
        ].filter(Boolean).join(' ')}
      >
        <section className={`sfe-main${isReadingLayout || !listDetailExpanded ? ' sfe-main--list-compact' : ''}`}>
          {loadError ? (
            <div className="sfe-list-section sfe-list-section--alert">
              <div className="sfe-error-banner" role="alert">{loadError}</div>
            </div>
          ) : null}

          <div className="sfe-list-section sfe-list-section--controls">
            <div className="sfe-list-controls">
              <p className="sfe-list-controls__meta">
                <span className="sfe-list-controls__count">
                  {loading && !items.length
                    ? 'Loading…'
                    : `${total.toLocaleString()} results`}
                </span>
                {isRefreshing ? (
                  <span className="sfe-list-controls__refresh" aria-live="polite">
                    <Loader2 className="spin-inline" size={12} aria-hidden />
                    Updating…
                  </span>
                ) : null}
              </p>
              <div className="sfe-list-controls__tools" role="toolbar" aria-label="List options">
                <label className="sfe-list-controls__sort">
                  <span className="sfe-list-controls__sort-label">Sort</span>
                  <select
                    className="sfe-sort-select"
                    value={`${sort}:${order}`}
                    onChange={(e) => handleSortChange(e.target.value)}
                    aria-label="Sort files"
                  >
                    <option value="filename:asc">Name A–Z</option>
                    <option value="filename:desc">Name Z–A</option>
                    <option value="modified_at:desc">Newest</option>
                    <option value="modified_at:asc">Oldest</option>
                    <option value="size_bytes:desc">Largest</option>
                  </select>
                </label>
                {!isReadingLayout ? (
                  <button
                    type="button"
                    className={`sfe-list-controls__btn${listDetailExpanded ? ' is-active' : ''}`}
                    onClick={() => setListDetailExpanded((value) => !value)}
                    aria-expanded={listDetailExpanded}
                    title={listDetailExpanded ? 'Show names only' : 'Show file details'}
                    aria-label={listDetailExpanded ? 'Compact list' : 'Expand file list'}
                  >
                    {listDetailExpanded ? <PanelLeftClose size={14} aria-hidden /> : <PanelLeftOpen size={14} aria-hidden />}
                  </button>
                ) : null}
                <div className="sfe-view-toggle sfe-view-toggle--segmented" role="group" aria-label="View mode">
                  <button type="button" className={viewMode === 'table' ? 'is-active' : ''} onClick={() => setViewMode('table')} aria-label="Table view">
                    <List size={14} />
                  </button>
                  <button type="button" className={viewMode === 'card' ? 'is-active' : ''} onClick={() => setViewMode('card')} aria-label="Card view">
                    <LayoutGrid size={14} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="sfe-list-section sfe-list-section--files">
            {loading && !items.length ? (
              <div className="sfe-loading"><Loader2 className="spin-inline" size={20} /> Loading files…</div>
            ) : (
              <>
                <DocumentResultList
                  items={items}
                  viewMode={viewMode}
                  selectedId={selected?.asset_id}
                  onSelect={handleSelect}
                  listDetailExpanded={listDetailExpanded}
                  groupByDocumentType
                />
                {hasMore ? (
                  <div className="sfe-load-more">
                    <button
                      type="button"
                      className="sfe-load-more__btn"
                      onClick={loadMore}
                      disabled={loadingMore}
                    >
                      {loadingMore ? (
                        <>
                          <Loader2 className="spin-inline" size={16} aria-hidden />
                          Loading more…
                        </>
                      ) : (
                        `Load more (${items.length} of ${total})`
                      )}
                    </button>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </section>
        <DocumentMetadataPanel
          assetId={selected?.asset_id}
          pinned={selected ? pinnedIds.includes(selected.asset_id) : false}
          onTogglePin={handleTogglePin}
          layoutMode={layoutMode}
        />
      </div>
    </div>
  );
}
