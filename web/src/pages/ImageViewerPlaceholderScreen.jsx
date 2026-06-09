import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Microscope, RefreshCw } from 'lucide-react';
import ImageTileViewer from '@/features/imaging/components/ImageTileViewer.jsx';
import ScientificMetadataPanel from '@/features/imaging/components/ScientificMetadataPanel.jsx';
import { INSTRUMENT_PHASE_LABEL } from '@/lib/scientificImagery.js';
import {
  fetchImageManifest,
  fetchImageMetadata,
  loadThumbnailBlobUrl,
} from '@/services/imageAssetsClient.js';
import '@/features/imaging/components/ImageTileViewer.css';

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
    <div className="panel image-viewer-placeholder sci-instrument-shell">
      <div className="image-viewer-placeholder__header sci-instrument-shell__header">
        <button type="button" className="btn btn-sm btn-ghost" onClick={onClose}>
          <ArrowLeft size={16} aria-hidden /> Back
        </button>
        <div className="sci-instrument-shell__title-block">
          <p className="text-caption">{INSTRUMENT_PHASE_LABEL}</p>
          <h3 className="panel-title sci-instrument-shell__title">
            <Microscope size={18} aria-hidden /> Scientific Imaging Instrument
          </h3>
          <p className="sci-instrument-shell__subtitle">
            Multiplex microscopy · preserved metadata · raw pixel probe · display-only windowing
          </p>
        </div>
        <button type="button" className="btn btn-sm btn-ghost" onClick={load} title="Refresh manifest">
          <RefreshCw size={14} />
        </button>
      </div>

      {loading ? (
        <p className="text-footnote muted">
          <Loader2 className="spin-inline" size={16} /> Loading instrument manifest…
        </p>
      ) : null}
      {error ? (
        <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>
          {error}
        </p>
      ) : null}

      {!loading && !error ? (
        <div className="image-viewer-shell sci-instrument-layout">
          <div className="sci-instrument-layout__main">
            <ImageTileViewer
              assetId={assetId}
              manifest={manifest}
              thumbUrl={thumbUrl}
              degraded={degraded}
            />
            {!tileReady ? (
              <p className="text-footnote muted sci-instrument-layout__pending">
                Pyramid tiles pending — run admin inspect for full instrument mode. Thumbnail preview only.
              </p>
            ) : null}
          </div>
          <ScientificMetadataPanel manifest={manifest} metadata={metadata} />
        </div>
      ) : null}
    </div>
  );
}
