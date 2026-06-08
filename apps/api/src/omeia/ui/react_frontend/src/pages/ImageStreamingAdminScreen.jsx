import { useCallback, useEffect, useState } from 'react';
import { Activity, Image, RefreshCw } from 'lucide-react';
import {
  fetchImageReadiness,
  inspectImageAssets,
  retryFailedImageJobs,
} from '@/services/imageAssetsClient.js';

export default function ImageStreamingAdminScreen({ onBack }) {
  const [stats, setStats] = useState(null);
  const [assetIds, setAssetIds] = useState('');
  const [note, setNote] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await fetchImageReadiness();
      setStats(data);
    } catch (err) {
      setError(String(err.message || err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runInspect = async () => {
    const ids = assetIds
      .split(/[\s,]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!ids.length) {
      setNote('Enter one or more asset_ids (comma or newline separated).');
      return;
    }
    setBusy(true);
    setNote(null);
    try {
      const result = await inspectImageAssets(ids);
      setNote(`Inspect queued: ${result.queued} — ${result.results?.filter((r) => r.status === 'done').length || 0} succeeded.`);
      await load();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  };

  const runRetry = async () => {
    setBusy(true);
    try {
      const result = await retryFailedImageJobs();
      setNote(`Retried ${result.retried} failed jobs.`);
      await load();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 className="panel-title" style={{ margin: 0 }}>
          <Image size={18} style={{ verticalAlign: 'middle', marginRight: '0.35rem' }} />
          Image Streaming Readiness
        </h3>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {onBack ? (
            <button type="button" className="btn btn-sm btn-ghost" onClick={onBack}>
              Back to admin
            </button>
          ) : null}
          <button type="button" className="btn btn-sm btn-secondary" onClick={load} disabled={busy}>
            <RefreshCw size={14} className={busy ? 'spin' : undefined} aria-hidden /> Refresh
          </button>
        </div>
      </div>

      {note ? <p className="text-footnote citation-footnote muted">{note}</p> : null}
      {error ? <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p> : null}

      {stats ? (
        <div className="grid-2col" style={{ gap: '1.5rem', alignItems: 'start' }}>
          <div>
            <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem' }}>
              <Activity size={16} style={{ verticalAlign: 'middle', marginRight: '0.25rem' }} /> Coverage
            </h4>
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
              <li className="text-footnote">TIFF assets in inventory: {stats.tiff_asset_count}</li>
              <li className="text-footnote">Inspected: {stats.inspected_count}</li>
              <li className="text-footnote">Thumbnail ready: {stats.thumbnail_ready_count}</li>
              <li className="text-footnote">Tile ready: {stats.tile_ready_count}</li>
              <li className="text-footnote">Failed: {stats.failed_count}</li>
              <li className="text-footnote">Pending jobs: {stats.pending_jobs}</li>
              <li className="text-footnote">Failed jobs: {stats.failed_jobs}</li>
            </ul>
            <p className="text-footnote muted" style={{ marginTop: '0.75rem' }}>
              tifffile: {stats.tifffile_available ? 'available' : 'missing'} · Pillow: {stats.pillow_available ? 'available' : 'missing'}
            </p>
          </div>
          <div>
            <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem' }}>
              Status breakdown
            </h4>
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
              {Object.entries(stats.status_breakdown || {}).map(([k, v]) => (
                <li key={k} className="text-footnote">{k}: {v}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <p className="text-footnote muted">Loading readiness stats…</p>
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem' }}>
          Inspect assets
        </h4>
        <textarea
          className="input"
          rows={3}
          placeholder="asset_abc123, asset_def456"
          value={assetIds}
          onChange={(e) => setAssetIds(e.target.value)}
          style={{ width: '100%', marginBottom: '0.5rem' }}
        />
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={runInspect} disabled={busy}>
            Run inspect
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={runRetry} disabled={busy}>
            Retry failed jobs
          </button>
        </div>
      </div>
    </div>
  );
}
