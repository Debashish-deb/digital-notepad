import { useEffect, useState } from 'react';
import { Loader2, FileText, AlertTriangle, Calendar, HardDrive, Tag, Clock, FileType } from 'lucide-react';
import DocumentFormatter from './DocumentFormatter.jsx';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';

export default function DocumentViewer({ documentId }) {
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { openTaskpad } = useTaskpad();

  useEffect(() => {
    if (!documentId) return;

    let mounted = true;
    setLoading(true);
    setError(null);

    fetch(`/database/docs/${documentId}.json`)
      .then(res => {
        if (!res.ok) throw new Error('Document not found in static database.');
        return res.json();
      })
      .then(data => {
        if (mounted) {
          setDoc(data);
          setLoading(false);
        }
      })
      .catch(err => {
        if (mounted) {
          console.error(err);
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [documentId]);

  if (!documentId) return (
    <div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px', color: 'var(--mac-ink-muted)' }}>
      <p>Select a document from the index to view its contents.</p>
    </div>
  );

  if (loading) return (
    <div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px' }}>
      <Loader2 size={24} className="spin" style={{ color: 'var(--color-primary)' }} />
    </div>
  );

  if (error) return (
    <div className="panel error-state" style={{ minHeight: '300px' }}>
      <AlertTriangle size={24} color="var(--mac-destructive)" />
      <p>{error}</p>
    </div>
  );

  if (!doc) return null;

  const m = doc.metadata || {};
  const source = m.source || {};
  const classification = m.classification || {};

  return (
    <article className="notebook-page">
      <header className="notebook-page-header">
        <h2 className="notebook-page-title">
          {doc.filename}
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--mac-ink-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
          <FolderIcon size={14} />
          <span>{doc.relative_path}</span>
        </div>
      </header>

      {(m.source || m.classification) && (
        <div className="notebook-meta-grid">
          {source.size_human && (
            <div className="notebook-meta-item">
              <span className="notebook-meta-label"><HardDrive size={12} style={{ display: 'inline', marginRight: '4px' }} /> Size</span>
              <span className="notebook-meta-value">{source.size_human}</span>
            </div>
          )}
          {source.modified && (
            <div className="notebook-meta-item">
              <span className="notebook-meta-label"><Calendar size={12} style={{ display: 'inline', marginRight: '4px' }} /> Modified</span>
              <span className="notebook-meta-value">{new Date(source.modified).toLocaleString()}</span>
            </div>
          )}
          {classification.family && (
            <div className="notebook-meta-item">
              <span className="notebook-meta-label"><FileType size={12} style={{ display: 'inline', marginRight: '4px' }} /> Format</span>
              <span className="notebook-meta-value" style={{ textTransform: 'capitalize' }}>{classification.family} ({classification.extension})</span>
            </div>
          )}
          {m.converted_at && (
            <div className="notebook-meta-item">
              <span className="notebook-meta-label"><Clock size={12} style={{ display: 'inline', marginRight: '4px' }} /> Extracted</span>
              <span className="notebook-meta-value">{new Date(m.converted_at).toLocaleString()}</span>
            </div>
          )}
        </div>
      )}

      <div className="notebook-page-body" style={{ minHeight: '300px' }}>
        {doc.full_text ? (
          <DocumentFormatter 
            text={doc.full_text} 
            onCreateTask={(section) => openTaskpad(section)}
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem 0', color: 'var(--mac-ink-muted)' }}>
            <FileText size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
            <p>No readable text content was extracted from this file.</p>
          </div>
        )}
      </div>
    </article>
  );
}

// Inline component for Folder icon since it wasn't imported from lucide-react in the top block to avoid conflicts
function FolderIcon({ size = 14, ...props }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
    </svg>
  );
}
