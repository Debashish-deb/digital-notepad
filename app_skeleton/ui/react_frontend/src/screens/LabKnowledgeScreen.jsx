import './MacPlusVisualStyles.css';
import { useCallback, useEffect, useState } from 'react';
import { BookOpen, Loader2, FileText, ChevronRight, Search, Folder, AlertCircle } from 'lucide-react';
import DocumentViewer from '../components/DocumentViewer.jsx';
import { databaseSectionIdForSub } from '../config/databaseSections.js';
import { teamDirectory } from '../data/teamDirectory.js';
import { activityLogs } from '../data/activityLogs.js';
import { Users, Activity } from 'lucide-react';

export default function LabKnowledgeScreen({ subId, navSub, API_URL, title, description }) {
  const sectionId = databaseSectionIdForSub(subId, navSub);
  
  const [catalog, setCatalog] = useState(null);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [catalogError, setCatalogError] = useState(null);
  
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [query, setQuery] = useState('');
  const [expandedSections, setExpandedSections] = useState({});

  useEffect(() => {
    let mounted = true;
    setLoadingCatalog(true);
    fetch('/database/catalog.json')
      .then(res => {
        if (!res.ok) throw new Error('Failed to load static database catalog.');
        return res.json();
      })
      .then(data => {
        if (mounted) {
          setCatalog(data);
          // Auto-expand all sections initially
          const initialExpand = {};
          Object.keys(data.sections || {}).forEach(sec => {
            initialExpand[sec] = true;
          });
          setExpandedSections(initialExpand);
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

  const toggleSection = (sec) => {
    setExpandedSections(prev => ({ ...prev, [sec]: !prev[sec] }));
  };

  const getFilteredSections = () => {
    if (!catalog || !catalog.sections) return {};
    const q = query.trim().toLowerCase();
    
    // Map legacy sectionId to new sections.
    // We want to hardcode the scoping so that searches don't bleed across tabs.
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

    const filtered = {};
    for (const sec of allowedSections) {
      const docs = catalog.sections[sec] || [];
      const matchedDocs = docs.filter(doc => 
        doc.title.toLowerCase().includes(q) || 
        doc.path.toLowerCase().includes(q)
      );
      if (matchedDocs.length > 0) {
        filtered[sec] = matchedDocs;
      }
    }
    return filtered;
  };

  const filteredSections = getFilteredSections();

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
          <ul className="stack-sm text-footnote" style={{ listStyle: 'none', padding: 0, marginTop: '1rem' }}>
            {teamDirectory.map((member) => (
              <li key={member.username} className="overview-news-row" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <strong className="text-body">{member.full_name}</strong>
                <span className="text-caption muted">{member.role}</span>
                <p className="text-caption" style={{ marginTop: '0.25rem' }}>
                  Allowed projects: {member.allowed_projects?.join(', ') || 'None'}
                </p>
              </li>
            ))}
          </ul>
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
          
          {!loadingCatalog && !catalogError && Object.keys(filteredSections).length === 0 && (
            <p className="text-caption muted">No matching files found.</p>
          )}

          {!loadingCatalog && !catalogError && Object.keys(filteredSections).map(sec => (
            <div key={sec} style={{ marginBottom: '1rem' }}>
              <button 
                className="section-header-btn" 
                onClick={() => toggleSection(sec)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%', 
                  background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left',
                  padding: '0.25rem 0', color: 'var(--mac-ink)', fontWeight: 600, fontSize: '0.9rem'
                }}
              >
                {expandedSections[sec] ? <ChevronRight size={14} style={{ transform: 'rotate(90deg)' }}/> : <ChevronRight size={14} />}
                <Folder size={16} style={{ color: 'var(--mac-blue)' }} />
                {sec.replace(/^[0-9]+_/, '').replace(/_/g, ' ')} ({filteredSections[sec].length})
              </button>
              
              {expandedSections[sec] && (
                <ul style={{ listStyle: 'none', padding: 0, margin: '0.25rem 0 0 1.5rem', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  {filteredSections[sec].map(doc => (
                    <li key={doc.id}>
                      <button
                        className={`doc-list-btn ${selectedDocId === doc.id ? 'active' : ''}`}
                        onClick={() => setSelectedDocId(doc.id)}
                        style={{
                          display: 'flex', alignItems: 'flex-start', gap: '0.5rem', width: '100%', 
                          background: selectedDocId === doc.id ? 'var(--mac-blue-alpha)' : 'none', 
                          border: 'none', cursor: 'pointer', textAlign: 'left',
                          padding: '0.35rem 0.5rem', borderRadius: '4px',
                          color: selectedDocId === doc.id ? 'var(--mac-blue)' : 'var(--mac-ink)',
                          fontSize: '0.85rem'
                        }}
                      >
                        <FileText size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
                        <span style={{ wordBreak: 'break-word', lineHeight: 1.3 }}>{doc.title}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>

        {/* Detail View */}
        <div className="lab-knowledge-detail" style={{ flex: 1, minWidth: 0 }}>
          <DocumentViewer documentId={selectedDocId} />
        </div>
      </div>
    </div>
  );
}
