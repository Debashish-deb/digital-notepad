import { User, Users, Calendar, FlaskConical, Database } from 'lucide-react';
import { formatSampleCount } from '../utils/digitalTwinUtils.js';
import ExpandableText from './ExpandableText.jsx';

/** Overview from digital twin only — extracted from project folder on disk. */
export default function ProjectIntroHeader({ twin }) {
  if (!twin) return null;

  const id = twin.identity || {};
  const responsible = id.responsible || id.project_lead;
  const pi = id.principal_investigator;
  const name = id.project_name || twin.project_code;
  const summary = id.project_summary;
  const researchQ = id.research_question;
  const timeline = id.timeline;
  const disease = id.disease_focus;
  const status = id.status;
  const priority = id.priority;
  const category = id.category_label || id.category;
  const personnel = twin.personnel || [];
  const modalities = twin.modalities || [];
  const cohorts = twin.cohorts || [];

  return (
    <section className="project-intro panel workspace-section">
      <header className="project-intro-header">
        <div className="project-intro-copy">
          <p className="project-intro-eyebrow">
            {category && <span className="project-intro-chip">{category}</span>}
            {id.project_index != null && <span className="project-intro-chip">Project #{id.project_index}</span>}
            <code className="project-intro-code">{id.project_code || twin.project_code}</code>
          </p>
          <h2 className="project-intro-title">{name}</h2>
          {summary && (
            <ExpandableText maxLength={400} className="project-intro-summary">
              {summary}
            </ExpandableText>
          )}
          {researchQ && researchQ !== summary && (
            <div className="project-intro-question">
              <h3 className="text-title-4">Research focus</h3>
              <ExpandableText maxLength={280} className="prose-block">
                {researchQ}
              </ExpandableText>
            </div>
          )}
        </div>
        <div className="project-intro-badges">
          {status && <span className="dt-badge">{status}</span>}
          {priority && <span className="dt-badge warning">{priority}</span>}
          {disease && <span className="project-intro-disease">{disease}</span>}
        </div>
      </header>

      <div className="project-intro-kv">
        {responsible && (
          <div className="project-intro-kv-item">
            <User size={16} aria-hidden />
            <span className="label">Responsible</span>
            <b>{responsible}</b>
          </div>
        )}
        {pi && pi !== responsible && (
          <div className="project-intro-kv-item">
            <User size={16} aria-hidden />
            <span className="label">Principal investigator</span>
            <b>{pi}</b>
          </div>
        )}
        {timeline && (
          <div className="project-intro-kv-item">
            <Calendar size={16} aria-hidden />
            <span className="label">Timeline</span>
            <b>{timeline}</b>
          </div>
        )}
      </div>

      {modalities.length > 0 && (
        <div className="project-intro-modalities">
          <FlaskConical size={16} aria-hidden />
          <div className="project-card-tags">
            {modalities.map((m) => (
              <span key={m.name || m} className="project-tag modality">
                {m.name || m}
              </span>
            ))}
          </div>
        </div>
      )}

      {cohorts.length > 0 && (
        <div className="project-intro-cohorts workspace-subsection">
          <h3 className="workspace-subpanel-title">
            <Database size={16} /> Cohorts
          </h3>
          <p className="text-footnote muted subsection-lead">From project logs and documentation</p>
          <div className="table-scroll">
            <table className="digital-twin-table compact">
              <thead>
                <tr>
                  <th>Batch</th>
                  <th>Samples</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {cohorts.map((c) => (
                  <tr key={c.batch_id}>
                    <td>
                      <b>{c.batch_id}</b>
                    </td>
                    <td>{formatSampleCount(c.sample_count)}</td>
                    <td className="wrap">
                      {c.description ? (
                        <ExpandableText maxLength={140} as="span">
                          {c.description}
                        </ExpandableText>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {personnel.length > 0 && (
        <div className="project-intro-team workspace-subsection">
          <h3 className="workspace-subpanel-title">
            <Users size={16} /> Team
          </h3>
          <p className="text-footnote muted subsection-lead">From project documentation</p>
          <div className="project-intro-team-grid">
            {personnel.map((p, i) => (
              <div key={`${p.name}-${i}`} className="project-intro-team-card">
                <b>{p.name}</b>
                <span>{p.role || p.focus || 'team member'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
