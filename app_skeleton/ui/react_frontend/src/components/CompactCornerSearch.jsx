import { useEffect, useId, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';
import './CompactCornerSearch.css';

/**
 * Small expandable search control for subsection cover corners.
 * Collapsed: icon pill. Expanded: compact input (~11rem).
 */
export default function CompactCornerSearch({
  value = '',
  onChange,
  placeholder = 'Search…',
  ariaLabel = 'Search',
  className = '',
}) {
  const inputId = useId();
  const inputRef = useRef(null);
  const [open, setOpen] = useState(Boolean(value));

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (value) setOpen(true);
  }, [value]);

  const handleToggle = () => {
    setOpen((prev) => {
      const next = !prev;
      if (!next && value) onChange?.('');
      return next;
    });
  };

  return (
    <div
      className={`compact-corner-search${open ? ' is-open' : ''}${className ? ` ${className}` : ''}`.trim()}
    >
      <button
        type="button"
        className="compact-corner-search__toggle"
        onClick={handleToggle}
        aria-label={open ? 'Collapse search' : ariaLabel}
        aria-expanded={open}
        aria-controls={inputId}
      >
        <Search size={13} aria-hidden />
      </button>
      {open ? (
        <div className="compact-corner-search__field">
          <label className="sr-only" htmlFor={inputId}>
            {ariaLabel}
          </label>
          <input
            ref={inputRef}
            id={inputId}
            type="search"
            className="compact-corner-search__input"
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            aria-label={ariaLabel}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                if (value) onChange?.('');
                else setOpen(false);
              }
            }}
          />
          {value ? (
            <button
              type="button"
              className="compact-corner-search__clear"
              onClick={() => onChange?.('')}
              aria-label="Clear search"
            >
              <X size={12} aria-hidden />
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
