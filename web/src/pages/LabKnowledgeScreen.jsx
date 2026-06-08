
import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '@/services/client.js';
import { BookOpen, Loader2, FileText, ChevronRight, Search, AlertCircle, Users, Activity } from 'lucide-react';
import DocumentViewer from '@/features/documents/components/DocumentViewer.jsx';
import { groupDocumentsByDocumentType } from '@/features/documents/documentTypeGroups.js';
import { getDocumentType } from '@/features/documents/documentTypeRegistry.js';
import '@/features/documents/components/documentTypeLayouts.css';
import { databaseSectionIdForSub } from '@/config/databaseSections.js';
import { teamDirectory } from '@/data/teamDirectory.js';
import LabTeamRoster from '@/features/lab/components/LabTeamRoster.jsx';
import { activityLogs } from '@/data/activityLogs.js';

export default function LabKnowledgeScreen({ subId, navSub, API_URL, title, description }) {
  const sectionId = databaseSectionIdForSub(subId, navSub);
  
  const [catalog, setCatalog] = useState(null);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [catalogError, setCatalogError] = useState(null);
  
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [query, setQuery] = useState('');
  const [expandedTypes, setExpandedTypes] = useState({});

  useEffect(() => {
    let mounted = true;
    setLoadingCatalog(true);
    apiFetch('/api/database/catalog', { timeoutMs: 30_000 })
      .then((data) => {
        if (mounted) {
          setCatalog(data);
          setExpandedTypes({});
          setLoadingCatalog(false);
        }
      })
      .catch(err => {
        if (mounted) {
          console.error(err);
          setCatalogError(err.message);
          setLoadingCatalog(false);
        }
      });
      
    return () => mounted = false;
  }, []);

  const toggleType = (typeId) => {
    setExpandedTypes((prev) => ({ ...prev, [typeId]: !prev[typeId] }));
  };

  const typeGroupedDocs = useMemo(() => {
    if (!catalog?.sections) return [];

    const q = query.trim().toLowerCase();
    let allowedSections = [];

    if (!sectionId || sectionId?.startsWith('overview_') || sectionId === 'get_started') {
      allowedSections = ['01_Overview', '00_General_Knowledge'];
    } else if (sectionId?.startsWith('orders_')) {
      allowedSections = ['02_Orders'];
    } else if (sectionId?.startsWith('social_')) {
      allowedSections = ['03_Social'];
    } else if (sectionId === 'wet_lab_files') {
      allowedSections = ['04_Wet_Lab'];
    } else {
      allowedSections = Object.keys(catalog.sections);
    }

    const flat = [];
    for (const sec of allowedSections) {
      for (const doc of catalog.sections[sec] || []) {
        if (
          !q
          || doc.title.toLowerCase().includes(q)
          || doc.path.toLowerCase().includes(q)
        ) {
          flat.push({ ...doc, catalogSection: sec });
        }
      }
    }

    const grouped = groupDocumentsByDocumentType(
      flat.map((doc) => ({
        ...doc,
        display_title: doc.title,
      })),
    );

    return Object.entries(grouped)
      .filter(([, docs]) => docs.length > 0)
      .map(([typeId, docs]) => ({
        typeId,
        type: getDocumentType(typeId),
        docs,
      }));
  }, [catalog, query, sectionId]);

  return (
    <div className="stack-md lab-knowledge-screen" style={{ height: 'calc(100vh - 60px)', display: 'flex', flexDirection: 'column' }}>
      {/* Top Special Legacy Panels */}
      {sectionId === 'overview_personnel' && (
        <div className="panel" style={{ flexShrink: 0 }}>
          <h3 className="panel-title">
            <Users size={18} /> Team Directory
          </h3>
          <p className="panel-lead prose-block">
            {description || 'Personnel records and support documents.'}
          </p>
          <LabTeamRoster members={teamDirectory} className="lab-team-panel__roster lab-team-panel__roster--spaced" />
        </div>
      )}

      {sectionId === 'social_misc' && (
        <div className="panel" style={{ flexShrink: 0 }}>
          <h3 className="panel-title">
            <Activity size={18} /> Platform Activity & Social
          </h3>
          <p className="panel-lead prose-block">
            {description || 'Recent events and platform logs.'}
          </p>
          <ul className="stack-sm text-footnote" style={{ listStyle: 'none', padding: 0, marginTop: '1rem' }}>
            {activityLogs.map((log) => (
              <li key={log.log_id} className="overview-news-row" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <strong className="text-body">{log.actor}</strong>
                  <span className="text-caption muted">{new Date(log.created_at).toLocaleString()}</span>
                </div>
                <span className="text-caption" style={{ marginTop: '0.25rem' }}>{log.event_type}</span>
                <p className="text-caption" style={{ marginTop: '0.25rem' }}>{log.description}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Main Master-Detail UI */}
      {sectionId !== 'overview_personnel' && sectionId !== 'social_misc' && (
        <div className="panel" style={{ flexShrink: 0 }}>
          <h3 className="panel-title">
            <BookOpen size={18} /> {title || 'Static Knowledge Database'}
          </h3>
          <p className="panel-lead prose-block">
            {description || 'Explore digitized files securely extracted from the internal file systems. Content is loaded statically without API calls.'}
          </p>
          <div className="disk-pad-toolbar" style={{ marginTop: '1rem' }}>
            <input
              type="search"
              className="input"
              placeholder='Search file names or paths...'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search catalog"
            />
          </div>
        </div>
      )}

      <div className="lab-knowledge-layout" style={{ flex: 1, minHeight: 0, display: 'flex', gap: '1rem', marginTop: sectionId === 'overview_personnel' ? '1rem' : 0 }}>
        {/* Master Sidebar */}
        <div className="lab-knowledge-sidebar panel" style={{ flex: '0 0 320px', overflowY: 'auto', padding: '1rem' }}>
          {loadingCatalog && (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', color: 'var(--mac-ink-muted)' }}>
              <Loader2 size={16} className="spin" /> Loading catalog...
            </div>
          )}
          {catalogError && (
            <div style={{ color: 'var(--mac-destructive)' }}>
              <AlertCircle size={16} /> {catalogError}
            </div>
          )}
          
          {!loadingCatalog && !catalogError && typeGroupedDocs.length === 0 && (
            <p className="text-caption muted">No matching files found.</p>
          )}

          {!loadingCatalog && !catalogError && typeGroupedDocs.map(({ typeId, type, docs }) => {
            const TypeIcon = type.icon;
            const expanded = expandedTypes[typeId] ?? true;
            return (
              <div key={typeId} className="lab-knowledge-type-group">
                <button
                  type="button"
                  className="lab-knowledge-type-header"
                  onClick={() => toggleType(typeId)}
                >
                  {expanded ? <ChevronRight size={14} style={{ transform: 'rotate(90deg)' }} /> : <ChevronRight size={14} />}
                  <TypeIcon size={15} className="lab-knowledge-type-header__icon" aria-hidden />
                  <span>{type.label}</span>
                  <span className="lab-knowledge-type-header__count">{docs.length}</span>
                </button>

                {expanded ? (
                  <ul style={{ listStyle: 'none', padding: 0, margin: '0.25rem 0 0 1.25rem', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    {docs.map((doc) => (
                      <li key={doc.id}>
                        <button
                          type="button"
                          className={`doc-list-btn ${selectedDocId === doc.id ? 'active' : ''}`}
                          onClick={() => setSelectedDocId(doc.id)}
                          style={{
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: '0.5rem',
                            width: '100%',
                            background: selectedDocId === doc.id ? 'var(--mac-blue-alpha)' : 'none',
                            border: 'none',
                            cursor: 'pointer',
                            textAlign: 'left',
                            padding: '0.35rem 0.5rem',
                            borderRadius: '4px',
                            color: selectedDocId === doc.id ? 'var(--mac-blue)' : 'var(--mac-ink)',
                            fontSize: '0.85rem',
                          }}
                        >
                          <FileText size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
                          <span style={{ wordBreak: 'break-word', lineHeight: 1.3 }}>{doc.title}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </div>

        {/* Detail View */}
        <div className="lab-knowledge-detail" style={{ flex: 1, minWidth: 0 }}>
          <DocumentViewer documentId={selectedDocId} />
        </div>
      </div>
    </div>
  );
}
