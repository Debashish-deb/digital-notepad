import { useEffect, useState } from 'react';
import { fetchCellInspection } from '@/services/imageAssetsClient.js';

export default function CellInspector({ assetId, cellId, onOpenProfile }) {
  const [cell, setCell] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!assetId || !cellId) {
      setCell(null);
      return undefined;
    }
    let alive = true;
    fetchCellInspection(assetId, cellId)
      .then((data) => { if (alive) setCell(data); })
      .catch((err) => { if (alive) setError(err?.message || 'Cell lookup failed'); });
    return () => { alive = false; };
  }, [assetId, cellId]);

  if (!cellId) {
    return <p className="text-footnote muted">Click a segmented cell to inspect.</p>;
  }
  if (error) return <p className="text-footnote text-danger">{error}</p>;
  if (!cell) return <p className="text-footnote muted">Loading cell…</p>;

  return (
    <div className="image-panel image-panel--cell">
      <p className="text-footnote"><strong>Cell ID:</strong> {cell.cell_id}</p>
      <p className="text-footnote"><strong>Area:</strong> {cell.area_um2} µm²</p>
      <p className="text-footnote"><strong>Eccentricity:</strong> {cell.eccentricity}</p>
      <p className="text-footnote">
        <strong>Centroid:</strong> ({cell.centroid?.x}, {cell.centroid?.y})
      </p>
      {cell.marker_intensities ? (
        <ul className="image-panel__intensity-list">
          {Object.entries(cell.marker_intensities).map(([k, v]) => (
            <li key={k}>{k}: {v}</li>
          ))}
        </ul>
      ) : null}
      <button type="button" className="btn btn-ghost btn-xs" onClick={() => onOpenProfile?.(cell)}>
        Open full profile (stub)
      </button>
    </div>
  );
}
