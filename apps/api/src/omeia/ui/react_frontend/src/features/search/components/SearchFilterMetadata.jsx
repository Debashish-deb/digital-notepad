import { AlertCircle, CheckCircle2, DatabaseZap } from 'lucide-react';

const FILTER_LABELS = {
  category: 'Category',
  smart_chip: 'Smart chip',
  domain_tab: 'Domain',
  system_view: 'System view',
  file_type: 'File type',
  date_from: 'From',
  date_to: 'To',
  indexed_status: 'Indexed status',
  project_codes: 'Projects',
  section_id: 'Section',
  source_buckets: 'Source buckets',
};

function formatFilterValue(value) {
  if (value == null || value === '') return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export default function SearchFilterMetadata({
  filtersApplied = {},
  unsupportedFilters = [],
  cacheHit = false,
  compact = false,
}) {
  const appliedEntries = Object.entries(filtersApplied || {}).filter(
    ([, value]) => value != null && String(value).trim() !== '',
  );
  const unsupported = Array.isArray(unsupportedFilters) ? unsupportedFilters : [];
  if (!appliedEntries.length && !unsupported.length && !cacheHit) return null;

  return (
    <div className={`search-filter-metadata${compact ? ' search-filter-metadata--compact' : ''}`}>
      {cacheHit ? (
        <span className="search-filter-metadata__cache" title="Results served from retrieval cache">
          <DatabaseZap size={12} aria-hidden />
          Cached
        </span>
      ) : null}
      {appliedEntries.length ? (
        <div className="search-filter-metadata__applied" role="status">
          <CheckCircle2 size={12} aria-hidden />
          <span className="search-filter-metadata__label">Filters applied:</span>
          {appliedEntries.map(([key, value]) => (
            <span key={key} className="search-filter-metadata__chip search-filter-metadata__chip--applied">
              {FILTER_LABELS[key] || key}: {formatFilterValue(value)}
            </span>
          ))}
        </div>
      ) : null}
      {unsupported.length ? (
        <div className="search-filter-metadata__unsupported" role="note">
          <AlertCircle size={12} aria-hidden />
          <span className="search-filter-metadata__label">Ignored for current scopes:</span>
          {unsupported.map((key) => (
            <span key={key} className="search-filter-metadata__chip search-filter-metadata__chip--unsupported">
              {FILTER_LABELS[key] || key}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
