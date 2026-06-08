import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Database, FileSearch, Layers, RefreshCw } from 'lucide-react';
import { apiGet } from '@/services/client.js';
import { fetchDocumentLibraryStats } from '@/services/documentLibraryClient.js';

const LAYER_META = [
  {
    id: 'discovery',
    label: 'Discovery',
    detail: 'Path, checksum, type, domain — every file on disk is inventoried.',
  },
  {
    id: 'text',
    label: 'Text extraction',
    detail: 'Full chunk text in rag.* / canonical tables; vault keeps excerpt previews.',
  },
  {
    id: 'search',
    label: 'Search index',
    detail: 'Qdrant vectors + hybrid keyword — what Copilot and ⌘K can actually find.',
  },
];

function pct(part, total) {
  if (!total) return 0;
  return Math.round((part / total) * 100);
}

export default function DataIndexObservatoryPanel({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [indexHealth, setIndexHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [libStats, health] = await Promise.all([
        fetchDocumentLibraryStats().catch(() => null),
        apiGet('/api/admin/index-health').catch(() => null),
      ]);
      setStats(libStats);
      setIndexHealth(health);
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const audit = stats?.audit_counts || {};
  const total = stats?.total_files || 0;
  const indexed = Math.max(0, total - (audit.not_indexed || 0));
  const extracted = Math.max(0, total - (audit.pending_extraction || 0) - (audit.not_started || 0));

  const coverage = useMemo(() => ({
    discovery: { value: total, pct: total ? 100 : 0 },
    text: { value: extracted, pct: pct(extracted, total) },
    search: { value: indexed, pct: pct(indexed, total) },
  }), [total, extracted, indexed]);

  const driftHints = indexHealth?.drift_hints || [];
  const pg = indexHealth?.postgres || {};
  const qdrant = indexHealth?.qdrant || {};

  return (
    <section className="data-index-observatory panel" aria-label="Data index observatory">
      <div className="data-index-observatory__head">
        <h4 className="text-title-3">
          <Layers size={16} aria-hidden />
          {' '}
          Data index observatory
        </h4>
        <button type="button" className="btn btn-sm btn-secondary" onClick={load} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : undefined} aria-hidden />
          Refresh
        </button>
      </div>
      <p className="text-footnote muted data-index-observatory__lead">
        OMEIA tracks lab data in three layers. Search and Copilot only see layer 3 — gaps in extraction or
        vectorization mean content exists on disk but answers cannot cite it.
      </p>

      {error ? <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p> : null}

      <div className="data-index-observatory__layers">
        {LAYER_META.map((layer) => {
          const row = coverage[layer.id];
          return (
            <article key={layer.id} className="data-index-observatory__layer">
              <div className="data-index-observatory__layer-head">
                <strong>{layer.label}</strong>
                <span>{row.value.toLocaleString()} files · {row.pct}%</span>
              </div>
              <div className="data-index-observatory__bar" aria-hidden>
                <span style={{ width: `${row.pct}%` }} />
              </div>
              <p className="text-footnote muted">{layer.detail}</p>
            </article>
          );
        })}
      </div>

      {stats ? (
        <div className="data-index-observatory__audit">
          <h5 className="text-footnote" style={{ fontWeight: 750 }}>Audit queue (needs attention)</h5>
          <ul className="data-index-observatory__audit-list">
            {[
              ['not_indexed', 'Not in search index'],
              ['pending_extraction', 'Text not extracted yet'],
              ['needs_redigitalization', 'Needs re-digitalization'],
              ['unknown_type', 'Unknown file type'],
              ['duplicate_groups', 'Duplicate groups'],
              ['preview_missing', 'Preview missing'],
            ].map(([key, label]) => (
              <li key={key}>
                <span>{label}</span>
                <strong>{(audit[key] || 0).toLocaleString()}</strong>
              </li>
            ))}
          </ul>
          {onNavigate ? (
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              onClick={() => onNavigate('library', 'all_files')}
            >
              <FileSearch size={14} aria-hidden />
              Open document library
            </button>
          ) : null}
        </div>
      ) : null}

      {indexHealth ? (
        <div className="data-index-observatory__health">
          <h5 className="text-footnote" style={{ fontWeight: 750 }}>
            <Database size={13} aria-hidden />
            {' '}
            Postgres vs Qdrant alignment
          </h5>
          <ul className="text-footnote muted" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            <li>rag.document_chunk: {pg.rag_document_chunk ?? '—'}</li>
            <li>raw_asset_vault: {pg.raw_asset_vault ?? '—'}</li>
            <li>Qdrant reachable: {qdrant.reachable ? 'yes' : 'no'}</li>
            {(qdrant.collections || []).map((c) => (
              <li key={c.collection}>
                {c.collection}: {c.points_count ?? '—'} points
              </li>
            ))}
          </ul>
          {driftHints.length ? (
            <ul className="data-index-observatory__drift">
              {driftHints.map((hint) => (
                <li key={hint}>
                  <AlertTriangle size={13} aria-hidden />
                  {hint}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <p className="text-footnote muted">Index-health details require admin role.</p>
      )}
    </section>
  );
}
