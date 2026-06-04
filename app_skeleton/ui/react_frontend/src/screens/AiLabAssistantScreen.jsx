import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  BookOpen, 
  UploadCloud, 
  Cpu, 
  Layers, 
  Plus, 
  ArrowRight, 
  Settings 
} from 'lucide-react';
import ChatWidget from '../components/ChatWidget';


export default function AiLabAssistantScreen({ API_URL, activeSubTab, hideChrome = false, dbProjects = [] }) {
  const [subTab, setSubTab] = useState(activeSubTab || 'copilot');

  useEffect(() => {
    if (activeSubTab) setSubTab(activeSubTab);
  }, [activeSubTab]);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);

  // Document Ingest Form
  const [docTitle, setDocTitle] = useState('');
  const [docContent, setDocContent] = useState('');
  const [docProject, setDocProject] = useState('SPACE');
  const [ingestStatus, setIngestStatus] = useState('');

  useEffect(() => {
    if (subTab === 'models') {
      fetchModels();
    }
  }, [subTab]);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/ai-models`);
      if (res.ok) {
        setModels(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleIngest = async (e) => {
    e.preventDefault();
    setIngestStatus('Ingesting and creating vector embeddings...');
    try {
      const res = await fetch(`${API_URL}/ingest-document`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_code: docProject,
          document_title: docTitle,
          content: docContent,
          author: "debdeba"
        })
      });
      if (res.ok) {
        setIngestStatus('Success! Document vectorized and indexed in Qdrant collections.');
        setDocTitle('');
        setDocContent('');
      } else {
        setIngestStatus('Failed to ingest document.');
      }
    } catch (e) {
      setIngestStatus('Connection error: ' + e);
    }
  };

  const menuItems = [
    { id: 'copilot', label: '💬 Chat Copilot' },
    { id: 'prompts', label: '💡 AI Prompt Templates' },
    { id: 'ingest', label: '📤 Ingest RAG Docs' },
    { id: 'models', label: '🤖 Model Registry' }
  ];

  return (
    <div style={{ display: 'flex', gap: hideChrome ? 0 : '2rem', minHeight: hideChrome ? 'auto' : 'calc(100vh - 8rem)' }}>
      {!hideChrome && (
      <div style={{width: '240px', flexShrink: 0, borderRight: '1px solid var(--border-color)', paddingRight: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
        <div style={{fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem', letterSpacing: '0.05em'}}>
          AI ASSISTANT SERVICES
        </div>
        {menuItems.map(item => (
          <button
            key={item.id}
            className={`sidebar-item ${subTab === item.id ? 'active' : ''}`}
            onClick={() => setSubTab(item.id)}
            style={{
              width: '100%', 
              textAlign: 'left', 
              border: 'none', 
              background: 'none', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.75rem',
              cursor: 'pointer',
              borderRadius: '8px',
              padding: '0.75rem 1rem',
              color: subTab === item.id ? '#ffffff' : 'var(--text-secondary)'
            }}
          >
            <span style={{fontSize: '0.9rem'}}>{item.label}</span>
          </button>
        ))}
      </div>
      )}

      <div style={{ flexGrow: 1, minWidth: 0 }}>
        {subTab === 'copilot' && <ChatWidget dbProjects={dbProjects} API_URL={API_URL} />}
        {subTab === 'prompts' && <PromptsLibraryTab />}
        
        {subTab === 'ingest' && (
          <div>
            <div className="page-header" style={{marginBottom: '1.5rem'}}>
              <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary)'}}>Ingest & Index RAG Documents</h2>
              <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Upload SOP protocols or scripts directly into Qdrant vector databases.</p>
            </div>

            <div className="panel" style={{maxWidth: '700px'}}>
              <h3 className="panel-title"><UploadCloud size={18} /> Document Vector Ingestion</h3>
              <form onSubmit={handleIngest} style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                <div className="form-group">
                  <label className="form-label">Scope Project Code</label>
                  <select className="form-select" value={docProject} onChange={(e) => setDocProject(e.target.value)}>
                    <option value="SPACE">SPACE</option>
                    <option value="EyeMT">EyeMT</option>
                    <option value="KRAS">KRAS</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Document Title</label>
                  <input type="text" className="form-input" required value={docTitle} onChange={(e) => setDocTitle(e.target.value)} placeholder="e.g. GeoMx Staining Protocol Batch 4" />
                </div>
                <div className="form-group">
                  <label className="form-label">Raw Text Content</label>
                  <textarea className="form-textarea" required value={docContent} onChange={(e) => setDocContent(e.target.value)} style={{height: '200px'}} placeholder="Paste text content of methodology or notes to index..." />
                </div>
                <button type="submit" className="btn btn-primary">Vectorize & Upload</button>
              </form>

              {ingestStatus && (
                <div style={{marginTop: '1.25rem', padding: '0.75rem 1rem', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', fontSize: '0.9rem', color: 'var(--color-success)'}}>
                  {ingestStatus}
                </div>
              )}
            </div>
          </div>
        )}

        {subTab === 'models' && (
          <div>
            <div className="page-header" style={{marginBottom: '1.5rem'}}>
              <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary)'}}>Deep Learning Model Registry</h2>
              <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Overview of neural network models active on regional cluster servers.</p>
            </div>

            <div className="panel">
              <h3 className="panel-title"><Cpu size={18} /> Active Models</h3>
              {loading ? (
                <p style={{color: 'var(--text-secondary)'}}>Loading registry records...</p>
              ) : models.length === 0 ? (
                <p style={{color: 'var(--text-muted)'}}>No AI models registered in PostgreSQL schemas.</p>
              ) : (
                <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                  {models.map(m => (
                    <div key={m.model_id} style={{border: '1px solid var(--border-color)', padding: '1.25rem', borderRadius: '8px', background: 'rgba(0,0,0,0.2)'}}>
                      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem'}}>
                        <span style={{fontWeight: 700, color: 'var(--color-primary)', fontSize: '1.05rem'}}>🤖 {m.model_name} (v{m.version})</span>
                        <span style={{fontSize: '0.75rem', background: 'rgba(129,140,248,0.12)', color: 'var(--color-accent)', padding: '0.2rem 0.5rem', borderRadius: '4px'}}>{m.framework}</span>
                      </div>
                      <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>{m.description}</p>
                      <div style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>
                        <div>Task Area: <b>{m.task_type}</b></div>
                        <div>Target Environment: <code>{m.target_hardware}</code></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

    </div>
  );
}

// --- PROMPTS LIBRARY ---
function PromptsLibraryTab() {
  const prompts = [
    {
      title: "✍️ Paper Abstract Improver",
      desc: "Paste your raw results, cohort counts, and spatial findings to generate a professional abstract for conferences.",
      prompt: "Act as an expert bioinformatician and clinical-spatial oncology oncologist. Review the following raw research observations and draft a cohesive, highly structured abstract suitable for EACR/AACR. Structure: Background, Methods, Results (include statistics), and Conclusions."
    },
    {
      title: "⚙️ Code Script Refactoring",
      desc: "Provide raw Python or R scripts to optimize memory, enable parallel threads, and format variables.",
      prompt: "Analyze the following Python/R script for cell phenotyping/spatial clustering. Optimize it to handle large data arrays efficiently. Add clear comments, modularize operations, and ensure memory configurations are minimized to prevent OOM errors."
    },
    {
      title: "📓 Logbook Summarizer",
      desc: "Compile multiple short meetings and notes into a clean, formal system notebook entry.",
      prompt: "Given these meeting updates and raw notebook items, synthesize them into a single, clean system of record note. Detail: 1) What was discussed, 2) Major gating or panel exclusions decided, 3) Action checklist items with assignees, and 4) Clear timeline milestones."
    }
  ];

  return (
    <div>
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-accent)'}}>AI Prompt Engineering Library</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Templates to leverage LLMs for improving manuscript writing and cluster analysis.</p>
      </div>

      <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
        {prompts.map((p, idx) => (
          <div key={idx} className="panel">
            <h4 style={{color: '#ffffff', fontSize: '1.1rem', marginBottom: '0.35rem'}}>{p.title}</h4>
            <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>{p.desc}</p>
            <div style={{background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)', position: 'relative'}}>
              <div style={{fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem', fontWeight: 700}}>PROMPT TEMPLATE:</div>
              <p style={{fontFamily: 'var(--font-sans)', fontSize: '0.92rem', color: 'var(--color-primary)', lineHeight: 1.4}}>{p.prompt}</p>
              <button 
                className="btn btn-secondary"
                onClick={() => {
                  navigator.clipboard.writeText(p.prompt);
                  alert("Copied to clipboard!");
                }}
                style={{position: 'absolute', right: '10px', top: '10px', padding: '0.2rem 0.5rem', fontSize: '0.75rem'}}
              >
                Copy Template
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
