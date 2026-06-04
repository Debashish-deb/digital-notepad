import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import { BookOpen, FileText } from 'lucide-react';

export default function NotebookWikiScreen({ dbProjects, API_URL, hideHeader = false, defaultSubTab = 'notebook' }) {
  const [notebookEntries, setNotebookEntries] = useState([]);
  const [wikiDocs, setWikiDocs] = useState([]);
  const [subTab, setSubTab] = useState(defaultSubTab);
  const [selectedNotebook, setSelectedNotebook] = useState(null);
  const [selectedWiki, setSelectedWiki] = useState(null);
  const [wikiSearch, setWikiSearch] = useState('');

  // New notebook entry form states
  const [nProj, setNProj] = useState(dbProjects[0]?.project_code || 'SPACE');
  const [nTitle, setNTitle] = useState('');
  const [nContent, setNContent] = useState('');
  const [nConclusions, setNConclusions] = useState('');
  const [nIssues, setNIssues] = useState('');
  const [nNext, setNNext] = useState('');
  const [nTags, setNTags] = useState('QC, run_log');
  const [nType, setNType] = useState('general_note');

  useEffect(() => {
    fetchNotebook();
    fetchWiki();
  }, []);

  useEffect(() => {
    if (dbProjects.length > 0 && !dbProjects.some((p) => p.project_code === nProj)) {
      setNProj(dbProjects[0].project_code);
    }
  }, [dbProjects, nProj]);

  const fetchNotebook = async () => {
    try {
      const res = await fetch(`${API_URL}/notebook`);
      if (res.ok) {
        const data = await res.json();
        setNotebookEntries(data);
        if (data.length > 0) setSelectedNotebook(data[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchWiki = async () => {
    try {
      const res = await fetch(`${API_URL}/wiki`);
      if (res.ok) {
        const data = await res.json();
        setWikiDocs(data);
        if (data.length > 0) setSelectedWiki(data[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateNotebook = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/notebook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_code: nProj,
          title: nTitle,
          content: nContent,
          conclusions: nConclusions,
          issues_found: nIssues,
          next_steps: nNext,
          tags: nTags.split(',').map(t => t.trim()),
          entry_type: nType,
          author_username: "debdeba"
        })
      });
      if (res.ok) {
        alert("Notebook entry successfully logged in system of record!");
        setNTitle('');
        setNContent('');
        setNConclusions('');
        setNIssues('');
        setNNext('');
        fetchNotebook();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      {!hideHeader && (
        <div className="page-header">
          <h1 className="page-title-gradient">Living Notebook & Wiki SOPs</h1>
          <p className="page-subtitle">Standard Operating Protocols and interactive notebook registers for the spatial biology laboratory.</p>
        </div>
      )}

      <div className="tabs-header">
        <button className={`tab-button ${subTab === 'notebook' ? 'active' : ''}`} onClick={() => setSubTab('notebook')}>
          📓 Lab Notebook Logs
        </button>
        <button className={`tab-button ${subTab === 'wiki' ? 'active' : ''}`} onClick={() => setSubTab('wiki')}>
          📚 Protocols Wiki SOPs
        </button>
      </div>

      {subTab === 'notebook' && (
        <div className="grid-2col">
          <div className="panel">
            <h3 className="panel-title"><BookOpen size={18} /> Select Notebook Logs</h3>
            <div style={{display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '450px', overflowY: 'auto'}}>
              {notebookEntries.map(e => (
                <div 
                  key={e.entry_id} 
                  className={`sidebar-item ${selectedNotebook?.entry_id === e.entry_id ? 'active' : ''}`}
                  onClick={() => setSelectedNotebook(e)}
                  style={{borderLeft: selectedNotebook?.entry_id === e.entry_id ? '4px solid var(--color-primary)' : 'none'}}
                >
                  <div style={{display: 'flex', flexDirection: 'column', width: '100%'}}>
                    <span style={{fontWeight: 600, fontSize: '0.9rem'}}>{e.title}</span>
                    <span style={{fontSize: '0.75rem', color: 'var(--text-muted)'}}>{e.project_code} | {e.created_at.slice(0, 10)}</span>
                  </div>
                </div>
              ))}
            </div>
            
            <hr style={{margin: '1.5rem 0', borderColor: 'var(--border-color)'}} />
            
            <h4 style={{fontSize: '1rem', marginBottom: '1rem'}}>🆕 Create Notebook Log</h4>
            <form onSubmit={handleCreateNotebook} style={{display: 'flex', flexDirection: 'column', gap: '0.85rem'}}>
              <div className="form-group">
                <label className="form-label">Project Code</label>
                <select className="form-select" value={nProj} onChange={(e) => setNProj(e.target.value)}>
                  {dbProjects.map(p => (
                    <option key={p.project_code} value={p.project_code}>{p.project_code}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Log Title</label>
                <input type="text" className="form-input" required value={nTitle} onChange={(e) => setNTitle(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Observations</label>
                <textarea className="form-textarea" required value={nContent} onChange={(e) => setNContent(e.target.value)} style={{height: '100px'}} />
              </div>
              <div className="form-group">
                <label className="form-label">Conclusions</label>
                <input type="text" className="form-input" value={nConclusions} onChange={(e) => setNConclusions(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Issues Found</label>
                <input type="text" className="form-input" value={nIssues} onChange={(e) => setNIssues(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Next Steps</label>
                <input type="text" className="form-input" value={nNext} onChange={(e) => setNNext(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Entry Type</label>
                <select className="form-select" value={nType} onChange={(e) => setNType(e.target.value)}>
                  <option value="general_note">General Note</option>
                  <option value="decision_note">Decision Note</option>
                  <option value="run_failure_note">Run Failure Note</option>
                  <option value="protocol_deviation_note">Protocol Deviation Note</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary">Record Entry in Logbook</button>
            </form>
          </div>

          <div className="panel">
            <h3 className="panel-title"><FileText size={18} /> Log Details</h3>
            {selectedNotebook ? (
              <div>
                <h2 style={{color: '#ffffff', marginBottom: '0.5rem'}}>{selectedNotebook.title}</h2>
                <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem'}}>
                  Project: <b>{selectedNotebook.project_code}</b> | Version: <b>{selectedNotebook.version}</b> | Date: <i>{selectedNotebook.created_at.replace('T', ' ').slice(0, 16)}</i>
                </div>
                <div className="markdown-body" style={{background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '8px', border: '1px solid var(--border-color)', minHeight: '180px', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)'}}>
                  {selectedNotebook.content}
                </div>
                
                {selectedNotebook.conclusions && (
                  <div style={{marginTop: '1.25rem', background: 'rgba(52,211,153,0.06)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(52,211,153,0.15)'}}>
                    <h5 style={{color: 'var(--color-success)', marginBottom: '0.25rem'}}>Conclusions</h5>
                    <p style={{fontSize: '0.9rem', color: 'var(--text-primary)'}}>{selectedNotebook.conclusions}</p>
                  </div>
                )}

                {selectedNotebook.issues_found && (
                  <div style={{marginTop: '1rem', background: 'rgba(248,113,113,0.06)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(248,113,113,0.15)'}}>
                    <h5 style={{color: 'var(--color-danger)', marginBottom: '0.25rem'}}>⚠️ Issues Found</h5>
                    <p style={{fontSize: '0.9rem', color: 'var(--text-primary)'}}>{selectedNotebook.issues_found}</p>
                  </div>
                )}
                
                {selectedNotebook.next_steps && (
                  <div style={{marginTop: '1rem', background: 'rgba(129,140,248,0.06)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(129,140,248,0.15)'}}>
                    <h5 style={{color: 'var(--color-accent)', marginBottom: '0.25rem'}}>💡 Recommended Next Steps</h5>
                    <p style={{fontSize: '0.9rem', color: 'var(--text-primary)'}}>{selectedNotebook.next_steps}</p>
                  </div>
                )}
              </div>
            ) : (
              <p style={{color: 'var(--text-muted)'}}>Select a log to view details.</p>
            )}
          </div>
        </div>
      )}

      {subTab === 'wiki' && (
        <div className="grid-2col">
          <div className="panel">
            <h3 className="panel-title"><BookOpen size={18} /> Protocols Wiki Articles</h3>
            <input 
              type="text" 
              placeholder="Search Wiki Articles..." 
              className="form-input" 
              value={wikiSearch} 
              onChange={(e) => setWikiSearch(e.target.value)} 
              style={{marginBottom: '1rem', width: '100%'}}
            />
            <div style={{display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '400px', overflowY: 'auto'}}>
              {wikiDocs.filter(w => 
                w.title.toLowerCase().includes(wikiSearch.toLowerCase()) ||
                w.content.toLowerCase().includes(wikiSearch.toLowerCase())
              ).map(w => (
                <div 
                  key={w.wiki_id} 
                  className={`sidebar-item ${selectedWiki?.wiki_id === w.wiki_id ? 'active' : ''}`}
                  onClick={() => setSelectedWiki(w)}
                >
                  <div style={{display: 'flex', flexDirection: 'column'}}>
                    <span style={{fontWeight: 600, fontSize: '0.9rem'}}>{w.title}</span>
                    <span style={{fontSize: '0.75rem', color: 'var(--text-muted)'}}>{w.wiki_type || 'SOP'} | Rev {w.revision || 1}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <h3 className="panel-title"><FileText size={18} /> Wiki Content</h3>
            {selectedWiki ? (
              <div>
                <h2 style={{color: '#ffffff', marginBottom: '0.5rem'}}>{selectedWiki.title}</h2>
                <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem'}}>
                  Category: <b>{selectedWiki.wiki_type || 'SOP'}</b> | Revision: <b>{selectedWiki.revision || 1}</b> | Editor: <i>{selectedWiki.author_name || 'debdeba'}</i>
                </div>
                <div style={{background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '8px', border: '1px solid var(--border-color)', minHeight: '300px', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)'}}>
                  {selectedWiki.content}
                </div>
              </div>
            ) : (
              <p style={{color: 'var(--text-muted)'}}>Select a wiki article to view.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
