import { BarChart3 } from 'lucide-react';
import { formatSampleCount } from '../utils/digitalTwinUtils.js';
import SmartLink from './SmartLink.jsx';

/** Real metrics from processed digital twin — no catalog placeholders. */
export default function ProjectTwinStats({ twin }) {
  if (!twin) return null;

  const m = twin.metrics || {};
  const cohortSamples = (twin.cohorts || []).reduce(
    (sum, c) => sum + (Number(c.sample_count) || 0),
    0
  );
  const repos = twin.data_assets?.repositories || [];

  const items = [
    { label: 'Files on disk', value: twin.total_assets_count ?? m.asset_count ?? '—' },
    { label: 'Documents indexed', value: m.document_count ?? '—' },
    { label: 'Timeline events', value: m.timeline_entries ?? twin.timeline?.length ?? '—' },
    { label: 'Cohort batches', value: twin.cohorts?.length ?? m.cohort_count ?? '—' },
    {
      label: 'Est. samples',
      value: cohortSamples ? formatSampleCount(cohortSamples) : formatSampleCount(m.estimated_sample_count),
    },
    { label: 'Protocols', value: m.protocol_count ?? twin.protocols?.length ?? '—' },
  ].filter((i) => i.value !== '—' && i.value != null && i.value !== 0);

  if (!items.length && !repos.length) return null;

  return (
    <section className="project-twin-stats workspace-section">
      <header className="workspace-section-header compact">
        <h3 className="workspace-subpanel-title">
          <BarChart3 size={16} /> Workspace vitals
        </h3>
      </header>

      {items.length > 0 && (
        <div className="metrics-grid vitals-metrics-grid">
          {items.map((item) => (
            <div key={item.label} className="metric-card accent">
              <div className="metric-label">{item.label}</div>
              <div className="metric-value">{item.value}</div>
            </div>
          ))}
        </div>
      )}

      {repos.length > 0 && (
        <div className="workspace-subsection panel-inset">
          <h4 className="workspace-subpanel-title">Repositories</h4>
          <p className="text-footnote muted subsection-lead">Detected in project files</p>
          <ul className="smart-link-list">
            {repos.map((url) => (
              <li key={url}>
                <SmartLink href={url} showCopy maxLabelLen={64} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {twin.processed_at && (
        <p className="text-footnote twin-scan-meta">
          Digital record scanned {twin.processed_at.slice(0, 16).replace('T', ' ')}
          {twin.content_root ? (
            <>
              {' · '}
              <SmartLink href={twin.content_root} showCopy maxLabelLen={40} />
            </>
          ) : null}
        </p>
      )}
    </section>
  );
}
