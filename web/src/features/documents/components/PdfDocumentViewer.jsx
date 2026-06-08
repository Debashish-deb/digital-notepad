import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Highlighter,
  Loader2,
  Maximize2,
  MessageSquarePlus,
  Minimize2,
  MousePointer2,
  Pencil,
  Printer,
  RotateCcw,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import * as pdfjsLib from 'pdfjs-dist';
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import DocumentExportMenu from './DocumentExportMenu.jsx';
import { triggerBrowserDownload } from '@/services/documentExportClient.js';
import {
  getPageAnnotations,
  loadPdfAnnotations,
  savePdfAnnotations,
  setPageAnnotations,
} from '@/lib/pdfAnnotationStore.js';
import './DocumentExportMenu.css';
import './DocumentViewerToolbar.css';
import './PdfDocumentViewer.css';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const THUMB_WIDTH = 68;
const EDIT_TOOLS = ['select', 'highlight', 'note', 'pen'];

function uid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

async function renderPageToCanvas(page, canvas, targetWidth) {
  const baseViewport = page.getViewport({ scale: 1 });
  const scale = targetWidth / baseViewport.width;
  const viewport = page.getViewport({ scale });
  const context = canvas.getContext('2d');
  canvas.width = Math.floor(viewport.width);
  canvas.height = Math.floor(viewport.height);
  await page.render({ canvasContext: context, viewport }).promise;
  return { width: canvas.width, height: canvas.height, scale };
}

function drawStrokes(ctx, strokes, width, height) {
  if (!ctx || !strokes?.length) return;
  for (const stroke of strokes) {
    const points = stroke.points || [];
    if (points.length < 2) continue;
    ctx.strokeStyle = stroke.color || 'rgba(250, 204, 21, 0.95)';
    ctx.lineWidth = stroke.width || 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.beginPath();
    points.forEach(([nx, ny], index) => {
      const x = nx * width;
      const y = ny * height;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
}

export default function PdfDocumentViewer({
  url,
  title = 'PDF document',
  className = '',
  assetId = null,
  exportLocal = null,
  documentKey = null,
}) {
  const storageKey = documentKey || assetId || url;
  const [pdfDoc, setPdfDoc] = useState(null);
  const [pageCount, setPageCount] = useState(0);
  const [activePage, setActivePage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [fitMode, setFitMode] = useState('width');
  const [thumbsOpen, setThumbsOpen] = useState(true);
  const [editTool, setEditTool] = useState('select');
  const [annotationData, setAnnotationData] = useState(() => loadPdfAnnotations(storageKey));
  const [draftRect, setDraftRect] = useState(null);
  const [draftStroke, setDraftStroke] = useState(null);
  const [editingNoteId, setEditingNoteId] = useState(null);

  const mainCanvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const mainWrapRef = useRef(null);
  const stageRef = useRef(null);
  const thumbRefs = useRef([]);
  const dragRef = useRef(null);

  const pageAnnotations = useMemo(
    () => getPageAnnotations(annotationData, activePage),
    [annotationData, activePage]
  );

  const updatePageAnnotations = useCallback((updater) => {
    setAnnotationData((prev) => {
      const current = getPageAnnotations(prev, activePage);
      const nextPage = updater(current);
      const next = setPageAnnotations(prev, activePage, nextPage);
      savePdfAnnotations(storageKey, next);
      return next;
    });
  }, [activePage, storageKey]);

  useEffect(() => {
    setAnnotationData(loadPdfAnnotations(storageKey));
  }, [storageKey]);

  useEffect(() => {
    if (!url) {
      setPdfDoc(null);
      setPageCount(0);
      setLoading(false);
      setError(null);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setActivePage(1);
    setPdfDoc(null);
    setPageCount(0);

    const task = pdfjsLib.getDocument({ url, withCredentials: true });
    task.promise
      .then((doc) => {
        if (cancelled) return;
        setPdfDoc(doc);
        setPageCount(doc.numPages);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.message || 'Failed to load PDF');
        setLoading(false);
      });

    return () => {
      cancelled = true;
      task.destroy().catch(() => {});
    };
  }, [url]);

  const resolveTargetWidth = useCallback(() => {
    const wrap = mainWrapRef.current;
    if (!wrap) return 640;
    const base = Math.max(320, wrap.clientWidth - 16);
    if (fitMode === 'page') {
      return base * zoom;
    }
    return base * zoom;
  }, [fitMode, zoom]);

  const renderMainPage = useCallback(async () => {
    if (!pdfDoc || !mainCanvasRef.current) return null;
    const page = await pdfDoc.getPage(activePage);
    const targetWidth = resolveTargetWidth();
    const size = await renderPageToCanvas(page, mainCanvasRef.current, targetWidth);

    const overlay = overlayCanvasRef.current;
    if (overlay && size) {
      overlay.width = size.width;
      overlay.height = size.height;
      const ctx = overlay.getContext('2d');
      ctx.clearRect(0, 0, size.width, size.height);
      drawStrokes(ctx, pageAnnotations.strokes, size.width, size.height);
      if (draftStroke?.points?.length) {
        drawStrokes(ctx, [draftStroke], size.width, size.height);
      }
    }
    return size;
  }, [pdfDoc, activePage, resolveTargetWidth, pageAnnotations.strokes, draftStroke]);

  useEffect(() => {
    renderMainPage().catch(() => {});
  }, [renderMainPage]);

  useEffect(() => {
    if (!pdfDoc || !pageCount) return undefined;
    let cancelled = false;
    (async () => {
      for (let pageNum = 1; pageNum <= pageCount; pageNum += 1) {
        if (cancelled) return;
        const canvas = thumbRefs.current[pageNum - 1];
        if (!canvas) continue;
        const page = await pdfDoc.getPage(pageNum);
        await renderPageToCanvas(page, canvas, THUMB_WIDTH);
      }
    })().catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [pdfDoc, pageCount]);

  useEffect(() => {
    const onResize = () => {
      renderMainPage().catch(() => {});
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [renderMainPage]);

  useEffect(() => {
    setEditingNoteId(null);
    setDraftRect(null);
    setDraftStroke(null);
  }, [activePage, editTool]);

  const goToPage = useCallback((pageNum) => {
    if (!pageCount) return;
    setActivePage(Math.min(pageCount, Math.max(1, pageNum)));
  }, [pageCount]);

  const pointerToNormalized = useCallback((event) => {
    const canvas = mainCanvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    if (x < 0 || y < 0 || x > 1 || y > 1) return null;
    return [x, y];
  }, []);

  const handlePointerDown = (event) => {
    if (editTool === 'select') return;
    const point = pointerToNormalized(event);
    if (!point) return;

    if (editTool === 'highlight') {
      dragRef.current = { kind: 'highlight', start: point };
      setDraftRect({ x: point[0], y: point[1], w: 0, h: 0 });
      return;
    }

    if (editTool === 'pen') {
      dragRef.current = { kind: 'pen', points: [point] };
      setDraftStroke({ id: uid(), points: [point], color: 'rgba(250, 204, 21, 0.95)', width: 2.5 });
      return;
    }

    if (editTool === 'note') {
      const note = {
        id: uid(),
        x: point[0],
        y: point[1],
        text: '',
        createdAt: new Date().toISOString(),
      };
      updatePageAnnotations((page) => ({
        ...page,
        notes: [...page.notes, note],
      }));
      setEditingNoteId(note.id);
    }
  };

  const handlePointerMove = (event) => {
    const drag = dragRef.current;
    if (!drag) return;
    const point = pointerToNormalized(event);
    if (!point) return;

    if (drag.kind === 'highlight') {
      const [sx, sy] = drag.start;
      const x = Math.min(sx, point[0]);
      const y = Math.min(sy, point[1]);
      const w = Math.abs(point[0] - sx);
      const h = Math.abs(point[1] - sy);
      setDraftRect({ x, y, w, h });
      return;
    }

    if (drag.kind === 'pen') {
      drag.points.push(point);
      setDraftStroke((prev) => ({
        ...prev,
        points: [...drag.points],
      }));
    }
  };

  const handlePointerUp = () => {
    const drag = dragRef.current;
    dragRef.current = null;

    if (drag?.kind === 'highlight' && draftRect && draftRect.w > 0.01 && draftRect.h > 0.005) {
      updatePageAnnotations((page) => ({
        ...page,
        highlights: [
          ...page.highlights,
          {
            id: uid(),
            ...draftRect,
            color: 'rgba(250, 204, 21, 0.38)',
          },
        ],
      }));
    }

    if (drag?.kind === 'pen' && draftStroke?.points?.length > 1) {
      updatePageAnnotations((page) => ({
        ...page,
        strokes: [...page.strokes, { ...draftStroke }],
      }));
    }

    setDraftRect(null);
    setDraftStroke(null);
  };

  const handleNoteChange = (noteId, text) => {
    updatePageAnnotations((page) => ({
      ...page,
      notes: page.notes.map((note) => (note.id === noteId ? { ...note, text } : note)),
    }));
  };

  const handleRemoveNote = (noteId) => {
    updatePageAnnotations((page) => ({
      ...page,
      notes: page.notes.filter((note) => note.id !== noteId),
    }));
    if (editingNoteId === noteId) setEditingNoteId(null);
  };

  const undoLastEdit = () => {
    updatePageAnnotations((page) => {
      if (page.strokes.length) {
        return { ...page, strokes: page.strokes.slice(0, -1) };
      }
      if (page.notes.length) {
        return { ...page, notes: page.notes.slice(0, -1) };
      }
      if (page.highlights.length) {
        return { ...page, highlights: page.highlights.slice(0, -1) };
      }
      return page;
    });
  };

  const downloadOriginal = async () => {
    try {
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) throw new Error('Download failed');
      const blob = await response.blob();
      const filename = (title || 'document').replace(/[^\w.-]+/g, '_');
      triggerBrowserDownload(blob, filename.endsWith('.pdf') ? filename : `${filename}.pdf`);
    } catch {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  const exportCurrentPagePng = () => {
    const canvas = mainCanvasRef.current;
    const overlay = overlayCanvasRef.current;
    if (!canvas) return;
    const merged = document.createElement('canvas');
    merged.width = canvas.width;
    merged.height = canvas.height;
    const ctx = merged.getContext('2d');
    ctx.drawImage(canvas, 0, 0);
    if (overlay) ctx.drawImage(overlay, 0, 0);

    for (const highlight of pageAnnotations.highlights) {
      ctx.fillStyle = highlight.color || 'rgba(250, 204, 21, 0.38)';
      ctx.fillRect(
        highlight.x * merged.width,
        highlight.y * merged.height,
        highlight.w * merged.width,
        highlight.h * merged.height
      );
    }

    merged.toBlob((blob) => {
      if (!blob) return;
      const base = (title || 'page').replace(/\.[^.]+$/, '').replace(/[^\w.-]+/g, '_');
      triggerBrowserDownload(blob, `${base}-page-${activePage}.png`);
    }, 'image/png');
  };

  const exportAnnotationsJson = () => {
    const payload = {
      title,
      url,
      asset_id: assetId,
      exported_at: new Date().toISOString(),
      annotations: annotationData,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' });
    const base = (title || 'document').replace(/\.[^.]+$/, '').replace(/[^\w.-]+/g, '_');
    triggerBrowserDownload(blob, `${base}-annotations.json`);
  };

  const handlePrint = () => {
    const canvas = mainCanvasRef.current;
    if (!canvas) {
      window.open(url, '_blank', 'noopener,noreferrer');
      return;
    }
    const win = window.open('', '_blank', 'noopener,noreferrer');
    if (!win) return;
    win.document.write(`<html><head><title>${title}</title></head><body style="margin:0"><img src="${canvas.toDataURL('image/png')}" style="width:100%" /></body></html>`);
    win.document.close();
    win.focus();
    win.print();
  };

  const hasEdits = useMemo(() => {
    return Object.values(annotationData.pages || {}).some((page) => {
      return (page?.highlights?.length || 0) + (page?.notes?.length || 0) + (page?.strokes?.length || 0) > 0;
    });
  }, [annotationData]);

  if (!url) return null;

  if (loading) {
    return (
      <div className={`pdf-doc-viewer pdf-doc-viewer--premium pdf-doc-viewer--loading ${className}`.trim()}>
        <Loader2 size={20} className="spin-inline" aria-hidden />
        <span>Loading PDF…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`pdf-doc-viewer pdf-doc-viewer--premium pdf-doc-viewer--error ${className}`.trim()}>
        <p className="text-footnote muted">{error}</p>
        <a href={url} target="_blank" rel="noreferrer" className="btn-link">
          Open PDF in new tab
        </a>
      </div>
    );
  }

  return (
    <div className={`pdf-doc-viewer pdf-doc-viewer--premium ${className}`.trim()} aria-label={title}>
      <header className="pdf-doc-viewer__chrome">
        <div className="pdf-doc-viewer__chrome-group">
          <button type="button" className="pdf-doc-viewer__btn" onClick={() => goToPage(activePage - 1)} disabled={activePage <= 1} title="Previous page" aria-label="Previous page">
            <ChevronLeft size={15} aria-hidden />
          </button>
          <span className="pdf-doc-viewer__page-indicator">
            {activePage} <span className="pdf-doc-viewer__page-of">/ {pageCount}</span>
          </span>
          <button type="button" className="pdf-doc-viewer__btn" onClick={() => goToPage(activePage + 1)} disabled={activePage >= pageCount} title="Next page" aria-label="Next page">
            <ChevronRight size={15} aria-hidden />
          </button>
        </div>

        <div className="pdf-doc-viewer__chrome-group">
          <button type="button" className="pdf-doc-viewer__btn" onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.1).toFixed(2)))} title="Zoom out" aria-label="Zoom out">
            <ZoomOut size={14} aria-hidden />
          </button>
          <span className="pdf-doc-viewer__zoom-label">{Math.round(zoom * 100)}%</span>
          <button type="button" className="pdf-doc-viewer__btn" onClick={() => setZoom((z) => Math.min(2.5, +(z + 0.1).toFixed(2)))} title="Zoom in" aria-label="Zoom in">
            <ZoomIn size={14} aria-hidden />
          </button>
          <button
            type="button"
            className={`pdf-doc-viewer__btn${fitMode === 'width' ? ' is-active' : ''}`}
            onClick={() => { setFitMode('width'); setZoom(1); }}
            title="Fit width"
          >
            <Maximize2 size={14} aria-hidden />
          </button>
          <button
            type="button"
            className={`pdf-doc-viewer__btn${fitMode === 'page' ? ' is-active' : ''}`}
            onClick={() => { setFitMode('page'); setZoom(1); }}
            title="Fit page"
          >
            <Minimize2 size={14} aria-hidden />
          </button>
        </div>

        <div className="pdf-doc-viewer__chrome-group pdf-doc-viewer__chrome-group--edit" role="toolbar" aria-label="PDF edit tools">
          {EDIT_TOOLS.map((tool) => {
            const icons = {
              select: MousePointer2,
              highlight: Highlighter,
              note: MessageSquarePlus,
              pen: Pencil,
            };
            const labels = {
              select: 'Select',
              highlight: 'Highlight',
              note: 'Note',
              pen: 'Draw',
            };
            const Icon = icons[tool];
            return (
              <button
                key={tool}
                type="button"
                className={`pdf-doc-viewer__btn pdf-doc-viewer__btn--tool${editTool === tool ? ' is-active' : ''}`}
                onClick={() => setEditTool(tool)}
                title={labels[tool]}
                aria-label={labels[tool]}
                aria-pressed={editTool === tool}
              >
                <Icon size={14} aria-hidden />
              </button>
            );
          })}
          <button type="button" className="pdf-doc-viewer__btn" onClick={undoLastEdit} disabled={!hasEdits} title="Undo last mark" aria-label="Undo last mark">
            <RotateCcw size={14} aria-hidden />
          </button>
        </div>

        <div className="pdf-doc-viewer__chrome-group pdf-doc-viewer__chrome-group--export">
          {(assetId || exportLocal) ? (
            <DocumentExportMenu
              assetId={assetId || undefined}
              local={exportLocal || undefined}
              compact
              toolbar
            />
          ) : null}
          <button type="button" className="pdf-doc-viewer__btn pdf-doc-viewer__btn--labeled" onClick={downloadOriginal} title="Download PDF">
            <Download size={14} aria-hidden />
            <span>PDF</span>
          </button>
          <button type="button" className="pdf-doc-viewer__btn" onClick={exportCurrentPagePng} title="Export page as PNG" aria-label="Export page as PNG">
            <Download size={14} aria-hidden />
          </button>
          <button type="button" className="pdf-doc-viewer__btn" onClick={exportAnnotationsJson} disabled={!hasEdits} title="Export annotations" aria-label="Export annotations">
            <span className="pdf-doc-viewer__export-json">JSON</span>
          </button>
          <button type="button" className="pdf-doc-viewer__btn" onClick={handlePrint} title="Print page" aria-label="Print page">
            <Printer size={14} aria-hidden />
          </button>
          <button
            type="button"
            className={`pdf-doc-viewer__btn${thumbsOpen ? ' is-active' : ''}`}
            onClick={() => setThumbsOpen((v) => !v)}
            title={thumbsOpen ? 'Hide thumbnails' : 'Show thumbnails'}
            aria-label={thumbsOpen ? 'Hide thumbnails' : 'Show thumbnails'}
          >
            <ChevronLeft size={14} aria-hidden style={{ transform: thumbsOpen ? 'none' : 'rotate(180deg)' }} />
          </button>
        </div>
      </header>

      <div className="pdf-doc-viewer__body">
        {thumbsOpen ? (
          <nav className="pdf-doc-viewer__thumbs" aria-label="Page thumbnails">
            {Array.from({ length: pageCount }, (_, index) => {
              const pageNum = index + 1;
              return (
                <button
                  key={pageNum}
                  type="button"
                  className={`pdf-doc-viewer__thumb${activePage === pageNum ? ' is-active' : ''}`}
                  onClick={() => goToPage(pageNum)}
                  aria-label={`Page ${pageNum}`}
                  aria-current={activePage === pageNum ? 'page' : undefined}
                >
                  <canvas
                    ref={(node) => {
                      thumbRefs.current[index] = node;
                    }}
                    aria-hidden
                  />
                  <span className="pdf-doc-viewer__thumb-label">{pageNum}</span>
                </button>
              );
            })}
          </nav>
        ) : null}

        <div className="pdf-doc-viewer__page" ref={mainWrapRef}>
          <div
            className={`pdf-doc-viewer__stage${editTool !== 'select' ? ' pdf-doc-viewer__stage--editing' : ''}`}
            ref={stageRef}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
          >
            <canvas ref={mainCanvasRef} className="pdf-doc-viewer__canvas" />
            <canvas ref={overlayCanvasRef} className="pdf-doc-viewer__overlay" aria-hidden />

            {pageAnnotations.highlights.map((highlight) => (
              <div
                key={highlight.id}
                className="pdf-doc-viewer__highlight"
                style={{
                  left: `${highlight.x * 100}%`,
                  top: `${highlight.y * 100}%`,
                  width: `${highlight.w * 100}%`,
                  height: `${highlight.h * 100}%`,
                  background: highlight.color,
                }}
              />
            ))}

            {draftRect ? (
              <div
                className="pdf-doc-viewer__highlight pdf-doc-viewer__highlight--draft"
                style={{
                  left: `${draftRect.x * 100}%`,
                  top: `${draftRect.y * 100}%`,
                  width: `${draftRect.w * 100}%`,
                  height: `${draftRect.h * 100}%`,
                }}
              />
            ) : null}

            {pageAnnotations.notes.map((note) => (
              <div
                key={note.id}
                className={`pdf-doc-viewer__note${editingNoteId === note.id ? ' is-editing' : ''}`}
                style={{ left: `${note.x * 100}%`, top: `${note.y * 100}%` }}
              >
                <button
                  type="button"
                  className="pdf-doc-viewer__note-pin"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingNoteId(note.id);
                    setEditTool('note');
                  }}
                  title="Edit note"
                >
                  <MessageSquarePlus size={12} aria-hidden />
                </button>
                {editingNoteId === note.id ? (
                  <div className="pdf-doc-viewer__note-editor" onPointerDown={(e) => e.stopPropagation()}>
                    <textarea
                      value={note.text}
                      onChange={(e) => handleNoteChange(note.id, e.target.value)}
                      placeholder="Add a note…"
                      rows={3}
                      autoFocus
                    />
                    <div className="pdf-doc-viewer__note-actions">
                      <button type="button" className="btn-link" onClick={() => setEditingNoteId(null)}>Done</button>
                      <button type="button" className="btn-link pdf-doc-viewer__note-delete" onClick={() => handleRemoveNote(note.id)}>Delete</button>
                    </div>
                  </div>
                ) : note.text ? (
                  <p className="pdf-doc-viewer__note-preview">{note.text}</p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
