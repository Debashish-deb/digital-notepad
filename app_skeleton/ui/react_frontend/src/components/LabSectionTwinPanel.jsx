import { useCallback, useEffect, useState } from 'react';
import { FileText, FolderTree, Loader2, Search, ChevronDown, ChevronUp } from 'lucide-react';
import DocumentViewer from './DocumentViewer.jsx';

/**
 * Shows extracted digital-twin data from the local static database catalog.
 */
export default function LabSectionTwinPanel({
  sectionId,
  title,
  description,
  knowledgeSearchHref = '/#data_storage:knowledge',
  compact = false,
  filterFolder = null,
  excludeFolder = null,
}) {
  const [catalog, setCatalog] = useState(null);
  const [docQuery, setDocQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetch('/database/catalog.json')
      .then(res => {
        if (!res.ok) throw new Error('Failed to load static database catalog.');
        return res.json();
      })
      .then(data => {
        if (mounted) {
          setCatalog(data);
          setLoading(false);
        }
      })
      .catch(err => {
        if (mounted) {
          setError(err.message);
          setLoading(false);
        }
      });
      
    return () => mounted = false;
  }, []);

  const getFilteredDocs = () => {
    if (!catalog || !catalog.sections) return [];
    
    // Map legacy sectionId to new sections
    let searchSections = [];
    if (sectionId?.includes('orders')) searchSections = ['02_Orders'];
    else if (sectionId?.includes('wet_lab')) searchSections = ['04_Wet_Lab'];
    else if (sectionId?.includes('social')) searchSections = ['03_Social'];
    else searchSections = ['01_Overview', '00_General_Knowledge'];
    
    let allDocs = [];
    for (const sec of searchSections) {
      if (catalog.sections[sec]) {
        allDocs = allDocs.concat(catalog.sections[sec]);
      }
    }
    
    if (docQuery.trim()) {
      const q = docQuery.toLowerCase();
      allDocs = allDocs.filter(d => d.title.toLowerCase().includes(q) || d.path.toLowerCase().includes(q));
    }
    
    if (filterFolder) {
      const qf = filterFolder.toLowerCase();
      allDocs = allDocs.filter(d => {
        const folder = d.path && d.path.includes('/') ? d.path.split('/')[0] : 'Root Documents';
        return folder.toLowerCase().includes(qf);
      });
    }

    if (excludeFolder) {
      const qf = excludeFolder.toLowerCase();
      allDocs = allDocs.filter(d => {
        const folder = d.path && d.path.includes('/') ? d.path.split('/')[0] : 'Root Documents';
        return !folder.toLowerCase().includes(qf);
      });
    }
    
    return allDocs;
  };

  const documents = getFilteredDocs();

  if (!sectionId) {
    return (
      <div className="panel">
        <p className="muted text-footnote">
          Select a subsection to view extracted documents from the lab database.
        </p>
      </div>
    );
  }

  const groupedDocuments = {};
  documents.forEach(d => {
    let folder = 'Root Documents';
    if (d.path && d.path.includes('/')) {
      folder = d.path.split('/')[0];
    }
    if (!groupedDocuments[folder]) groupedDocuments[folder] = [];
    groupedDocuments[folder].push(d);
  });

  const sortedFolders = Object.keys(groupedDocuments).sort();

  return (
    <div className={`stack-md lab-section-twin ${compact ? 'lab-section-twin--compact' : ''}`}>
      <div className="panel">
        <h3 className="panel-title">
          <FileText size={18} /> {title || sectionId}
        </h3>
        <p className="panel-lead prose-block">
          {description || 'Extracted documents from the static lab database.'}
        </p>
        {loading && (
          <p className="text-footnote muted">
            <Loader2 size={14} className="spin-inline" /> Loading digital twin…
          </p>
        )}
        {error && (
          <p className="text-footnote" style={{ color: 'var(--mac-destructive)' }}>
            {error}
          </p>
        )}
        {catalog && !loading && (
          <>
            <p className="text-footnote">
              <strong>{documents.length}</strong> static assets matched in this section.
            </p>
            <p className="text-footnote citation-footnote">
              Source: local static database (`/public/database/`)
            </p>
          </>
        )}
      </div>

      {catalog && (
        <div className="panel">
          <div className="disk-pad-toolbar">
            <h4 className="text-title-3" style={{ margin: 0 }}>
              Documents by Folder
            </h4>
            <input
              type="search"
              className="input"
              placeholder="Filter by filename…"
              value={docQuery}
              onChange={(e) => setDocQuery(e.target.value)}
              aria-label="Filter section documents"
            />
          </div>
          {!documents.length && (
            <p className="muted text-footnote" style={{ marginTop: '1rem' }}>No documents in preview.</p>
          )}

          <div style={{ marginTop: '1.5rem' }}>
            {sortedFolders.map(folder => {
              const docs = groupedDocuments[folder];
              return (
                <div key={folder} style={{ marginBottom: '2rem' }}>
                  <h4 style={{ 
                    borderBottom: '1px solid var(--mac-border)', 
                    paddingBottom: '0.5rem', 
                    marginBottom: '1rem',
                    color: 'var(--mac-ink)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}>
                    <FolderTree size={16} className="muted" /> {folder} <span className="muted" style={{ fontSize: '0.8rem' }}>({docs.length})</span>
                  </h4>
                  <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
                    {docs.slice(0, 50).map((d) => (
                      <li key={d.id} className="overview-news-row" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}>
                          <strong className="text-footnote">{d.title}</strong>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => setSelectedDocId(selectedDocId === d.id ? null : d.id)}
                          >
                            {selectedDocId === d.id ? <><ChevronUp size={14}/> Hide Content</> : <><ChevronDown size={14}/> Read Content</>}
                          </button>
                        </div>
                        <span className="text-caption muted">{d.path}</span>
                        
                        {selectedDocId === d.id && (
                          <div style={{ width: '100%', marginTop: '1rem', borderTop: '1px solid var(--mac-border)', paddingTop: '1rem' }}>
                            <DocumentViewer documentId={d.id} />
                          </div>
                        )}
                      </li>
                    ))}
                    {docs.length > 50 && (
                      <li className="text-caption muted" style={{ marginTop: '0.5rem' }}>
                        Showing 50 of {docs.length} matches in this folder. Use the search bar to refine.
                      </li>
                    )}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
