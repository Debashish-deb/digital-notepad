import { formatLength, pixelSizeUm } from '@/features/imaging/utils/measurementHelpers.js';

export default function ScaleBar({ manifest, zoom, visible, unit = 'um' }) {
  if (!visible) return null;
  const umPerPx = pixelSizeUm(manifest);
  if (!umPerPx) {
    return (
      <div className="image-scale-bar image-scale-bar--unknown">
        <span>No physical pixel size in manifest</span>
      </div>
    );
  }

  const targetUm = unit === 'mm' ? 100 : 50;
  let barPx = targetUm / umPerPx;
  barPx = Math.max(40, Math.min(barPx * zoom, 200));
  const barUm = barPx * umPerPx / zoom;

  return (
    <div className="image-scale-bar">
      <div className="image-scale-bar__line" style={{ width: `${barPx}px` }} />
      <span>{formatLength(barUm, unit)}</span>
    </div>
  );
}
