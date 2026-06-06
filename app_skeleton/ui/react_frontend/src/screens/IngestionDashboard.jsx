
import { useCallback, useEffect, useState } from 'react';
import { BarChart3, RefreshCw } from 'lucide-react';
import { apiGet } from '../api/client.js';
export default function IngestionDashboard({ title, description }) {
  const [summary, setSummary] = useState(null);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [vault, dig] = await Promise.all([
        apiGet('/api/vault/summary').catch(() => null),
        apiGet('/api/digitalize/runs', { params: new URLSearchParams({ limit: '12' }) }).catch(() => ({ runs: [] })),
      ]);
      setSummary(vault?.summary || vault);
      setRuns(dig?.runs || []);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const s = summary || {};

  return (
    <div className="stack-md ingestion-dashboard">
      <div className="panel">
        <h3 className="panel-title">
          <BarChart3 size={18} /> {title || 'Ingestion dashboard'}
        </h3>
        <p className="panel-lead prose-block">
          {description || 'Vault asset counts and recent digitalization runs from Postgres.'}
        </p>
        <div className="disk-pad-toolbar" style={{ marginTop: '0.75rem' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={14} /> {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
        {error && <p className="text-footnote citation-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p>}
      </div>

      <div className="panel">
        <h4 className="text-title-3">Vault extraction summary</h4>
        <div className="ingestion-metrics-grid">
          <Metric label="Assets indexed" value={s.asset_count ?? '—'} />
          <Metric label="Postgres rows" value={s.postgres_asset_count ?? '—'} />
          <Metric label="Needs review" value={s.needs_review_count ?? '—'} />
          <Metric label="Failed extraction" value={s.failed_extraction_count ?? s.failed_count ?? '—'} />
          <Metric label="Uncategorized" value={s.uncategorized_count ?? '—'} />
          <Metric label="Vectorized" value={s.vectorized_count ?? '—'} />
        </div>
        {s.last_ingest_at && (
          <p className="text-footnote citation-footnote muted">Last vault ingest: {s.last_ingest_at}</p>
        )}
      </div>

      <div className="panel">
        <h4 className="text-title-3">Digitalization runs</h4>
        {!runs.length && <p className="text-footnote muted">No runs recorded yet.</p>}
        <table className="data-table" style={{ width: '100%', marginTop: '0.5rem' }}>
          <thead>
            <tr>
              <th>Run</th>
              <th>Mode</th>
              <th>Project</th>
              <th>Status</th>
              <th>Dry run</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.run_id}>
                <td className="text-caption">{String(r.run_id).slice(0, 8)}…</td>
                <td>{r.mode}</td>
                <td>{r.project_name || '—'}</td>
                <td>{r.status}</td>
                <td>{r.dry_run ? 'yes' : 'no'}</td>
                <td className="text-caption">{r.started_at ? new Date(r.started_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="ingestion-metric-card">
      <span className="ingestion-metric-value">{value}</span>
      <span className="ingestion-metric-label">{label}</span>
    </div>
  );
}
