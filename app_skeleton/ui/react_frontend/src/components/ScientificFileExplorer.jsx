import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Database,
  FileCode,
  FileSpreadsheet,
  FileText,
  FileType,
  Film,
  Image,
  Info,
  LayoutGrid,
  List,
  Loader2,
  PanelLeftClose,
  PanelLeftOpen,
  Pin,
  Search,
  ExternalLink,
} from 'lucide-react';
import TaxonomyConnectorMap from './TaxonomyConnectorMap.jsx';
import {
  DOMAIN_TABS,
  SYSTEM_VIEWS,
  fetchDocumentLibraryFacets,
  fetchDocumentLibraryStats,
  fetchDocumentPreview,
  formatBytes,
  loadPinnedIds,
  loadRecentIds,
  pushRecentId,
  searchDocumentLibrary,
  togglePinnedId,
} from '../api/documentLibraryClient.js';
import { buildViewerHash, loadThumbnailBlobUrl } from '../api/imageAssetsClient.js';
import { getMediaPreviewKind } from '../utils/mediaPreviewKind.js';
import { getFilePreviewKind, inferCodeLanguage } from '../utils/filePreviewKind.js';
import { useSpreadsheetPreview } from '../hooks/useSpreadsheetPreview.js';
import { useRawFilePreview } from '../hooks/useRawFilePreview.js';
import { apiSpreadsheetSheetsToModels } from '../utils/spreadsheetPreview.js';
import { smartDocumentTitle, documentTitleSubline } from '../utils/smartDocumentTitle.js';
import DocumentFormatter from './DocumentFormatter.jsx';
import SpreadsheetPreview from './SpreadsheetPreview.jsx';
import CodePreview from './CodePreview.jsx';
import MediaViewer from './MediaViewer.jsx';
import DocumentExportMenu from './DocumentExportMenu.jsx';
import DocumentProofreadPanel from './DocumentProofreadPanel.jsx';
import { DocumentViewerExpandButton, DocumentViewerExpandPortal } from './DocumentViewerExpand.jsx';
import {
  DocumentViewerMetaChip,
  DocumentViewerToolButton,
  DocumentViewerToolbar,
} from './DocumentViewerToolbar.jsx';
import { useModuleShellCover } from '../contexts/ModuleShellCoverContext.jsx';
import { consumeSearchNavigation } from '../utils/searchHits.js';
import { useResizableGridColumns } from '../utils/useResizableGridColumns.js';
import './ScientificFileExplorer.css';
import './OverviewReadingPage.css';
import './DocumentExportMenu.css';
import './DocumentViewerExpand.css';
import './DocumentViewerToolbar.css';

const ROW_HEIGHT = 52;
const CARD_HEIGHT = 100;

const SFE_LIST_COLUMNS = [
  { id: 'name', label: 'Name', defaultWidth: 300, minWidth: 140, maxWidth: 720 },
  { id: 'category', label: 'Category', defaultWidth: 140, minWidth: 72, maxWidth: 360 },
  { id: 'size', label: 'Size', defaultWidth: 76, minWidth: 56, maxWidth: 140 },
  { id: 'modified', label: 'Modified', defaultWidth: 100, minWidth: 80, maxWidth: 160 },
  { id: 'status', label: 'Status', defaultWidth: 128, minWidth: 96, maxWidth: 220 },
];
const SFE_COLUMN_WIDTHS_KEY = 'sfe-file-list-column-widths';

function StatusBadges({ item }) {
  const badges = [];
  if (item.indexed_in_search) badges.push(['Indexed', 'indexed']);
  else if (item.digitalization_status === 'indexed') badges.push(['Indexed', 'indexed']);
  else if (item.digitalization_status === 'metadata_only') badges.push(['Metadata only', 'metadata_only']);
  else if (item.has_extracted_content) badges.push(['Extracted', 'partial']);
  else if (item.digitalization_status === 'needs_redigitalization') badges.push(['Needs redigitalization', 'needs_redigitalization']);
  else if (item.digitalization_status === 'pending_extraction') badges.push(['Pending extraction', 'not_started']);
  else if (item.digitalization_status === 'failed') badges.push(['Extraction failed', 'warn']);
  else if (item.digitalization_status === 'not_started') badges.push(['Not indexed', 'not_started']);
  else badges.push(['Not indexed', 'not_started']);
  if (item.preview_status === 'missing' && item.digitalization_status !== 'metadata_only') {
    badges.push(['Preview missing', 'warn']);
  }
  if (item.duplicate_status === 'duplicate') badges.push(['Duplicate', 'duplicate']);
  if (item.unknown_type) badges.push(['Unknown type', 'unknown']);
  if (item.needs_review) badges.push(['Needs review', 'review']);
  const visible = badges.slice(0, 3);
  return (
    <span className="sfe-badges">
      {visible.map(([label, cls]) => (
        <span key={label} className={`sfe-badge sfe-badge--${cls}`}>{label}</span>
      ))}
    </span>
  );
}

function FilterBar({
  facets,
  filters,
  onChange,
  advancedOpen,
  onToggleAdvanced,
  onClear,
  hideScopeFilters = false,
  scopeChips = [],
  scopeChipIds = null,
  scopeLabel = '',
  systemView = 'all_files',
  onSystemView,
  stats = null,
  scopedStats = null,
  initialFilters = {},
}) {
  const facet = facets?.facets || {};
  const set = (key, value) => onChange({ ...filters, [key]: value || undefined });
  const setCategory = (value) => onChange({
    ...filters,
    category: value || undefined,
    subcategory: undefined,
  });
  const activeCount = Object.values(filters).filter((v) => v !== undefined && v !== '').length;
  const subcategoryOptions = filters.category ? (facet.subcategory || {}) : {};

  return (
    <div className="sfe-filter-bar" aria-label="Filters">
      <div className="sfe-filter-bar__primary">
        {!hideScopeFilters ? (
          <FilterSelect compact label="Domain" value={filters.domain} options={facet.domain} onChange={(v) => set('domain', v)} />
        ) : null}
        <FilterSelect compact label="Category" value={filters.category} options={facet.category} onChange={setCategory} />
        <FilterSelect
          compact
          label="Subcategory"
          value={filters.subcategory}
          options={subcategoryOptions}
          onChange={(v) => set('subcategory', v)}
          disabled={!filters.category}
          placeholder={filters.category ? 'Any' : 'Select category first'}
        />
        <FilterSelect compact label="File type" value={filters.file_type} options={facet.file_type} onChange={(v) => set('file_type', v)} />
        <FilterSelect compact label="Digitalization" value={filters.digitalization_status} options={facet.digitalization_status} onChange={(v) => set('digitalization_status', v)} />
        <FilterSelect compact label="Preview" value={filters.preview_status} options={facet.preview_status} onChange={(v) => set('preview_status', v)} />
        <FilterSelect compact label="Duplicates" value={filters.duplicate_status} options={facet.duplicate_status} onChange={(v) => set('duplicate_status', v)} />
        <label className="sfe-filter-inline">
          <span>Unknown</span>
          <select
            value={filters.unknown_type === true ? 'yes' : ''}
            onChange={(e) => set('unknown_type', e.target.value === 'yes' ? true : undefined)}
          >
            <option value="">Any</option>
            <option value="yes">Only</option>
          </select>
        </label>
        <button type="button" className="sfe-filter-advanced-toggle" onClick={onToggleAdvanced}>
          {advancedOpen ? 'Less filters' : 'More filters'}
        </button>
        {activeCount > 0 ? (
          <button type="button" className="sfe-filter-clear" onClick={onClear}>Clear ({activeCount})</button>
        ) : null}
      </div>

      <TaxonomyFilterRail
        facets={facets}
        filters={filters}
        onFilterChange={onChange}
        hideScopeFilters={hideScopeFilters}
        scopeChips={scopeChips}
        scopeChipIds={scopeChipIds}
        scopeLabel={scopeLabel}
        systemView={systemView}
        onSystemView={onSystemView}
        stats={stats}
        scopedStats={scopedStats}
        initialFilters={initialFilters}
      />

      {advancedOpen ? (
        <div className="sfe-filter-bar__advanced">
          <SystemViewFilterRail
            systemView={systemView}
            onSystemView={onSystemView}
            onFilterChange={onChange}
            filters={filters}
            stats={stats}
            scopedStats={scopedStats}
          />
          <div className="sfe-filter-bar__advanced-fields">
            <FilterSelect compact label="Project" value={filters.project} options={facets?.project} onChange={(v) => set('project', v)} />
            <FilterSelect compact label="Assay" value={filters.assay} options={facets?.assay} onChange={(v) => set('assay', v)} />
            <FilterSelect compact label="Tissue" value={filters.tissue} options={facets?.tissue} onChange={(v) => set('tissue', v)} />
            <FilterSelect compact label="Marker" value={filters.marker} options={facets?.marker} onChange={(v) => set('marker', v)} />
            <label className="sfe-filter-inline">
              <span>Modified after</span>
              <input
                type="date"
                value={filters.modified_after?.slice(0, 10) || ''}
                onChange={(e) => set('modified_after', e.target.value ? `${e.target.value}T00:00:00` : undefined)}
              />
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function FilterSelect({
  label, value, options, onChange, compact = false, disabled = false, placeholder = 'Any',
}) {
  const entries = Object.entries(options || {}).sort((a, b) => b[1] - a[1]);
  return (
    <label className={`sfe-filter-inline${compact ? ' sfe-filter-inline--compact' : ''}${disabled ? ' is-disabled' : ''}`}>
      <span>{label}</span>
      <select
        value={value || ''}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value || undefined)}
      >
        <option value="">{placeholder}</option>
        {entries.slice(0, 80).map(([k, count]) => (
          <option key={k} value={k}>{prettifyCategory(k)} ({count})</option>
        ))}
      </select>
    </label>
  );
}

function MetadataSection({ title, children }) {
  if (!children) return null;
  return (
    <section className="sfe-preview-section">
      <h4 className="sfe-preview-section__title">{title}</h4>
      {children}
    </section>
  );
}

function MetaCell({ label, value }) {
  if (value == null || value === '' || (Array.isArray(value) && !value.length)) return null;
  const display = Array.isArray(value) ? value.join(', ') : String(value);
  return (
    <div className="sfe-meta-cell">
      <span className="sfe-meta-cell__label">{label}</span>
      <span className="sfe-meta-cell__value">{display}</span>
    </div>
  );
}

const MAINTENANCE_CHIP_IDS = [
  'all_files',
  'not_indexed',
  'needs_redigitalization',
  'duplicates',
  'unknown_type',
  'large_files',
];

function prettifyCategory(value) {
  return (value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

function extensionFromListItem(item) {
  let ext = (item?.extension || item?.metadata?.extension || '').toLowerCase();
  if (!ext && item?.filename) {
    const match = item.filename.match(/\.[^.]+$/i);
    if (match) ext = match[0].toLowerCase();
  }
  if (!ext && item?.logical_path) {
    const match = item.logical_path.match(/\.[^.]+$/i);
    if (match) ext = match[0].toLowerCase();
  }
  if (ext && !ext.startsWith('.')) ext = `.${ext}`;
  return ext;
}

function resolveFileBulletKind(item) {
  const ext = extensionFromListItem(item);
  const fileType = item?.file_type || item?.metadata?.file_type;
  if (fileType === 'image' || getMediaPreviewKind(ext) === 'image') return 'image';
  if (fileType === 'video' || getMediaPreviewKind(ext) === 'video') return 'video';

  const previewKind = getFilePreviewKind(ext, item?.logical_path);
  if (previewKind === 'spreadsheet') return 'spreadsheet';
  if (previewKind === 'code' || previewKind === 'json') return 'code';
  if (ext === '.pdf') return 'pdf';
  if (previewKind === 'text') return 'text';
  if (['.csv', '.tsv', '.parquet'].includes(ext)) return 'data';
  return 'document';
}

const FILE_BULLET_ICONS = {
  document: FileText,
  pdf: FileType,
  spreadsheet: FileSpreadsheet,
  image: Image,
  video: Film,
  code: FileCode,
  text: FileText,
  data: Database,
};

function FileListBullet({ item, selected = false }) {
  const kind = resolveFileBulletKind(item);
  const Icon = FILE_BULLET_ICONS[kind] || FileText;
  const indexed = Boolean(
    item?.indexed_in_search
    || item?.digitalization_status === 'indexed'
    || item?.has_extracted_content,
  );

  return (
    <span
      className={[
        'sfe-file-marker',
        `sfe-file-marker--${kind}`,
        selected ? 'is-selected' : '',
        indexed ? 'is-indexed' : '',
      ].filter(Boolean).join(' ')}
      aria-hidden
    >
      <span className="sfe-file-marker__stem" />
      <span className="sfe-file-marker__glass">
        <Icon size={12} strokeWidth={2} />
      </span>
    </span>
  );
}

function extensionFromPreview(preview) {
  const md = preview?.metadata || {};
  let ext = (md.extension || preview?.extension || '').toLowerCase();
  if (!ext && preview?.filename) {
    const match = preview.filename.match(/\.[^.]+$/i);
    if (match) ext = match[0].toLowerCase();
  }
  if (ext && !ext.startsWith('.')) ext = `.${ext}`;
  return ext;
}

function resolvePreviewMedia(preview) {
  if (!preview) return null;
  const md = preview.metadata || {};
  const extension = extensionFromPreview(preview);
  const kind =
    getMediaPreviewKind(extension) ||
    (md.file_type === 'image' ? 'image' : md.file_type === 'video' ? 'video' : null);
  if (!kind) return null;

  const logical = preview.logical_path || md.logical_path;
  const url =
    preview.preview_url ||
    (logical ? `/database-static/${logical.split('/').map(encodeURIComponent).join('/')}` : null);
  if (!url) return null;

  return { kind, url, extension };
}

const SCOPE_OVERLAY_FILTER_KEYS = ['protocol_category', 'reagent_category', 'smart_chip', 'file_type'];

function scopeChipToFilters(chip, baseFilters) {
  const next = { ...baseFilters };
  SCOPE_OVERLAY_FILTER_KEYS.forEach((key) => delete next[key]);
  const chipFilter = chip.filter || {};
  Object.entries(chipFilter).forEach(([key, value]) => {
    if (key === 'system_view') return;
    if (value === undefined || value === null || value === '') {
      delete next[key];
    } else {
      next[key] = value;
    }
  });
  return next;
}

function TaxonomyFilterCard({ chip, active, onClick }) {
  return (
    <button
      type="button"
      className={`sfe-taxonomy-card sfe-taxonomy-card--${chip.kind}${active ? ' is-active' : ''}`}
      onClick={() => onClick(chip)}
      title={chip.description || chip.label}
      aria-pressed={active}
    >
      <span className="sfe-taxonomy-card__label">{chip.label}</span>
      {chip.count != null ? (
        <span className="sfe-taxonomy-card__count">{chip.count.toLocaleString()}</span>
      ) : null}
    </button>
  );
}

function FilterChipGroup({ label, hint, chips, isChipActive, onChipClick, layout = 'grid' }) {
  if (!chips.length) return null;

  const layoutClass = layout === 'strip'
    ? 'sfe-taxonomy-strip'
    : layout === 'row'
      ? 'sfe-taxonomy-row'
      : 'sfe-taxonomy-grid';

  return (
    <div className="sfe-filter-taxonomy__group">
      <header className="sfe-filter-taxonomy__heading">
        <span className="sfe-filter-taxonomy__label">{label}</span>
        {hint ? <span className="sfe-filter-taxonomy__hint">{hint}</span> : null}
      </header>
      <div
        className={layoutClass}
        role="group"
        aria-label={label}
      >
        {chips.map((chip) => (
          <TaxonomyFilterCard
            key={`${chip.kind}-${chip.id}`}
            chip={chip}
            active={isChipActive(chip)}
            onClick={onChipClick}
          />
        ))}
      </div>
    </div>
  );
}

function TaxonomyFilterRail({
  systemView,
  onSystemView,
  stats,
  scopedStats,
  facets,
  filters,
  onFilterChange,
  hideScopeFilters = false,
  scopeChips = [],
  scopeChipIds = null,
  scopeLabel = '',
  initialFilters = {},
}) {
  const facet = facets?.facets || {};
  const subcategoryFacet = filters.category ? (facet.subcategory || {}) : {};

  const scopeChipItems = useMemo(
    () => (scopeChips || [])
      .filter((chip) => chip.count > 0)
      .filter((chip) => !scopeChipIds || scopeChipIds.has(chip.id))
      .map((chip) => ({
        kind: 'scope',
        id: chip.id,
        label: chip.label,
        description: chip.description,
        count: chip.count,
        filter: chip.filter,
      })),
    [scopeChips, scopeChipIds],
  );

  const categoryChipItems = useMemo(
    () => Object.entries(facet.category || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 14)
      .map(([id, count]) => ({
        kind: 'category',
        id,
        label: prettifyCategory(id),
        count,
      })),
    [facet.category],
  );

  const subcategoryChipItems = useMemo(
    () => Object.entries(subcategoryFacet)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 14)
      .map(([id, count]) => ({
        kind: 'subcategory',
        id,
        label: prettifyCategory(id),
        count,
      })),
    [subcategoryFacet],
  );

  const scopedBaseFilters = useMemo(
    () => Object.fromEntries(
      Object.entries(initialFilters).filter(([, value]) => value != null && value !== ''),
    ),
    [initialFilters],
  );

  const handleChipClick = (chip) => {
    onSystemView('all_files');
    if (chip.kind === 'scope') {
      const base = hideScopeFilters ? scopedBaseFilters : filters;
      const next = scopeChipToFilters(chip, base);
      const isActive = chip.filter && Object.entries(chip.filter).every(([k, v]) => filters[k] === v);
      onFilterChange(isActive ? { ...scopedBaseFilters } : next);
      return;
    }
    if (chip.kind === 'category') {
      onFilterChange({
        ...filters,
        category: filters.category === chip.id ? undefined : chip.id,
        subcategory: undefined,
      });
      return;
    }
    if (chip.kind === 'subcategory') {
      onFilterChange({
        ...filters,
        subcategory: filters.subcategory === chip.id ? undefined : chip.id,
      });
    }
  };

  const isChipActive = (chip) => {
    if (chip.kind === 'scope') {
      return chip.filter && Object.entries(chip.filter).every(([k, v]) => filters[k] === v);
    }
    if (chip.kind === 'category') {
      return !MAINTENANCE_CHIP_IDS.includes(systemView) && filters.category === chip.id;
    }
    if (chip.kind === 'subcategory') {
      return !MAINTENANCE_CHIP_IDS.includes(systemView) && filters.subcategory === chip.id;
    }
    return false;
  };

  const categoryMapChips = useMemo(
    () => categoryChipItems.map((chip) => ({
      ...chip,
      filter: { category: chip.id },
    })),
    [categoryChipItems],
  );

  const subcategoryMapChips = useMemo(
    () => subcategoryChipItems.map((chip) => ({
      ...chip,
      filter: { category: filters.category, subcategory: chip.id },
    })),
    [subcategoryChipItems, filters.category],
  );

  const hasScopeMap = scopeChipItems.length > 0;
  const showCategoryMap = !hideScopeFilters && categoryMapChips.length > 0;
  const showSubcategoryMap = !hideScopeFilters && filters.category && subcategoryMapChips.length > 0;

  if (!hasScopeMap && !showCategoryMap && !showSubcategoryMap) return null;

  return (
    <div className="sfe-taxonomy-maps">
      {hasScopeMap ? (
        <TaxonomyConnectorMap
          chips={scopeChipItems}
          scopeLabel={scopeLabel || (hideScopeFilters ? 'Library scope' : 'Domain scope')}
          initialFilters={scopedBaseFilters}
          isChipActive={isChipActive}
          onChipClick={handleChipClick}
          onResetScope={() => {
            onSystemView('all_files');
            onFilterChange({ ...scopedBaseFilters });
          }}
        />
      ) : null}
      {showCategoryMap ? (
        <TaxonomyConnectorMap
          chips={categoryMapChips}
          scopeLabel="Categories"
          initialFilters={filters}
          isChipActive={isChipActive}
          onChipClick={handleChipClick}
          onResetScope={() => onFilterChange({ ...filters, category: undefined, subcategory: undefined })}
        />
      ) : null}
      {showSubcategoryMap ? (
        <TaxonomyConnectorMap
          chips={subcategoryMapChips}
          scopeLabel={prettifyCategory(filters.category)}
          initialFilters={filters}
          isChipActive={isChipActive}
          onChipClick={handleChipClick}
          onResetScope={() => onFilterChange({ ...filters, subcategory: undefined })}
        />
      ) : null}
    </div>
  );
}

function SystemViewFilterRail({
  systemView,
  onSystemView,
  onFilterChange,
  filters,
  stats,
  scopedStats,
}) {
  const audit = (scopedStats?.audit_counts || stats?.audit_counts) || {};
  const maintenanceChips = MAINTENANCE_CHIP_IDS.map((id) => {
    const view = SYSTEM_VIEWS.find((v) => v.id === id);
    if (!view) return null;
    const count = id === 'not_indexed' ? audit.not_indexed
      : id === 'needs_redigitalization' ? audit.needs_redigitalization
        : id === 'unknown_type' ? audit.unknown_type
          : id === 'duplicates' ? (audit.duplicate_copies ?? audit.duplicate_groups)
            : id === 'large_files' ? audit.large_files
              : null;
    return { kind: 'system', id, label: view.label, count };
  }).filter(Boolean);

  if (!maintenanceChips.length) return null;

  return (
    <FilterChipGroup
      label="Library health views"
      hint="Operational shortcuts"
      chips={maintenanceChips}
      layout="strip"
      isChipActive={(chip) => systemView === chip.id}
      onChipClick={(chip) => {
        onFilterChange({ ...filters });
        onSystemView(chip.id);
      }}
    />
  );
}

function DocumentTitleSubline({ item, className = 'sfe-row-original', pathFallback = null }) {
  const subline = documentTitleSubline(item);
  if (!subline.dateLabel && !subline.filename) {
    return pathFallback ? <div className="sfe-row-path">{pathFallback}</div> : null;
  }
  return (
    <div className={className}>
      {subline.dateLabel ? (
        <span className="sfe-preview-date">{subline.dateLabel}</span>
      ) : null}
      {subline.filename ? <span>{subline.filename}</span> : null}
    </div>
  );
}

function VirtualFileList({
  items,
  viewMode,
  selectedId,
  onSelect,
  listDetailExpanded = false,
}) {
  const scrollRef = useRef(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportH, setViewportH] = useState(480);
  const { gridTemplateColumns, startResize } = useResizableGridColumns(
    SFE_COLUMN_WIDTHS_KEY,
    SFE_LIST_COLUMNS,
  );
  const rowGridStyle = useMemo(
    () => ({ gridTemplateColumns }),
    [gridTemplateColumns],
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(() => setViewportH(el.clientHeight || 480));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const rowH = viewMode === 'card' ? CARD_HEIGHT : ROW_HEIGHT;
  const totalH = items.length * rowH;
  const start = Math.max(0, Math.floor(scrollTop / rowH) - 4);
  const visible = Math.ceil(viewportH / rowH) + 8;
  const end = Math.min(items.length, start + visible);
  const slice = items.slice(start, end);
  const offsetY = start * rowH;

  if (!items.length) {
    return <div className="sfe-empty">No files match your filters.</div>;
  }

  if (viewMode === 'card') {
    return (
      <div className="sfe-card-grid">
        {items.map((item) => (
          <button
            key={item.asset_id}
            type="button"
            className={`sfe-card${selectedId === item.asset_id ? ' is-selected' : ''}`}
            onClick={() => onSelect(item)}
          >
            <div className="sfe-card-name-line">
              <FileListBullet item={item} selected={selectedId === item.asset_id} />
              <div className="sfe-card-name">{smartDocumentTitle(item)}</div>
            </div>
            <DocumentTitleSubline item={item} />
            <div className="sfe-row-path">{item.project_category_original || item.category || item.domain} · {formatBytes(item.size_bytes)}</div>
            <StatusBadges item={item} />
          </button>
        ))}
      </div>
    );
  }

  const listWrapClass = [
    'sfe-list-wrap',
    listDetailExpanded ? 'sfe-list-wrap--resizable' : 'sfe-list-wrap--compact',
  ].join(' ');

  return (
    <div className={listWrapClass}>
      {listDetailExpanded ? (
        <div
          className="sfe-row sfe-row--header"
          style={rowGridStyle}
          role="row"
        >
          {SFE_LIST_COLUMNS.map((col, index) => (
            <div key={col.id} className="sfe-col-header" role="columnheader">
              <span className="sfe-col-label">{col.label}</span>
              {index < SFE_LIST_COLUMNS.length - 1 ? (
                <button
                  type="button"
                  className="sfe-col-resize-handle"
                  aria-label={`Resize ${col.label} column`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    startResize(index, e.clientX);
                  }}
                />
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
      <div
        className="sfe-virtual-scroll"
        ref={scrollRef}
        onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
      >
        <div className="sfe-virtual-inner" style={{ height: totalH }}>
          <div style={{ transform: `translateY(${offsetY}px)` }}>
            {slice.map((item, rowIndex) => (
              <div
                key={item.asset_id}
                className={`sfe-row${selectedId === item.asset_id ? ' is-selected' : ''}${(start + rowIndex) % 2 === 1 ? ' sfe-row--alt' : ''}`}
                style={listDetailExpanded ? { ...rowGridStyle, height: ROW_HEIGHT } : { height: ROW_HEIGHT }}
                onClick={() => onSelect(item)}
                onKeyDown={(e) => e.key === 'Enter' && onSelect(item)}
                role="button"
                tabIndex={0}
              >
                <div className="sfe-col-cell sfe-col-cell--name">
                  <div className="sfe-row-name-line">
                    <FileListBullet item={item} selected={selectedId === item.asset_id} />
                    <div className="sfe-row-name-copy">
                      <div className="sfe-row-title">{smartDocumentTitle(item)}</div>
                      {listDetailExpanded ? (
                        <DocumentTitleSubline item={item} pathFallback={item.logical_path} />
                      ) : null}
                    </div>
                  </div>
                </div>
                {listDetailExpanded ? (
                  <>
                    <span className="sfe-row-category sfe-col-cell">
                      {item.professional_role_label || prettifyCategory(item.project_category_original || item.category) || item.domain || '—'}
                    </span>
                    <span className="sfe-col-cell">{formatBytes(item.size_bytes)}</span>
                    <span className="sfe-col-cell">{item.modified_at?.slice(0, 10) || '—'}</span>
                    <span className="sfe-col-cell sfe-col-cell--status">
                      <StatusBadges item={item} />
                    </span>
                  </>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ImageMetadataCard({ preview, hideThumb = false }) {
  const [thumbUrl, setThumbUrl] = useState(null);
  const imgMeta = preview.image_metadata || {};

  useEffect(() => {
    if (!preview.is_streamable_image || !preview.asset_id || hideThumb) return undefined;
    let alive = true;
    let objectUrl = null;
    loadThumbnailBlobUrl(preview.asset_id)
      .then((url) => {
        if (alive) {
          objectUrl = url;
          setThumbUrl(url);
        } else {
          URL.revokeObjectURL(url);
        }
      })
      .catch(() => { if (alive) setThumbUrl(null); });
    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [preview.asset_id, preview.is_streamable_image, hideThumb]);

  const openViewer = () => {
    window.location.hash = buildViewerHash(preview.asset_id);
  };

  const dimensions = imgMeta.width && imgMeta.height
    ? `${imgMeta.width} × ${imgMeta.height}`
    : imgMeta.dimensions?.shape?.join(' × ');

  return (
    <div className="sfe-image-meta-row">
      <div className="sfe-preview-meta-inline">
        <MetaCell label="Format" value={imgMeta.format} />
        <MetaCell label="Status" value={imgMeta.streaming_status} />
        <MetaCell label="Dimensions" value={dimensions} />
        <MetaCell label="Channels" value={imgMeta.channels} />
        <MetaCell label="Pyramid" value={imgMeta.pyramid_levels} />
        <MetaCell label="OME-XML" value={imgMeta.ome_xml_present ? 'present' : 'no'} />
      </div>
      {!hideThumb && thumbUrl ? (
        <img src={thumbUrl} alt="" className="sfe-preview-thumb-inline" loading="lazy" />
      ) : null}
      <button type="button" className="sfe-preview-viewer-btn" onClick={openViewer}>
        <ExternalLink size={12} aria-hidden /> Streaming viewer
      </button>
    </div>
  );
}

function PreviewMediaPanel({ preview }) {
  const [streamThumbUrl, setStreamThumbUrl] = useState(null);
  const media = useMemo(() => resolvePreviewMedia(preview), [preview]);

  useEffect(() => {
    if (!preview?.is_streamable_image || !preview.asset_id) {
      setStreamThumbUrl(null);
      return undefined;
    }
    let alive = true;
    let objectUrl = null;
    loadThumbnailBlobUrl(preview.asset_id)
      .then((url) => {
        if (alive) {
          objectUrl = url;
          setStreamThumbUrl(url);
        } else {
          URL.revokeObjectURL(url);
        }
      })
      .catch(() => { if (alive) setStreamThumbUrl(null); });
    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setStreamThumbUrl(null);
    };
  }, [preview?.asset_id, preview?.is_streamable_image]);

  const viewerUrl = preview?.is_streamable_image
    ? (streamThumbUrl || media?.url)
    : media?.url;
  const viewerKind = media?.kind || 'image';

  if (!viewerUrl) {
    if (!preview?.is_streamable_image) return null;
    return (
      <div className="sfe-preview-media">
        <ImageMetadataCard preview={preview} hideThumb />
        <div className="sfe-preview-media-loading">
          <Loader2 size={22} className="spin-inline" aria-hidden />
          <span>Loading image preview…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="sfe-preview-media">
      {preview.is_streamable_image ? (
        <ImageMetadataCard preview={preview} hideThumb />
      ) : null}
      <MediaViewer
        url={viewerUrl}
        title={smartDocumentTitle(preview)}
        kind={viewerKind}
        labels={{
          loading: 'Loading image…',
          failed: 'Could not load image.',
          videoLoading: 'Loading video…',
          videoFailed: 'Could not load video.',
        }}
      />
    </div>
  );
}

function FilePreviewPanel({
  assetId,
  pinned,
  onTogglePin,
  onExpandChange = null,
  layoutMode = 'split',
}) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [viewerExpanded, setViewerExpanded] = useState(false);
  const [draftNotesOpen, setDraftNotesOpen] = useState(false);
  const [draftNotesByAsset, setDraftNotesByAsset] = useState({});
  const isReading = layoutMode === 'reading';

  const extension = extensionFromPreview(preview);
  const previewKind = preview ? getFilePreviewKind(extension, preview.logical_path) : 'document';
  const isPdf = extension === '.pdf';
  const isSpreadsheet = previewKind === 'spreadsheet';
  const previewUrl = preview?.preview_url || null;

  const spreadsheetPreview = useSpreadsheetPreview(
    isSpreadsheet && previewUrl ? previewUrl : null,
    extension,
  );
  const rawFilePreview = useRawFilePreview(
    previewUrl && !isSpreadsheet && !isPdf ? previewUrl : null,
    previewKind,
    { fallbackText: preview?.excerpt },
  );

  const mergedSpreadsheetPreview = useMemo(() => {
    if (!isSpreadsheet || !preview) return null;
    const apiSheets = apiSpreadsheetSheetsToModels(
      preview.spreadsheet_sheets || preview.metadata?.sheets,
    );
    const fileSheets = spreadsheetPreview.sheets;
    const sheets = fileSheets?.length ? fileSheets : apiSheets;
    const fromApi = Boolean(!fileSheets?.length && apiSheets?.length);
    const sheetLoading = !sheets?.length && spreadsheetPreview.loading;
    const error =
      !sheets?.length && !sheetLoading && spreadsheetPreview.error
        ? spreadsheetPreview.error
        : null;
    return {
      loading: sheetLoading,
      sheets,
      repairNotes: [
        ...(spreadsheetPreview.repairNotes || []),
        ...(fromApi ? ['Rendered from extracted spreadsheet metadata.'] : []),
      ],
      error,
      strategy: fileSheets?.length ? spreadsheetPreview.strategy : fromApi ? 'metadata' : null,
    };
  }, [isSpreadsheet, preview, spreadsheetPreview]);

  const spreadsheetReady = Boolean(mergedSpreadsheetPreview?.sheets?.length);
  const showSpreadsheet = isSpreadsheet && (mergedSpreadsheetPreview?.loading || spreadsheetReady);
  const rawLoading = Boolean(rawFilePreview?.loading);
  const rawContent = rawFilePreview?.content;
  const rawError = rawFilePreview?.error;
  const language = inferCodeLanguage(extension, preview?.logical_path);
  const showCode =
    (previewKind === 'code' || previewKind === 'json') && (rawLoading || rawContent || rawError);
  const showPlainText =
    previewKind === 'text' && (rawLoading || rawContent || rawError) && !showSpreadsheet;
  const showMarkup =
    previewKind === 'markup' && (rawContent || preview?.excerpt) && !showSpreadsheet;

  useEffect(() => {
    if (!assetId) {
      setPreview(null);
      return undefined;
    }
    let alive = true;
    setLoading(true);
    fetchDocumentPreview(assetId)
      .then((data) => { if (alive) setPreview(data); })
      .catch(() => { if (alive) setPreview(null); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [assetId]);

  useEffect(() => {
    setViewerExpanded(false);
    setDraftNotesOpen(false);
  }, [assetId]);

  useEffect(() => {
    onExpandChange?.(viewerExpanded);
  }, [viewerExpanded, onExpandChange]);

  const emptyShellClass = isReading
    ? 'overview-reading-article overview-reading-article--empty'
    : 'sfe-preview-panel';

  if (!assetId) {
    const Wrapper = isReading ? 'article' : 'aside';
    return (
      <Wrapper className={emptyShellClass}>
        <div className="sfe-preview-empty">
          <FileText size={32} strokeWidth={1.25} aria-hidden />
          <p>{isReading ? 'Select a document from the list to read.' : 'Select a file to preview metadata and status.'}</p>
        </div>
      </Wrapper>
    );
  }

  if (loading) {
    const Wrapper = isReading ? 'article' : 'aside';
    return (
      <Wrapper className={emptyShellClass}>
        <div className="sfe-preview-empty"><Loader2 className="spin-inline" size={24} /> Loading preview…</div>
      </Wrapper>
    );
  }

  if (!preview) {
    const Wrapper = isReading ? 'article' : 'aside';
    return (
      <Wrapper className={emptyShellClass}>
        <div className="sfe-preview-empty">Preview unavailable.</div>
      </Wrapper>
    );
  }

  const md = preview.metadata || {};
  const completeness = preview.metadata_completeness ?? 0;
  const previewMedia = resolvePreviewMedia(preview);
  const showMedia = Boolean(previewMedia || preview.is_streamable_image);
  const previewTitle = smartDocumentTitle(preview);
  const previewSubline = documentTitleSubline(preview);
  const hasFormattedText =
    Boolean(preview.excerpt)
    && !showMedia
    && !showSpreadsheet
    && !showCode
    && !showPlainText
    && !showMarkup
    && !isPdf;
  const proofreadSource = showMarkup
    ? (rawContent || preview.excerpt || '')
    : hasFormattedText
      ? (preview.excerpt || '')
      : showPlainText || showCode
        ? (rawContent || '')
        : '';

  const proseReaderClass = isReading
    ? 'overview-reading-prose'
    : 'sfe-preview-reader kindle-doc-scroll academic-manuscript doc-preview-prose';

  const previewBody = (
    <>
      {showMedia ? <PreviewMediaPanel preview={preview} /> : null}
      {!showMedia && showSpreadsheet ? (
        <SpreadsheetPreview
          sheets={mergedSpreadsheetPreview?.sheets}
          repairNotes={mergedSpreadsheetPreview?.repairNotes}
          loading={mergedSpreadsheetPreview?.loading}
          error={mergedSpreadsheetPreview?.error}
          fileUrl={previewUrl}
        />
      ) : null}
      {!showMedia && !showSpreadsheet && isPdf && previewUrl ? (
        <iframe
          title={preview.filename}
          src={previewUrl}
          className="sfe-pdf-frame"
        />
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && showCode ? (
        <CodePreview
          content={rawContent}
          language={previewKind === 'json' ? 'json' : language}
          loading={rawLoading}
          error={rawError}
        />
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && showPlainText ? (
        <CodePreview
          content={rawContent}
          language="plaintext"
          loading={rawLoading}
          error={rawError}
        />
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && showMarkup ? (
        <div className={proseReaderClass}>
          <DocumentFormatter text={rawContent || preview.excerpt} preferProse />
        </div>
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && hasFormattedText ? (
        <div className={proseReaderClass}>
          <DocumentFormatter text={preview.excerpt} preferProse />
        </div>
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && !hasFormattedText && !showCode && !showPlainText && !showMarkup ? (
        <p className="text-footnote muted sfe-preview-empty-text">
          No extracted text yet. Run digitalization to enrich this file.
        </p>
      ) : null}
      {proofreadSource.trim() && !showMedia && !showSpreadsheet && !isPdf ? (
        <DocumentProofreadPanel content={proofreadSource} className="doc-preview-proofread" />
      ) : null}
    </>
  );

  const showExpandControl = !isReading || isPdf;

  const headerActions = (
    <DocumentViewerToolbar>
      {showExpandControl ? (
        <DocumentViewerExpandButton
          variant="toolbar"
          expanded={viewerExpanded}
          onToggle={() => setViewerExpanded((value) => !value)}
        />
      ) : null}
      <DocumentExportMenu assetId={preview.asset_id} compact toolbar />
      <DocumentViewerToolButton
        active={pinned}
        onClick={onTogglePin}
        title={pinned ? 'Unpin file' : 'Pin file'}
      >
        <Pin size={14} aria-hidden />
      </DocumentViewerToolButton>
      <DocumentViewerToolButton
        active={detailsOpen}
        onClick={() => setDetailsOpen((v) => !v)}
        title={detailsOpen ? 'Hide metadata details' : 'Show metadata details'}
      >
        <Info size={14} aria-hidden />
      </DocumentViewerToolButton>
    </DocumentViewerToolbar>
  );

  const metadataFooter = (
    <footer className={`${isReading ? 'overview-reading-footer' : 'sfe-preview-footer'}${detailsOpen ? ' is-expanded' : ''}`}>
      {!detailsOpen ? (
        <div className="sfe-preview-meta-inline">
          <MetaCell label="Category" value={md.category} />
          <MetaCell label="Role" value={md.document_role} />
          <MetaCell label="Project" value={md.project} />
          <MetaCell label="Platform" value={md.assay_tags || md.inferred_platforms} />
          <MetaCell label="Digitalization" value={md.digitalization_status} />
          <MetaCell label="Metadata grade" value={preview.metadata_grade} />
        </div>
      ) : (
        <div className="sfe-preview-footer-scroll">
          <MetadataSection title="Scientific context">
            <div className="sfe-preview-meta-inline">
              <MetaCell label="Project" value={md.project} />
              <MetaCell label="Inferred projects" value={md.inferred_project_codes} />
              <MetaCell label="Sample IDs" value={md.inferred_sample_ids} />
              <MetaCell label="Platform / assay" value={md.assay_tags || md.inferred_platforms} />
              <MetaCell label="Tissue / site" value={md.tissue_tags} />
              <MetaCell label="Markers / panels" value={md.marker_tags} />
              <MetaCell label="Years" value={md.inferred_years} />
            </div>
          </MetadataSection>
          <MetadataSection title="Organization">
            <div className="sfe-preview-meta-inline">
              <MetaCell label="Domain" value={md.domain} />
              <MetaCell label="Section" value={md.section_label || md.section} />
              <MetaCell label="Category" value={md.category} />
              <MetaCell label="Subcategory" value={md.subcategory} />
              <MetaCell label="Folder root" value={md.domain_folder} />
              <MetaCell label="Owner" value={md.owner || md.inferred_people} />
            </div>
          </MetadataSection>
          <MetadataSection title="File & indexing">
            <div className="sfe-preview-meta-inline">
              <MetaCell label="File type" value={md.file_type} />
              <MetaCell label="Document kind" value={md.document_kind} />
              <MetaCell label="Extension" value={md.extension} />
              <MetaCell label="Size" value={formatBytes(preview.size_bytes)} />
              <MetaCell label="Word count" value={md.word_count} />
              <MetaCell label="Extractor" value={md.extractor} />
              <MetaCell label="Modified" value={preview.modified_at?.slice(0, 10)} />
              <MetaCell label="Indexed" value={preview.indexed_at?.slice(0, 10)} />
              <MetaCell label="Digitalization" value={md.digitalization_status} />
              <MetaCell label="Extraction" value={md.extraction_status} />
              <MetaCell label="Vector status" value={md.vector_status} />
              <MetaCell label="Review" value={md.review_status} />
              <MetaCell label="Sensitivity" value={md.sensitivity_level} />
              <MetaCell label="Redigitalization" value={md.redigitalization_reason} />
              <MetaCell label="Protocol category" value={md.protocol_category} />
              <MetaCell label="Reagent category" value={md.reagent_category} />
              <MetaCell label="Path" value={preview.logical_path} />
            </div>
          </MetadataSection>
          {md.processed_metadata && Object.keys(md.processed_metadata).length > 0 ? (
            <MetadataSection title="Extracted file metadata">
              <div className="sfe-preview-meta-inline">
                {Object.entries(md.processed_metadata).slice(0, 16).map(([key, value]) => (
                  <MetaCell
                    key={key}
                    label={prettifyCategory(key)}
                    value={typeof value === 'object' ? JSON.stringify(value) : value}
                  />
                ))}
              </div>
            </MetadataSection>
          ) : null}
        </div>
      )}
    </footer>
  );

  if (isReading) {
    const draftKey = preview.asset_id;
    const draftValue = draftNotesByAsset[draftKey] || '';

    return (
      <>
        <article className={`overview-reading-article${viewerExpanded ? ' overview-reading-article--hidden' : ''}`}>
          <header className="overview-reading-hero">
            <h1 className="overview-reading-hero__title">{previewTitle}</h1>
            <div className="overview-reading-hero__subline">
              {previewSubline.dateLabel ? (
                <span className="sfe-preview-date">{previewSubline.dateLabel}</span>
              ) : null}
              {previewSubline.filename ? (
                <span className="sfe-preview-filename">{previewSubline.filename}</span>
              ) : null}
              {(preview.badges || []).map((b) => (
                <span key={b} className="sfe-badge sfe-badge--partial">{b}</span>
              ))}
            </div>
          </header>

          {preview.duplicate_warning ? (
            <div className="overview-reading-warn">{preview.duplicate_warning}</div>
          ) : null}

          <div className="overview-reading-toolbar">
            <DocumentViewerMetaChip value={completeness} low={completeness < 40} />
            <div className="overview-reading-toolbar__actions">
              <DocumentViewerToolButton
                labeled
                active={draftNotesOpen}
                onClick={() => setDraftNotesOpen((v) => !v)}
                title={draftNotesOpen ? 'Hide draft notes' : 'Open draft notes'}
              >
                <span>{draftNotesOpen ? 'Hide notes' : 'Draft notes'}</span>
              </DocumentViewerToolButton>
              {headerActions}
            </div>
          </div>

          {draftNotesOpen ? (
            <div className="overview-reading-draft">
              <textarea
                value={draftValue}
                onChange={(e) => {
                  setDraftNotesByAsset((prev) => ({ ...prev, [draftKey]: e.target.value }));
                }}
                placeholder="Session-only notes while reading — not saved to the library."
                aria-label="Draft reading notes"
              />
              <p className="overview-reading-draft__hint">Notes stay in this browser session only.</p>
            </div>
          ) : null}

          <div className="overview-reading-body kindle-doc-scroll academic-manuscript doc-preview-prose">
            {previewBody}
          </div>

          {metadataFooter}
        </article>

        {showExpandControl ? (
          <DocumentViewerExpandPortal
            expanded={viewerExpanded}
            onClose={() => setViewerExpanded(false)}
            title={previewTitle}
            subtitle={previewSubline.dateLabel || previewSubline.filename || preview.filename}
            headerActions={headerActions}
          >
            <div className="sfe-preview-content sfe-preview-content--expanded">{previewBody}</div>
          </DocumentViewerExpandPortal>
        ) : null}
      </>
    );
  }

  return (
    <>
    <aside className={`sfe-preview-panel${viewerExpanded ? ' sfe-preview-panel--hidden' : ''}`}>
      <header className="sfe-preview-top">
        <div className="sfe-preview-top__primary">
          <div className="sfe-preview-top__main">
            <h3 className="sfe-preview-title">{previewTitle}</h3>
            <div className="sfe-preview-top__subline">
              {previewSubline.dateLabel ? (
                <span className="sfe-preview-date">{previewSubline.dateLabel}</span>
              ) : null}
              {previewSubline.filename ? (
                <span className="sfe-preview-filename">{previewSubline.filename}</span>
              ) : null}
              {(preview.badges || []).map((b) => (
                <span key={b} className="sfe-badge sfe-badge--partial">{b}</span>
              ))}
            </div>
          </div>
          <div className="sfe-preview-top__rail">
            <DocumentViewerMetaChip value={completeness} low={completeness < 40} />
            {headerActions}
          </div>
        </div>
      </header>

      {preview.duplicate_warning ? (
        <div className="sfe-preview-warn">{preview.duplicate_warning}</div>
      ) : null}

      <div className="sfe-preview-content">{previewBody}</div>

      {metadataFooter}
    </aside>

    <DocumentViewerExpandPortal
      expanded={viewerExpanded}
      onClose={() => setViewerExpanded(false)}
      title={previewTitle}
      subtitle={previewSubline.dateLabel || previewSubline.filename || preview.filename}
      headerActions={headerActions}
    >
      <div className="sfe-preview-content sfe-preview-content--expanded">{previewBody}</div>
    </DocumentViewerExpandPortal>
    </>
  );
}

function filterClientView(items, systemView) {
  if (systemView === 'recently_opened') {
    const recent = new Set(loadRecentIds());
    return items.filter((i) => recent.has(i.asset_id));
  }
  if (systemView === 'pinned') {
    const pinned = new Set(loadPinnedIds());
    return items.filter((i) => pinned.has(i.asset_id));
  }
  return items;
}

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
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [viewMode, setViewMode] = useState('table');
  const [sort, setSort] = useState('filename');
  const [order, setOrder] = useState('asc');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [listDetailExpanded, setListDetailExpanded] = useState(false);
  const [pinnedIds, setPinnedIds] = useState(() => loadPinnedIds());
  const coverCtx = useModuleShellCover();
  const hideHeroText = Boolean(coverCtx?.showModuleCover);

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

  const searchParams = useMemo(() => ({
    q: debouncedQ,
    domain_tab: effectiveDomainTab === 'all_files' ? undefined : effectiveDomainTab,
    system_view: ['recently_opened', 'pinned'].includes(systemView) ? undefined : (systemView === 'all_files' ? undefined : systemView),
    sort,
    order,
    offset: 0,
    limit: 5000,
    ...filters,
  }), [debouncedQ, effectiveDomainTab, systemView, sort, order, filters]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setLoadError(null);
    Promise.all([
      searchDocumentLibrary(searchParams),
      fetchDocumentLibraryFacets(searchParams),
    ])
      .then(([searchRes, facetRes]) => {
        if (!alive) return;
        let rows = searchRes.items || [];
        rows = filterClientView(rows, systemView);
        setItems(rows);
        setTotal(systemView === 'recently_opened' || systemView === 'pinned' ? rows.length : searchRes.total || 0);
        setFacets(facetRes);
      })
      .catch((err) => {
        if (!alive) return;
        setItems([]);
        setTotal(0);
        setLoadError(err?.message || 'Could not load document library.');
      })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [searchParams, systemView]);

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

  const scopedStats = facets?.scoped_stats;
  const scopeChips = facets?.scope_chips || [];
  const scopedAudit = scopedStats?.audit_counts;
  const displayTotal = scopedStats?.total_files ?? stats?.total_files;
  const audit = scopedAudit || stats?.audit_counts || {};

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

        <FilterBar
          facets={facets}
          filters={filters}
          onChange={setFilters}
          advancedOpen={advancedOpen}
          onToggleAdvanced={() => setAdvancedOpen((v) => !v)}
          onClear={() => setFilters(
            hideScopeFilters
              ? Object.fromEntries(Object.entries(initialFilters).filter(([, v]) => v != null && v !== ''))
              : {},
          )}
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
        <section className={`sfe-main${!isReadingLayout && !listDetailExpanded ? ' sfe-main--list-compact' : ''}`}>
          {loadError ? (
            <div className="sfe-list-section sfe-list-section--alert">
              <div className="sfe-error-banner" role="alert">{loadError}</div>
            </div>
          ) : null}

          <div className="sfe-list-section sfe-list-section--controls">
            <div className="sfe-list-controls">
              <p className="sfe-list-controls__meta">
                <span className="sfe-list-controls__count">
                  {loading ? 'Loading…' : `${total.toLocaleString()} results`}
                </span>
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
            {loading ? (
              <div className="sfe-loading"><Loader2 className="spin-inline" size={20} /> Loading files…</div>
            ) : (
              <VirtualFileList
                items={items}
                viewMode={viewMode}
                selectedId={selected?.asset_id}
                onSelect={handleSelect}
                listDetailExpanded={listDetailExpanded}
              />
            )}
          </div>
        </section>
        <FilePreviewPanel
          assetId={selected?.asset_id}
          pinned={selected ? pinnedIds.includes(selected.asset_id) : false}
          onTogglePin={handleTogglePin}
          layoutMode={layoutMode}
        />
      </div>
    </div>
  );
}
