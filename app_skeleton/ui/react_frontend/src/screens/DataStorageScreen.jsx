import { useCallback, useEffect, useState } from 'react';
import { CloudUpload, Database, HardDrive, Search } from 'lucide-react';
import { apiGet, apiPatch, apiPost } from '../api/client.js';
export default function DataStorageScreen({ title, description, section = 'vault' }) {
  const [summary, setSummary] = useState(null);
  const [roots, setRoots] = useState([]);
  const [connectors, setConnectors] = useState([]);
  const [platformConnectors, setPlatformConnectors] = useState(null);
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState([]);
  const [review, setReview] = useState([]);
  const [reviewQueue, setReviewQueue] = useState('uncategorized');
  const [ingestStatus, setIngestStatus] = useState(null);
  const [projectName, setProjectName] = useState('');
  const [vaultProjectId, setVaultProjectId] = useState('');
  const [digReviewKind, setDigReviewKind] = useState('uncategorized');
  const [digReview, setDigReview] = useState([]);
  const [digQuery, setDigQuery] = useState('');
  const [digHits, setDigHits] = useState([]);
  const [runs, setRuns] = useState([]);
  const [error, setError] = useState(null);
  const [syncDryRun, setSyncDryRun] = useState(true);
  const [supabaseSyncStatus, setSupabaseSyncStatus] = useState(null);
  const [labSections, setLabSections] = useState([]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, r, c, rq, dr, digRuns, plat, syncSt, labSec] = await Promise.all([
        apiGet('/api/vault/summary').catch(() => null),
        apiGet('/api/storage/roots').catch(() => ({ providers: [] })),
        apiGet('/api/storage/connectors/status').catch(() => ({ connectors: [] })),
        apiGet('/api/vault/review-queue', {
          params: new URLSearchParams({ limit: '15', queue: reviewQueue }),
        }).catch(() => ({ items: [] })),
        apiGet('/api/digitalize/review', {
          params: new URLSearchParams({ kind: digReviewKind, limit: '15' }),
        }).catch(() => ({ items: [] })),
        apiGet('/api/digitalize/runs', { params: new URLSearchParams({ limit: '8' }) }).catch(() => ({ runs: [] })),
        apiGet('/api/platform/connectors').catch(() => null),
        apiGet('/api/supabase/sync/status').catch(() => null),
        apiGet('/api/lab/sections').catch(() => ({ sections: [] })),
      ]);
      setSummary(s?.summary || s);
      setRoots(r.providers || []);
      setConnectors(c.connectors || []);
      setReview(rq.items || []);
      setDigReview(dr.items || []);
      setRuns(digRuns.runs || []);
      setPlatformConnectors(plat);
      setSupabaseSyncStatus(syncSt);
      setLabSections(labSec?.sections || []);
    } catch (e) {
      setError(String(e.message || e));
    }
  }, [reviewQueue, digReviewKind]);

  useEffect(() => {
    load();
  }, [load]);

  const markReviewed = async (assetId) => {
    setError(null);
    try {
      await apiPatch(`/api/vault/review/${assetId}`, {
        params: new URLSearchParams({ review_status: 'reviewed' }),
      });
      await load();
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const digitalizeProject = async (dryRun = false) => {
    const name = projectName.trim();
    if (!name) return;
    setError(null);
    setIngestStatus(`Digitalizing ${name}${dryRun ? ' (dry run)' : ''}…`);
    try {
      const data = await apiPost(`/api/digitalize/project/${encodeURIComponent(name)}`, {
        params: new URLSearchParams({ dry_run: dryRun ? 'true' : 'false' }),
      });
      setIngestStatus(`Digitalize: ${JSON.stringify(data.counts || data.status || 'done')}`);
      await load();
    } catch (e) {
      setError(String(e.message || e));
      setIngestStatus(null);
    }
  };

  const vaultIngestProject = async () => {
    const id = vaultProjectId.trim();
    if (!id) return;
    setIngestStatus(`Vault ingest project ${id}…`);
    try {
      const data = await apiPost(`/api/vault/ingest/project/${encodeURIComponent(id)}`);
      setIngestStatus(`Vault ingest: ${JSON.stringify(data.counts || {})}`);
      await load();
    } catch (e) {
      setError(String(e.message || e));
      setIngestStatus(null);
    }
  };

  const retryFailedIngest = async () => {
    setIngestStatus('Retrying failed vault extractions…');
    try {
      const data = await apiPost('/api/vault/ingest/retry-failed');
      setIngestStatus(`Retry: ${JSON.stringify(data.counts || {})}`);
      await load();
    } catch (e) {
      setError(String(e.message || e));
      setIngestStatus(null);
    }
  };

  const supabaseSync = async () => {
    setIngestStatus(`Supabase document sync${syncDryRun ? ' (dry run)' : ''}…`);
    try {
      const data = await apiPost('/api/supabase/sync/documents', {
        params: new URLSearchParams({ dry_run: syncDryRun ? 'true' : 'false' }),
      });
      setIngestStatus(
        syncDryRun
          ? `Dry run: would sync ${data.would_sync ?? data.document_rows_synced ?? 0} rows`
          : `Synced: ${data.document_rows_synced ?? 0} rows — ${data.status || 'ok'}`,
      );
      await load();
    } catch (e) {
      setError(String(e.message || e));
      setIngestStatus(null);
    }
  };

  const runVaultSearch = async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setError(null);
    try {
      const data = await apiGet('/api/vault/search', {
        params: new URLSearchParams({ q, limit: '25', uncategorized_only: 'false' }),
      });
      setHits(data.results || []);
    } catch (e) {
      setError(String(e.message || e));
      setHits([]);
    }
  };

  const runDigSearch = async () => {
    const q = digQuery.trim();
    if (q.length < 1) return;
    try {
      const data = await apiGet('/api/digitalize/search', {
        params: new URLSearchParams({ q, limit: '20' }),
      });
      setDigHits(data.items || []);
    } catch (e) {
      setError(String(e.message || e));
      setDigHits([]);
    }
  };

  const showVault = section === 'vault' || section === 'all';
  const showRoots = section === 'roots' || section === 'all';
  const showIngest = section === 'ingest' || section === 'all';

  return (
    <div className="stack-md">
      <div className="panel">
        <h3 className="panel-title">
          <HardDrive size={18} /> {title || 'Data & Storage'}
        </h3>
        <p className="panel-lead prose-block">
          {description || 'Raw knowledge vault, storage roots, connectors, and ingestion pipelines.'}
        </p>
        {summary && (
          <p className="text-footnote citation-footnote muted">
            Vault: {summary.asset_count ?? 0} assets · Postgres: {summary.postgres_asset_count ?? '—'} · Review:{' '}
            {summary.needs_review_count ?? '—'}
          </p>
        )}
        {error && <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p>}
        {ingestStatus && <p className="text-footnote muted">{ingestStatus}</p>}
      </div>

      {(showRoots || showIngest) && (
        <div className="panel">
          <h4 className="text-title-3">Storage roots & connectors</h4>
          {showRoots && (
            <>
              <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
                {roots.map((p) => (
                  <li key={p.id || p.storage_root_id} className="text-footnote">
                    <strong>{p.id || p.storage_root_id}</strong> — {p.role}{' '}
                    {p.configured ? '✓ configured' : '○ not configured'}
                    {p.root_logical_path ? ` · ${p.root_logical_path}` : ''}
                  </li>
                ))}
              </ul>
              <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, marginTop: '0.75rem' }}>
                {connectors
                  .filter((c) => !c.deprecated && !c.deprecated_storage_provider)
                  .map((c) => (
                    <li key={c.provider_id} className="text-footnote">
                      {c.provider_id}: {c.configured ? 'ready' : 'not configured'}
                      {c.role ? ` (${c.role})` : ''}
                    </li>
                  ))}
              </ul>
            </>
          )}
          {platformConnectors?.supabase && (
            <p className="text-footnote citation-footnote muted" style={{ marginTop: '0.5rem' }}>
              Supabase hosted: {platformConnectors.supabase.hosted_configured ? 'configured' : 'local Postgres fallback'}
            </p>
          )}
          {(supabaseSyncStatus?.status || platformConnectors?.supabase_sync) && (
            <p className="text-footnote citation-footnote muted" style={{ marginTop: '0.35rem' }}>
              Document sync:{' '}
              {supabaseSyncStatus?.status?.enabled || platformConnectors?.supabase_sync?.enabled
                ? 'enabled'
                : 'disabled'}
              {' · '}
              last:{' '}
              {supabaseSyncStatus?.status?.last_run ||
                supabaseSyncStatus?.last_report?.finished_at ||
                platformConnectors?.supabase_sync?.last_run ||
                '—'}
              {' · '}
              status:{' '}
              {supabaseSyncStatus?.status?.last_status ||
                supabaseSyncStatus?.last_report?.status ||
                platformConnectors?.supabase_sync?.last_status ||
                '—'}
              {supabaseSyncStatus?.last_report?.document_rows_synced != null
                ? ` · synced ${supabaseSyncStatus.last_report.document_rows_synced}`
                : ''}
            </p>
          )}
          {labSections.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <h5 className="text-title-3">Lab sections (vault counts)</h5>
              <ul className="stack-sm text-footnote" style={{ listStyle: 'none', padding: 0 }}>
                {labSections.map((sec) => (
                  <li key={sec.section_id}>
                    {sec.section_label}: vault {sec.vault_asset_count ?? 0}
                    {sec.processed ? ` · processed (${sec.metrics?.total_assets ?? '—'} assets)` : ' · not processed'}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {showIngest && (
            <div style={{ marginTop: '1rem' }}>
              <h4 className="text-title-3">
                <CloudUpload size={16} style={{ verticalAlign: 'middle' }} /> Supabase document sync (admin)
              </h4>
              <p className="text-footnote muted">
                Pushes document metadata from local Postgres to hosted Supabase. Enable dry run first; live sync requires
                admin role when auth is on.
              </p>
              <label className="text-footnote" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <input type="checkbox" checked={syncDryRun} onChange={(e) => setSyncDryRun(e.target.checked)} />
                Dry run (recommended)
              </label>
              <button type="button" className="btn btn-secondary btn-sm" style={{ marginTop: '0.5rem' }} onClick={supabaseSync}>
                Run sync
              </button>
            </div>
          )}
        </div>
      )}

      {showVault && (
        <div className="panel">
          <div className="disk-pad-toolbar">
            <input
              type="search"
              className="input"
              placeholder="Search vault metadata…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && runVaultSearch()}
            />
            <button type="button" className="btn btn-primary btn-sm" onClick={runVaultSearch}>
              <Search size={14} /> Vault search
            </button>
          </div>
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, marginTop: '0.75rem' }}>
            {hits.map((h) => (
              <li key={h.asset_id} className="text-footnote">
                <Database size={12} style={{ verticalAlign: 'middle' }} /> {h.filename}{' '}
                <span className="muted">— {h.logical_path}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {showIngest && (
        <>
          <div className="panel">
            <h4 className="text-title-3">Project digitalization</h4>
            <div className="disk-pad-toolbar">
              <input
                className="input"
                placeholder="Project folder name"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
              />
              <button type="button" className="btn btn-primary btn-sm" onClick={() => digitalizeProject(false)}>
                Digitalize
              </button>
              <button type="button" className="btn btn-sm" onClick={() => digitalizeProject(true)}>
                Dry run
              </button>
            </div>
            <div className="disk-pad-toolbar" style={{ marginTop: '0.5rem' }}>
              <input
                className="input"
                placeholder="Vault ingest project id"
                value={vaultProjectId}
                onChange={(e) => setVaultProjectId(e.target.value)}
              />
              <button type="button" className="btn btn-sm" onClick={vaultIngestProject}>
                Vault ingest project
              </button>
            </div>
          </div>

          <div className="panel">
            <h4 className="text-title-3">Digitalization search & review</h4>
            <div className="disk-pad-toolbar">
              <input
                className="input"
                placeholder="Digitalize corpus search"
                value={digQuery}
                onChange={(e) => setDigQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runDigSearch()}
              />
              <button type="button" className="btn btn-sm" onClick={runDigSearch}>
                Search
              </button>
              <select className="input" value={digReviewKind} onChange={(e) => setDigReviewKind(e.target.value)}>
                <option value="projects">Project candidates</option>
                <option value="uncategorized">Uncategorized</option>
                <option value="failed">Failed</option>
                <option value="large_files">Large files</option>
                <option value="tables">Tables</option>
                <option value="texts">Texts</option>
              </select>
            </div>
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, marginTop: '0.5rem' }}>
              {digHits.map((r) => (
                <li key={r.asset_id} className="text-caption">
                  {r.filename || r.project_name}
                </li>
              ))}
              {digReview.slice(0, 15).map((r) => (
                <li key={r.asset_id || r.project_candidate_id} className="text-caption">
                  {r.project_name || r.filename} — {r.extraction_status || r.project_status || '—'}
                </li>
              ))}
            </ul>
          </div>

          <div className="panel">
            <h4 className="text-title-3">Recent digitalization runs</h4>
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
              {runs.map((r) => (
                <li key={r.run_id} className="text-footnote">
                  {r.mode} · {r.project_name || 'full'} · {r.status}
                  {r.dry_run ? ' (dry)' : ''} — {r.started_at ? new Date(r.started_at).toLocaleString() : '—'}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {showVault && (
        <div className="panel">
          <h4 className="text-title-3">Vault review queue</h4>
          <div className="disk-pad-toolbar">
            <select className="input" value={reviewQueue} onChange={(e) => setReviewQueue(e.target.value)}>
              <option value="uncategorized">Uncategorized</option>
              <option value="failed">Failed extraction</option>
              <option value="low_confidence">Low confidence</option>
            </select>
            <button type="button" className="btn btn-sm" onClick={retryFailedIngest}>
              Retry failed
            </button>
          </div>
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, marginTop: '0.5rem' }}>
            {review.slice(0, 15).map((r) => (
              <li key={r.asset_id} className="text-caption" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span>
                  {r.filename} — {r.extraction_status || '—'}
                </span>
                <button type="button" className="btn btn-sm" onClick={() => markReviewed(r.asset_id)}>
                  Mark reviewed
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
