import { BarChart3, ChevronRight } from 'lucide-react';
import { formatSampleCount } from '../utils/digitalTwinUtils.js';
import SmartLink from './SmartLink.jsx';

/** Compact, collapsible workspace vitals — expanded only when there is enough to show. */
export default function ProjectTwinStats({ twin }) {
  if (!twin) return null;

  const m = twin.metrics || {};
  const cohortSamples = (twin.cohorts || []).reduce(
    (sum, c) => sum + (Number(c.sample_count) || 0),
    0,
  );
  const repos = twin.data_assets?.repositories || [];

  const cohortCount = twin.cohorts?.length ?? m.cohort_count;

  const items = [
    { label: 'Cohorts', value: cohortCount },
    {
      label: 'Cohort samples',
      value: cohortSamples
        ? formatSampleCount(cohortSamples)
        : formatSampleCount(m.estimated_sample_count),
    },
    { label: 'Files', value: twin.total_assets_count ?? m.asset_count },
    { label: 'Docs', value: m.document_count },
    { label: 'Events', value: m.timeline_entries ?? twin.timeline?.length },
    { label: 'Protocols', value: m.protocol_count ?? twin.protocols?.length },
  ].filter((i) => i.value != null && i.value !== '—' && i.value !== 0);

  const hasScanMeta = Boolean(twin.processed_at || twin.content_root);
  const isSparse = items.length <= 2 && repos.length <= 1 && !hasScanMeta;

  if (isSparse && !items.length) return null;

  return (
    <details className="project-twin-stats workspace-collapsible" open={items.length > 4}>
      <summary className="workspace-collapsible__summary">
        <BarChart3 size={14} aria-hidden />
        <span>Workspace vitals</span>
        {items.length > 0 ? (
          <span className="workspace-collapsible__preview">
            {items.slice(0, 4).map((i) => `${i.value} ${i.label.toLowerCase()}`).join(' · ')}
          </span>
        ) : null}
        <ChevronRight size={14} className="workspace-collapsible__chevron" aria-hidden />
      </summary>

      <div className="workspace-collapsible__body">
        {items.length > 0 ? (
          <div className="workspace-stat-strip" role="list">
            {items.map((item) => (
              <span key={item.label} className="workspace-stat-pill" role="listitem">
                <span className="workspace-stat-pill__value">{item.value}</span>
                <span className="workspace-stat-pill__label">{item.label}</span>
              </span>
            ))}
          </div>
        ) : null}

        {repos.length > 1 ? (
          <div className="workspace-inline-links">
            <span className="workspace-inline-links__label">Repos</span>
            {repos.map((url) => (
              <SmartLink key={url} href={url} showCopy maxLabelLen={40} />
            ))}
          </div>
        ) : null}

        {hasScanMeta ? (
          <p className="text-footnote twin-scan-meta">
            Scanned {twin.processed_at?.slice(0, 16).replace('T', ' ')}
            {twin.content_root ? (
              <>
                {' · '}
                <SmartLink href={twin.content_root} showCopy maxLabelLen={32} />
              </>
            ) : null}
          </p>
        ) : null}
      </div>
    </details>
  );
}
