import { useMemo } from 'react';
import TaxonomyConnectorMap from './TaxonomyConnectorMap.jsx';
import { SYSTEM_VIEWS } from '@/services/documentLibraryClient.js';
import {
  MAINTENANCE_CHIP_IDS,
  prettifyCategory,
  scopeChipToFilters,
} from '@/features/documents/documentLibraryUi.js';

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

  const scopeChipItems = useMemo(
    () => (scopeChips || [])
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
  const allSubcategoryChipItems = useMemo(
    () => Object.entries(facet.subcategory || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 14)
      .map(([id, count]) => ({
        kind: 'subcategory',
        id,
        label: prettifyCategory(id),
        count,
        filter: { subcategory: id },
      })),
    [facet.subcategory],
  );

  const allSubcategoryMapChips = useMemo(
    () => allSubcategoryChipItems.map((chip) => ({
      ...chip,
      filter: filters.category
        ? { category: filters.category, subcategory: chip.id }
        : { subcategory: chip.id },
    })),
    [allSubcategoryChipItems, filters.category],
  );

  const showCategoryMap = categoryMapChips.length > 0;
  const showSubcategoryMap = allSubcategoryMapChips.length > 0;

  if (!hasScopeMap && !showCategoryMap && !showSubcategoryMap) return null;

  return (
    <div className="sfe-taxonomy-maps">
      {hasScopeMap ? (
        <TaxonomyConnectorMap
          chips={scopeChipItems}
          scopeLabel={scopeLabel || (hideScopeFilters ? 'Library scope' : 'Domain scope')}
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
          isChipActive={isChipActive}
          onChipClick={handleChipClick}
          onResetScope={() => onFilterChange({ ...filters, category: undefined, subcategory: undefined })}
        />
      ) : null}
      {showSubcategoryMap ? (
        <TaxonomyConnectorMap
          chips={allSubcategoryMapChips}
          scopeLabel={filters.category ? prettifyCategory(filters.category) : 'Subcategories'}
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

export default function DocumentFilterPanel({
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
