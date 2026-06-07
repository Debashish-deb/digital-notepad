import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Image as ImageIcon, Loader2, RefreshCw } from 'lucide-react';
import ImageTileViewer from '../components/ImageTileViewer.jsx';
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
      .catch(() => {
        if (alive) setThumbUrl(null);
      });
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
  const degraded = imgMeta.streaming_status === 'degraded' || manifest?.streaming_status === 'degraded';
  const tileReady = manifest?.tile_ready || imgMeta.tile_ready;

  return (
    <div className="panel image-viewer-placeholder">
      <div className="image-viewer-placeholder__header">
        <button type="button" className="btn btn-sm btn-ghost" onClick={onClose}>
          <ArrowLeft size={16} aria-hidden /> Back
        </button>
        <h3 className="panel-title" style={{ margin: 0 }}>
          <ImageIcon size={18} style={{ verticalAlign: 'middle', marginRight: '0.35rem' }} />
          Microscopy viewer
        </h3>
        <button type="button" className="btn btn-sm btn-ghost" onClick={load} title="Refresh manifest">
          <RefreshCw size={14} />
        </button>
        <span className="text-footnote muted">
          Napari-style channels · Z-stack · tile zoom/pan
        </span>
      </div>

      {loading ? (
        <p className="text-footnote muted">
          <Loader2 className="spin-inline" size={16} /> Loading manifest…
        </p>
      ) : null}
      {error ? (
        <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>
          {error}
        </p>
      ) : null}

      {!loading && !error ? (
        <div className="image-viewer-shell">
          <ImageTileViewer
            assetId={assetId}
            manifest={manifest}
            thumbUrl={thumbUrl}
            degraded={degraded}
          />
          <aside className="image-viewer-shell__meta stack-sm">
            <p className="text-footnote">
              <strong>Asset:</strong> {assetId}
            </p>
            <p className="text-footnote">
              <strong>Format:</strong> {imgMeta.format || manifest?.format || '—'}
            </p>
            <p className="text-footnote">
              <strong>Status:</strong> {imgMeta.streaming_status || manifest?.streaming_status || 'unknown'}
            </p>
            <p className="text-footnote">
              <strong>Dimensions:</strong>{' '}
              {manifest?.width && manifest?.height
                ? `${manifest.width} × ${manifest.height}`
                : imgMeta.dimensions?.shape?.join(' × ') || '—'}
            </p>
            <p className="text-footnote">
              <strong>Channels:</strong> {manifest?.channels ?? imgMeta.channels ?? '—'}
            </p>
            <p className="text-footnote">
              <strong>Z / T:</strong>{' '}
              {manifest?.z_slices ?? manifest?.z ?? 1} / {manifest?.timepoints ?? manifest?.t ?? 1}
            </p>
            <p className="text-footnote">
              <strong>Pyramid:</strong> {manifest?.pyramid_levels ?? imgMeta.pyramid_levels ?? 0} levels
            </p>
            <p className="text-footnote">
              <strong>OME-XML:</strong> {manifest?.ome_xml_present || imgMeta.ome_xml_present ? 'yes' : 'no'}
            </p>
            <p className="text-footnote">
              <strong>Tiles:</strong>{' '}
              {tileReady
                ? `ready (${manifest?.tile_size || 256}px)`
                : 'pending — thumbnail fallback'}
            </p>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
