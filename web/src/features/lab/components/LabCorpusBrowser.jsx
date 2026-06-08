import { useCallback, useEffect, useState } from 'react';
import { BookOpen, FolderTree, Loader2 } from 'lucide-react';
import { apiGet } from '@/services/client.js';

export default function LabCorpusBrowser({ title, description }) {
  const [sections, setSections] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadSections = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet('/api/lab/sections');
      const rows = data.sections || [];
      setSections(rows);
      setActiveId((prev) => {
        if (prev) return prev;
        const first =
          rows.find((s) => s.processed) || rows.find((s) => s.folder_exists) || rows[0];
        return first?.section_id || null;
      });
    } catch (e) {
      setError(String(e.message || e));
      setSections([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSections();
  }, [loadSections]);

  useEffect(() => {
    if (!activeId) {
      setSummary(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setDetailLoading(true);
      setError(null);
      try {
        const data = await apiGet(`/api/lab/section/${encodeURIComponent(activeId)}`);
        if (!cancelled) setSummary(data);
      } catch (e) {
        if (!cancelled) {
          setSummary(null);
          setError(String(e.message || e));
        }
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeId]);

  const active = sections.find((s) => s.section_id === activeId);

  return (
    <div className="stack-md lab-corpus-browser">
      <div className="panel">
        <h3 className="panel-title">
          <BookOpen size={18} /> {title || 'Lab corpus browser'}
        </h3>
        <p className="panel-lead prose-block">
          {description ||
            'Browse all database sections (Overview, Orders, Social, Wet-lab) with processed twins and vault counts.'}
        </p>
        {error && (
          <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>
            {error}
          </p>
        )}
      </div>

      <div className="panel" style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 1fr) 2fr', gap: '1rem' }}>
        <div>
          <h4 className="text-title-3">Sections ({sections.length})</h4>
          {loading ? (
            <p className="text-footnote muted">
              <Loader2 size={14} className="spin-inline" /> Loading…
            </p>
          ) : (
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
              {sections.map((s) => (
                <li key={s.section_id}>
                  <button
                    type="button"
                    className={`btn btn-sm ${activeId === s.section_id ? 'btn-primary' : 'btn-ghost'}`}
                    style={{ width: '100%', textAlign: 'left' }}
                    onClick={() => setActiveId(s.section_id)}
                  >
                    {s.section_label}
                    <span className="muted" style={{ display: 'block', fontSize: '0.75rem' }}>
                      {s.processed ? 'processed' : 'not processed'}
                      {s.extracted_document_count != null
                        ? ` · ${s.extracted_document_count} extracted`
                        : ''}
                      {s.vault_asset_count != null ? ` · vault ${s.vault_asset_count}` : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          {active && (
            <>
              <h4 className="text-title-3">{active.section_label}</h4>
              <p className="text-footnote muted">{active.description}</p>
              <p className="text-footnote citation-footnote">
                Root: {active.relative_root}
                {active.processed_at ? ` · processed ${active.processed_at}` : ''}
              </p>
            </>
          )}
          {detailLoading && (
            <p className="text-footnote muted">
              <Loader2 size={14} /> Loading summary…
            </p>
          )}
          {summary && !detailLoading && (
            <div className="stack-sm" style={{ marginTop: '0.75rem' }}>
              <p className="text-footnote">
                Assets on disk: {summary.metrics?.total_assets ?? summary.document_index_count ?? '—'} · Vault:{' '}
                {summary.vault_asset_count ?? '—'} · Extracted docs:{' '}
                {summary.metrics?.extracted_document_count ??
                  summary.extraction?.status_counts?.extracted ??
                  '—'}{' '}
                · Chunks: {summary.metrics?.knowledge_chunk_count ?? '—'}
              </p>
              {(summary.folder_tree || []).length > 0 && (
                <div>
                  <h5 className="text-title-3">
                    <FolderTree size={14} /> Folders
                  </h5>
                  <ul className="stack-sm text-footnote" style={{ listStyle: 'none', padding: 0 }}>
                    {summary.folder_tree.slice(0, 12).map((f) => (
                      <li key={f.path}>
                        {f.path} ({f.file_count} files)
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(summary.document_index_preview || summary.document_index || []).length > 0 && (
                <div>
                  <h5 className="text-title-3">Documents (sample)</h5>
                  <ul className="stack-sm text-footnote" style={{ listStyle: 'none', padding: 0 }}>
                    {(summary.document_index_preview || summary.document_index).slice(0, 15).map((d) => (
                      <li key={d.path || d.filename}>
                        <strong>{d.title || d.path || d.filename}</strong>
                        {d.extraction_status ? ` · ${d.extraction_status}` : ''}
                        {d.excerpt && (
                          <p className="text-caption muted" style={{ margin: '0.2rem 0 0' }}>
                            {d.excerpt.slice(0, 120)}
                            {d.excerpt.length > 120 ? '…' : ''}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
