export default function HeatmapOverlay({ viewerFlags = {}, opacity = 0.5, onOpacityChange }) {
  if (!viewerFlags.heatmaps) {
    return (
      <div className="image-panel image-panel--heatmap">
        <p className="text-footnote muted">Heatmap overlays disabled (IMAGE_ENABLE_HEATMAPS=false).</p>
      </div>
    );
  }

  return (
    <div className="image-panel image-panel--heatmap">
      <p className="text-footnote muted">
        Density heatmap architecture stub — future endpoint will supply raster overlay_asset_id.
      </p>
      <label className="image-panel__field">
        Opacity
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={opacity}
          onChange={(e) => onOpacityChange?.(Number(e.target.value))}
        />
      </label>
    </div>
  );
}
