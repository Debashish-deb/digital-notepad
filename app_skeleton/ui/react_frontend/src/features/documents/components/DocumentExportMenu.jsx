import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import {
  buildLocalExportFormats,
  downloadAssetExport,
  downloadLocalExport,
  fetchExportFormats,
  triggerBrowserDownload,
} from '@/services/documentExportClient.js';

export default function DocumentExportMenu({
  assetId,
  local,
  compact = false,
  toolbar = false,
  className = '',
}) {
  const [formats, setFormats] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const rootRef = useRef(null);

  useEffect(() => {
    if (assetId) {
      fetchExportFormats(assetId)
        .then((data) => setFormats(data?.formats || []))
        .catch(() => setFormats([]));
      return undefined;
    }
    if (local) {
      setFormats(buildLocalExportFormats(local).formats);
      return undefined;
    }
    setFormats([]);
    return undefined;
  }, [assetId, local]);

  useEffect(() => {
    if (!open) return undefined;
    const onDocClick = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  const handleExport = useCallback(async (formatId) => {
    setBusyId(formatId);
    setLoading(true);
    try {
      if (assetId) {
        const { blob, filename } = await downloadAssetExport(assetId, formatId);
        triggerBrowserDownload(blob, filename);
      } else if (local) {
        await downloadLocalExport(local, formatId);
      }
      setOpen(false);
    } catch (err) {
      console.error('[DocumentExportMenu]', err);
    } finally {
      setLoading(false);
      setBusyId(null);
    }
  }, [assetId, local]);

  const disabled = useMemo(() => !formats.length, [formats.length]);

  return (
    <div
      className={[
        'doc-export-menu',
        compact ? 'doc-export-menu--compact' : '',
        toolbar ? 'doc-export-menu--toolbar' : '',
        className,
      ].filter(Boolean).join(' ')}
      ref={rootRef}
    >
      <button
        type="button"
        className="doc-export-menu__trigger"
        onClick={() => setOpen((v) => !v)}
        disabled={disabled}
        title="Export document"
        aria-label="Export document"
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {loading ? <Loader2 size={compact ? 12 : 14} className="spin-inline" aria-hidden /> : <Download size={compact ? 12 : 14} aria-hidden />}
        {!compact ? <span>Export</span> : null}
      </button>
      {open ? (
        <div className="doc-export-menu__panel" role="menu">
          {formats.map((fmt) => (
            <button
              key={fmt.id}
              type="button"
              role="menuitem"
              className="doc-export-menu__item"
              disabled={busyId === fmt.id}
              onClick={() => handleExport(fmt.id)}
            >
              {busyId === fmt.id ? <Loader2 size={12} className="spin-inline" aria-hidden /> : null}
              <span>{fmt.label}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
