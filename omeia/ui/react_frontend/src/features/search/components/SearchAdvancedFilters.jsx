import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

const INDEXED_OPTIONS = [
  { value: '', label: 'Any indexed status' },
  { value: 'indexed', label: 'Indexed' },
  { value: 'not_indexed', label: 'Not indexed' },
];

const DOMAIN_TAB_OPTIONS = [
  { value: '', label: 'Any domain' },
  { value: 'overview', label: 'Lab administration' },
  { value: 'wet_lab', label: 'Lab operations' },
  { value: 'orders', label: 'Orders & procurement' },
  { value: 'all_files', label: 'Full library' },
];

const EMPTY_ADVANCED = {
  smartChip: '',
  category: '',
  fileType: '',
  indexedStatus: '',
  domainTab: '',
  dateFrom: '',
  dateTo: '',
};

export function emptyAdvancedFilters() {
  return { ...EMPTY_ADVANCED };
}

export default function SearchAdvancedFilters({ value, onChange, compact = false }) {
  const [open, setOpen] = useState(false);
  const filters = value || EMPTY_ADVANCED;

  const setField = (field, next) => {
    onChange?.({ ...filters, [field]: next });
  };

  const hasActive = Object.values(filters).some((v) => String(v || '').trim());

  return (
    <div className={`search-advanced-filters${compact ? ' search-advanced-filters--compact' : ''}`}>
      <button
        type="button"
        className={`search-advanced-filters__toggle${open ? ' is-open' : ''}${hasActive ? ' has-active' : ''}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? <ChevronUp size={14} aria-hidden /> : <ChevronDown size={14} aria-hidden />}
        Advanced filters
        {hasActive ? <span className="search-advanced-filters__badge">{Object.values(filters).filter((v) => String(v || '').trim()).length}</span> : null}
      </button>
      {open ? (
        <div className="search-advanced-filters__panel" role="group" aria-label="Advanced search filters">
          <label className="search-advanced-filters__field">
            <span>Smart chip</span>
            <input
              type="text"
              value={filters.smartChip}
              placeholder="protocol, sop…"
              onChange={(e) => setField('smartChip', e.target.value)}
            />
          </label>
          <label className="search-advanced-filters__field">
            <span>Category</span>
            <input
              type="text"
              value={filters.category}
              placeholder="Category slug"
              onChange={(e) => setField('category', e.target.value)}
            />
          </label>
          <label className="search-advanced-filters__field">
            <span>File type</span>
            <input
              type="text"
              value={filters.fileType}
              placeholder="pdf, csv…"
              onChange={(e) => setField('fileType', e.target.value)}
            />
          </label>
          <label className="search-advanced-filters__field">
            <span>Indexed</span>
            <select value={filters.indexedStatus} onChange={(e) => setField('indexedStatus', e.target.value)}>
              {INDEXED_OPTIONS.map((opt) => (
                <option key={opt.value || 'any'} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label className="search-advanced-filters__field">
            <span>Domain tab</span>
            <select value={filters.domainTab} onChange={(e) => setField('domainTab', e.target.value)}>
              {DOMAIN_TAB_OPTIONS.map((opt) => (
                <option key={opt.value || 'any'} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label className="search-advanced-filters__field">
            <span>Date from</span>
            <input type="date" value={filters.dateFrom} onChange={(e) => setField('dateFrom', e.target.value)} />
          </label>
          <label className="search-advanced-filters__field">
            <span>Date to</span>
            <input type="date" value={filters.dateTo} onChange={(e) => setField('dateTo', e.target.value)} />
          </label>
          {hasActive ? (
            <button type="button" className="search-advanced-filters__clear" onClick={() => onChange?.(emptyAdvancedFilters())}>
              Clear advanced filters
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function advancedFiltersToSearchParams(advanced = {}) {
  const params = {};
  if (advanced.smartChip?.trim()) params.smartChip = advanced.smartChip.trim();
  if (advanced.category?.trim()) params.category = advanced.category.trim();
  if (advanced.fileType?.trim()) params.fileType = advanced.fileType.trim();
  if (advanced.indexedStatus?.trim()) params.indexedStatus = advanced.indexedStatus.trim();
  if (advanced.domainTab?.trim()) params.domainTab = advanced.domainTab.trim();
  if (advanced.dateFrom?.trim()) params.dateFrom = advanced.dateFrom.trim();
  if (advanced.dateTo?.trim()) params.dateTo = advanced.dateTo.trim();
  return params;
}
