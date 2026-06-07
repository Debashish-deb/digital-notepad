import './DocumentViewerToolbar.css';

export function DocumentViewerToolbar({ children, className = '', label = 'Document actions' }) {
  return (
    <div
      className={`doc-viewer-toolbar${className ? ` ${className}` : ''}`}
      role="toolbar"
      aria-label={label}
    >
      {children}
    </div>
  );
}

export function DocumentViewerToolButton({
  onClick,
  title,
  ariaLabel,
  active = false,
  disabled = false,
  labeled = false,
  children,
  className = '',
}) {
  return (
    <button
      type="button"
      className={[
        'doc-viewer-tool',
        labeled ? 'doc-viewer-tool--labeled' : '',
        active ? 'is-active' : '',
        className,
      ].filter(Boolean).join(' ')}
      onClick={onClick}
      title={title}
      aria-label={ariaLabel || title}
      aria-pressed={active || undefined}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export function DocumentViewerMetaChip({ value, label = 'Metadata', low = false }) {
  if (value == null || Number.isNaN(value)) return null;

  return (
    <div className="doc-viewer-meta-chip" title={`${label} completeness`}>
      <span className="doc-viewer-meta-chip__label">{label}</span>
      <span className={`doc-viewer-meta-chip__value${low ? ' is-low' : ''}`}>{value}%</span>
    </div>
  );
}
