import { useCallback, useEffect, useState } from 'react';
import { Activity, Cpu, RefreshCw } from 'lucide-react';
import { apiGet } from '@/services/client.js';

export default function ComputeStatusPanel() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet('/api/system/compute-status');
      setStatus(data);
    } catch (err) {
      setError(String(err.message || err));
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !status) {
    return <p className="text-footnote muted">Loading compute status…</p>;
  }

  if (error) {
    return (
      <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>
        {error}
      </p>
    );
  }

  if (!status) return null;

  const caps = status.capabilities || {};
  const imaging = caps.imaging || {};

  return (
    <div className="stack-sm">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <h4 className="text-title-3" style={{ margin: 0, flex: 1 }}>
          <Cpu size={16} style={{ verticalAlign: 'middle', marginRight: '0.25rem' }} />
          Adaptive compute
        </h4>
        <button type="button" className="btn btn-sm btn-ghost" onClick={load} title="Refresh">
          <RefreshCw size={14} />
        </button>
      </div>
      <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        <li className="text-footnote">
          Profile: <strong>{status.profile}</strong>
          {status.adaptive_compute_enabled ? '' : ' (adaptive compute off)'}
        </li>
        {status.model_tier ? (
          <li className="text-footnote">Model tier: {status.model_tier}</li>
        ) : null}
        {status.image_viewer_mode ? (
          <li className="text-footnote">Image mode: {status.image_viewer_mode}</li>
        ) : null}
        <li className="text-footnote">
          Ollama: {caps.ollama?.reachable ? 'reachable' : 'unavailable'}
        </li>
        <li className="text-footnote">
          Qdrant: {caps.qdrant?.reachable ? 'reachable' : 'unavailable'}
        </li>
        <li className="text-footnote">
          TIFF streaming: {imaging.streaming_ready ? 'ready' : 'not ready'}
        </li>
        <li className="text-footnote">
          DATABASE_ROOT: {caps.database_root?.readable ? 'readable' : 'missing'}
        </li>
      </ul>
      {status.message ? (
        <p className="text-footnote muted">{status.message}</p>
      ) : null}
      <p className="text-footnote muted">
        <Activity size={12} style={{ verticalAlign: 'middle' }} /> See docs/ADAPTIVE_COMPUTE_PROFILES.md
      </p>
    </div>
  );
}
