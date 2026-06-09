import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  FileText,
  FolderOpen,
  FolderTree,
  LayoutGrid,
  List,
  Loader2,
  NotebookPen,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Users,
} from 'lucide-react';
import DocumentFolderTree from '@/features/documents/components/DocumentFolderTree.jsx';
import DocumentFolderBreadcrumb from '@/features/documents/components/DocumentFolderBreadcrumb.jsx';
import DocumentResultList from '@/features/documents/components/DocumentResultList.jsx';
import DocumentMetadataPanel from '@/features/documents/components/DocumentMetadataPanel.jsx';
import useDocumentLibrary from '@/features/documents/hooks/useDocumentLibrary.js';
import { fetchCategoryTrees } from '@/services/documentLibraryClient.js';
import ProjectBrandMark from './ProjectBrandMark.jsx';
import ProjectCoverTeamStrip from './ProjectCoverTeamStrip.jsx';
import {
  findFolderTreeNode,
  projectFolderScopeLabel,
  projectFolderTreeRoot,
  summarizeProjectFolderTree,
} from '@/lib/projectFolderPage.js';
import './ProjectFolderPage.css';
import '@/features/documents/components/ScientificFileExplorer.css';

const STATUS_STYLES = {
  active: { label: 'Active', bg: 'rgba(45,212,191,0.12)', color: 'var(--color-success)' },
  completed: { label: 'Completed', bg: 'rgba(96,165,250,0.12)', color: '#60a5fa' },
  discontinued: { label: 'Discontinued', bg: 'rgba(148,163,184,0.12)', color: 'var(--text-muted)' },
  archived: { label: 'Archived', bg: 'rgba(148,163,184,0.12)', color: 'var(--text-muted)' },
};

const SECTION_TABS = [
  { id: 'files', label: 'Files', icon: FolderOpen },
  { id: 'notes', label: 'Notes', icon: NotebookPen, stub: true },
  { id: 'activity', label: 'Activity', icon: Activity, stub: true },
];

function ProjectFolderHeader({
  projectCode,
  projectData,
  twin,
  folderSummary,
  displayTotal,
}) {
  const identity = twin?.identity || {};
  const projectName = projectData?.project_name || identity.project_name || projectCode;
  const statusKey = String(projectData?.status || identity.status || 'active').toLowerCase();
  const status = STATUS_STYLES[statusKey] || STATUS_STYLES.active;
  const summary = (
    projectData?.project_summary ||
    identity.project_summary ||
    projectData?.research_question ||
    ''
  ).trim();
  const fileTotal = displayTotal ?? folderSummary.fileCount;

  return (
    <header className="pfp-header" aria-label="Project hub">
      <div className="pfp-header-main">
        <div className="pfp-header-title-row">
          <ProjectBrandMark
            code={projectCode}
            index={projectData?.project_index ?? identity.project_index}
            name={projectName}
            variant="card"
          />
          <h2 className="pfp-header-title">{projectName}</h2>
          <span className="pfp-header-code">{projectCode}</span>
          <span
            className="pfp-status-badge"
            style={{ background: status.bg, color: status.color }}
          >
            {status.label}
          </span>
        </div>
        {summary ? <p className="pfp-header-summary">{summary}</p> : null}
        <div className="pfp-header-stats" aria-label="Project file statistics">
          <span className="pfp-stat-pill">
            <FolderTree size={13} aria-hidden />
            {folderSummary.folderCount} folders
          </span>
          <span className="pfp-stat-pill">
            <FileText size={13} aria-hidden />
            {Number(fileTotal).toLocaleString()} files indexed
          </span>
          {projectData?.project_lead || identity.project_lead ? (
            <span className="pfp-stat-pill">
              <Users size={13} aria-hidden />
              Lead: {projectData?.project_lead || identity.project_lead}
            </span>
          ) : null}
        </div>
      </div>
      {twin?.personnel?.length || twin?.identity ? (
        <div className="pfp-header-team">
          <ProjectCoverTeamStrip personnel={twin.personnel} identity={twin.identity} />
        </div>
      ) : null}
    </header>
  );
}

function FolderContextMeta({ selectedFolderPath, folderTreeNodes }) {
  const folderNode = findFolderTreeNode(folderTreeNodes, selectedFolderPath);
  if (!folderNode) return null;
  return (
    <p className="pfp-folder-meta text-footnote muted">
      <strong>{folderNode.label}</strong>
      {' · '}
      {folderNode.file_count ?? 0} indexed file{(folderNode.file_count ?? 0) === 1 ? '' : 's'}
    </p>
  );
}

export default function ProjectFolderPage({
  projectCode,
  projectData,
  twin,
  onOpenNotebook,
}) {
  const [sectionTab, setSectionTab] = useState('files');
  const folderTreeRoot = useMemo(() => projectFolderTreeRoot(projectCode), [projectCode]);
  const scopeLabel = projectFolderScopeLabel(
    projectData?.project_name || twin?.identity?.project_name,
    projectCode,
  );

  const [categoryTrees, setCategoryTrees] = useState(null);
  const [treesLoading, setTreesLoading] = useState(true);
  const [treesError, setTreesError] = useState(null);

  const library = useDocumentLibrary({
    initialDomainTab: 'projects',
    taxonomyTab: 'projects',
    initialSystemView: 'all_files',
    initialFilters: {},
    hideScopeFilters: true,
    layoutMode: 'split',
    folderTreeRoot,
  });

  const {
    query,
    setQuery,
    loadError,
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
    handleSortChange,
    handleSelect,
    pinnedIds,
    handleTogglePin,
    displayTotal,
    selectedFolderPath,
    handleSelectFolder,
    listDetailExpanded,
    setListDetailExpanded,
  } = library;

  useEffect(() => {
    let alive = true;
    setTreesLoading(true);
    fetchCategoryTrees()
      .then((data) => {
        if (!alive) return;
        setCategoryTrees(data);
        setTreesError(null);
      })
      .catch((err) => {
        if (!alive) return;
        setCategoryTrees(null);
        setTreesError(err?.message || 'Could not load folder tree.');
      })
      .finally(() => {
        if (alive) setTreesLoading(false);
      });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (folderTreeRoot) handleSelectFolder(folderTreeRoot);
  }, [folderTreeRoot, projectCode, handleSelectFolder]);

  const folderTreeNodes = useMemo(
    () => categoryTrees?.category_tree_folder_derived?.nodes || [],
    [categoryTrees],
  );

  const folderSummary = useMemo(
    () => summarizeProjectFolderTree(folderTreeNodes, folderTreeRoot),
    [folderTreeNodes, folderTreeRoot],
  );

  const groupByDocumentType = !selectedFolderPath;
  const showFolderTree = folderTreeNodes.length > 0;

  if (!folderTreeRoot) {
    return (
      <div className="panel text-empty">
        <p>Project code is required to browse folders.</p>
      </div>
    );
  }

  return (
    <section className="panel workspace-section pfp-root" aria-label="Project folder hub">
      <ProjectFolderHeader
        projectCode={projectCode}
        projectData={projectData}
        twin={twin}
        folderSummary={folderSummary}
        displayTotal={displayTotal}
      />

      <nav className="pfp-section-tabs" aria-label="Project hub sections">
        {SECTION_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              className={`pfp-section-tab${sectionTab === tab.id ? ' is-active' : ''}`}
              onClick={() => setSectionTab(tab.id)}
              aria-current={sectionTab === tab.id ? 'page' : undefined}
            >
              <Icon size={14} aria-hidden />
              {tab.label}
              {tab.stub ? ' (soon)' : null}
            </button>
          );
        })}
      </nav>

      {sectionTab === 'notes' ? (
        <div className="pfp-stub-panel">
          <h3>Project notes</h3>
          <p>
            Structured experiment notes live in the Living notebook tab.
            {onOpenNotebook ? ' Open it from here when you are ready to draft protocols or wiki pages.' : ''}
          </p>
          {onOpenNotebook ? (
            <button type="button" className="btn btn-primary btn-sm" style={{ marginTop: '0.75rem' }} onClick={onOpenNotebook}>
              Open living notebook
            </button>
          ) : null}
        </div>
      ) : null}

      {sectionTab === 'activity' ? (
        <div className="pfp-stub-panel">
          <h3>Activity feed</h3>
          <p>
            Full audit trails (SciNote task activity / Benchling entry history pattern) will surface
            scan events, file uploads, and notebook edits here. Until then, use the sidebar on the Files tab.
          </p>
        </div>
      ) : null}

      {sectionTab === 'files' ? (
        <div className="pfp-body sfe-body sfe-body--with-tree">
          {showFolderTree ? (
            <DocumentFolderTree
              nodes={folderTreeNodes}
              rootPrefix={folderTreeRoot}
              selectedPath={selectedFolderPath}
              onSelect={handleSelectFolder}
              loading={treesLoading}
              error={treesError}
            />
          ) : null}

          <section className="pfp-main sfe-main" aria-label="Project files">
            {selectedFolderPath ? (
              <div className="sfe-list-section sfe-list-section--breadcrumb">
                <DocumentFolderBreadcrumb
                  selectedPath={selectedFolderPath}
                  rootPrefix={folderTreeRoot}
                  scopeLabel={scopeLabel}
                  onNavigate={handleSelectFolder}
                />
                <FolderContextMeta
                  selectedFolderPath={selectedFolderPath}
                  folderTreeNodes={folderTreeNodes}
                />
              </div>
            ) : null}

            <div className="pfp-main-toolbar">
              <label className="pfp-search">
                <Search size={14} aria-hidden />
                <input
                  type="search"
                  placeholder="Search files in this project…"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  aria-label="Search project files"
                />
              </label>
              <label className="sfe-list-controls__sort">
                <span className="sfe-list-controls__sort-label">Sort</span>
                <select
                  className="sfe-sort-select"
                  value={`${sort}:asc`}
                  onChange={(event) => handleSortChange(event.target.value)}
                  aria-label="Sort files"
                >
                  <option value="filename:asc">Name A–Z</option>
                  <option value="filename:desc">Name Z–A</option>
                  <option value="modified_at:desc">Newest</option>
                  <option value="size_bytes:desc">Largest</option>
                </select>
              </label>
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
              <div className="sfe-view-toggle sfe-view-toggle--segmented" role="group" aria-label="View mode">
                <button
                  type="button"
                  className={viewMode === 'table' ? 'is-active' : ''}
                  onClick={() => setViewMode('table')}
                  aria-label="Table view"
                >
                  <List size={14} />
                </button>
                <button
                  type="button"
                  className={viewMode === 'card' ? 'is-active' : ''}
                  onClick={() => setViewMode('card')}
                  aria-label="Card view"
                >
                  <LayoutGrid size={14} />
                </button>
              </div>
              {isRefreshing ? (
                <span className="text-footnote muted">
                  <Loader2 size={12} className="spin-inline" aria-hidden /> Updating…
                </span>
              ) : null}
            </div>

            <div className="pfp-main-content sfe-list-section sfe-list-section--files">
              {loadError ? (
                <div className="sfe-error-banner" role="alert">{loadError}</div>
              ) : null}

              {!treesLoading && !folderSummary.hasTree ? (
                <div className="pfp-empty">
                  <FolderOpen size={28} className="muted" aria-hidden style={{ marginBottom: '0.5rem' }} />
                  <p>No indexed folders under <code>{folderTreeRoot}</code> yet.</p>
                  <p className="text-footnote muted">Run Scan project folder to index this workspace.</p>
                </div>
              ) : loading && !items.length ? (
                <div className="sfe-loading"><Loader2 className="spin-inline" size={20} /> Loading files…</div>
              ) : (
                <>
                  <p className="text-footnote muted" style={{ margin: '0 0 0.35rem 0.35rem' }}>
                    {total.toLocaleString()} result{total === 1 ? '' : 's'}
                    {selectedFolderPath ? ' in folder' : ''}
                  </p>
                  <DocumentResultList
                    items={items}
                    viewMode={viewMode}
                    selectedId={selected?.asset_id}
                    onSelect={handleSelect}
                    listDetailExpanded={listDetailExpanded}
                    groupByDocumentType={groupByDocumentType}
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
            layoutMode="split"
          />
        </div>
      ) : null}
    </section>
  );
}
