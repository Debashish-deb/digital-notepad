import { useEffect, useState } from 'react';
import { fetchImageOverlays } from '@/services/imageAssetsClient.js';

const OVERLAY_TYPES = ['mesmer', 'stardist', 'cell', 'nucleus'];

export default function SegmentationOverlay({
  assetId,
  enabled,
  onSelectCell,
  viewerFlags = {},
}) {
  const [overlays, setOverlays] = useState([]);
  const [visible, setVisible] = useState(true);
  const [opacity, setOpacity] = useState(0.6);
  const [boundaryColor, setBoundaryColor] = useState('#ffd400');
  const [boundaryWidth, setBoundaryWidth] = useState(1.5);
  const [activeId, setActiveId] = useState(null);

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
      <p className="text-footnote muted">
        Supported types: {OVERLAY_TYPES.join(', ')}. Overlay geometry loads via overlay_asset_id (stub render).
      </p>
      <button type="button" className="btn btn-ghost btn-xs" onClick={() => onSelectCell?.('cell_demo_1')}>
        Inspect demo cell
      </button>
    </div>
  );
}
