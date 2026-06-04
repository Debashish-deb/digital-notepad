import './MacPlusVisualStyles.css';
import React, { useEffect, useState } from 'react';
import { Users, Terminal, Settings, Activity, FolderOpen } from 'lucide-react';
import MetricCard from '../components/MetricCard';
import { apiGet } from '../api/client.js';

export default function DashboardScreen({
  stats,
  team,
  auditLogs,
  projectCodes,
  setProjectCodes,
  dbProjects,
  API_URL,
  hideHeader = false,
  onNavigate,
}) {
  const activeProjCount = Object.keys(stats.project_samples || {}).length;
  const [gap, setGap] = useState(null);
  const [personnelFiles, setPersonnelFiles] = useState([]);

  useEffect(() => {
    if (!API_URL) return;
    fetch(`${API_URL}/gap-analysis`)
      .then((res) => (res.ok ? res.json() : null))
      .then(setGap)
      .catch(() => setGap(null));
  }, [API_URL]);

  useEffect(() => {
    apiGet('/api/lab/section/overview_personnel')
      .then((data) => {
        const docs = (data?.document_index_preview || data?.document_index || []).slice(0, 12);
        setPersonnelFiles(
          docs.map((d) => ({
            path: d.path || d.relative_path,
            name: d.title || d.path || 'Document',
          })),
        );
      })
      .catch(() => setPersonnelFiles([]));
  }, []);

  const roster = team?.length
    ? team.map((m) => ({
        key: m.username || m.full_name,
        name: m.full_name || m.username,
        role: m.role || 'Researcher',
        focus: (m.allowed_projects || []).join(', ') || '—',
      }))
    : personnelFiles.map((f) => ({
        key: f.path,
        name: f.name,
        role: 'Personnel document',
        focus: 'Open under Overview → Personnel',
      }));

  const researcherCount = team?.length || personnelFiles.length;

  return (
    <div>
      {!hideHeader && (
        <div className="page-header">
          <h1 className="page-title-gradient">Lab Overview Dashboard</h1>
          <p className="page-subtitle">Clinical-spatial research status, audit trails, and multiomic data metrics.</p>
        </div>
      )}

      <div className="metrics-grid">
        <MetricCard label="Total Patients" value={stats.patient_count || 0} />
        <MetricCard label="Total Samples" value={stats.sample_count || 0} variant="success" />
        <MetricCard
          label="Active Scoped Projects"
          value={dbProjects.filter((p) => p.status === 'active').length || activeProjCount}
          variant="accent"
        />
        <MetricCard label="Team records" value={researcherCount} variant="warning" />
      </div>

      {gap && (
        <div className="panel">
          <h3 className="panel-title"><Activity size={18} /> Platform Readiness</h3>
          <div className="projects-stats-bar" style={{ marginBottom: '1rem' }}>
            <div className="projects-stat">
              <span className="projects-stat-value">{gap.readiness_score}%</span>
              <span className="projects-stat-label">Checklist readiness</span>
            </div>
            <div className="projects-stat">
              <span className="projects-stat-value">{gap.ai_models_count}</span>
              <span className="projects-stat-label">AI models</span>
            </div>
            <div className="projects-stat">
              <span className="projects-stat-value">{gap.documents_count}</span>
              <span className="projects-stat-label">Ingested docs</span>
            </div>
            <div className="projects-stat">
              <span className="projects-stat-value">{gap.datasets_count}</span>
              <span className="projects-stat-label">Datasets</span>
            </div>
          </div>
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
            {(gap.recommendations || []).map((rec, i) => (
              <li key={i} className="text-body-secondary">{rec}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid-2col">
        <div className="panel">
          <h3 className="panel-title"><Settings size={18} /> Project Scope Selector</h3>
          <p className="panel-lead">
            Select active research projects to scope down LLM Copilot queries and coordinate global metrics:
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {dbProjects.map((p) => {
              const isChecked = projectCodes.includes(p.project_code);
              return (
                <label key={p.project_code} className={`scope-chip ${isChecked ? 'is-checked' : ''}`}>
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => {
                      if (isChecked) {
                        setProjectCodes(projectCodes.filter((c) => c !== p.project_code));
                      } else {
                        setProjectCodes([...projectCodes, p.project_code]);
                      }
                    }}
                  />
                  <span>{p.project_code}</span>
                </label>
              );
            })}
          </div>
        </div>

        <div className="panel">
          <h3 className="panel-title"><Terminal size={18} /> System Audit Trail</h3>
          <div className="feed-scroll" style={{ maxHeight: '250px' }}>
            {auditLogs.slice(0, 15).map((log, idx) => (
              <div key={idx} className="audit-log-item">
                <div className="audit-log-meta">
                  <span><strong>{log.actor}</strong> · {log.event_type}</span>
                  <span>{log.created_at.replace('T', ' ').slice(0, 16)}</span>
                </div>
                <div className="audit-log-body">{log.description}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="panel">
        <h3 className="panel-title section-divider-title">
          <Users size={18} /> Research team
        </h3>
        <p className="panel-lead">
          {team?.length
            ? 'Roster from the platform database (PostgreSQL).'
            : 'Team API unavailable — showing personnel documents from the processed lab twin.'}
        </p>

        {!roster.length ? (
          <p className="muted">No team or personnel files found. Add documents under database/Overview/PERSONNEL.</p>
        ) : (
          <div className="roster-grid">
            {roster.map((member) => (
              <div key={member.key} className="roster-card">
                <div className="roster-avatar">{(member.name || '?').slice(0, 1)}</div>
                <h4 className="roster-name">{member.name}</h4>
                <span className="roster-role">{member.role}</span>
                <p className="roster-focus">{member.focus}</p>
              </div>
            ))}
          </div>
        )}

        {typeof onNavigate === 'function' && (
          <button
            type="button"
            className="btn btn-secondary"
            style={{ marginTop: '1rem' }}
            onClick={() => onNavigate('overview', 'personnel')}
          >
            <FolderOpen size={16} /> Open personnel folder
          </button>
        )}
      </div>
    </div>
  );
}
