import { Loader2 } from 'lucide-react';
import './LazyViewFallback.css';

const VARIANT_CLASS = {
  'diagram-3d': 'lazy-fallback--diagram-3d',
  'scene-3d': 'lazy-fallback--scene-3d',
  panel: 'lazy-fallback--panel',
  map: 'lazy-fallback--map',
};

/**
 * Compact glass-style placeholder for lazy-loaded views.
 */
export function LazyViewFallback({
  variant = 'panel',
  label = 'Loading…',
  className = '',
  showBars = true,
}) {
  const variantClass = VARIANT_CLASS[variant] || VARIANT_CLASS.panel;

  return (
    <div
      className={`lazy-fallback ${variantClass} ${className}`.trim()}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <span className="lazy-fallback__shimmer" aria-hidden />
      <div className="lazy-fallback__inner">
        <Loader2 size={variant === 'scene-3d' ? 22 : 18} className="spin" aria-hidden />
        <p className="lazy-fallback__label">{label}</p>
        {showBars && variant !== 'panel' ? (
          <div className="lazy-fallback__bars" aria-hidden>
            <span className="lazy-fallback__bar lazy-fallback__bar--long" />
            <span className="lazy-fallback__bar lazy-fallback__bar--mid" />
            <span className="lazy-fallback__bar lazy-fallback__bar--short" />
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default LazyViewFallback;
