import { Database, Files, GitBranch, Users2 } from 'lucide-react';
import { formatSampleCount } from '@/lib/digitalTwinUtils.js';
import SmartLink from '@/shared/ui/SmartLink.jsx';

/** Compact resource chips — cohorts, repos, files — for the intro card corner. */
export default function ProjectResourceCorner({ twin }) {
  if (!twin) return null;

  const m = twin.metrics || {};
  const cohorts = twin.cohorts || [];
  const repos = twin.data_assets?.repositories || [];
  const cohortSamples = cohorts.reduce((sum, c) => sum + (Number(c.sample_count) || 0), 0);
  const fileCount = twin.total_assets_count ?? m.asset_count;
  const cohortCount = cohorts.length || m.cohort_count;

  const hasCohorts = cohortCount > 0;
  const hasRepos = repos.length > 0;
  const hasFiles = fileCount != null && fileCount !== '—';

  if (!hasCohorts && !hasRepos && !hasFiles) return null;

  const cohortLabel = (() => {
    if (!hasCohorts) return null;
    const countPart = `${cohortCount} cohort${cohortCount !== 1 ? 's' : ''}`;
    const firstBatch = cohorts.length === 1 ? cohorts[0].batch_id : null;
    const samplesPart = cohortSamples ? `${formatSampleCount(cohortSamples)} cohort samples` : null;
    return [countPart, firstBatch, samplesPart].filter(Boolean).join(' · ');
  })();

  return (
    <div className="project-resource-corner" aria-label="Project resources">
      {cohortLabel ? (
        <span className="project-resource-chip" title="Cohort batches">
          <Users2 size={12} aria-hidden />
          <span>{cohortLabel}</span>
        </span>
      ) : null}

      {hasRepos ? (
        repos.length === 1 ? (
          <span className="project-resource-chip project-resource-chip--link">
            <GitBranch size={12} aria-hidden />
            <SmartLink href={repos[0]} showCopy maxLabelLen={36} />
          </span>
        ) : (
          <span className="project-resource-chip" title={repos.join('\n')}>
            <GitBranch size={12} aria-hidden />
            <span>{repos.length} repos</span>
          </span>
        )
      ) : null}

      {hasFiles ? (
        <span className="project-resource-chip" title="Files on disk">
          <Files size={12} aria-hidden />
          <span>{fileCount} files</span>
        </span>
      ) : null}

      {m.protocol_count > 0 || twin.protocols?.length ? (
        <span className="project-resource-chip" title="Protocols">
          <Database size={12} aria-hidden />
          <span>{m.protocol_count ?? twin.protocols?.length} protocols</span>
        </span>
      ) : null}
    </div>
  );
}

/** Extra repository links when there are multiple — cohorts stay in ProjectCohortStrip. */
export function ProjectResourceDetails({ twin }) {
  if (!twin) return null;

  const repos = twin.data_assets?.repositories || [];
  if (repos.length <= 1) return null;

  return (
    <details className="project-resource-details">
      <summary className="project-resource-details__summary">
        Repositories ({repos.length})
      </summary>
      <div className="project-resource-details__body">
        <ul className="smart-link-list project-resource-details__repos">
          {repos.map((url) => (
            <li key={url}>
              <SmartLink href={url} showCopy maxLabelLen={48} />
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}
