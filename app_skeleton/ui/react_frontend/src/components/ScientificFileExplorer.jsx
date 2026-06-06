import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  LayoutGrid,
  List,
  Loader2,
  Pin,
  Search,
  FileText,
  ExternalLink,
} from 'lucide-react';
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
import './ScientificFileExplorer.css';

const ROW_HEIGHT = 52;
const CARD_HEIGHT = 100;

function StatusBadges({ item }) {
  const badges = [];
  if (item.digitalization_status === 'indexed') badges.push(['Indexed', 'indexed']);
  else if (item.digitalization_status === 'not_started') badges.push(['Not indexed', 'not_started']);
  if (item.preview_status === 'missing') badges.push(['Preview missing', 'warn']);
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

function FilterBar({ facets, filters, onChange, advancedOpen, onToggleAdvanced, onClear, hideScopeFilters = false }) {
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
          {advancedOpen ? 'Less' : 'More'}
        </button>
        {activeCount > 0 ? (
          <button type="button" className="sfe-filter-clear" onClick={onClear}>Clear ({activeCount})</button>
        ) : null}
      </div>
      {advancedOpen ? (
        <div className="sfe-filter-bar__advanced">
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

function MetaRow({ label, value }) {
  if (value == null || value === '' || (Array.isArray(value) && !value.length)) return null;
  const display = Array.isArray(value) ? value.join(', ') : String(value);
  return (
    <>
      <dt>{label}</dt>
      <dd>{display}</dd>
    </>
  );
}

const FILE_TYPE_LABELS = {
  table_or_registry: 'Spreadsheets',
  document: 'Documents',
  image: 'Images',
  presentation: 'Slides',
  video: 'Video',
  unknown_no_extension: 'Unknown type',
  other: 'Other',
};

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

function DynamicExplorerChips({
  systemView,
  onSystemView,
  stats,
  facets,
  filters,
  onFilterChange,
  hideScopeFilters = false,
}) {
  const audit = stats?.audit_counts || {};
  const subcategoryFacet = filters.category ? (facets?.facets?.subcategory || {}) : {};

  const subcategoryChips = useMemo(
    () => Object.entries(subcategoryFacet)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([id, count]) => ({
        kind: 'subcategory',
        id,
        label: prettifyCategory(id),
        count,
      })),
    [subcategoryFacet],
  );

  const maintenanceChips = MAINTENANCE_CHIP_IDS.map((id) => {
    const view = SYSTEM_VIEWS.find((v) => v.id === id);
    if (!view) return null;
    const count = id === 'not_indexed' ? audit.not_indexed
      : id === 'needs_redigitalization' ? audit.needs_redigitalization
        : id === 'unknown_type' ? audit.unknown_type
          : id === 'duplicates' ? audit.duplicate_groups
            : id === 'large_files' ? audit.large_files
              : null;
    return { kind: 'system', id, label: view.label, count };
  }).filter(Boolean);

  const handleCategoryChip = (chip) => {
    onSystemView('all_files');
    if (chip.kind === 'subcategory') {
      onFilterChange({
        ...filters,
        subcategory: filters.subcategory === chip.id ? undefined : chip.id,
      });
      return;
    }
    onFilterChange({ ...filters });
    onSystemView(chip.id);
  };

  const isChipActive = (chip) => {
    if (chip.kind === 'subcategory') {
      return !MAINTENANCE_CHIP_IDS.includes(systemView) && filters.subcategory === chip.id;
    }
    return systemView === chip.id;
  };

  const chips = hideScopeFilters
    ? maintenanceChips
    : [...subcategoryChips, ...maintenanceChips];

  return (
    <div className="sfe-chips-row" role="toolbar" aria-label="Quick filters">
      {chips.map((chip) => (
        <button
          key={`${chip.kind}-${chip.id}`}
          type="button"
          className={`sfe-chip sfe-chip--${chip.kind}${isChipActive(chip) ? ' is-active' : ''}`}
          onClick={() => handleCategoryChip(chip)}
        >
          {chip.label}
          {chip.count != null ? ` (${chip.count})` : ''}
        </button>
      ))}
    </div>
  );
}

function VirtualFileList({
  items,
  viewMode,
  selectedId,
  onSelect,
  sort,
  order,
  onSortChange,
}) {
  const scrollRef = useRef(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportH, setViewportH] = useState(480);

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
            <div className="sfe-card-name">{item.display_title || item.title || item.filename}</div>
            {item.display_title && item.display_title !== item.filename ? (
              <div className="sfe-row-original">{item.filename}</div>
            ) : null}
            <div className="sfe-row-path">{item.project_category_original || item.category || item.domain} · {formatBytes(item.size_bytes)}</div>
            <StatusBadges item={item} />
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="sfe-list-wrap">
      <div className="sfe-row" style={{ fontWeight: 600, background: 'var(--surface-subtle)', cursor: 'default' }}>
        <span>
          Name
          <select className="sfe-sort-select" value={`${sort}:${order}`} onChange={(e) => onSortChange(e.target.value)} aria-label="Sort">
            <option value="filename:asc">Name A–Z</option>
            <option value="filename:desc">Name Z–A</option>
            <option value="modified_at:desc">Newest</option>
            <option value="modified_at:asc">Oldest</option>
            <option value="size_bytes:desc">Largest</option>
          </select>
        </span>
        <span>Category</span>
        <span>Size</span>
        <span>Modified</span>
        <span>Status</span>
      </div>
      <div
        className="sfe-virtual-scroll"
        ref={scrollRef}
        onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
      >
        <div className="sfe-virtual-inner" style={{ height: totalH }}>
          <div style={{ transform: `translateY(${offsetY}px)` }}>
            {slice.map((item) => (
              <div
                key={item.asset_id}
                className={`sfe-row${selectedId === item.asset_id ? ' is-selected' : ''}`}
                style={{ height: ROW_HEIGHT }}
                onClick={() => onSelect(item)}
                onKeyDown={(e) => e.key === 'Enter' && onSelect(item)}
                role="button"
                tabIndex={0}
              >
                <div>
                  <div className="sfe-row-title">{item.display_title || item.title || item.filename}</div>
                  {item.display_title && item.display_title !== item.filename ? (
                    <div className="sfe-row-original">{item.filename}</div>
                  ) : (
                    <div className="sfe-row-path">{item.logical_path}</div>
                  )}
                </div>
                <span className="sfe-row-category">
                  {item.professional_role_label || prettifyCategory(item.project_category_original || item.category) || item.domain || '—'}
                </span>
                <span>{formatBytes(item.size_bytes)}</span>
                <span>{item.modified_at?.slice(0, 10) || '—'}</span>
                <StatusBadges item={item} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ImageMetadataCard({ preview }) {
  const [thumbUrl, setThumbUrl] = useState(null);
  const imgMeta = preview.image_metadata || {};

  useEffect(() => {
    if (!preview.is_streamable_image || !preview.asset_id) return undefined;
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
  }, [preview.asset_id, preview.is_streamable_image]);

  const openViewer = () => {
    window.location.hash = buildViewerHash(preview.asset_id);
  };

  return (
    <MetadataSection title="TIFF / OME-TIFF">
      <dl className="sfe-preview-meta">
        <MetaRow label="Format" value={imgMeta.format} />
        <MetaRow label="Streaming status" value={imgMeta.streaming_status} />
        <MetaRow
          label="Dimensions"
          value={
            imgMeta.width && imgMeta.height
              ? `${imgMeta.width} × ${imgMeta.height}`
              : imgMeta.dimensions?.shape?.join(' × ')
          }
        />
        <MetaRow label="Channels" value={imgMeta.channels} />
        <MetaRow label="Pyramid levels" value={imgMeta.pyramid_levels} />
        <MetaRow label="OME-XML" value={imgMeta.ome_xml_present ? 'present' : 'no'} />
      </dl>
      {thumbUrl ? (
        <img src={thumbUrl} alt="" className="sfe-preview-image" loading="lazy" style={{ marginTop: '0.5rem' }} />
      ) : (
        <p className="text-footnote muted">Thumbnail loading or unavailable.</p>
      )}
      <button type="button" className="btn btn-sm btn-secondary" style={{ marginTop: '0.5rem' }} onClick={openViewer}>
        <ExternalLink size={14} aria-hidden /> Open in Image Viewer
      </button>
    </MetadataSection>
  );
}

function FilePreviewPanel({ assetId, pinned, onTogglePin }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);

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

  if (!assetId) {
    return (
      <aside className="sfe-preview-panel">
        <div className="sfe-preview-empty">
          <FileText size={32} strokeWidth={1.25} aria-hidden />
          <p>Select a file to preview metadata and status.</p>
        </div>
      </aside>
    );
  }

  if (loading) {
    return (
      <aside className="sfe-preview-panel">
        <div className="sfe-preview-empty"><Loader2 className="spin-inline" size={24} /> Loading preview…</div>
      </aside>
    );
  }

  if (!preview) {
    return (
      <aside className="sfe-preview-panel">
        <div className="sfe-preview-empty">Preview unavailable.</div>
      </aside>
    );
  }

  const md = preview.metadata || {};
  const completeness = preview.metadata_completeness ?? 0;
  return (
    <aside className="sfe-preview-panel">
      <div className="sfe-preview-header">
        <div>
          <div className="sfe-preview-title">{preview.display_title || preview.title || preview.filename}</div>
          <div className="sfe-preview-filename">{preview.filename}</div>
          {preview.subtitle ? <div className="sfe-preview-subtitle">{preview.subtitle}</div> : null}
          {preview.document_role ? (
            <div className="sfe-preview-role">{prettifyCategory(preview.document_role)}</div>
          ) : null}
        </div>
        <div className="sfe-preview-completeness" title="Metadata completeness">
          <span className="sfe-preview-completeness__label">Metadata</span>
          <span className={`sfe-preview-completeness__value${completeness < 40 ? ' is-low' : ''}`}>{completeness}%</span>
        </div>
      </div>
      <div className="sfe-preview-badges">
        {(preview.badges || []).map((b) => (
          <span key={b} className="sfe-badge sfe-badge--partial">{b}</span>
        ))}
      </div>
      <div className="sfe-preview-actions">
        <button type="button" className="btn btn-sm btn-secondary sfe-preview-pin" onClick={onTogglePin}>
          <Pin size={14} aria-hidden /> {pinned ? 'Unpin' : 'Pin'}
        </button>
        <button type="button" className="btn btn-sm btn-ghost" onClick={() => setDetailsOpen((v) => !v)}>
          {detailsOpen ? 'Hide details' : 'View full metadata'}
        </button>
      </div>
      {preview.duplicate_warning ? (
        <div className="sfe-preview-warn">{preview.duplicate_warning}</div>
      ) : null}
      <div className="sfe-preview-content">
        {preview.is_streamable_image ? <ImageMetadataCard preview={preview} /> : null}
        {!preview.is_streamable_image && preview.preview_url && (preview.preview_type === 'thumbnail' || md.file_type === 'image') ? (
          <img src={preview.preview_url} alt="" className="sfe-preview-image" loading="lazy" />
        ) : null}
        {preview.excerpt ? (
          <div className="sfe-preview-excerpt">{preview.excerpt}</div>
        ) : (
          <p className="text-footnote muted sfe-preview-empty-text">
            {preview.preview_type === 'thumbnail' ? 'Image file — open via static mount.' : 'No extracted text yet. Run digitalization to enrich this file.'}
          </p>
        )}
      </div>
      <div className={`sfe-preview-meta-scroll${detailsOpen ? ' is-expanded' : ''}`}>
        {!detailsOpen ? (
          <MetadataSection title="Key details">
            <dl className="sfe-preview-meta">
              <MetaRow label="Category" value={md.category} />
              <MetaRow label="Role" value={md.document_role} />
              <MetaRow label="Project" value={md.project} />
              <MetaRow label="Platform" value={md.assay_tags || md.inferred_platforms} />
              <MetaRow label="Digitalization" value={md.digitalization_status} />
              <MetaRow label="Metadata grade" value={preview.metadata_grade} />
            </dl>
          </MetadataSection>
        ) : null}
        {detailsOpen ? (
        <>
        <MetadataSection title="Scientific context">
          <dl className="sfe-preview-meta">
            <MetaRow label="Project" value={md.project} />
            <MetaRow label="Inferred projects" value={md.inferred_project_codes} />
            <MetaRow label="Sample IDs" value={md.inferred_sample_ids} />
            <MetaRow label="Platform / assay" value={md.assay_tags || md.inferred_platforms} />
            <MetaRow label="Tissue / site" value={md.tissue_tags} />
            <MetaRow label="Markers / panels" value={md.marker_tags} />
            <MetaRow label="Years" value={md.inferred_years} />
          </dl>
        </MetadataSection>
        <MetadataSection title="Organization">
          <dl className="sfe-preview-meta">
            <MetaRow label="Domain" value={md.domain} />
            <MetaRow label="Section" value={md.section_label || md.section} />
            <MetaRow label="Category" value={md.category} />
            <MetaRow label="Subcategory" value={md.subcategory} />
            <MetaRow label="Folder root" value={md.domain_folder} />
            <MetaRow label="Owner" value={md.owner || md.inferred_people} />
          </dl>
        </MetadataSection>
        <MetadataSection title="File & indexing">
          <dl className="sfe-preview-meta">
            <MetaRow label="Path" value={preview.logical_path} />
            <MetaRow label="File type" value={md.file_type} />
            <MetaRow label="Document kind" value={md.document_kind} />
            <MetaRow label="Extension" value={md.extension} />
            <MetaRow label="Size" value={formatBytes(preview.size_bytes)} />
            <MetaRow label="Word count" value={md.word_count} />
            <MetaRow label="Extractor" value={md.extractor} />
            <MetaRow label="Modified" value={preview.modified_at?.slice(0, 10)} />
            <MetaRow label="Indexed" value={preview.indexed_at?.slice(0, 10)} />
            <MetaRow label="Digitalization" value={md.digitalization_status} />
            <MetaRow label="Extraction" value={md.extraction_status} />
            <MetaRow label="Vector status" value={md.vector_status} />
            <MetaRow label="Review" value={md.review_status} />
            <MetaRow label="Sensitivity" value={md.sensitivity_level} />
            <MetaRow label="Redigitalization" value={md.redigitalization_reason} />
            <MetaRow label="Protocol category" value={md.protocol_category} />
          </dl>
        </MetadataSection>
        {md.processed_metadata && Object.keys(md.processed_metadata).length > 0 ? (
          <MetadataSection title="Extracted file metadata">
            <dl className="sfe-preview-meta">
              {Object.entries(md.processed_metadata).slice(0, 16).map(([key, value]) => (
                <MetaRow key={key} label={prettifyCategory(key)} value={
                  typeof value === 'object' ? JSON.stringify(value) : value
                } />
              ))}
            </dl>
          </MetadataSection>
        ) : null}
        </>
        ) : null}
      </div>
    </aside>
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
  initialSystemView = 'all_files',
  initialFilters = {},
  initialQuery = '',
  showDomainTabs = true,
  hideScopeFilters = false,
  className = '',
}) {
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
  const [pinnedIds, setPinnedIds] = useState(() => loadPinnedIds());

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

  const searchParams = useMemo(() => ({
    q: debouncedQ,
    domain_tab: domainTab === 'all_files' ? undefined : domainTab,
    system_view: ['recently_opened', 'pinned'].includes(systemView) ? undefined : (systemView === 'all_files' ? undefined : systemView),
    sort,
    order,
    offset: 0,
    limit: 5000,
    ...filters,
  }), [debouncedQ, domainTab, systemView, sort, order, filters]);

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

  const handleSelect = useCallback((item) => {
    setSelected(item);
    pushRecentId(item.asset_id);
  }, []);

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

  const audit = stats?.audit_counts || {};

  return (
    <div className={`sfe-root ${className}`.trim()}>
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
        {showDomainTabs ? (
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
        ) : null}
      </header>

      <div className="sfe-stats-bar" aria-live="polite">
        <span className="sfe-stat-pill">{stats?.total_files?.toLocaleString() ?? '—'} files</span>
        <span className="sfe-stat-pill sfe-stat-pill--warn">{audit.not_started ?? '—'} not started</span>
        <span className="sfe-stat-pill sfe-stat-pill--warn">{audit.needs_redigitalization ?? '—'} redigitalization</span>
        <span className="sfe-stat-pill">{audit.unknown_type ?? '—'} unknown type</span>
        <span className="sfe-stat-pill">{audit.duplicate_groups ?? '—'} duplicate groups</span>
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
      />

      <div className="sfe-body">
        <section className="sfe-main">
          <DynamicExplorerChips
            systemView={systemView}
            onSystemView={setSystemView}
            stats={stats}
            facets={facets}
            filters={filters}
            onFilterChange={setFilters}
            hideScopeFilters={hideScopeFilters}
          />
          {loadError ? (
            <div className="sfe-error-banner" role="alert">{loadError}</div>
          ) : null}
          <div className="sfe-toolbar">
            <span>{loading ? 'Loading…' : `${total.toLocaleString()} results`}</span>
            <div className="sfe-view-toggle">
              <button type="button" className={viewMode === 'table' ? 'is-active' : ''} onClick={() => setViewMode('table')} aria-label="Table view">
                <List size={14} />
              </button>
              <button type="button" className={viewMode === 'card' ? 'is-active' : ''} onClick={() => setViewMode('card')} aria-label="Card view">
                <LayoutGrid size={14} />
              </button>
            </div>
          </div>
          {loading ? (
            <div className="sfe-loading"><Loader2 className="spin-inline" size={20} /> Loading files…</div>
          ) : (
            <VirtualFileList
              items={items}
              viewMode={viewMode}
              selectedId={selected?.asset_id}
              onSelect={handleSelect}
              sort={sort}
              order={order}
              onSortChange={handleSortChange}
            />
          )}
        </section>
        <FilePreviewPanel
          assetId={selected?.asset_id}
          pinned={selected ? pinnedIds.includes(selected.asset_id) : false}
          onTogglePin={handleTogglePin}
        />
      </div>
    </div>
  );
}
