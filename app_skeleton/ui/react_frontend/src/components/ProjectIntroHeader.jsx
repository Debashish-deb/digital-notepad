import { Calendar, FlaskConical } from 'lucide-react';
import ExpandableText from './ExpandableText.jsx';
import ProjectBrandMark from './ProjectBrandMark.jsx';
import ProjectCohortStrip from './ProjectCohortStrip.jsx';
import ProjectResourceCorner, { ProjectResourceDetails } from './ProjectResourceCorner.jsx';
import { ProjectTeamSection } from './ProjectTeamRoster.jsx';

/** Overview body from digital twin — no duplicate project title card (taskbar shows context). */
export default function ProjectIntroHeader({ twin, className = '' }) {
  if (!twin) return null;

  const id = twin.identity || {};
  const m = twin.metrics || {};
  const summary = id.project_summary;
  const researchQ = id.research_question;
  const timeline = id.timeline;
  const personnel = twin.personnel || [];
  const modalities = twin.modalities || [];
  const cohorts = twin.cohorts || [];
  const repos = twin.data_assets?.repositories || [];
  const fileCount = twin.total_assets_count ?? m.asset_count;

  const hasResourceCorner =
    (cohorts.length || m.cohort_count) > 0
    || repos.length > 0
    || (fileCount != null && fileCount !== '—')
    || (m.protocol_count ?? twin.protocols?.length) > 0;

  const hasContent =
    summary
    || (researchQ && researchQ !== summary)
    || timeline
    || modalities.length > 0
    || cohorts.length > 0
    || m.cohort_count > 0
    || personnel.length > 0
    || id.principal_investigator
    || repos.length > 1
    || hasResourceCorner;

  if (!hasContent) return null;

  return (
    <section className={`project-intro panel workspace-section workspace-section--no-hero${className ? ` ${className}` : ''}`}>
      <ProjectBrandMark
        code={id.project_code}
        index={id.project_index}
        name={id.project_name}
        variant="intro"
      />
      <ProjectResourceCorner twin={twin} />

      {summary ? (
        <ExpandableText maxLength={400} className="project-intro-summary">
          {summary}
        </ExpandableText>
      ) : null}

      {researchQ && researchQ !== summary ? (
        <details className="project-intro-research-details workspace-collapsible workspace-collapsible--nested">
          <summary className="workspace-collapsible__summary workspace-collapsible__summary--sm">
            Research focus
          </summary>
          <ExpandableText maxLength={280} className="prose-block project-intro-question-body">
            {researchQ}
          </ExpandableText>
        </details>
      ) : null}

      {timeline ? (
        <div className="project-intro-kv project-intro-kv--timeline">
          <div className="project-intro-kv-item">
            <Calendar size={14} aria-hidden />
            <span className="label">Timeline</span>
            <b>{timeline}</b>
          </div>
        </div>
      ) : null}

      {modalities.length > 0 ? (
        <div className="project-intro-modalities">
          <FlaskConical size={14} aria-hidden />
          <div className="project-card-tags">
            {modalities.map((m) => (
              <span key={m.name || m} className="project-tag modality">
                {m.name || m}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <ProjectCohortStrip cohorts={cohorts} metrics={twin.metrics} />
      <ProjectTeamSection personnel={personnel} identity={id} />
      <ProjectResourceDetails twin={twin} />
    </section>
  );
}
