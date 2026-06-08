import { useCallback, useEffect, useMemo, useState } from 'react';

function loadWidths(storageKey, columns) {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return columns.map((c) => c.defaultWidth);
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length !== columns.length) {
      return columns.map((c) => c.defaultWidth);
    }
    return parsed.map((w, i) => {
      const min = columns[i].minWidth;
      const max = columns[i].maxWidth ?? 640;
      const n = Number(w);
      if (!Number.isFinite(n)) return columns[i].defaultWidth;
      return Math.min(max, Math.max(min, Math.round(n)));
    });
  } catch {
    return columns.map((c) => c.defaultWidth);
  }
}

/**
 * Drag-to-resize column widths for CSS grid tables. Persists to localStorage.
 */
export function useResizableGridColumns(storageKey, columns) {
  const [widths, setWidths] = useState(() => loadWidths(storageKey, columns));

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(widths));
    } catch {
      /* ignore quota errors */
    }
  }, [storageKey, widths]);

  const gridTemplateColumns = useMemo(
    () => widths.map((w) => `${w}px`).join(' '),
    [widths],
  );

  const startResize = useCallback((columnIndex, clientX) => {
    const startX = clientX;
    const startWidth = widths[columnIndex];
    const minW = columns[columnIndex].minWidth;
    const maxW = columns[columnIndex].maxWidth ?? 720;

    const onMove = (e) => {
      const next = Math.min(maxW, Math.max(minW, startWidth + (e.clientX - startX)));
      setWidths((prev) => {
        if (prev[columnIndex] === next) return prev;
        const copy = [...prev];
        copy[columnIndex] = next;
        return copy;
      });
    };

    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.classList.remove('sfe-col-resizing');
    };

    document.body.classList.add('sfe-col-resizing');
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [columns, widths]);

  const resetWidths = useCallback(() => {
    setWidths(columns.map((c) => c.defaultWidth));
  }, [columns]);

  return { widths, gridTemplateColumns, startResize, resetWidths };
}
