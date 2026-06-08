import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Maximize2, Minimize2, X } from 'lucide-react';
import { DocumentViewerToolButton } from './DocumentViewerToolbar.jsx';
import './DocumentViewerExpand.css';
import './DocumentViewerToolbar.css';

const BODY_LOCK_CLASS = 'doc-viewer-expanded-active';

export function DocumentViewerExpandButton({
  expanded,
  onToggle,
  expandLabel = 'Expand viewer',
  collapseLabel = 'Exit expanded view',
  variant = 'toolbar',
  className = 'btn btn-secondary btn-sm',
}) {
  if (variant === 'toolbar') {
    return (
      <button
        type="button"
        className={`doc-viewer-tool doc-viewer-expand-btn${expanded ? ' is-active' : ''}`}
        onClick={onToggle}
        title={expanded ? collapseLabel : expandLabel}
        aria-label={expanded ? collapseLabel : expandLabel}
        aria-pressed={expanded}
      >
        {expanded ? <Minimize2 size={14} aria-hidden /> : <Maximize2 size={14} aria-hidden />}
      </button>
    );
  }

  return (
    <button
      type="button"
      className={`${className} doc-viewer-expand-btn`}
      onClick={onToggle}
      title={expanded ? collapseLabel : expandLabel}
      aria-label={expanded ? collapseLabel : expandLabel}
      aria-pressed={expanded}
    >
      {expanded ? <Minimize2 size={14} aria-hidden /> : <Maximize2 size={14} aria-hidden />}
      <span>{expanded ? 'Collapse' : 'Expand'}</span>
    </button>
  );
}

export function DocumentViewerExpandPortal({
  expanded,
  onClose,
  title,
  subtitle,
  headerActions = null,
  children,
}) {
  useEffect(() => {
    if (!expanded) return undefined;

    document.body.classList.add(BODY_LOCK_CLASS);

    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.classList.remove(BODY_LOCK_CLASS);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [expanded, onClose]);

  if (!expanded || typeof document === 'undefined') return null;

  return createPortal(
    <div
      className="doc-viewer-expanded-shell"
      role="dialog"
      aria-modal="true"
      aria-label={title ? `Expanded view: ${title}` : 'Expanded document view'}
    >
      <header className="doc-viewer-expanded-shell__header">
        <div className="doc-viewer-expanded-shell__titles">
          {title ? <h2 className="doc-viewer-expanded-shell__title">{title}</h2> : null}
          {subtitle ? <p className="doc-viewer-expanded-shell__subtitle">{subtitle}</p> : null}
        </div>
        <div className="doc-viewer-expanded-shell__actions">
          {headerActions}
          <DocumentViewerToolButton labeled onClick={onClose} title="Close expanded view">
            <X size={14} aria-hidden />
            <span>Close</span>
          </DocumentViewerToolButton>
        </div>
      </header>
      <div className="doc-viewer-expanded-shell__body">{children}</div>
    </div>,
    document.body
  );
}
