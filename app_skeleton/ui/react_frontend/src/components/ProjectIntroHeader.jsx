import { Calendar, Layers, Target } from 'lucide-react';
import GlassCardStack, { GlassMiniCard } from './GlassCardStack.jsx';
import ProjectCoverNarrative from './ProjectCoverNarrative.jsx';
import ProjectCoverTeamStrip from './ProjectCoverTeamStrip.jsx';
import { sanitizeCoverSummary } from '../utils/projectCoverSummary.js';
import { normalizeModalityList } from '../utils/modalityMeta.js';
import './ProjectIntroHeader.css';
import './GlassCardStack.css';

const STATUS_META = {
  active: { label: 'Active', tone: '#34d399' },
  completed: { label: 'Completed', tone: '#60a5fa' },
  discontinued: { label: 'Discontinued', tone: '#94a3b8' },
  archived: { label: 'Archived', tone: '#94a3b8' },
};

function ProjectCoverStatus({ status }) {
  const key = (status || 'active').toLowerCase();
  const meta = STATUS_META[key] || STATUS_META.active;
  return (
    <div className="project-cover-status" title={`Project status: ${meta.label}`}>
      <span className="project-cover-status__dot" style={{ '--status-tone': meta.tone }} aria-hidden />
      <span className="project-cover-status__label">{meta.label}</span>
    </div>
  );
}

function ProjectCoverTitle({ identity }) {
  const code = identity.project_code || '';
  const index = identity.project_index;
  if (!code) return null;

  return (
    <h2 className="project-cover__title">
      {code}
      {index != null && index !== '' ? (
        <sup className="project-cover__index" aria-label={`project number ${index}`}>
          {index}
        </sup>
      ) : null}
    </h2>
  );
}

/** Ultra-compact glass cover card for the project workspace. */
export default function ProjectIntroHeader({ twin, className = '' }) {
  if (!twin) return null;

  const id = twin.identity || {};
  const narrative = sanitizeCoverSummary(id.project_summary);
  const personnel = twin.personnel || [];
  const modalities = twin.modalities || [];

  const stackItems = [
    ...normalizeModalityList(modalities).map((item) => ({
      key: `modality-${item.name}`,
      label: item.label,
      value: item.name,
      icon: item.Icon,
      tone: item.tone,
    })),
    ...(id.disease_focus
      ? [{
        key: 'focus',
        label: 'Focus',
        value: id.disease_focus,
        icon: Target,
        tone: '#f43f5e',
      }]
      : []),
    ...(id.timeline
      ? [{
        key: 'timeline',
        label: 'Timeline',
        value: id.timeline,
        icon: Calendar,
        tone: '#38bdf8',
      }]
      : []),
  ].slice(0, 6);

  const hasContent =
    narrative.length > 0
    || modalities.length > 0
    || personnel.length > 0
    || id.principal_investigator
    || id.disease_focus
    || id.timeline;

  if (!hasContent) return null;

  return (
    <section
      className={`project-cover project-cover--glass workspace-section workspace-section--no-hero${className ? ` ${className}` : ''}`}
      aria-label="Project overview"
    >
      <div
        className="project-cover__art"
        style={{ backgroundImage: "url('/covers/overlays/project-workspace.svg')" }}
        aria-hidden
      />
      <div className="project-cover__scrim" aria-hidden />

      <div className="project-cover__row project-cover__row--main">
        <div className="project-cover__identity">
          <div className="project-cover__glyph" aria-hidden>
            <Layers size={18} strokeWidth={1.75} />
          </div>
          <div className="project-cover__copy">
            <div className="project-cover__title-row">
              <ProjectCoverTitle identity={id} />
            </div>
            <ProjectCoverNarrative summary={id.project_summary} compact />
          </div>
        </div>

        {stackItems.length > 0 ? (
          <GlassCardStack className="project-cover__stack" columns={3} rows={2} meta compact>
            {stackItems.map((item, index) => (
              <GlassMiniCard
                key={item.key}
                label={item.label}
                value={item.value}
                icon={item.icon}
                tone={item.tone}
                delay={index * 90}
                compact
                title={`${item.label} — ${item.value}`}
              />
            ))}
          </GlassCardStack>
        ) : null}
      </div>

      <div className="project-cover__divider" aria-hidden />

      <div className="project-cover__row project-cover__row--footer">
        <ProjectCoverTeamStrip personnel={personnel} identity={id} />
        <ProjectCoverStatus status={id.status} />
      </div>
    </section>
  );
}
