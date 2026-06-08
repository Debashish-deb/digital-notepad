/**
 * Glass mini-card grid. Use `meta` for cover-style tiles (wider, 3×2-friendly, full labels).
 */
function shouldShowDetailValue(label, value) {
  if (!value) return false;
  const l = String(label || '').trim().toLowerCase();
  const v = String(value).trim().toLowerCase();
  if (!l || l === v) return false;
  if (v.startsWith(l) && v.length - l.length < 4) return false;
  return true;
}

export function GlassMiniCard({
  label,
  value = null,
  icon: Icon = null,
  tone = 'var(--color-primary)',
  delay = 0,
  onClick = null,
  title = null,
  highlight = false,
  compact = false,
  className = '',
  children = null,
}) {
  const Tag = onClick ? 'button' : 'article';
  const tooltip = title || (value && value !== label ? `${label} — ${value}` : label);
  const showDetailValue = compact ? shouldShowDetailValue(label, value) : Boolean(value);
  const iconSize = compact ? 14 : 13;
  const iconStroke = compact ? 2.1 : 2.1;

  return (
    <Tag
      type={onClick ? 'button' : undefined}
      className={`glass-mini-card sci-fi-card${onClick ? ' glass-mini-card--action' : ''}${highlight ? ' glass-mini-card--highlight' : ''}${compact ? ' glass-mini-card--compact' : ''}${compact && !showDetailValue ? ' glass-mini-card--solo' : ''}${className ? ` ${className}` : ''}`}
      style={{ '--card-tone': tone, '--card-delay': `${delay}ms` }}
      onClick={onClick}
      title={tooltip}
      aria-label={onClick ? tooltip : undefined}
    >
      <span className="glass-mini-card__sheen" aria-hidden />
      {Icon ? (
        <span className="glass-mini-card__icon" aria-hidden>
          <Icon size={iconSize} strokeWidth={iconStroke} />
        </span>
      ) : null}
      {compact ? (
        <span className="glass-mini-card__copy glass-mini-card__copy--stacked">
          <span className="glass-mini-card__label">{label}</span>
          {showDetailValue ? (
            <span className="glass-mini-card__value glass-mini-card__value--stacked">{value}</span>
          ) : null}
          {children}
        </span>
      ) : (
        <span className="glass-mini-card__copy">
          <span className="glass-mini-card__label">{label}</span>
          {value ? <span className="glass-mini-card__value">{value}</span> : null}
          {children}
        </span>
      )}
    </Tag>
  );
}

export default function GlassCardStack({
  children,
  className = '',
  columns = 2,
  rows = 3,
  wide = false,
  meta = false,
  compact = false,
}) {
  const isWide = wide || meta || compact;
  const isMeta = meta || compact;
  return (
    <div
      className={`glass-card-stack glass-card-stack--grid${isWide ? ' glass-card-stack--wide' : ''}${isMeta ? ' glass-card-stack--meta' : ''}${compact ? ' glass-card-stack--meta-compact' : ''}${className ? ` ${className}` : ''}`}
      style={{ '--stack-cols': columns, '--stack-rows': rows }}
    >
      {children}
    </div>
  );
}
