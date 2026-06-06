import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Image as ImageIcon, Loader2 } from 'lucide-react';
import {
  fetchImageManifest,
  fetchImageMetadata,
  loadThumbnailBlobUrl,
} from '../api/imageAssetsClient.js';

export default function ImageViewerPlaceholderScreen({ assetId, onClose }) {
  const [manifest, setManifest] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [thumbUrl, setThumbUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!assetId) return;
    setLoading(true);
    setError(null);
    try {
      const [m, md] = await Promise.all([
        fetchImageManifest(assetId),
        fetchImageMetadata(assetId),
      ]);
      setManifest(m);
      setMetadata(md);
    } catch (err) {
      setError(String(err.message || err));
      setManifest(null);
      setMetadata(null);
    } finally {
      setLoading(false);
    }
  }, [assetId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!assetId) return undefined;
    let alive = true;
    let objectUrl = null;
    loadThumbnailBlobUrl(assetId)
      .then((url) => {
        if (alive) {
          objectUrl = url;
          setThumbUrl(url);
        } else URL.revokeObjectURL(url);
      })
      .catch(() => { if (alive) setThumbUrl(null); });
    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [assetId]);

  if (!assetId) {
    return (
      <div className="panel">
        <p className="text-footnote muted">No image asset selected.</p>
      </div>
    );
  }

  const imgMeta = metadata?.image_metadata || manifest || {};

  return (
    <div className="panel image-viewer-placeholder">
      <div className="image-viewer-placeholder__header">
        <button type="button" className="btn btn-sm btn-ghost" onClick={onClose}>
          <ArrowLeft size={16} aria-hidden /> Back
        </button>
        <h3 className="panel-title" style={{ margin: 0 }}>
          <ImageIcon size={18} style={{ verticalAlign: 'middle', marginRight: '0.35rem' }} />
          Image Viewer (preview)
        </h3>
      </div>

      {loading ? (
        <p className="text-footnote muted"><Loader2 className="spin-inline" size={16} /> Loading manifest…</p>
      ) : null}
      {error ? <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p> : null}

      {!loading && !error ? (
        <div className="grid-2col" style={{ gap: '1.5rem', alignItems: 'start' }}>
          <div>
            {thumbUrl ? (
              <img
                src={thumbUrl}
                alt="Thumbnail preview"
                className="sfe-preview-image"
                style={{ maxWidth: '100%', borderRadius: '8px' }}
              />
            ) : (
              <p className="text-footnote muted">Thumbnail loading…</p>
            )}
            <p className="text-footnote muted" style={{ marginTop: '0.75rem' }}>
              Full interactive viewer is not built yet. This route validates manifest, metadata, and tile API readiness.
            </p>
          </div>
          <div className="stack-sm">
            <p className="text-footnote"><strong>Asset:</strong> {assetId}</p>
            <p className="text-footnote"><strong>Format:</strong> {imgMeta.format || manifest?.format || '—'}</p>
            <p className="text-footnote"><strong>Status:</strong> {imgMeta.streaming_status || manifest?.streaming_status || 'unknown'}</p>
            <p className="text-footnote">
              <strong>Dimensions:</strong>{' '}
              {manifest?.width && manifest?.height
                ? `${manifest.width} × ${manifest.height}`
                : imgMeta.dimensions?.shape?.join(' × ') || '—'}
            </p>
            <p className="text-footnote"><strong>Channels:</strong> {manifest?.channels ?? imgMeta.channels ?? '—'}</p>
            <p className="text-footnote"><strong>Pyramid levels:</strong> {manifest?.pyramid_levels ?? imgMeta.pyramid_levels ?? 0}</p>
            <p className="text-footnote"><strong>OME-XML:</strong> {manifest?.ome_xml_present || imgMeta.ome_xml_present ? 'yes' : 'no'}</p>
            <p className="text-footnote">
              <strong>Tile API:</strong>{' '}
              {manifest?.tile_ready || imgMeta.tile_ready
                ? `ready (${manifest?.tile_size || 256}px tiles)`
                : 'pending inspection — run admin inspect job'}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
