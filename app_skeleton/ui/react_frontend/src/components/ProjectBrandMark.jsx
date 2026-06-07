
/** Logo-style project code with superscript catalog index (workspace + portfolio). */
export default function ProjectBrandMark({
  code,
  index = null,
  name = null,
  variant = 'intro',
  className = '',
}) {
  if (!code) return null;

  const showSubtitle = name && name.trim() && name.trim().toUpperCase() !== code.trim().toUpperCase();

  return (
    <div
      className={`project-brand-mark project-brand-mark--${variant}${className ? ` ${className}` : ''}`}
      aria-label={
        index != null && index !== ''
          ? `Project ${code}, number ${index}`
          : `Project ${code}`
      }
    >
      <span className="project-brand-mark__word">
        {code}
        {index != null && index !== '' ? (
          <sup className="project-brand-mark__index" aria-hidden="true">
            {index}
          </sup>
        ) : null}
      </span>
      {showSubtitle ? <span className="project-brand-mark__name">{name}</span> : null}
    </div>
  );
}
