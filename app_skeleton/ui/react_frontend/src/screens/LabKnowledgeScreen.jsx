import './MacPlusVisualStyles.css';
import { useCallback, useEffect, useState } from 'react';
import { BookOpen, Loader2, MapPin, Search } from 'lucide-react';
import { databaseSectionIdForSub } from '../config/databaseSections.js';
import LabSectionTwinPanel from '../components/LabSectionTwinPanel.jsx';
import { apiGet, apiFetch } from '../api/client.js';

export default function LabKnowledgeScreen({ subId, navSub, API_URL, title, description }) {
  const sectionId = databaseSectionIdForSub(subId, navSub);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [selected, setSelected] = useState(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [allSections, setAllSections] = useState([]);

  const loadStats = useCallback(async () => {
    try {
      const data = await apiGet('/api/knowledge/lab/stats').catch(() => null);
      if (data) setStats(data);
    } catch {
      setStats(null);
    }
  }, [API_URL]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    if (sectionId) {
      setAllSections([]);
      return;
    }
    apiGet('/api/lab/sections')
      .then((data) => setAllSections((data?.sections || []).filter((s) => s.processed)))
      .catch(() => setAllSections([]));
  }, [sectionId]);

  const runSearch = async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setLoading(true);
    setError(null);
    setSelected(null);
    try {
      const params = new URLSearchParams({ q });
      if (sectionId) params.set('section_id', sectionId);
      const data = await apiGet('/api/knowledge/lab/search', { params });
      setResults(data.results || []);
      if (!data.results?.length) {
        setError('No indexed matches. Run “Index into app database” if this section was never ingested.');
      }
    } catch (e) {
      setError(String(e.message || e));
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const runIngest = async () => {
    setIngestLoading(true);
    setError(null);
    try {
      const path = sectionId
        ? `/api/knowledge/lab/ingest/${encodeURIComponent(sectionId)}`
        : '/api/knowledge/lab/ingest-all';
      const data = await apiFetch(path, {
        method: 'POST',
        body: { refresh_extract: false },
      });
      await loadStats();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setIngestLoading(false);
    }
  };

  return (
    <div className="stack-md lab-knowledge-screen">
      {sectionId && (
        <LabSectionTwinPanel
          sectionId={sectionId}
          title={title}
          description={description}
          compact
        />
      )}

      {!sectionId && allSections.length > 0 && (
        <div className="panel">
          <h4 className="text-title-3">Processed lab sections</h4>
          <ul className="stack-sm text-footnote" style={{ listStyle: 'none', padding: 0 }}>
            {allSections.map((s) => (
              <li key={s.section_id}>
                <strong>{s.section_label}</strong> — {s.extracted_document_count ?? 0} extracted /{' '}
                {s.disk_asset_count ?? s.document_index_count ?? '—'} assets
              </li>
            ))}
          </ul>
          <p className="text-footnote muted">Open a subsection in the sidebar to browse documents.</p>
        </div>
      )}

      <div className="panel">
        <h3 className="panel-title">
          <BookOpen size={18} /> {sectionId ? 'Indexed search' : title || 'Lab knowledge'}
        </h3>
        <p className="panel-lead prose-block">
          {sectionId
            ? 'Search the PostgreSQL/Qdrant knowledge index for this section (after “Index into app database”).'
            : description || 'Search the canonical lab knowledge index (PostgreSQL + vectors).'}
          {' '}Extracted files above come from the local processed twin; indexing copies them into{' '}
          <code>rag.document_source</code> / <code>rag.document_chunk</code>.
        </p>
        {stats && !stats.error && (
          <p className="text-footnote muted">
            Indexed corpus: {stats.documents ?? 0} documents, {stats.chunks ?? 0} chunks
            {sectionId && stats.by_section
              ? ` · this section: ${
                  stats.by_section.find((s) => s.section_id === sectionId)?.chunks ?? 0
                } chunks`
              : ''}
          </p>
        )}
        {stats?.error && (
          <p className="text-footnote" style={{ color: 'var(--danger)' }}>
            Database unavailable: {stats.error}. Start Postgres and run indexing.
          </p>
        )}
      </div>

      <div className="panel">
        <div className="disk-pad-toolbar">
          <input
            type="search"
            className="input"
            placeholder='Search e.g. "lab coats", "onboarding", "FedEx shipping"...'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runSearch()}
            aria-label="Search lab knowledge"
          />
          <button type="button" className="btn btn-primary btn-sm" onClick={runSearch} disabled={loading}>
            {loading ? <Loader2 size={14} className="spin" /> : <Search size={14} />}
            Search
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={runIngest}
            disabled={ingestLoading}
            title="Assimilate extracted text into app database"
          >
            {ingestLoading ? <Loader2 size={14} className="spin" /> : 'Index into app database'}
          </button>
        </div>
        {error && <p className="text-footnote" style={{ color: 'var(--danger)', marginTop: '0.5rem' }}>{error}</p>}
      </div>

      <div className="lab-knowledge-layout">
        <div className="lab-knowledge-results panel">
          <h4 className="text-title-3">Results ({results.length})</h4>
          {!results.length && !loading && (
            <p className="muted text-footnote">Enter a query to search indexed lab documents.</p>
          )}
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {results.map((hit) => (
              <li key={hit.chunk_uid}>
                <button
                  type="button"
                  className={`disk-pad-folder-item lab-knowledge-hit ${selected?.chunk_uid === hit.chunk_uid ? 'active' : ''}`}
                  style={{ width: '100%' }}
                  onClick={() => setSelected(hit)}
                >
                  <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                    <strong>{hit.title}</strong>
                    <div className="text-caption" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '0.2rem' }}>
                      <MapPin size={12} />
                      {hit.where_to_find || hit.citation}
                    </div>
                    <p className="text-caption" style={{ marginTop: '0.35rem' }}>
                      {hit.excerpt?.slice(0, 200)}
                      {hit.excerpt?.length > 200 ? '…' : ''}
                    </p>
                  </div>
                  <span className="text-caption">{(hit.score * 100).toFixed(0)}%</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="lab-knowledge-detail panel">
          {!selected && <p className="muted text-footnote">Select a result to read indexed content and source location.</p>}
          {selected && (
            <>
              <header className="disk-pad-preview-header">
                <div>
                  <h4 className="text-title-3">{selected.title}</h4>
                  <p className="text-caption">
                    <MapPin size={14} style={{ verticalAlign: 'middle' }} /> {selected.where_to_find}
                  </p>
                  <p className="text-footnote muted">
                    Document code: <code>{selected.document_code}</code>
                  </p>
                </div>
              </header>
              <pre className="disk-pad-preview-body">{selected.full_text || selected.excerpt}</pre>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
