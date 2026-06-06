import { Search } from 'lucide-react';

/** Compact file search for the module shell header (top-right). */
export default function DocumentFileSearch({
  value,
  onChange,
  fileCount,
  searchPlaceholder,
  searchAria,
  filesLabel,
  compact = false,
}) {
  return (
    <label
      className={`module-doc-search${compact ? ' module-doc-search--compact' : ''}`}
      aria-label={searchAria}
    >
      <Search size={compact ? 9 : 12} className="module-doc-search-icon" aria-hidden />
      <input
        type="search"
        className="module-doc-search-input"
        placeholder={searchPlaceholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <span className="module-doc-search-count" title={filesLabel}>
        {fileCount}
      </span>
    </label>
  );
}
