import { normalizeModalityList } from '../utils/modalityMeta.js';

/** Compact modality chips — inline beside the project title on the glass cover card. */
export default function ProjectModalityPills({
  modalities = [],
  className = '',
  maxVisible = 4,
}) {
  const items = normalizeModalityList(modalities);
  if (!items.length) return null;

  const shown = items.slice(0, maxVisible);
  const overflow = items.length - shown.length;

  return (
    <div
      className={`project-modality-pills${className ? ` ${className}` : ''}`}
      aria-label="Project modalities"
    >
      {shown.map((item) => (
        <span
          key={item.name}
          className="project-modality-pill"
          title={item.name}
          style={{ '--modality-tone': item.tone }}
        >
          <span>{item.label}</span>
        </span>
      ))}
      {overflow > 0 ? (
        <span className="project-modality-pill project-modality-pill--overflow" title={items.slice(maxVisible).map((i) => i.name).join(', ')}>
          +{overflow}
        </span>
      ) : null}
    </div>
  );
}
