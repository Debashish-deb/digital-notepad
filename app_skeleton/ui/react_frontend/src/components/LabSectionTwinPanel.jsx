import { useCallback, useEffect, useState } from 'react';
import { FileText, FolderTree, Loader2, Search } from 'lucide-react';
import { apiGet } from '../api/client.js';
import {
  documentPreviewRow,
  fetchLabSectionProcessed,
  hydrateSectionDocuments,
  sectionDetailFromTwin,
} from '../utils/labDatabaseUtils.js';

/**
 * Shows extracted digital-twin data from GET /api/lab/section/{id} (local processed JSON).
 */
export default function LabSectionTwinPanel({
  sectionId,
  title,
  description,
  knowledgeSearchHref = '/#data_storage:knowledge',
  compact = false,
}) {
  const [detail, setDetail] = useState(null);
  const [docQuery, setDocQuery] = useState('');
  const [documents, setDocuments] = useState([]);
  const [docTotal, setDocTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [docLoading, setDocLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadDetail = useCallback(async () => {
    if (!sectionId) {
      setDetail(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet(`/api/lab/section/${encodeURIComponent(sectionId)}`);
      const hydrated = await hydrateSectionDocuments(data, sectionId);
      setDetail(hydrated.detail);
      setDocuments(hydrated.documents);
      setDocTotal(hydrated.docTotal);
    } catch (e) {
      const twin = await fetchLabSectionProcessed(sectionId);
      const fallback = sectionDetailFromTwin(twin, sectionId);
      if (fallback) {
        setDetail(fallback);
        setDocuments(fallback.document_index_preview || []);
        setDocTotal(fallback.document_index_count ?? 0);
        setError(
          'API offline — showing cached processed twin. Start the backend on port 8000 for live data.',
        );
      } else {
        setDetail(null);
        setDocuments([]);
        setDocTotal(0);
        const msg = String(e.message || e);
        setError(
          msg === 'Failed to fetch' || msg.includes('fetch')
            ? 'Could not reach the API (is uvicorn running on port 8000?). Run database_processor --section overview_onboarding --refresh if no processed twin exists.'
            : msg,
        );
      }
    } finally {
      setLoading(false);
    }
  }, [sectionId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const searchDocuments = async () => {
    if (!sectionId) return;
    setDocLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ offset: '0', limit: '50' });
      const q = docQuery.trim();
      if (q.length >= 2) params.set('q', q);
      const data = await apiGet(
        `/api/lab/section/${encodeURIComponent(sectionId)}/documents`,
        { params },
      );
      setDocuments(data.documents || []);
      setDocTotal(data.total ?? 0);
    } catch (e) {
      const twin = await fetchLabSectionProcessed(sectionId);
      if (twin?.document_index?.length) {
        const tokens = docQuery.trim().toLowerCase().split(/\s+/).filter((t) => t.length >= 2);
        const relRoot = twin.relative_root || detail?.relative_root;
        let docs = (twin.document_index || []).map((doc) => documentPreviewRow(doc, relRoot));
        if (tokens.length) {
          docs = docs.filter((doc) => {
            const blob = `${doc.path} ${doc.title} ${doc.excerpt || ''}`.toLowerCase();
            return tokens.some((tok) => blob.includes(tok));
          });
        }
        setDocuments(docs.slice(0, 50));
        setDocTotal(docs.length);
      } else {
        setError(String(e.message || e));
      }
    } finally {
      setDocLoading(false);
    }
  };

  if (!sectionId) {
    return (
      <div className="panel">
        <p className="muted text-footnote">
          Select a subsection to view extracted documents from the lab database twin.
        </p>
      </div>
    );
  }

  const metrics = detail?.metrics || {};
  const extracted = metrics.extracted_document_count ?? detail?.extraction?.status_counts?.extracted;

  return (
    <div className={`stack-md lab-section-twin ${compact ? 'lab-section-twin--compact' : ''}`}>
      <div className="panel">
        <h3 className="panel-title">
          <FileText size={18} /> {title || detail?.section_label || sectionId}
        </h3>
        <p className="panel-lead prose-block">
          {description || detail?.description || 'Extracted documents from the on-disk lab database folder.'}
        </p>
        {loading && (
          <p className="text-footnote muted">
            <Loader2 size={14} className="spin-inline" /> Loading digital twin…
          </p>
        )}
        {error && (
          <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>
            {error}
          </p>
        )}
        {detail && !loading && (
          <>
            <p className="text-footnote">
              <strong>{metrics.total_assets ?? docTotal}</strong> assets on disk ·{' '}
              <strong>{extracted ?? '—'}</strong> extracted ·{' '}
              <strong>{metrics.knowledge_chunk_count ?? '—'}</strong> chunks · Vault:{' '}
              {detail.vault_asset_count ?? '—'}
              {detail.processed_at ? (
                <>
                  {' '}
                  · processed {detail.processed_at.slice(0, 16).replace('T', ' ')}
                </>
              ) : null}
            </p>
            <p className="text-footnote citation-footnote">
              Source: local processed twin ({detail.twin_file || detail.storage_key}) · root:{' '}
              {detail.relative_root}
            </p>
            <a className="btn btn-secondary btn-sm" href={knowledgeSearchHref} style={{ marginTop: '0.5rem' }}>
              Search in Knowledge index
            </a>
          </>
        )}
      </div>

      {detail && (detail.folder_tree || []).length > 0 && !compact && (
        <div className="panel">
          <h4 className="text-title-3">
            <FolderTree size={16} /> Top folders
          </h4>
          <ul className="stack-sm text-footnote" style={{ listStyle: 'none', padding: 0 }}>
            {(detail.folder_tree || []).slice(0, 12).map((f) => (
              <li key={f.path}>
                {f.path} ({f.file_count} files)
              </li>
            ))}
          </ul>
        </div>
      )}

      {detail && (
        <div className="panel">
          <div className="disk-pad-toolbar">
            <h4 className="text-title-3" style={{ margin: 0 }}>
              Documents ({docTotal})
            </h4>
            <input
              type="search"
              className="input"
              placeholder="Filter by filename or excerpt…"
              value={docQuery}
              onChange={(e) => setDocQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && searchDocuments()}
              aria-label="Filter section documents"
            />
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={searchDocuments}
              disabled={docLoading}
            >
              {docLoading ? <Loader2 size={14} className="spin" /> : <Search size={14} />}
              Filter
            </button>
          </div>
          {!documents.length && !docLoading && (
            <p className="muted text-footnote">No documents in preview. Run lab database processing if empty.</p>
          )}
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, marginTop: '0.75rem' }}>
            {documents.map((d) => (
              <li key={d.path} className="overview-news-row" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'baseline' }}>
                  <strong className="text-footnote">{d.title || d.path}</strong>
                  {d.open_url && (
                    <a
                      className="btn btn-secondary btn-sm"
                      href={d.open_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open original
                    </a>
                  )}
                </div>
                <span className="text-caption muted">{d.path}</span>
                {d.extraction_status && (
                  <span className="text-caption">{d.extraction_status}</span>
                )}
                {d.excerpt && (
                  <p className="text-caption" style={{ marginTop: '0.25rem' }}>
                    {d.excerpt.slice(0, 280)}
                    {d.excerpt.length > 280 ? '…' : ''}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
