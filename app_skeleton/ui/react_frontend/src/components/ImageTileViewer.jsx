import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Maximize2, ZoomIn, ZoomOut } from 'lucide-react';
import { useImageTileLoader } from '../hooks/useImageTileLoader.js';
import './ImageTileViewer.css';

const CHANNEL_COLORS = ['#00d4ff', '#ff4fd8', '#ffd400', '#4ade80', '#fb923c', '#a78bfa', '#f472b6', '#38bdf8'];

function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

function pyramidLevelForScale(scale, maxLevels) {
  let level = 0;
  while (level < maxLevels - 1 && scale < 1 / 2 ** (level + 1)) level += 1;
  return level;
}

function defaultChannelState(channels) {
  return Array.from({ length: Math.max(1, channels) }, (_, i) => ({
    index: i,
    visible: i < 3,
    color: CHANNEL_COLORS[i % CHANNEL_COLORS.length],
    label: `Channel ${i}`,
  }));
}

function axisCount(dimensions, axis) {
  const axes = dimensions?.axes || '';
  const shape = dimensions?.shape;
  if (!axes || !shape || !axes.includes(axis)) return 1;
  const idx = axes.indexOf(axis);
  return Math.max(1, Number(shape[idx]) || 1);
}

/**
 * Napari / Cylinter-style multi-channel tile canvas with Z/T navigation.
 */
export default function ImageTileViewer({
  assetId,
  manifest,
  thumbUrl = null,
  degraded = false,
}) {
  const dimensions = manifest?.dimensions;
  const width = manifest?.width || 1024;
  const height = manifest?.height || 1024;
  const channels = Math.max(1, manifest?.channels || 1);
  const zSlices = Math.max(
    1,
    manifest?.z_slices || manifest?.z || axisCount(dimensions, 'Z'),
  );
  const timepoints = Math.max(
    1,
    manifest?.timepoints || manifest?.t || axisCount(dimensions, 'T'),
  );
  const tileSize = manifest?.tile_size || 256;
  const pyramidLevels = Math.max(1, manifest?.pyramid_levels || 1);
  const tileReady = manifest?.tile_ready !== false && !degraded;

  const wrapRef = useRef(null);
  const canvasRef = useRef(null);
  const panRef = useRef({ active: false, lastX: 0, lastY: 0 });
  const renderGenRef = useRef(0);

  const [channelState, setChannelState] = useState(() => defaultChannelState(channels));
  const [zIndex, setZIndex] = useState(0);
  const [tIndex, setTIndex] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [status, setStatus] = useState('Ready');
  const [renderError, setRenderError] = useState(null);

  const { loadTile } = useImageTileLoader(assetId);

  useEffect(() => {
    setChannelState(defaultChannelState(channels));
    setZIndex(0);
    setTIndex(0);
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setRenderError(null);
  }, [assetId, channels]);

  const visibleChannels = useMemo(
    () => channelState.filter((ch) => ch.visible),
    [channelState],
  );

  const fitToView = useCallback(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const rect = wrap.getBoundingClientRect();
    const scale = Math.min(rect.width / width, rect.height / height, 1) * 0.95;
    setZoom(scale);
    setPan({
      x: (rect.width - width * scale) / 2,
      y: (rect.height - height * scale) / 2,
    });
  }, [width, height]);

  useEffect(() => {
    fitToView();
    const ro = new ResizeObserver(() => fitToView());
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [fitToView, assetId]);

  const drawTiles = useCallback(async () => {
    if (!tileReady) return;
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const gen = ++renderGenRef.current;
    const rect = wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;

    const ctx = canvas.getContext('2d', { alpha: false });
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#0b0f18';
    ctx.fillRect(0, 0, rect.width, rect.height);

    const level = pyramidLevelForScale(zoom, pyramidLevels);
    const levelScale = 2 ** level;
    const imgW = Math.max(1, Math.ceil(width / levelScale));
    const imgH = Math.max(1, Math.ceil(height / levelScale));

    const viewLeft = -pan.x / zoom;
    const viewTop = -pan.y / zoom;
    const viewRight = viewLeft + rect.width / zoom;
    const viewBottom = viewTop + rect.height / zoom;

    const x0 = Math.max(0, Math.floor(viewLeft / tileSize) * tileSize);
    const y0 = Math.max(0, Math.floor(viewTop / tileSize) * tileSize);
    const x1 = Math.min(imgW, Math.ceil(viewRight / tileSize) * tileSize);
    const y1 = Math.min(imgH, Math.ceil(viewBottom / tileSize) * tileSize);

    const active = visibleChannels.length ? visibleChannels : [channelState[0]];
    setStatus(`Loading ${active.length} channel(s) · Z ${zIndex + 1}/${zSlices}`);

    const offscreen = document.createElement('canvas');
    const offCtx = offscreen.getContext('2d');

    try {
      for (const ch of active) {
        for (let ty = y0; ty < y1; ty += tileSize) {
          for (let tx = x0; tx < x1; tx += tileSize) {
            if (gen !== renderGenRef.current) return;
            const tw = Math.min(tileSize, imgW - tx);
            const th = Math.min(tileSize, imgH - ty);
            const bitmap = await loadTile({
              level,
              x: tx,
              y: ty,
              width: tw,
              height: th,
              channel: ch.index,
              z: zIndex,
              t: tIndex,
            });
            if (gen !== renderGenRef.current) return;

            offscreen.width = tw;
            offscreen.height = th;
            offCtx.clearRect(0, 0, tw, th);
            offCtx.drawImage(bitmap, 0, 0);
            const imageData = offCtx.getImageData(0, 0, tw, th);
            const { r, g, b } = hexToRgb(ch.color);
            const data = imageData.data;
            for (let i = 0; i < data.length; i += 4) {
              const lum = data[i];
              data[i] = (lum * r) / 255;
              data[i + 1] = (lum * g) / 255;
              data[i + 2] = (lum * b) / 255;
              data[i + 3] = 255;
            }
            offCtx.putImageData(imageData, 0, 0);

            const screenX = pan.x + tx * levelScale * zoom;
            const screenY = pan.y + ty * levelScale * zoom;
            const screenW = tw * levelScale * zoom;
            const screenH = th * levelScale * zoom;
            ctx.globalAlpha = active.length > 1 ? 0.85 : 1;
            ctx.globalCompositeOperation = active.length > 1 ? 'lighter' : 'source-over';
            ctx.drawImage(offscreen, screenX, screenY, screenW, screenH);
          }
        }
      }
      if (gen === renderGenRef.current) {
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = 'source-over';
        setStatus(`Z ${zIndex + 1}/${zSlices} · T ${tIndex + 1}/${timepoints} · ${Math.round(zoom * 100)}%`);
        setRenderError(null);
      }
    } catch (err) {
      if (gen === renderGenRef.current) {
        setRenderError(err?.message || 'Tile render failed');
        setStatus('Degraded');
      }
    }
  }, [
    tileReady,
    zoom,
    pan,
    visibleChannels,
    channelState,
    zIndex,
    tIndex,
    zSlices,
    timepoints,
    width,
    height,
    tileSize,
    pyramidLevels,
    loadTile,
  ]);

  useEffect(() => {
    const id = requestAnimationFrame(() => drawTiles());
    return () => cancelAnimationFrame(id);
  }, [drawTiles]);

  const onWheel = useCallback(
    (e) => {
      e.preventDefault();
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      const nextZoom = Math.min(32, Math.max(0.02, zoom * factor));
      const ratio = nextZoom / zoom;
      setPan({
        x: mx - (mx - pan.x) * ratio,
        y: my - (my - pan.y) * ratio,
      });
      setZoom(nextZoom);
    },
    [zoom, pan],
  );

  const onPointerDown = useCallback((e) => {
    panRef.current = { active: true, lastX: e.clientX, lastY: e.clientY };
    setIsPanning(true);
    e.currentTarget.setPointerCapture?.(e.pointerId);
  }, []);

  const onPointerMove = useCallback((e) => {
    if (!panRef.current.active) return;
    const dx = e.clientX - panRef.current.lastX;
    const dy = e.clientY - panRef.current.lastY;
    panRef.current.lastX = e.clientX;
    panRef.current.lastY = e.clientY;
    setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
  }, []);

  const onPointerUp = useCallback(() => {
    panRef.current.active = false;
    setIsPanning(false);
  }, []);

  const toggleChannel = (index) => {
    setChannelState((rows) =>
      rows.map((row) => (row.index === index ? { ...row, visible: !row.visible } : row)),
    );
  };

  if (!tileReady) {
    return (
      <div className="image-tile-viewer">
        <div className="image-tile-viewer__viewport-wrap" ref={wrapRef}>
          <div className="image-tile-viewer__fallback">
            <p>Pyramid tiles are not ready. Showing thumbnail preview.</p>
            {thumbUrl ? <img src={thumbUrl} alt="Thumbnail preview" /> : <p>No thumbnail available.</p>}
            {degraded ? <p className="muted">Streaming is degraded for this asset.</p> : null}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="image-tile-viewer">
      <div className="image-tile-viewer__toolbar">
        <div className="image-tile-viewer__toolbar-group">
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setZoom((z) => Math.min(32, z * 1.25))} title="Zoom in">
            <ZoomIn size={14} />
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setZoom((z) => Math.max(0.02, z / 1.25))} title="Zoom out">
            <ZoomOut size={14} />
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={fitToView} title="Fit to view">
            <Maximize2 size={14} />
          </button>
        </div>
        <span className="image-tile-viewer__toolbar-label">{status}</span>
        {renderError ? <span className="text-danger text-sm">{renderError}</span> : null}
      </div>

      <aside className="image-tile-viewer__channels" aria-label="Channel controls">
        <h3 className="image-tile-viewer__channels-title">Channels</h3>
        {channelState.map((ch) => (
          <label
            key={ch.index}
            className={`image-tile-viewer__channel-row${ch.visible ? '' : ' is-off'}`}
          >
            <input
              type="checkbox"
              checked={ch.visible}
              onChange={() => toggleChannel(ch.index)}
            />
            <span className="image-tile-viewer__channel-name">{ch.label}</span>
            <span
              className="image-tile-viewer__channel-swatch"
              style={{ backgroundColor: ch.color }}
              aria-hidden
            />
          </label>
        ))}

        {zSlices > 1 ? (
          <div className="image-tile-viewer__slider-block">
            <label>
              <span>Z slice</span>
              <span>
                {zIndex + 1} / {zSlices}
              </span>
            </label>
            <input
              type="range"
              min={0}
              max={zSlices - 1}
              value={zIndex}
              onChange={(e) => setZIndex(Number(e.target.value))}
            />
          </div>
        ) : null}

        {timepoints > 1 ? (
          <div className="image-tile-viewer__slider-block">
            <label>
              <span>Time</span>
              <span>
                {tIndex + 1} / {timepoints}
              </span>
            </label>
            <input
              type="range"
              min={0}
              max={timepoints - 1}
              value={tIndex}
              onChange={(e) => setTIndex(Number(e.target.value))}
            />
          </div>
        ) : null}
      </aside>

      <div className="image-tile-viewer__viewport-wrap" ref={wrapRef}>
        <canvas
          ref={canvasRef}
          className={`image-tile-viewer__canvas${isPanning ? ' is-panning' : ''}`}
          onWheel={onWheel}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onDoubleClick={fitToView}
        />
        <div className="image-tile-viewer__status">
          {width}×{height} · {channels} ch · scroll zoom · drag pan
        </div>
      </div>
    </div>
  );
}
