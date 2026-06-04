import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import { Scale } from 'lucide-react';

export default function DecisionsScreen({ dbProjects, API_URL, hideHeader = false }) {
  const [decisions, setDecisions] = useState([]);
  const [proj, setProj] = useState(dbProjects[0]?.project_code || 'SPACE');
  const [title, setTitle] = useState('');
  const [details, setDetails] = useState('');
  const [rationale, setRationale] = useState('');

  useEffect(() => {
    fetchDecisions();
  }, []);

  useEffect(() => {
    if (dbProjects.length > 0 && !dbProjects.some((p) => p.project_code === proj)) {
      setProj(dbProjects[0].project_code);
    }
  }, [dbProjects, proj]);

  const fetchDecisions = async () => {
    try {
      const res = await fetch(`${API_URL}/decisions`);
      if (res.ok) {
        setDecisions(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/decisions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_code: proj,
          title,
          decision_details: details,
          rationale,
          decider_name: "debdeba"
        })
      });
      if (res.ok) {
        alert("Decision registry entry saved!");
        setTitle('');
        setDetails('');
        setRationale('');
        fetchDecisions();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      {!hideHeader && (
        <div className="page-header">
          <h1 className="page-title-gradient">Research Decisions Ledger</h1>
          <p className="page-subtitle">Registry of project scope definitions, antibody design panel configurations, and sample exclusions.</p>
        </div>
      )}

      <div className="grid-2col">
        <div className="panel">
          <h3 className="panel-title"><Scale size={18} /> Register Decision</h3>
          <form onSubmit={handleSubmit} className="stack-lg">
            <div className="form-group">
              <label className="form-label">Project Code</label>
              <select className="form-select" value={proj} onChange={(e) => setProj(e.target.value)}>
                {dbProjects.map(p => (
                  <option key={p.project_code} value={p.project_code}>{p.project_code}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Title</label>
              <input type="text" className="form-input" required value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Details</label>
              <textarea className="form-textarea" required value={details} onChange={(e) => setDetails(e.target.value)} style={{height: '100px'}} />
            </div>
            <div className="form-group">
              <label className="form-label">Rationale</label>
              <input type="text" className="form-input" required value={rationale} onChange={(e) => setRationale(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary">Log Decision</button>
          </form>
        </div>

        <div className="panel">
          <h3 className="panel-title"><Scale size={18} /> Active Decisions</h3>
          <div className="feed-scroll">
            {decisions.map((d, idx) => (
              <div key={idx} className="feed-item-accent">
                <h5 className="feed-item-title">{d.title}</h5>
                <div className="feed-item-meta">
                  {d.project_code} · {d.decider_name} · {d.decision_date}
                </div>
                <p className="feed-item-body">{d.decision_details}</p>
                <p className="text-footnote" style={{ marginTop: '0.35rem' }}>Rationale: {d.rationale}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
