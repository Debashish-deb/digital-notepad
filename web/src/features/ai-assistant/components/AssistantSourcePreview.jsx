import { lazy, Suspense, useEffect, useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';
import { fetchDocumentPreview } from '@/services/documentLibraryClient.js';
import { getApiUrl } from '@/services/client.js';

const PdfDocumentViewer = lazy(() => import('@/features/documents/components/PdfDocumentViewer.jsx'));

function resolveAssetId(hit) {
  const meta = hit?.metadata || {};
  return meta.asset_id || hit?.asset_id || hit?.source_uuid || null;
}

function isPdfHit(hit) {
  const meta = hit?.metadata || {};
  const path = String(meta.logical_path || meta.path || hit?.logical_path || '').toLowerCase();
  const ext = String(meta.extension || hit?.extension || '').toLowerCase();
  const type = String(meta.file_type || hit?.file_type || '').toLowerCase();
  return type === 'pdf' || ext === '.pdf' || ext === 'pdf' || path.endsWith('.pdf');
}

export default function AssistantSourcePreview({ hit }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const assetId = resolveAssetId(hit);
  const title = hit?.title || 'Source preview';
  const snippet = hit?.text_preview || hit?.snippet || hit?.highlights?.[0] || '';

  useEffect(() => {
    if (!assetId || !isPdfHit(hit)) {
      setPreview(null);
      setLoading(false);
      setError('');
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError('');
    fetchDocumentPreview(assetId)
      .then((data) => {
        if (cancelled) return;
        setPreview(data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.message || 'Preview unavailable');
        setPreview(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [assetId, hit]);

  if (!hit) {
    return (
      <div className="assistant-source-preview assistant-source-preview--empty">
        <FileText size={28} aria-hidden />
        <p>Select a source to preview evidence.</p>
      </div>
    );
  }

  const previewUrl = preview?.preview_url
    ? (preview.preview_url.startsWith('http')
      ? preview.preview_url
      : `${getApiUrl()}${preview.preview_url}`)
    : null;

  if (loading) {
    return (
      <div className="assistant-source-preview assistant-source-preview--loading">
        <Loader2 size={22} className="spin" aria-hidden />
        <p>Loading preview…</p>
      </div>
    );
  }

  if (previewUrl && isPdfHit(hit)) {
    return (
      <div className="assistant-source-preview assistant-source-preview--pdf">
        <Suspense fallback={<div className="assistant-source-preview--loading">Loading PDF…</div>}>
          <PdfDocumentViewer
            url={previewUrl}
            title={title}
            assetId={assetId}
            compact
          />
        </Suspense>
      </div>
    );
  }

  return (
    <div className="assistant-source-preview assistant-source-preview--text">
      <h4>{title}</h4>
      {error ? <p className="assistant-source-preview__error">{error}</p> : null}
      {snippet ? <p className="assistant-source-preview__snippet">{snippet}</p> : (
        <p className="assistant-source-preview__hint">Open in the library for full document view.</p>
      )}
    </div>
  );
}
