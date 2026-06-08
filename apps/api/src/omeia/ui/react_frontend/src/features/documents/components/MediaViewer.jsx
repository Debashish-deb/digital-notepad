import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Expand,
  Loader2,
  Maximize2,
  Minimize2,
  Minus,
  Plus,
  RotateCw,
  Shrink,
  X,
} from 'lucide-react';

const MIN_SCALE = 0.15;
const MAX_SCALE = 12;
const ZOOM_STEP = 0.25;

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

/**
 * Premium image and video viewer with zoom, pan, rotate, fullscreen, and gallery navigation.
 */
export default function MediaViewer({
  url,
  title,
  kind = 'image',
  gallery = [],
  currentPath,
  onNavigate,
  labels = {},
}) {
  const stageRef = useRef(null);
  const videoRef = useRef(null);
  const dragRef = useRef({ active: false, x: 0, y: 0, panX: 0, panY: 0 });

  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [rotation, setRotation] = useState(0);
  const [fitMode, setFitMode] = useState('contain');
  const [fullscreen, setFullscreen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [naturalSize, setNaturalSize] = useState({ w: 0, h: 0 });

  const galleryIndex = useMemo(
    () => gallery.findIndex((item) => item.path === currentPath),
    [gallery, currentPath]
  );
  const galleryCount = gallery.length;
  const hasGallery = galleryCount > 1 && typeof onNavigate === 'function';

  const resetView = useCallback(() => {
    setScale(1);
    setPan({ x: 0, y: 0 });
    setRotation(0);
    setFitMode('contain');
  }, []);

  useEffect(() => {
    resetView();
    setLoading(true);
    setError(null);
  }, [url, kind, resetView]);

  const zoomBy = useCallback((delta) => {
    setFitMode('custom');
    setScale((s) => clamp(s + delta, MIN_SCALE, MAX_SCALE));
  }, []);

  const fitToStage = useCallback(() => {
    setFitMode('contain');
    setScale(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const actualSize = useCallback(() => {
    setFitMode('actual');
    setScale(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const toggleFullscreen = useCallback(async () => {
    const el = stageRef.current;
    if (!el) return;
    if (!document.fullscreenElement) {
      await el.requestFullscreen?.();
      setFullscreen(true);
    } else {
      await document.exitFullscreen?.();
      setFullscreen(false);
    }
  }, []);

  useEffect(() => {
    const onFsChange = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  const goGallery = useCallback(
    (direction) => {
      if (!hasGallery || galleryIndex < 0) return;
      const next = (galleryIndex + direction + galleryCount) % galleryCount;
      onNavigate(gallery[next].path);
    },
    [gallery, galleryCount, galleryIndex, hasGallery, onNavigate]
  );

  useEffect(() => {
    const onKey = (e) => {
      if (e.target?.closest?.('input, textarea, [contenteditable="true"]')) return;
      if (e.key === 'ArrowLeft') goGallery(-1);
      if (e.key === 'ArrowRight') goGallery(1);
      if (e.key === '+' || e.key === '=') zoomBy(ZOOM_STEP);
      if (e.key === '-') zoomBy(-ZOOM_STEP);
      if (e.key === '0') fitToStage();
      if (e.key === 'f' || e.key === 'F') toggleFullscreen();
      if (e.key === 'Escape' && fullscreen) toggleFullscreen();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [fitToStage, fullscreen, goGallery, toggleFullscreen, zoomBy]);

  const onWheel = useCallback(
    (e) => {
      if (kind !== 'image') return;
      e.preventDefault();
      const delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
      setFitMode('custom');
      setScale((s) => clamp(s + delta, MIN_SCALE, MAX_SCALE));
    },
    [kind]
  );

  const onPointerDown = useCallback(
    (e) => {
      if (kind !== 'image') return;
      dragRef.current = {
        active: true,
        x: e.clientX,
        y: e.clientY,
        panX: pan.x,
        panY: pan.y,
      };
      e.currentTarget.setPointerCapture?.(e.pointerId);
    },
    [kind, pan.x, pan.y]
  );

  const onPointerMove = useCallback((e) => {
    if (!dragRef.current.active || kind !== 'image') return;
    const dx = e.clientX - dragRef.current.x;
    const dy = e.clientY - dragRef.current.y;
    setPan({ x: dragRef.current.panX + dx, y: dragRef.current.panY + dy });
  }, [kind]);

  const onPointerUp = useCallback((e) => {
    dragRef.current.active = false;
    e.currentTarget.releasePointerCapture?.(e.pointerId);
  }, []);

  const onImageLoad = useCallback((e) => {
    setLoading(false);
    setNaturalSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight });
  }, []);

  const onImageError = useCallback(() => {
    setLoading(false);
    setError(labels.failed || 'Could not load image.');
  }, [labels.failed]);

  const onVideoReady = useCallback(() => {
    setLoading(false);
    setError(null);
  }, []);

  const onVideoError = useCallback(() => {
    setLoading(false);
    setError(labels.videoFailed || 'Could not load video.');
  }, [labels.videoFailed]);

  const imageStyle =
    fitMode === 'actual' && naturalSize.w
      ? { width: naturalSize.w, height: naturalSize.h, maxWidth: 'none', maxHeight: 'none' }
      : { maxWidth: '100%', maxHeight: '100%', width: 'auto', height: 'auto' };

  const transform =
    kind === 'image'
      ? `translate(${pan.x}px, ${pan.y}px) rotate(${rotation}deg) scale(${scale})`
      : undefined;

  return (
    <div className={`media-viewer${fullscreen ? ' media-viewer--fullscreen' : ''}`}>
      <div className="media-viewer-toolbar" role="toolbar" aria-label={labels.toolbar || 'Media controls'}>
        {kind === 'image' ? (
          <>
            <button type="button" className="media-viewer-btn" onClick={() => zoomBy(-ZOOM_STEP)} title={labels.zoomOut || 'Zoom out'}>
              <Minus size={14} aria-hidden />
            </button>
            <span className="media-viewer-zoom-label">{Math.round(scale * 100)}%</span>
            <button type="button" className="media-viewer-btn" onClick={() => zoomBy(ZOOM_STEP)} title={labels.zoomIn || 'Zoom in'}>
              <Plus size={14} aria-hidden />
            </button>
            <button type="button" className="media-viewer-btn" onClick={fitToStage} title={labels.fit || 'Fit to view'}>
              <Shrink size={14} aria-hidden />
            </button>
            <button type="button" className="media-viewer-btn" onClick={actualSize} title={labels.actualSize || 'Actual size'}>
              <Expand size={14} aria-hidden />
            </button>
            <button
              type="button"
              className="media-viewer-btn"
              onClick={() => setRotation((r) => (r + 90) % 360)}
              title={labels.rotate || 'Rotate'}
            >
              <RotateCw size={14} aria-hidden />
            </button>
          </>
        ) : null}
        <button type="button" className="media-viewer-btn" onClick={toggleFullscreen} title={labels.fullscreen || 'Fullscreen'}>
          {fullscreen ? <Minimize2 size={14} aria-hidden /> : <Maximize2 size={14} aria-hidden />}
        </button>
        {url ? (
          <a
            className="media-viewer-btn media-viewer-btn--link"
            href={url}
            download={title}
            target="_blank"
            rel="noreferrer"
            title={labels.download || 'Download'}
          >
            <Download size={14} aria-hidden />
          </a>
        ) : null}
        {hasGallery ? (
          <span className="media-viewer-counter" aria-live="polite">
            {galleryIndex + 1} / {galleryCount}
          </span>
        ) : null}
      </div>

      <div
        ref={stageRef}
        className={`media-viewer-stage media-viewer-stage--${kind}`}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onDoubleClick={kind === 'image' ? resetView : undefined}
      >
        {hasGallery ? (
          <>
            <button
              type="button"
              className="media-viewer-nav media-viewer-nav--prev"
              onClick={() => goGallery(-1)}
              aria-label={labels.previous || 'Previous'}
            >
              <ChevronLeft size={22} aria-hidden />
            </button>
            <button
              type="button"
              className="media-viewer-nav media-viewer-nav--next"
              onClick={() => goGallery(1)}
              aria-label={labels.next || 'Next'}
            >
              <ChevronRight size={22} aria-hidden />
            </button>
          </>
        ) : null}

        {loading && !error ? (
          <div className="media-viewer-loading">
            <Loader2 size={24} className="spin" aria-hidden />
            <span>{kind === 'video' ? labels.videoLoading || 'Loading video…' : labels.loading || 'Loading…'}</span>
          </div>
        ) : null}

        {error ? (
          <p className="media-viewer-error">{error}</p>
        ) : kind === 'video' ? (
          <video
            ref={videoRef}
            key={url}
            className="media-viewer-video"
            src={url}
            controls
            playsInline
            preload="metadata"
            onLoadedData={onVideoReady}
            onError={onVideoError}
          >
            <track kind="captions" />
          </video>
        ) : (
          <div className="media-viewer-canvas" style={{ transform }}>
            <img
              key={url}
              src={url}
              alt={title || ''}
              className="media-viewer-image"
              style={imageStyle}
              draggable={false}
              onLoad={onImageLoad}
              onError={onImageError}
            />
          </div>
        )}
      </div>

      {fullscreen ? (
        <button
          type="button"
          className="media-viewer-close-fs"
          onClick={toggleFullscreen}
          aria-label={labels.close || 'Close fullscreen'}
        >
          <X size={16} aria-hidden />
        </button>
      ) : null}
    </div>
  );
}
