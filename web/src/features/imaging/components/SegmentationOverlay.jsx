import { useEffect, useMemo, useState } from 'react';
import { fetchImageOverlays, fetchOverlayGeometry } from '@/services/imageAssetsClient.js';

const OVERLAY_TYPES = ['mesmer', 'stardist', 'cell', 'nucleus'];

export default function SegmentationOverlay({
  assetId,
  enabled,
  onSelectCell,
  onContoursChange,
  viewerFlags = {},
}) {
  const [overlays, setOverlays] = useState([]);
  const [visible, setVisible] = useState(true);
  const [opacity, setOpacity] = useState(0.6);
  const [boundaryColor, setBoundaryColor] = useState('#ffd400');
  const [boundaryWidth, setBoundaryWidth] = useState(1.5);
  const [activeId, setActiveId] = useState(null);
  const [geometry, setGeometry] = useState(null);
  const [phenotypeFilter, setPhenotypeFilter] = useState('');
  const [cellSearch, setCellSearch] = useState('');

  useEffect(() => {
    if (!enabled || !viewerFlags.segmentation_overlays) return undefined;
    let alive = true;
    fetchImageOverlays(assetId)
      .then((data) => {
        if (alive) {
          setOverlays(data.overlays || []);
          if (data.overlays?.length) setActiveId(data.overlays[0].overlay_id);
        }
      })
      .catch(() => {});
    return () => { alive = false; };
  }, [assetId, enabled, viewerFlags.segmentation_overlays]);

  useEffect(() => {
    if (!activeId || !visible) {
      setGeometry(null);
      onContoursChange?.([]);
      return undefined;
    }
    let alive = true;
    fetchOverlayGeometry(assetId, activeId)
      .then((data) => { if (alive) setGeometry(data); })
      .catch(() => { if (alive) setGeometry(null); });
    return () => { alive = false; };
  }, [assetId, activeId, visible, onContoursChange]);

  const cells = useMemo(() => {
    const raw = geometry?.cells || {};
    return Object.entries(raw).map(([id, entry]) => ({ id, ...entry }));
  }, [geometry]);

  const filteredCells = useMemo(() => {
    let list = cells;
    if (phenotypeFilter) {
      const pf = phenotypeFilter.toLowerCase();
      list = list.filter((c) => String(c.phenotype || c.label || '').toLowerCase().includes(pf));
    }
    if (cellSearch.trim()) {
      const q = cellSearch.trim().toLowerCase();
      list = list.filter((c) => c.id.toLowerCase().includes(q));
    }
    return list;
  }, [cells, phenotypeFilter, cellSearch]);

  useEffect(() => {
    if (!visible) {
      onContoursChange?.([]);
      return;
    }
    const contours = [];
    if (geometry?.contours?.length) {
      geometry.contours.forEach((c) => {
        contours.push({
          points: c.points || c,
          color: boundaryColor,
          width: boundaryWidth,
          opacity,
          closed: c.closed !== false,
        });
      });
    } else if (cells.length) {
      cells.forEach((cell) => {
        const pts = cell.contour || cell.boundary;
        if (pts?.length >= 3) {
          contours.push({
            points: pts,
            color: boundaryColor,
            width: boundaryWidth,
            opacity,
            closed: true,
            cellId: cell.id,
          });
        } else if (cell.centroid) {
          const { x, y } = cell.centroid;
          const r = 6;
          const circlePts = Array.from({ length: 12 }, (_, i) => {
            const a = (i / 12) * Math.PI * 2;
            return { x: x + Math.cos(a) * r, y: y + Math.sin(a) * r };
          });
          contours.push({
            points: circlePts,
            color: boundaryColor,
            width: boundaryWidth,
            opacity,
            closed: true,
            cellId: cell.id,
          });
        }
      });
    }
    onContoursChange?.(contours);
  }, [geometry, cells, visible, boundaryColor, boundaryWidth, opacity, onContoursChange]);

  if (!viewerFlags.segmentation_overlays) {
    return <p className="text-footnote muted">Segmentation overlays disabled by server flag.</p>;
  }

  const active = overlays.find((o) => o.overlay_id === activeId);

  return (
    <div className="image-panel image-panel--segmentation">
      <label className="image-panel__toggle">
        <input type="checkbox" checked={visible} onChange={(e) => setVisible(e.target.checked)} />
        Show overlay
      </label>
      <label className="image-panel__field">
        Opacity
        <input type="range" min={0} max={1} step={0.05} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} />
      </label>
      <label className="image-panel__field">
        Boundary color
        <input type="color" value={boundaryColor} onChange={(e) => setBoundaryColor(e.target.value)} />
      </label>
      <label className="image-panel__field">
        Boundary width
        <input type="range" min={0.5} max={4} step={0.5} value={boundaryWidth} onChange={(e) => setBoundaryWidth(Number(e.target.value))} />
      </label>
      <select value={activeId || ''} onChange={(e) => setActiveId(e.target.value)}>
        <option value="">— select overlay —</option>
        {overlays.map((o) => (
          <option key={o.overlay_id} value={o.overlay_id}>
            {o.label || o.overlay_type} ({o.overlay_asset_id})
          </option>
        ))}
      </select>
      {active ? (
        <p className="text-footnote">
          Type: {active.overlay_type} · asset {active.overlay_asset_id}
        </p>
      ) : null}
      <label className="image-panel__field">
        Phenotype filter
        <input type="text" placeholder="e.g. CD8, tumor" value={phenotypeFilter} onChange={(e) => setPhenotypeFilter(e.target.value)} />
      </label>
      <label className="image-panel__field">
        Cell search
        <input type="text" placeholder="cell id" value={cellSearch} onChange={(e) => setCellSearch(e.target.value)} />
      </label>
      <ul className="image-panel__roi-list">
        {filteredCells.slice(0, 20).map((cell) => (
          <li key={cell.id}>
            <button type="button" className="btn btn-ghost btn-xs" onClick={() => onSelectCell?.(cell.id)}>
              {cell.id}
            </button>
            {cell.phenotype ? <span className="text-footnote muted"> {cell.phenotype}</span> : null}
          </li>
        ))}
      </ul>
      {!cells.length && !geometry?.contours?.length ? (
        <p className="text-footnote muted">
          No overlay geometry — attach metadata.contours or metadata.cells. Types: {OVERLAY_TYPES.join(', ')}.
        </p>
      ) : null}
    </div>
  );
}
