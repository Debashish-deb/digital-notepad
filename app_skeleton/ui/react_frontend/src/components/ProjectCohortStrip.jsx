import { Database } from 'lucide-react';
import { formatSampleCount } from '../utils/digitalTwinUtils.js';
import ExpandableText from './ExpandableText.jsx';

/** Always-visible compact cohort list — preserves batch, samples, and description. */
export default function ProjectCohortStrip({ cohorts = [], metrics = {} }) {
  const batchCount = cohorts.length || metrics.cohort_count;
  if (!batchCount) return null;

  return (
    <div className="project-intro-cohorts workspace-subsection">
      <h3 className="workspace-subpanel-title workspace-subpanel-title--compact">
        <Database size={14} aria-hidden /> Cohorts
        <span className="project-intro-cohorts__count">
          {batchCount} cohort batch{batchCount !== 1 ? 'es' : ''}
        </span>
      </h3>
      {cohorts.length > 0 ? (
        <div className="project-cohort-strip" role="list">
          {cohorts.map((c) => (
            <article key={c.batch_id} className="project-cohort-chip" role="listitem">
              <span className="project-cohort-chip__batch">{c.batch_id}</span>
              {c.sample_count != null && c.sample_count !== '' ? (
                <span className="project-cohort-chip__samples">
                  {formatSampleCount(c.sample_count)} cohort samples
                </span>
              ) : null}
              {c.description ? (
                <ExpandableText maxLength={100} as="span" className="project-cohort-chip__desc">
                  {c.description}
                </ExpandableText>
              ) : (
                <span className="project-cohort-chip__desc muted">No cohort notes</span>
              )}
            </article>
          ))}
        </div>
      ) : (
        <p className="text-footnote muted project-intro-cohorts__fallback">
          {batchCount} cohort batch{batchCount !== 1 ? 'es' : ''} indexed — open the taskbar to
          edit cohort roster details.
        </p>
      )}
    </div>
  );
}
