import { useCallback, useEffect, useRef } from 'react';
import { fetchImageHistogram } from '@/services/imageAssetsClient.js';

export default function HistogramPanel({
  assetId,
  channelIndex,
  channelLabel,
  min,
  max,
  onWindowChange,
  zIndex = 0,
  enabled = true,
}) {
  const canvasRef = useRef(null);
  const dragRef = useRef(null);

  const drawHistogram = useCallback((counts, lo, hi) => {
    const canvas = canvasRef.current;
    if (!canvas || !counts?.length) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const maxCount = Math.max(...counts, 1);
    const barW = w / counts.length;
    ctx.fillStyle = '#334155';
    counts.forEach((c, i) => {
      const barH = (c / maxCount) * (h - 20);
      ctx.fillRect(i * barW, h - barH, barW, barH);
    });
    const xMin = (lo / 255) * w;
    const xMax = (hi / 255) * w;
    ctx.strokeStyle = '#00d4ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(xMin, 0);
    ctx.lineTo(xMin, h);
    ctx.stroke();
    ctx.strokeStyle = '#ff4fd8';
    ctx.beginPath();
    ctx.moveTo(xMax, 0);
    ctx.lineTo(xMax, h);
    ctx.stroke();
  }, []);

  useEffect(() => {
    if (!enabled || !assetId) return undefined;
    let alive = true;
    fetchImageHistogram(assetId, { channel: channelIndex, z: zIndex })
      .then((data) => {
        if (alive) drawHistogram(data.counts, min, max);
      })
      .catch(() => {});
    return () => { alive = false; };
  }, [assetId, channelIndex, zIndex, enabled, drawHistogram, min, max]);

  useEffect(() => {
    drawHistogram(null, min, max);
  }, [min, max, drawHistogram]);

  const handlePointer = (e, kind) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const val = Math.round((x / rect.width) * 255);
    if (kind === 'min') onWindowChange({ min: Math.min(val, max - 1) });
    else onWindowChange({ max: Math.max(val, min + 1) });
  };

  return (
    <div className="image-panel image-panel--histogram">
      <h4>{channelLabel || `Channel ${channelIndex + 1}`}</h4>
      <canvas
        ref={canvasRef}
        width={240}
        height={80}
        className="image-panel__histogram-canvas"
        onPointerDown={(e) => {
          const canvas = canvasRef.current;
          if (!canvas) return;
          const rect = canvas.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const val = Math.round((x / rect.width) * 255);
          dragRef.current = Math.abs(val - min) < Math.abs(val - max) ? 'min' : 'max';
        }}
        onPointerMove={(e) => {
          if (dragRef.current) handlePointer(e, dragRef.current);
        }}
        onPointerUp={() => { dragRef.current = null; }}
        onPointerLeave={() => { dragRef.current = null; }}
      />
      <div className="image-panel__histogram-labels">
        <span>Min: {min}</span>
        <span>Max: {max}</span>
      </div>
    </div>
  );
}
