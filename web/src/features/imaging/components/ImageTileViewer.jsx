import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Crosshair, Maximize2, Ruler, ZoomIn, ZoomOut } from 'lucide-react';
import { useImageTileLoader } from '@/shared/hooks/useImageTileLoader.js';
import { applyIntensity, defaultChannelState } from '@/features/imaging/utils/channelState.js';
import ChannelManager from './ChannelManager.jsx';
import HistogramPanel from './HistogramPanel.jsx';
import PixelInspector from './PixelInspector.jsx';
import ScaleBar from './ScaleBar.jsx';
import SegmentationOverlay from './SegmentationOverlay.jsx';
import HeatmapOverlay from './HeatmapOverlay.jsx';
import ROIManager from './ROIManager.jsx';
import CellInspector from './CellInspector.jsx';
import MeasurementTools from './MeasurementTools.jsx';
import SpatialAnalysisOverlay from './SpatialAnalysisOverlay.jsx';
import './ImageTileViewer.css';

const SIDEBAR_TABS = [
  { id: 'channels', label: 'Channels' },
  { id: 'histogram', label: 'Histogram' },
  { id: 'roi', label: 'ROI' },
  { id: 'overlays', label: 'Overlays' },
  { id: 'analysis', label: 'Analysis' },
  { id: 'inspect', label: 'Inspect' },
];

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

function axisCount(dimensions, axis) {
  const axes = dimensions?.axes || '';
  const shape = dimensions?.shape;
  if (!axes || !shape || !axes.includes(axis)) return 1;
  const idx = axes.indexOf(axis);
  return Math.max(1, Number(shape[idx]) || 1);
}

function screenToImage(screenX, screenY, pan, zoom) {
  return {
    x: (screenX - pan.x) / zoom,
    y: (screenY - pan.y) / zoom,
  };
}

/**
 * Napari / Cylinter-style multi-channel tile canvas with research viewer panels (Phase 7B).
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
  const channelNames = manifest?.channel_names || [];
  const viewerFlags = manifest?.viewer_flags || {};
  const zSlices = Math.max(1, manifest?.z_slices || manifest?.z || axisCount(dimensions, 'Z'));
  const timepoints = Math.max(1, manifest?.timepoints || manifest?.t || axisCount(dimensions, 'T'));
  const tileSize = manifest?.tile_size || 256;
  const pyramidLevels = Math.max(1, manifest?.pyramid_levels || 1);
  const tileReady = manifest?.tile_ready !== false && !degraded;

  const wrapRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayRef = useRef(null);
  const panRef = useRef({ active: false, lastX: 0, lastY: 0 });
  const renderGenRef = useRef(0);
  const tileIntensityCache = useRef(new Map());

  const [channelState, setChannelState] = useState(() => defaultChannelState(channels, channelNames));
  const [selectedChannel, setSelectedChannel] = useState(0);
  const [sidebarTab, setSidebarTab] = useState('channels');
  const [zIndex, setZIndex] = useState(0);
  const [tIndex, setTIndex] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [status, setStatus] = useState('Ready');
  const [renderError, setRenderError] = useState(null);
  const [inspectionMode, setInspectionMode] = useState(false);
  const [showScaleBar, setShowScaleBar] = useState(true);
  const [scaleUnit, setScaleUnit] = useState('um');
  const [pixelInfo, setPixelInfo] = useState(null);
  const [imageCoords, setImageCoords] = useState(null);
  const [roiTool, setRoiTool] = useState('rectangle');
  const [draftRoi, setDraftRoi] = useState(null);
  const [measurement, setMeasurement] = useState(null);
  const [selectedCellId, setSelectedCellId] = useState(null);
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.5);

  const { loadTile } = useImageTileLoader(assetId);

  useEffect(() => {
    setChannelState(defaultChannelState(channels, channelNames));
    setSelectedChannel(0);
    setZIndex(0);
    setTIndex(0);
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setRenderError(null);
    setDraftRoi(null);
    setMeasurement(null);
    tileIntensityCache.current.clear();
  }, [assetId, channels, channelNames.join('|')]);

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
              const lum = applyIntensity(data[i], ch);
              const alpha = Math.max(0, Math.min(255, lum * ch.opacity));
              data[i] = (alpha * r) / 255;
              data[i + 1] = (alpha * g) / 255;
              data[i + 2] = (alpha * b) / 255;
              data[i + 3] = alpha;
            }
            offCtx.putImageData(imageData, 0, 0);

            const cacheKey = `${ch.index}:${tx}:${ty}:${tw}:${th}:${zIndex}:${tIndex}`;
            if (inspectionMode) {
              tileIntensityCache.current.set(cacheKey, {
                channel: ch.index,
                tx: tx * levelScale,
                ty: ty * levelScale,
                tw: tw * levelScale,
                th: th * levelScale,
                data: offCtx.getImageData(0, 0, tw, th).data,
                label: ch.label,
                color: ch.color,
              });
            }

            const screenX = pan.x + tx * levelScale * zoom;
            const screenY = pan.y + ty * levelScale * zoom;
            const screenW = tw * levelScale * zoom;
            const screenH = th * levelScale * zoom;
            ctx.globalAlpha = active.length > 1 ? 0.92 : 1;
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
    inspectionMode,
  ]);

  useEffect(() => {
    const id = requestAnimationFrame(() => drawTiles());
    return () => cancelAnimationFrame(id);
  }, [drawTiles]);

  const drawMeasurementOverlay = useCallback(() => {
    const overlay = overlayRef.current;
    const wrap = wrapRef.current;
    if (!overlay || !wrap) return;
    const rect = wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    overlay.width = Math.floor(rect.width * dpr);
    overlay.height = Math.floor(rect.height * dpr);
    overlay.style.width = `${rect.width}px`;
    overlay.style.height = `${rect.height}px`;
    const ctx = overlay.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    const toScreen = (ix, iy) => ({ x: pan.x + ix * zoom, y: pan.y + iy * zoom });

    if (draftRoi?.x != null) {
      ctx.strokeStyle = '#ffd400';
      ctx.lineWidth = 2;
      const p = toScreen(draftRoi.x, draftRoi.y);
      ctx.strokeRect(p.x, p.y, draftRoi.width * zoom, draftRoi.height * zoom);
    }

    if (measurement?.points?.length >= 2 && measurement.type === 'distance') {
      ctx.strokeStyle = '#00d4ff';
      ctx.beginPath();
      measurement.points.forEach((pt, i) => {
        const s = toScreen(pt.x, pt.y);
        if (i === 0) ctx.moveTo(s.x, s.y);
        else ctx.lineTo(s.x, s.y);
      });
      ctx.stroke();
    }
  }, [pan, zoom, draftRoi, measurement]);

  useEffect(() => {
    drawMeasurementOverlay();
  }, [drawMeasurementOverlay]);

  const samplePixelIntensities = useCallback(
    (ix, iy) => {
      const intensities = [];
      for (const [, tile] of tileIntensityCache.current) {
        const lx = Math.floor(ix - tile.tx);
        const ly = Math.floor(iy - tile.ty);
        if (lx < 0 || ly < 0 || lx >= tile.tw || ly >= tile.th) continue;
        const idx = (ly * (tile.data.length / 4 / tile.th) + lx) * 4;
        intensities.push({
          index: tile.channel,
          label: tile.label,
          color: tile.color,
          value: tile.data[idx],
        });
      }
      return intensities;
    },
    [],
  );

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

  const onPointerDown = useCallback(
    (e) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const img = screenToImage(sx, sy, pan, zoom);

      if (inspectionMode && sidebarTab === 'roi' && roiTool === 'rectangle') {
        setDraftRoi({ x: img.x, y: img.y, width: 0, height: 0, startX: img.x, startY: img.y });
        panRef.current = { active: true, mode: 'roi', lastX: e.clientX, lastY: e.clientY, start: img };
        return;
      }
      if (inspectionMode && measurement?.type === 'distance') {
        setMeasurement((m) => ({
          ...m,
          points: [...(m.points || []), img].slice(-2),
        }));
        return;
      }

      panRef.current = { active: true, mode: 'pan', lastX: e.clientX, lastY: e.clientY };
      setIsPanning(true);
      e.currentTarget.setPointerCapture?.(e.pointerId);
    },
    [inspectionMode, sidebarTab, roiTool, pan, zoom, measurement],
  );

  const onPointerMove = useCallback(
    (e) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const img = screenToImage(sx, sy, pan, zoom);
      setImageCoords(img);
      if (inspectionMode) {
        setPixelInfo({ intensities: samplePixelIntensities(img.x, img.y) });
      }

      if (!panRef.current.active) return;

      if (panRef.current.mode === 'roi' && draftRoi) {
        const start = panRef.current.start;
        setDraftRoi({
          ...draftRoi,
          x: Math.min(start.x, img.x),
          y: Math.min(start.y, img.y),
          width: Math.abs(img.x - start.x),
          height: Math.abs(img.y - start.y),
        });
        return;
      }

      const dx = e.clientX - panRef.current.lastX;
      const dy = e.clientY - panRef.current.lastY;
      panRef.current.lastX = e.clientX;
      panRef.current.lastY = e.clientY;
      setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
    },
    [pan, zoom, inspectionMode, samplePixelIntensities, draftRoi],
  );

  const onPointerUp = useCallback(() => {
    panRef.current.active = false;
    setIsPanning(false);
  }, []);

  const selectedCh = channelState[selectedChannel] || channelState[0];

  const sidebarContent = () => {
    switch (sidebarTab) {
      case 'histogram':
        return (
          <HistogramPanel
            assetId={assetId}
            channelIndex={selectedChannel}
            channelLabel={selectedCh?.label}
            min={selectedCh?.min ?? 0}
            max={selectedCh?.max ?? 255}
            zIndex={zIndex}
            enabled={!viewerFlags.low_resource_mode}
            onWindowChange={(patch) =>
              setChannelState((rows) =>
                rows.map((row) => (row.index === selectedChannel ? { ...row, ...patch } : row)),
              )
            }
          />
        );
      case 'roi':
        return (
          <ROIManager
            assetId={assetId}
            activeTool={roiTool}
            onToolChange={setRoiTool}
            draftGeometry={draftRoi}
            onDraftClear={() => setDraftRoi(null)}
            viewerFlags={viewerFlags}
          />
        );
      case 'overlays':
        return (
          <>
            <SegmentationOverlay
              assetId={assetId}
              enabled={tileReady}
              onSelectCell={setSelectedCellId}
              viewerFlags={viewerFlags}
            />
            <HeatmapOverlay viewerFlags={viewerFlags} opacity={heatmapOpacity} onOpacityChange={setHeatmapOpacity} />
          </>
        );
      case 'analysis':
        return <SpatialAnalysisOverlay />;
      case 'inspect':
        return (
          <>
            <PixelInspector pixel={pixelInfo} imageCoords={imageCoords} channelState={channelState} />
            <CellInspector assetId={assetId} cellId={selectedCellId} />
            <MeasurementTools manifest={manifest} measurement={measurement} unit={scaleUnit} />
          </>
        );
      default:
        return (
          <ChannelManager channelState={channelState} onChange={setChannelState} viewerFlags={viewerFlags} />
        );
    }
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
          <button
            type="button"
            className={`btn btn-ghost btn-sm${inspectionMode ? ' is-active' : ''}`}
            onClick={() => setInspectionMode((v) => !v)}
            title="Inspection mode"
          >
            <Crosshair size={14} />
          </button>
          <button
            type="button"
            className={`btn btn-ghost btn-sm${measurement?.type === 'distance' ? ' is-active' : ''}`}
            onClick={() => setMeasurement({ type: 'distance', mode: 'distance', points: [] })}
            title="Measure distance"
          >
            <Ruler size={14} />
          </button>
        </div>
        <label className="image-tile-viewer__toolbar-toggle">
          <input type="checkbox" checked={showScaleBar} onChange={(e) => setShowScaleBar(e.target.checked)} />
          Scale bar
        </label>
        <select value={scaleUnit} onChange={(e) => setScaleUnit(e.target.value)} className="image-tile-viewer__unit-select">
          <option value="um">µm</option>
          <option value="mm">mm</option>
        </select>
        <span className="image-tile-viewer__toolbar-label">{status}</span>
        {renderError ? <span className="text-danger text-sm">{renderError}</span> : null}
      </div>

      <aside className="image-tile-viewer__sidebar" aria-label="Viewer panels">
        <nav className="image-tile-viewer__tabs">
          {SIDEBAR_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`image-tile-viewer__tab${sidebarTab === tab.id ? ' is-active' : ''}`}
              onClick={() => setSidebarTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        {sidebarTab === 'channels' ? (
          <>
            <div className="image-tile-viewer__channel-select">
              <label>
                Histogram channel
                <select value={selectedChannel} onChange={(e) => setSelectedChannel(Number(e.target.value))}>
                  {channelState.map((ch) => (
                    <option key={ch.index} value={ch.index}>{ch.label}</option>
                  ))}
                </select>
              </label>
            </div>
          </>
        ) : null}
        {sidebarContent()}
        {zSlices > 1 ? (
          <div className="image-tile-viewer__slider-block">
            <label>
              <span>Z slice</span>
              <span>{zIndex + 1} / {zSlices}</span>
            </label>
            <input type="range" min={0} max={zSlices - 1} value={zIndex} onChange={(e) => setZIndex(Number(e.target.value))} />
          </div>
        ) : null}
        {timepoints > 1 ? (
          <div className="image-tile-viewer__slider-block">
            <label>
              <span>Time</span>
              <span>{tIndex + 1} / {timepoints}</span>
            </label>
            <input type="range" min={0} max={timepoints - 1} value={tIndex} onChange={(e) => setTIndex(Number(e.target.value))} />
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
        <canvas ref={overlayRef} className="image-tile-viewer__overlay-canvas" />
        {showScaleBar ? <ScaleBar manifest={manifest} zoom={zoom} visible={showScaleBar} unit={scaleUnit} /> : null}
        <div className="image-tile-viewer__status">
          {width}×{height} · {channels} ch · scroll zoom · drag pan
          {inspectionMode ? ' · inspection on' : ''}
        </div>
      </div>
    </div>
  );
}
