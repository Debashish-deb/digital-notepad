import CopyPathButton from './CopyPathButton.jsx';

/**
 * Unified document section header — title block + integrated category tab row.
 * Used by catalog document browsers (Overview, Orders, Wet-lab, etc.).
 */
export default function DocumentSectionHeader({
  eyebrow = null,
  title,
  description = null,
  icon: Icon = null,
  contentRoot = null,
  children = null,
  className = '',
}) {
  if (!title) return children || null;

  return (
    <header className={`doc-section-header${className ? ` ${className}` : ''}`}>
      <div className="doc-section-header__main">
        <div className="doc-section-header__identity">
          {eyebrow ? <p className="doc-section-header__eyebrow">{eyebrow}</p> : null}
          <div className="doc-section-header__title-row">
            {Icon ? <Icon size={18} className="doc-section-header__icon" aria-hidden /> : null}
            <h2 className="doc-section-header__title">{title}</h2>
          </div>
          {description ? (
            <p className="doc-section-header__lead">{description}</p>
          ) : null}
        </div>
        {contentRoot ? (
          <div className="doc-section-header__actions">
            <CopyPathButton
              value={contentRoot}
              label="Copy folder path"
              iconOnly
            />
          </div>
        ) : null}
      </div>
      {children ? <div className="doc-section-header__toolbar">{children}</div> : null}
    </header>
  );
}
