import { documentTitleSubline } from '@/lib/smartDocumentTitle.js';

/**
 * Second-row metadata: place · document type · date (small, muted).
 */
export default function DocumentListMetadataRow({
  item,
  subline: sublineProp = null,
  className = 'sfe-row-original',
  pathFallback = null,
  showPathFallback = false,
}) {
  const subline = sublineProp || documentTitleSubline(item);

  if (subline.chips?.length) {
    return (
      <div className={className} aria-label="Document metadata">
        {subline.chips.map((chip) => (
          <span key={chip.key} className={chip.className}>
            {chip.label}
          </span>
        ))}
      </div>
    );
  }

  if (showPathFallback && pathFallback) {
    return <div className="sfe-row-path">{pathFallback}</div>;
  }

  return null;
}
