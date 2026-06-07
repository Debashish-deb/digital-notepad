import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, Scale, Trash2 } from 'lucide-react';
import { apiDelete } from '../../api/client.js';
import ResearchAssistPanel from './ResearchAssistPanel.jsx';
import './ResearchAssistPanel.css';

export default function DecisionsPanel({
  dbProjects = [],
  API_URL,
  projectCode = null,
  lockProject = false,
  onOpenProject,
  onNavigate,
  onSelectProject,
  embedded = false,
}) {
  const [decisions, setDecisions] = useState([]);
  const [proj, setProj] = useState(projectCode || dbProjects[0]?.project_code || 'SPACE');
  const [title, setTitle] = useState('');
  const [details, setDetails] = useState('');
  const [rationale, setRationale] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (projectCode) setProj(projectCode);
  }, [projectCode]);

  useEffect(() => {
    if (dbProjects.length > 0 && !dbProjects.some((p) => p.project_code === proj)) {
      setProj(projectCode || dbProjects[0].project_code);
    }
  }, [dbProjects, proj, projectCode]);

  const fetchDecisions = useCallback(async () => {
    setLoading(true);
    try {
      const query = projectCode ? `?project_code=${encodeURIComponent(projectCode)}` : '';
      const res = await fetch(`${API_URL}/decisions${query}`);
      if (res.ok) {
        setDecisions(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [API_URL, projectCode]);

  useEffect(() => {
    fetchDecisions();
  }, [fetchDecisions]);

  const handleDelete = async (decisionId) => {
    if (!window.confirm('Permanently delete this decision registry entry?')) return;
    try {
      await apiDelete(`/decisions/${decisionId}`);
      fetchDecisions();
    } catch (e) {
      console.error(e);
      alert('Failed to delete decision registry entry.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/decisions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_code: lockProject ? projectCode || proj : proj,
          title,
          decision_details: details,
          rationale,
          decider_name: 'debdeba',
        }),
      });
      if (res.ok) {
        setTitle('');
        setDetails('');
        setRationale('');
        fetchDecisions();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const activeProject = lockProject ? projectCode || proj : proj;

  const showAssist = Boolean(projectCode);

  return (
    <div className={`decisions-panel${embedded ? ' decisions-panel--embedded' : ''}`}>
      {embedded && projectCode ? (
        <p className="decisions-panel__lead text-footnote muted">
          Formal decisions for <strong>{projectCode}</strong>. New entries are also logged to the living notebook when the API is available.
        </p>
      ) : null}

      <div className={showAssist ? 'research-assist-panel__layout' : ''}>
      <div className="decisions-panel__grid">
        <div className="panel">
          <h3 className="panel-title">
            <Scale size={18} /> Register decision
          </h3>
          <form onSubmit={handleSubmit} className="stack-lg">
            {!lockProject ? (
              <div className="form-group">
                <label className="form-label">Project</label>
                <select className="form-select" value={proj} onChange={(e) => setProj(e.target.value)}>
                  {dbProjects.map((p) => (
                    <option key={p.project_code} value={p.project_code}>
                      {p.project_code}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <p className="text-footnote muted">Project: {activeProject}</p>
            )}
            <div className="form-group">
              <label className="form-label">Title</label>
              <input type="text" className="form-input" required value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Details</label>
              <textarea className="form-textarea" required value={details} onChange={(e) => setDetails(e.target.value)} style={{ height: '100px' }} />
            </div>
            <div className="form-group">
              <label className="form-label">Rationale</label>
              <input type="text" className="form-input" required value={rationale} onChange={(e) => setRationale(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary">Log decision</button>
          </form>
        </div>

        <div className="panel">
          <h3 className="panel-title">
            <Scale size={18} /> {projectCode && lockProject ? `${projectCode} decisions` : 'Decision register'}
            {loading ? <span className="text-footnote muted"> · loading…</span> : null}
          </h3>
          <div className="feed-scroll">
            {decisions.length === 0 && !loading ? (
              <p className="text-footnote muted">No decisions recorded yet.</p>
            ) : null}
            {decisions.map((d, idx) => (
              <div key={d.decision_id || idx} className="feed-item-accent">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h5 className="feed-item-title" style={{ margin: 0 }}>{d.title}</h5>
                  <button
                    type="button"
                    onClick={() => handleDelete(d.decision_id)}
                    className="decisions-panel__delete"
                    title="Delete decision"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="feed-item-meta" style={{ marginTop: '0.25rem' }}>
                  {d.project_code} · {d.decider_name} · {d.decision_date}
                </div>
                <p className="feed-item-body">{d.decision_details}</p>
                <p className="text-footnote" style={{ marginTop: '0.35rem' }}>Rationale: {d.rationale}</p>
                {onOpenProject && d.project_code && !lockProject ? (
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost decisions-panel__open-project"
                    onClick={() => onOpenProject(d.project_code)}
                  >
                    Open {d.project_code} workspace <ArrowRight size={12} />
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </div>

      {showAssist ? (
        <ResearchAssistPanel
          mode="decisions"
          projectCode={projectCode}
          decisionDraft={{ title, details, rationale }}
          priorDecisions={decisions.filter((d) => d.project_code === projectCode)}
          onApplySuggestion={(parsed) => {
            if (parsed.title) setTitle(parsed.title);
            if (parsed.details) setDetails(parsed.details);
            if (parsed.rationale) setRationale(parsed.rationale);
          }}
          onNavigate={onNavigate}
          onSelectProject={onSelectProject}
        />
      ) : null}
      </div>
    </div>
  );
}
