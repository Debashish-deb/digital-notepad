import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  BookOpen, 
  Scale, 
  FileText, 
  Edit, 
  Save, 
  BookMarked,
  Calendar,
  Plus,
  LayoutDashboard,
  Database,
  Settings,
  AlertCircle
} from 'lucide-react';

import NotepadWidget from '../components/NotepadWidget';
import DigitalTwinPanel from '../components/DigitalTwinPanel';
import ProjectIntroHeader from '../components/ProjectIntroHeader';
import ProjectTwinStats from '../components/ProjectTwinStats';
import ProjectFolderBrowser from '../components/ProjectFolderBrowser';
import TasksScreen from './TasksScreen';
import { useDigitalTwin } from '../hooks/useDigitalTwin.js';
import { resolveProject, fetchWithTimeout } from '../utils/projectUtils.js';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';

export default function WorkspaceScreen({ projectCode, onBack, API_URL, dbProjects = [] }) {
  const [projectData, setProjectData] = useState(() => resolveProject(projectCode, dbProjects));
  const [projectFolders, setProjectFolders] = useState([]);
  const [workspaceMenu, setWorkspaceMenu] = useState('overview');
  const [activeSub, setActiveSub] = useState({});
  const [checklists, setChecklists] = useState([]);
  const [milestoneScore, setMilestoneScore] = useState(0);
  const [loadError, setLoadError] = useState(null);
  
  const { isOpen: isTaskpadOpen, taskContent, setTaskContent, openTaskpad, closeTaskpad } = useTaskpad();
  const { twin, loading: twinLoading, saving: twinSaving, error: twinError, refresh: refreshTwin, save: saveTwin } = useDigitalTwin(projectCode, API_URL);

  useEffect(() => {
    setProjectData(resolveProject(projectCode, dbProjects));
    fetchProjectDetails();
    fetchChecklists();
    fetchProjectFolders();
  }, [projectCode, dbProjects]);

  const fetchProjectFolders = async () => {
    try {
      const res = await fetch(`${API_URL}/documents/${projectCode}`);
      if (res.ok) {
        const docs = await res.json();
        const folders = new Set();
        docs.forEach(d => {
          if (d.folder_path && d.folder_path !== '.') {
            folders.add(d.folder_path.split('/')[0]);
          }
        });
        setProjectFolders(Array.from(folders).sort());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchProjectDetails = async () => {
    setLoadError(null);
    const localProject = resolveProject(projectCode, dbProjects);
    if (localProject) setProjectData(localProject);

    try {
      const res = await fetchWithTimeout(`${API_URL}/projects`);
      if (res.ok) {
        const data = await res.json();
        const resolved = resolveProject(projectCode, data);
        if (resolved) {
          setProjectData(resolved);
          return;
        }
      }
    } catch (e) {
      console.error(e);
    }

    if (!localProject) {
      setLoadError(`Project "${projectCode}" was not found in the catalog or API.`);
    }
  };

  const fetchChecklists = async () => {
    try {
      const res = await fetch(`${API_URL}/checklists/${projectCode}`);
      if (res.ok) {
        const data = await res.json();
        setChecklists(data);
        if (data.length > 0) {
          const completed = data.filter(c => c.status === 'completed').length;
          setMilestoneScore(Math.round((completed / data.length) * 100));
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (!projectData) {
    return (
      <div className="panel panel-danger">
        <h3 className="text-title-3" style={{ color: 'var(--color-danger)' }}>Project not found</h3>
        <p className="text-body-secondary" style={{ marginBottom: '1rem' }}>{loadError || 'Unable to load project details.'}</p>
        <button className="btn btn-secondary" onClick={onBack}>Back to Portfolio</button>
      </div>
    );
  }

  const menuItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'plan', label: 'Plan', icon: Calendar },
    { id: 'data', label: 'Data', icon: Database },
    { id: 'methods', label: 'Methods', icon: FileText },
    { id: 'writing', label: 'Writing', icon: Edit },
    { id: 'archive', label: 'Archive', icon: BookMarked },
    { id: 'log', label: 'Log', icon: BookOpen }
  ];

  const currentMenu = menuItems.find(m => m.id === workspaceMenu) || menuItems[0];

  const renderSubcategory = () => {
    if (workspaceMenu === 'overview') {
      return (
        <div className="stack-lg">
          <div>
            <div className="page-header-row">
              <div className="page-header">
                <h2 className="text-title-1">{twin?.identity?.project_name || projectCode}</h2>
                <p className="page-lead">Live project overview. Scan the folder to update data.</p>
              </div>
              <button type="button" className="btn btn-secondary btn-sm" onClick={refreshTwin} disabled={twinLoading}>
                {twinLoading ? 'Scanning folder…' : '↻ Scan project folder'}
              </button>
            </div>
            {twinLoading && !twin && <div className="panel"><p className="text-loading">Loading scanned project record…</p></div>}
            {twin && <ProjectIntroHeader twin={twin} />}
          </div>

          {twin ? (
            <DigitalTwinPanel
              twin={twin}
              onSave={saveTwin}
              saving={twinSaving}
              section="overview"
              projectCode={projectCode}
              API_URL={API_URL}
            />
          ) : null}

          <ProjectFolderBrowser twin={twin} projectCode={projectCode} API_URL={API_URL} projectName={twin?.identity?.project_name || projectData?.project_name} />
          {twin ? <ProjectTwinStats twin={twin} /> : null}
          <EditMetadataTab projectData={projectData} fetchProjectDetails={fetchProjectDetails} API_URL={API_URL} />
          
          <hr className="divider" />
          <h3 className="text-title-2">Project Team & References</h3>
          <ProjectMembersTab projectData={projectData} twin={twin} />
        </div>
      );
    } 
    else if (workspaceMenu === 'plan') {
      return (
        <div className="stack-lg">
          <TasksScreen projectCode={projectCode} dbProjects={dbProjects} API_URL={API_URL} hideProjectSelect />
          <ChecklistTab projectCode={projectCode} checklists={checklists} fetchChecklists={fetchChecklists} API_URL={API_URL} />
          <hr className="divider" />
          <DecisionsTab projectCode={projectCode} API_URL={API_URL} />
        </div>
      );
    }
    else if (workspaceMenu === 'data') {
      return (
        <div className="stack-lg">
          <DataCatalogTab projectCode={projectCode} API_URL={API_URL} twin={twin} twinLoading={twinLoading} twinSaving={twinSaving} saveTwin={saveTwin} />
          <hr className="divider" />
          <ProjectDocumentsTab projectCode={projectCode} API_URL={API_URL} />
        </div>
      );
    }
    else if (workspaceMenu === 'methods') {
      return (
        <div className="stack-lg">
          <CombinedReportTab projectCode={projectCode} API_URL={API_URL} twin={twin} twinLoading={twinLoading} twinSaving={twinSaving} refreshTwin={refreshTwin} saveTwin={saveTwin} />
          <hr className="divider" />
          <NotepadTab projectCode={projectCode} API_URL={API_URL} />
        </div>
      );
    }
    else if (workspaceMenu === 'writing') {
      return <AbstractsTab twin={twin} twinLoading={twinLoading} twinSaving={twinSaving} saveTwin={saveTwin} projectCode={projectCode} API_URL={API_URL} />;
    }
    else if (workspaceMenu === 'archive') {
      return <div className="panel text-empty"><p>Archive modules are in development.</p></div>;
    }
    else if (workspaceMenu === 'log') {
      return <NotebookLogsTab projectCode={projectCode} API_URL={API_URL} />;
    }

    return (
      <div className="panel text-empty" style={{ padding: '2rem' }}>
        <p>No backend integration yet for: {currentMenu.label}</p>
      </div>
    );
  };

  return (
    <div className="workspace-layout">
      {/* Sub-navigation Menu */}
      <div className="workspace-nav">
        <button className="btn btn-secondary workspace-nav-back" onClick={onBack}>
          <ArrowLeft size={16} /> Back to Portfolio
        </button>

        <div className="workspace-nav-label">Workspace modules</div>

        {menuItems.map(item => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`workspace-nav-item ${workspaceMenu === item.id ? 'active' : ''}`}
              onClick={() => setWorkspaceMenu(item.id)}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </button>
          );
        })}

        <div className="workspace-context-card">
          <div className="workspace-context-code">{projectCode}</div>
          {twin?.identity?.project_lead && (
            <div className="workspace-context-meta">Lead: {twin.identity.project_lead}</div>
          )}
        </div>
      </div>

      {/* Main Workspace Content Pane */}
      {/* Main Workspace Content Pane */}
      <div className="workspace-main" style={{ position: 'relative' }}>
        {renderSubcategory()}
      </div>

      {/* FAB Taskpad Button */}
      <button 
        className="btn btn-primary" 
        style={{
          position: 'fixed', bottom: '2rem', right: '2rem', 
          borderRadius: '50px', padding: '1rem',
          boxShadow: '0 8px 16px rgba(0,0,0,0.3)',
          zIndex: 1000, display: 'flex', alignItems: 'center', gap: '0.5rem'
        }}
        onClick={() => openTaskpad()}
      >
        <Plus size={20} />
        <span style={{ fontWeight: 600 }}>Taskpad</span>
      </button>

      {/* Taskpad Side Sheet */}
      {isTaskpadOpen && (
        <div style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, width: '400px',
          background: 'var(--panel-bg)', borderLeft: '1px solid var(--border-color)',
          boxShadow: '-10px 0 30px rgba(0,0,0,0.5)', zIndex: 1001,
          display: 'flex', flexDirection: 'column', padding: '1.5rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h3 style={{ margin: 0, color: 'var(--color-primary)' }}>Quick Capture</h3>
            <button className="btn btn-sm btn-secondary" onClick={closeTaskpad}>Close</button>
          </div>
          <div className="form-group">
            <label className="form-label">Target Area</label>
            <select className="form-select">
              {menuItems.map(m => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
            <label className="form-label">Note / Task / Status Update</label>
            <textarea 
              className="form-textarea" 
              style={{ flexGrow: 1, resize: 'none' }} 
              placeholder="Type here..."
              value={taskContent}
              onChange={(e) => setTaskContent(e.target.value)}
            ></textarea>
          </div>
          <button className="btn btn-primary" onClick={() => { alert('Saved to Taskpad!'); closeTaskpad(); }}>
            Save Entry
          </button>
        </div>
      )}
    </div>
  );
}

/* ========================================================================= */
/* WORKSPACE MODULE COMPONENTS                                               */
/* ========================================================================= */

// --- COMBINED REPORT MODULE ---
function CombinedReportTab({ projectCode, API_URL, twin, twinLoading, twinSaving, refreshTwin, saveTwin }) {
  const [reportChapter, setReportChapter] = useState('protocols');
  const [rawReport, setRawReport] = useState(null);
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    if (!showRaw) return;
    fetch(`${API_URL}/api/project-files/report/${projectCode}`)
      .then((res) => (res.ok ? res.json() : null))
      .then(setRawReport)
      .catch(() => setRawReport(null));
  }, [projectCode, API_URL, showRaw]);

  const sectionMap = { protocols: 'protocols', pipelines: 'content', analytics: 'timeline' };

  if (twinLoading && !twin) {
    return <div className="text-loading">Building structured digital record from project files…</div>;
  }

  return (
    <div>
      <div className="page-header-row">
        <div className="module-page-header">
          <h2 className="text-title-1">Digital Research Record</h2>
          <p className="page-lead">Grouped, deduplicated project data. Click Edit to modify — Save to persist.</p>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={refreshTwin}>↻ Reprocess from disk</button>
      </div>

      <div className="tab-bar">
        {['protocols', 'pipelines', 'analytics'].map(chap => (
          <button
            key={chap}
            className={`btn btn-sm ${reportChapter === chap ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setReportChapter(chap)}
          >
            {chap === 'protocols' ? '🧪 Protocols' : chap === 'pipelines' ? '🖼️ Files & Figures' : '📊 Activity'}
          </button>
        ))}
        <button type="button" className={`btn ${showRaw ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setShowRaw((v) => !v)}>
          {showRaw ? 'Hide raw files' : 'View raw source files'}
        </button>
      </div>

      {twin ? (
        <DigitalTwinPanel
          twin={twin}
          onSave={saveTwin}
          saving={twinSaving}
          section={sectionMap[reportChapter] || 'protocols'}
          projectCode={projectCode}
          API_URL={API_URL}
        />
      ) : (
        <div className="panel"><p className="muted">Digital record unavailable. Use raw source view or reprocess.</p></div>
      )}

      {showRaw && rawReport && (
        <div className="panel" style={{ marginTop: '1.5rem' }}>
          <h3 className="panel-title">Raw Source Files (reference only)</h3>
          <div className="markdown-body" style={{ whiteSpace: 'pre-wrap', maxHeight: '400px', overflow: 'auto' }}>
            {rawReport.overview?.slice(0, 8000) || 'No overview files found.'}
          </div>
        </div>
      )}
    </div>
  );
}

// --- LOGBOOK TIMELINE MODULE ---
function LogbookTimelineTab({ twin, twinLoading, twinSaving, saveTwin, projectCode, API_URL }) {
  return (
    <div>
      <div className="module-page-header">
        <h2 className="text-title-1">Chronological Logbook</h2>
        <p className="page-lead">Deduplicated timeline from project logs — filter by category.</p>
      </div>

      {twinLoading && !twin ? (
        <div className="text-loading">Loading structured timeline…</div>
      ) : twin ? (
        <DigitalTwinPanel twin={twin} onSave={saveTwin} saving={twinSaving} section="timeline" projectCode={projectCode} API_URL={API_URL} />
      ) : (
        <p className="muted">No digital timeline available.</p>
      )}
    </div>
  );
}

// --- NOTEPAD MODULE ---
function NotepadTab({ projectCode, API_URL }) {
  const [fileList, setFileList] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchFileList();
  }, [projectCode]);

  const fetchFileList = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/project-files/list/${projectCode}`);
      if (res.ok) {
        setFileList(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="module-page-header">
        <h2 className="text-title-1">Folder Interactive Notepad</h2>
        <p className="page-lead">Access and edit documentation, experimental notes, and logs directly from your project directory.</p>
      </div>

      <div className="panel">
        {loading ? (
          <div style={{color: 'var(--text-secondary)'}}>Loading folder structure...</div>
        ) : (
          <NotepadWidget 
            projectCode={projectCode} 
            fileList={fileList} 
            fetchReport={() => {}} 
            API_URL={API_URL} 
          />
        )}
      </div>
    </div>
  );
}

// --- ABSTRACTS MODULE ---
function AbstractsTab({ twin, twinLoading, twinSaving, saveTwin, projectCode, API_URL }) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [rawContent, setRawContent] = useState(null);

  const items = twin?.outputs?.length
    ? twin.outputs
    : [...(twin?.dissemination || []), ...(twin?.publications || [])];

  useEffect(() => {
    setSelectedIdx(0);
    setRawContent(null);
  }, [projectCode, twin]);

  useEffect(() => {
    if (!items[selectedIdx]?.source_file) {
      setRawContent(null);
      return;
    }
    fetch(`${API_URL}/api/project-files/read?project_code=${encodeURIComponent(projectCode)}&relative_path=${encodeURIComponent(items[selectedIdx].source_file)}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setRawContent(data?.content || null))
      .catch(() => setRawContent(null));
  }, [selectedIdx, items, projectCode, API_URL]);

  return (
    <div>
      <div className="module-page-header">
        <h2 className="text-title-1">Paper Abstracts & Dissemination</h2>
        <p className="page-lead">Merged publications and abstracts — edit to correct, then Save.</p>
      </div>

      {twinLoading && !twin ? (
        <div className="text-loading">Loading abstract registry…</div>
      ) : !twin || items.length === 0 ? (
        <p className="text-footnote">No scientific abstracts indexed for this project.</p>
      ) : (
        <>
          <DigitalTwinPanel twin={twin} onSave={saveTwin} saving={twinSaving} section="abstracts" projectCode={projectCode} API_URL={API_URL} />
          <div className="panel" style={{ marginTop: '1rem' }}>
            <label className="form-label">Preview source document:</label>
            <select
              className="form-select"
              value={selectedIdx}
              onChange={(e) => setSelectedIdx(Number(e.target.value))}
              style={{ marginBottom: '1rem' }}
            >
              {items.map((ab, idx) => (
                <option key={idx} value={idx}>{ab.title}</option>
              ))}
            </select>
            {rawContent && (
              <div className="digital-twin-source-preview">
                <h4>{items[selectedIdx]?.source_file}</h4>
                <div className="markdown-body">{rawContent.slice(0, 6000)}{rawContent.length > 6000 ? '…' : ''}</div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// --- CHECKLIST MODULE ---
function ChecklistTab({ projectCode, checklists, fetchChecklists, API_URL }) {
  const categories = Array.from(new Set(checklists.map(c => c.category))).sort();

  const handleToggle = async (item) => {
    const nextStatus = item.status === 'completed' ? 'pending' : 'completed';
    try {
      const res = await fetch(`${API_URL}/checklists/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          checklist_id: item.checklist_id,
          status: nextStatus,
          username: "debdeba"
        })
      });
      if (res.ok) {
        fetchChecklists();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      <div className="module-page-header">
        <h2 className="text-title-1">Onboarding Milestone Checklists</h2>
        <p className="page-lead">Follow checklist criteria to register cell masks and image QC metrics.</p>
      </div>

      <div className="panel">
        {checklists.length === 0 ? (
          <p style={{color: 'var(--text-muted)'}}>No milestone checklist entries registered.</p>
        ) : (
          categories.map(cat => (
            <div key={cat} style={{marginBottom: '1.5rem'}}>
              <h4 style={{color: 'var(--color-primary)', fontSize: '1rem', textTransform: 'uppercase', marginBottom: '0.75rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.25rem'}}>{cat}</h4>
              <div style={{display: 'flex', flexDirection: 'column'}}>
                {checklists.filter(c => c.category === cat).map(item => (
                  <div key={item.checklist_id} className="checklist-item">
                    <input 
                      type="checkbox" 
                      className="checklist-checkbox"
                      checked={item.status === 'completed'}
                      onChange={() => handleToggle(item)}
                    />
                    <div style={{flexGrow: 1}}>
                      <div style={{fontWeight: 600, fontSize: '0.95rem'}}>{item.item_name}</div>
                      <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)'}}>{item.description}</div>
                    </div>
                    {item.checked_at && (
                      <span style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>✓ Checked {item.checked_at.slice(0, 10)}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// --- NOTEBOOK LOGS MODULE ---
function NotebookLogsTab({ projectCode, API_URL }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchLogs();
  }, [projectCode]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/notebook?project_code=${projectCode}`);
      if (res.ok) {
        setEntries(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (entryId) => {
    if (!window.confirm("Are you sure you want to permanently delete this notebook entry? This action cannot be undone.")) return;
    try {
      const res = await fetch(`${API_URL}/notebook/${entryId}`, { method: 'DELETE' });
      if (res.ok) {
        alert("Notebook entry permanently deleted.");
        fetchLogs();
      } else {
        alert("Failed to delete notebook entry.");
      }
    } catch (e) {
      console.error(e);
      alert("Failed to delete notebook entry.");
    }
  };

  return (
    <div>
      <div className="module-page-header">
        <h2 className="text-title-1">Lab Notebook Logs</h2>
        <p className="page-lead">System logbook entries containing research conclusions and next steps.</p>
      </div>

      <div className="panel">
        {loading ? (
          <p style={{color: 'var(--text-secondary)'}}>Loading notebook logs...</p>
        ) : entries.length === 0 ? (
          <p style={{color: 'var(--text-muted)'}}>No notebook entries recorded for this project.</p>
        ) : (
          <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
            {entries.map(e => (
              <div key={e.entry_id} style={{border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem', background: 'rgba(255,255,255,0.01)'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
                  <span style={{fontWeight: 600, color: 'var(--color-primary)'}}>{e.title} (v{e.version})</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>{e.created_at.replace('T', ' ').slice(0, 16)}</span>
                    <button type="button" className="btn btn-secondary btn-sm" style={{ borderColor: 'var(--color-danger)', color: 'var(--color-danger)', background: 'transparent', padding: '1px 6px', fontSize: '0.75rem' }} onClick={() => handleDelete(e.entry_id)}>
                      Delete
                    </button>
                  </div>
                </div>
                <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', marginBottom: '0.75rem'}}>{e.content}</p>
                
                {e.conclusions && (
                  <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '4px', marginTop: '0.5rem'}}>
                    <b>Conclusions:</b> {e.conclusions}
                  </div>
                )}
                {e.issues_found && (
                  <div style={{fontSize: '0.85rem', color: 'var(--color-danger)', background: 'rgba(248,113,113,0.05)', padding: '0.5rem', borderRadius: '4px', marginTop: '0.5rem'}}>
                    ⚠️ <b>Issues Found:</b> {e.issues_found}
                  </div>
                )}
                {e.next_steps && (
                  <div style={{fontSize: '0.85rem', color: 'var(--color-accent)', background: 'rgba(129,140,248,0.05)', padding: '0.5rem', borderRadius: '4px', marginTop: '0.5rem'}}>
                    💡 <b>Next Steps:</b> {e.next_steps}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- DECISIONS MODULE ---
function DecisionsTab({ projectCode, API_URL }) {
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDecisions();
  }, [projectCode]);

  const fetchDecisions = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/decisions`);
      if (res.ok) {
        const data = await res.json();
        setDecisions(data.filter(d => d.project_code === projectCode));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (decisionId) => {
    if (!window.confirm("Are you sure you want to permanently delete this decision registry entry? This action cannot be undone.")) return;
    try {
      const res = await fetch(`${API_URL}/decisions/${decisionId}`, { method: 'DELETE' });
      if (res.ok) {
        alert("Decision registry entry deleted.");
        fetchDecisions();
      } else {
        alert("Failed to delete decision registry entry.");
      }
    } catch (e) {
      console.error(e);
      alert("Failed to delete decision registry entry.");
    }
  };

  return (
    <div>
      <div className="module-page-header">
        <h2 className="text-title-1">Decisions Registry Ledger</h2>
        <p className="page-lead">Formally logged research decisions regarding experimental configurations.</p>
      </div>

      <div className="panel">
        {loading ? (
          <div style={{color: 'var(--text-secondary)'}}>Loading decisions...</div>
        ) : decisions.length === 0 ? (
          <p style={{color: 'var(--text-muted)'}}>No decisions logged for this project.</p>
        ) : (
          <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
            {decisions.map(d => (
              <div key={d.decision_id} style={{borderLeft: '4px solid var(--color-success)', background: 'rgba(52,211,153,0.03)', padding: '1rem', borderRadius: '0 8px 8px 0'}}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h5 style={{fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-primary)', margin: 0}}>🎯 {d.title}</h5>
                  <button type="button" className="btn btn-secondary btn-sm" style={{ borderColor: 'var(--color-danger)', color: 'var(--color-danger)', background: 'transparent', padding: '1px 6px', fontSize: '0.75rem' }} onClick={() => handleDelete(d.decision_id)}>
                    Delete
                  </button>
                </div>
                <div style={{fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.4rem', marginTop: '0.25rem'}}>
                  Decided By: <b>{d.decider_name}</b> | Date: <i>{d.decision_date}</i>
                </div>
                <p style={{fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '0.25rem'}}>{d.decision_details}</p>
                <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)'}}><i>Rationale:</i> {d.rationale}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- DATA CATALOG MODULE ---
function DataCatalogTab({ projectCode, API_URL, twin, twinLoading, twinSaving, saveTwin }) {
  const [folders, setFolders] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCatalog();
  }, [projectCode]);

  const fetchCatalog = async () => {
    setLoading(true);
    try {
      const rf = await fetch(`${API_URL}/folders?project_code=${projectCode}`);
      if (rf.ok) setFolders(await rf.json());
      const rd = await fetch(`${API_URL}/datasets?project_code=${projectCode}`);
      if (rd.ok) setDatasets(await rd.json());
      const rr = await fetch(`${API_URL}/pipeline_runs?project_code=${projectCode}`);
      if (rr.ok) setRuns(await rr.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const hasDbCatalog = folders.length > 0 || datasets.length > 0 || runs.length > 0;

  return (
    <div>
      <div className="module-page-header">
        <h2 className="text-title-1">Data Folders & Pipeline Runs</h2>
        <p className="page-lead">Storage paths, repositories, and modalities — grouped and editable.</p>
      </div>

      {twinLoading && !twin ? (
        <div style={{color: 'var(--text-secondary)', marginBottom: '1rem'}}>Loading digital catalog…</div>
      ) : twin ? (
        <>
          <ProjectFolderBrowser
            twin={twin}
            projectCode={projectCode}
            API_URL={API_URL}
            projectName={twin?.identity?.project_name}
          />
          <DigitalTwinPanel twin={twin} onSave={saveTwin} saving={twinSaving} section="catalog" projectCode={projectCode} API_URL={API_URL} />
        </>
      ) : null}

      {hasDbCatalog && (
        <>
          <h3 className="panel-title" style={{ marginTop: '1.5rem' }}>Database Registry</h3>
          {loading ? (
            <div style={{color: 'var(--text-secondary)'}}>Loading database catalogs...</div>
          ) : (
            <div className="grid-3col">
          <div className="panel">
            <h4 style={{fontSize: '1rem', color: '#ffffff', marginBottom: '1rem'}}>📁 Folders Catalog</h4>
            {folders.length === 0 ? <p style={{color: 'var(--text-muted)', fontSize: '0.85rem'}}>None registered.</p> : (
              <div style={{fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
                {folders.map((f, idx) => (
                  <div key={idx} style={{background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '4px'}}>
                    <b>{f.folder_purpose}:</b> <code style={{color: 'var(--color-primary)', wordBreak: 'break-all'}}>{f.absolute_path}</code>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="panel">
            <h4 style={{fontSize: '1rem', color: '#ffffff', marginBottom: '1rem'}}>🧪 Datasets Inventory</h4>
            {datasets.length === 0 ? <p style={{color: 'var(--text-muted)', fontSize: '0.85rem'}}>None registered.</p> : (
              <div style={{fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
                {datasets.map((d, idx) => (
                  <div key={idx} style={{background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '4px'}}>
                    <b>{d.dataset_name}:</b> <span style={{color: 'var(--color-success)'}}>{d.data_format}</span> ({d.sample_count} samples)
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="panel">
            <h4 style={{fontSize: '1rem', color: '#ffffff', marginBottom: '1rem'}}>🚀 Pipeline Runs</h4>
            {runs.length === 0 ? <p style={{color: 'var(--text-muted)', fontSize: '0.85rem'}}>None registered.</p> : (
              <div style={{fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
                {runs.map((r, idx) => (
                  <div key={idx} style={{background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '4px'}}>
                    <b>Run {r.run_id.slice(0, 8)}:</b> Status: <span style={{color: r.status === 'completed' ? 'var(--color-success)' : 'var(--color-warning)'}}>{r.status}</span>
                    <div>Script: <code>{r.script_name}</code></div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
          )}
        </>
      )}
    </div>
  );
}

// --- EDIT METADATA MODULE ---
function EditMetadataTab({ projectData, fetchProjectDetails, API_URL }) {
  const [shortTitle, setShortTitle] = useState(projectData.project_short_title || '');
  const [question, setQuestion] = useState(projectData.research_question || '');
  const [type, setType] = useState(projectData.project_type || 'spatial_profiling');
  const [priority, setPriority] = useState(projectData.priority || 'medium');
  const [ethics, setEthics] = useState(projectData.ethics_approval_reference || '');
  const [blockers, setBlockers] = useState(projectData.current_blockers || '');
  const [nextActions, setNextActions] = useState(projectData.next_actions || '');
  const [summary, setSummary] = useState(projectData.project_summary || '');
  const [latestUpdate, setLatestUpdate] = useState(projectData.latest_update || '');
  const [updating, setUpdating] = useState(false);

  const handleUpdate = async (e) => {
    e.preventDefault();
    setUpdating(true);
    try {
      const res = await fetch(`${API_URL}/projects/${projectData.project_code}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_short_title: shortTitle,
          research_question: question,
          project_type: type,
          priority: priority,
          ethics_approval_reference: ethics,
          current_blockers: blockers,
          next_actions: nextActions,
          project_summary: summary,
          latest_update: latestUpdate
        })
      });
      if (res.ok) {
        alert("Project registry metadata successfully updated!");
        fetchProjectDetails();
      } else {
        alert("Failed to update registry.");
      }
    } catch (err) {
      alert("Error: " + err);
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div>
      <div className="module-page-header">
        <h2 className="text-title-1">Edit Project Registry Settings</h2>
        <p className="page-lead">Configure the database descriptors, ethics permits, and study priority status.</p>
      </div>

      <div className="panel">
        <form onSubmit={handleUpdate} style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
          <div className="grid-2col" style={{marginBottom: 0}}>
            <div className="form-group">
              <label className="form-label">Short Title</label>
              <input type="text" className="form-input" value={shortTitle} onChange={(e) => setShortTitle(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Ethics Reference</label>
              <input type="text" className="form-input" value={ethics} onChange={(e) => setEthics(e.target.value)} />
            </div>
          </div>

          <div className="grid-2col" style={{marginBottom: 0}}>
            <div className="form-group">
              <label className="form-label">Project Type</label>
              <select className="form-select" value={type} onChange={(e) => setType(e.target.value)}>
                <option value="spatial_profiling">Spatial Profiling</option>
                <option value="clinical_trial">Clinical Trial</option>
                <option value="pilot_study">Pilot Study</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Priority</label>
              <select className="form-select" value={priority} onChange={(e) => setPriority(e.target.value)}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Research Question</label>
            <textarea className="form-textarea" value={question} onChange={(e) => setQuestion(e.target.value)} />
          </div>

          <div className="form-group">
            <label className="form-label">Project Summary</label>
            <textarea className="form-textarea" value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>

          <div className="grid-2col" style={{marginBottom: 0}}>
            <div className="form-group">
              <label className="form-label">Current Blockers</label>
              <textarea className="form-textarea" value={blockers} onChange={(e) => setBlockers(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Next Actions</label>
              <textarea className="form-textarea" value={nextActions} onChange={(e) => setNextActions(e.target.value)} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Latest Activity Update</label>
            <input type="text" className="form-input" value={latestUpdate} onChange={(e) => setLatestUpdate(e.target.value)} />
          </div>

          <button type="submit" className="btn btn-primary" disabled={updating}>
            {updating ? "Saving revisions..." : "Update Project & Log Action"}
          </button>
        </form>
      </div>
    </div>
  );
}

function ProjectDocumentsTab({ projectCode, API_URL, folderFilters }) {
  const [docs, setDocs] = useState([]);
  const [error, setError] = useState(null);
  const [ingesting, setIngesting] = useState(false);
  const [ingestMessage, setIngestMessage] = useState("");
  const [openFolders, setOpenFolders] = useState({});
  const [previewFile, setPreviewFile] = useState(null);

  const fetchDocuments = () => {
    if (!API_URL) return;
    fetch(`${API_URL}/api/documents/registry?corpus=project_workspace&limit=500`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('registry unavailable'))))
      .then((data) => {
        const filtered = (data.documents || []).filter(
          (d) => (d.metadata?.project_code || d.project_code || '').toUpperCase() === projectCode.toUpperCase(),
        );
        setDocs(filtered);
      })
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    fetchDocuments();
  }, [API_URL, projectCode]);

  const handleIngest = async () => {
    setIngesting(true);
    setIngestMessage("Scanning project folder & synchronizing...");
    try {
      const res = await fetch(`${API_URL}/api/projects/${projectCode}/knowledge/ingest`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setIngestMessage(`Success: ${data.message} (${data.extracted_chunks} chunks)`);
        fetchDocuments();
      } else {
        setIngestMessage(`Error: ${data.detail || 'Failed to ingest'}`);
      }
    } catch (e) {
      setIngestMessage(`Error: ${e.message}`);
    } finally {
      setIngesting(false);
    }
  };

  const toggleFolder = (folder) => {
    setOpenFolders(prev => ({ ...prev, [folder]: !prev[folder] }));
  };

  // Group by folder
  const groupedDocs = docs.reduce((acc, doc) => {
    let folder = doc.folder_path || doc.metadata?.folder_path || '/';
    
    let shouldInclude = true;
    if (folderFilters && folderFilters.length > 0) {
      shouldInclude = folderFilters.some(filter => {
        if (filter === '.' || filter === '/') {
          return folder === '.' || folder === '/';
        }
        return folder.startsWith(filter);
      });
    }

    if (!shouldInclude) return acc;

    if (!acc[folder]) acc[folder] = [];
    acc[folder].push(doc);
    return acc;
  }, {});

  const isFiltered = folderFilters && folderFilters.length > 0;

  return (
    <div>
      {!isFiltered && (
        <div className="module-page-header">
          <h2 className="text-title-1">Assimilated Knowledge Base</h2>
          <p className="page-lead">Searchable, semantically indexed documents and media from the physical project workspace.</p>
        </div>
      )}

      {!isFiltered && (
        <div className="panel" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 className="panel-title" style={{ margin: 0 }}>Database Synchronization</h3>
              <p className="text-footnote" style={{ marginTop: '0.25rem' }}>Extract text and index visual media from disk.</p>
            </div>
            <button 
              className="btn btn-primary" 
              onClick={handleIngest} 
              disabled={ingesting}
            >
              {ingesting ? 'Processing...' : '↻ Synchronize Folder to Database'}
            </button>
          </div>
          {ingestMessage && (
            <div className="text-callout" style={{ marginTop: '1rem' }}>
              {ingestMessage}
            </div>
          )}
        </div>
      )}

      {error && <p className="text-footnote text-danger">Document registry: {error}</p>}
      
      {!docs.length && !error && (
        <div className="panel text-empty" style={{ padding: '2rem' }}>
          <p>No assimilated documents for this project yet. Click Synchronize above to extract knowledge.</p>
        </div>
      )}

      {Object.keys(groupedDocs).sort().map(folder => {
        // When filtered (e.g. looking specifically at 'Data & Figures'), 
        // strip that leading path out of the header so we only see 'Data/1. t-CycIF' instead of 'Data & Figures/Data/...'
        let displayName = folder === '.' ? 'Root Directory' : folder;
        if (isFiltered && folderFilters[0] !== '.' && folderFilters[0] !== '/') {
          const filterPrefix = folderFilters[0] + '/';
          if (folder.startsWith(filterPrefix)) {
            displayName = folder.substring(filterPrefix.length);
          } else if (folder === folderFilters[0]) {
            displayName = folder.split('/').pop() || folder;
          }
        }

        return (
        <div key={folder} className="panel" style={{ marginBottom: '1rem' }}>
          <div 
            style={{ display: 'flex', justifyContent: 'space-between', cursor: 'pointer' }}
            onClick={() => toggleFolder(folder)}
          >
            <h4 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)' }}>
              📁 {displayName}
            </h4>
            <span className="text-footnote">{groupedDocs[folder].length} files</span>
          </div>
          
          {openFolders[folder] !== false && (
            <div style={{ marginTop: '1rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
                {groupedDocs[folder].map(d => {
                  const type = d.source_type?.toLowerCase() || 'txt';
                  const isVisual = ['pdf', 'pptx'].includes(type);
                  const isPdf = type === 'pdf';
                  const isPptx = type === 'pptx';
                  const icon = isPdf ? '📄' : isPptx ? '📊' : '📝';
                  const bg = isPdf ? 'rgba(239, 68, 68, 0.1)' : isPptx ? 'rgba(249, 115, 22, 0.1)' : 'var(--mac-bg-1)';
                  
                  return (
                    <div 
                      key={d.document_code || d.document_id} 
                      className="panel" 
                      onClick={() => isVisual && setPreviewFile(d)}
                      style={{ 
                        cursor: isVisual ? 'pointer' : 'default', 
                        display: 'flex', 
                        flexDirection: 'column', 
                        padding: '1rem',
                      }}
                    >
                      <div style={{ height: '80px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: bg, borderRadius: '8px', marginBottom: '1rem' }}>
                        <span style={{ fontSize: '2.5rem' }}>{icon}</span>
                      </div>
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                        <h4 style={{ margin: 0, fontSize: '0.9rem', wordBreak: 'break-word', lineHeight: 1.2 }}>{d.title || d.document_code}</h4>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem' }}>
                          <span className="text-footnote" style={{ color: 'var(--mac-muted)', fontWeight: 'bold' }}>
                            {type.toUpperCase()}
                          </span>
                          {!isVisual && d.chunk_count != null && (
                            <span className="text-footnote" style={{ color: 'var(--mac-muted)' }}>
                              {d.chunk_count} chunks
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )})}

      {previewFile && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', 
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', zIndex: 9999, 
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div className="panel" style={{ width: '85%', height: '85%', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', borderBottom: '1px solid var(--mac-border)', background: 'var(--mac-bg-1)' }}>
              <h3 style={{ margin: 0 }}>{previewFile.title}</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setPreviewFile(null)}>Close Preview</button>
            </div>
            <div style={{ flex: 1, background: '#f5f5f5', overflow: 'hidden' }}>
              {previewFile.source_type?.toLowerCase() === 'pdf' ? (
                 <iframe 
                   title={previewFile.title}
                   src={`${API_URL}/api/project-files/serve?project_code=${encodeURIComponent(projectCode)}&relative_path=${encodeURIComponent(previewFile.metadata?.relative_path)}`} 
                   style={{ width: '100%', height: '100%', border: 'none' }} 
                 />
              ) : previewFile.source_type?.toLowerCase() === 'pptx' ? (
                 <div style={{ textAlign: 'center', marginTop: '15%' }}>
                   <span style={{ fontSize: '4rem' }}>📊</span>
                   <h2 style={{ color: 'var(--mac-ink)' }}>PowerPoint Presentation</h2>
                   <p className="text-lead" style={{ marginBottom: '2rem' }}>Cannot preview native PPTX in the browser securely.</p>
                   <a className="btn btn-primary" href={`${API_URL}/api/project-files/serve?project_code=${encodeURIComponent(projectCode)}&relative_path=${encodeURIComponent(previewFile.metadata?.relative_path)}`} download>
                     Download & Open Presentation
                   </a>
                 </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ProjectDataTab({ projectCode, twin }) {
  const datasets = twin?.data_catalog?.datasets || twin?.datasets || [];
  return (
    <div className="panel">
      <h3 className="panel-title">Data & datasets — {projectCode}</h3>
      {datasets.length ? (
        <ul className="simple-list">
          {datasets.map((ds, i) => (
            <li key={ds.id || i}>{ds.name || ds.label || JSON.stringify(ds)}</li>
          ))}
        </ul>
      ) : (
        <p className="text-footnote">Open Data Catalog for full dataset matrix, or process project files to populate the twin.</p>
      )}
    </div>
  );
}

function ProjectMembersTab({ projectData, twin }) {
  const members = twin?.team || projectData?.members || [];
  const lead = projectData?.project_lead;
  return (
    <div className="panel">
      <h3 className="panel-title">Project members</h3>
      {lead && <p><strong>Lead:</strong> {lead}</p>}
      {members.length ? (
        <ul className="simple-list">
          {members.map((m, i) => (
            <li key={m.email || m.name || i}>{m.name || m.full_name || m.email || String(m)}</li>
          ))}
        </ul>
      ) : (
        <p className="text-footnote">Member roster comes from the project catalog and digital twin metadata.</p>
      )}
    </div>
  );
}
