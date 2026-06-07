import { useMemo, useState } from 'react';
import { Database, Users, FlaskConical, Calendar, FileText, GitBranch, FolderOpen } from 'lucide-react';
import { categoryColor, formatSampleCount } from '../utils/digitalTwinUtils.js';

export function DigitalTwinMetrics({ metrics, processedAt }) {
  if (!metrics) return null;
  const items = [
    { label: 'Documents', value: metrics.document_count, tone: 'primary' },
    { label: 'Timeline Events', value: metrics.timeline_entries, tone: 'accent' },
    { label: 'Cohorts', value: metrics.cohort_count, tone: 'success' },
    { label: 'Est. Samples', value: formatSampleCount(metrics.estimated_sample_count), tone: 'warning' },
    { label: 'Protocols', value: metrics.protocol_count, tone: 'primary' },
    { label: 'Repositories', value: metrics.repository_count, tone: 'accent' },
  ];

  return (
    <div className="digital-twin-metrics">
      {items.map((item) => (
        <div key={item.label} className={`metric-card ${item.tone}`}>
          <div className="metric-label">{item.label}</div>
          <div className="metric-value">{item.value ?? '—'}</div>
        </div>
      ))}
      {processedAt && (
        <div className="digital-twin-processed-at">
          Processed {processedAt.slice(0, 10)}
        </div>
      )}
    </div>
  );
}

export function DigitalTwinOverview({ twin }) {
  const { identity, personnel, modalities, cohorts } = twin;
  const summary = identity?.project_summary || identity?.research_question;

  return (
    <div className="digital-twin-sections">
      <div className="panel digital-twin-identity">
        <h3 className="panel-title">Project Identity</h3>
        <div className="digital-twin-kv-grid">
          <div><span>Code</span><code>{identity?.project_code}</code></div>
          <div><span>Lead</span><b>{identity?.project_lead}</b></div>
          <div><span>PI</span><b>{identity?.principal_investigator}</b></div>
          <div><span>Disease</span><b>{identity?.disease_focus || '—'}</b></div>
          <div><span>Status</span><span className="dt-badge">{identity?.status}</span></div>
          <div><span>Priority</span><span className="dt-badge warning">{identity?.priority}</span></div>
          <div><span>Category</span><b>{identity?.category_label || identity?.category}</b></div>
          <div><span>Timeline</span><b>{identity?.timeline || '—'}</b></div>
        </div>
        {summary && (
          <p className="digital-twin-summary">{summary}</p>
        )}
      </div>

      {personnel?.length > 0 && (
        <div className="panel">
          <h3 className="panel-title"><Users size={18} /> Personnel Registry</h3>
          <table className="digital-twin-table">
            <thead>
              <tr><th>Name</th><th>Role</th><th>Focus</th></tr>
            </thead>
            <tbody>
              {personnel.map((p) => (
                <tr key={p.name}>
                  <td><b>{p.name}</b></td>
                  <td>{p.role}</td>
                  <td className="muted">{p.focus || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modalities?.length > 0 && (
        <div className="panel">
          <h3 className="panel-title"><FlaskConical size={18} /> Assay Modalities</h3>
          <table className="digital-twin-table">
            <thead>
              <tr><th>Modality</th><th>Type</th><th>Notes</th></tr>
            </thead>
            <tbody>
              {modalities.map((m) => (
                <tr key={m.name}>
                  <td><span className="project-tag modality">{m.name}</span></td>
                  <td>{m.type || 'assay'}</td>
                  <td className="muted">{m.description || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {cohorts?.length > 0 && (
        <div className="panel">
          <h3 className="panel-title"><Database size={18} /> Cohort Batches</h3>
          <table className="digital-twin-table">
            <thead>
              <tr><th>Batch</th><th>Samples</th><th>Description</th><th>Exclusions</th></tr>
            </thead>
            <tbody>
              {cohorts.map((c) => (
                <tr key={c.batch_id}>
                  <td><b>{c.batch_id}</b></td>
                  <td>{formatSampleCount(c.sample_count)}</td>
                  <td className="wrap">{c.description?.slice(0, 200)}{c.description?.length > 200 ? '…' : ''}</td>
                  <td>
                    {c.exclusions?.length ? (
                      <ul className="dt-exclusion-list">
                        {c.exclusions.map((ex) => <li key={ex}>{ex}</li>)}
                      </ul>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function DigitalTwinTimeline({ timeline, meetings }) {
  const [filter, setFilter] = useState('all');
  const categories = useMemo(() => {
    const set = new Set((timeline || []).map((e) => e.category).filter(Boolean));
    return ['all', ...Array.from(set).sort()];
  }, [timeline]);

  const filtered = useMemo(() => {
    if (!timeline) return [];
    if (filter === 'all') return timeline;
    return timeline.filter((e) => e.category === filter);
  }, [timeline, filter]);

  return (
    <div>
      <div className="digital-twin-filter-bar">
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`btn btn-sm ${filter === cat ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter(cat)}
          >
            {cat === 'all' ? 'All events' : cat}
          </button>
        ))}
      </div>

      {meetings?.length > 0 && (
        <div className="panel" style={{ marginBottom: '1rem' }}>
          <h4 className="workspace-subpanel-title">Meeting Index ({meetings.length})</h4>
          <div className="digital-twin-meeting-chips">
            {meetings.slice(0, 12).map((m) => (
              <span key={`${m.date}-${m.title}`} className="dt-meeting-chip">
                {m.date}: {m.title}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="digital-twin-timeline">
        {filtered.length === 0 ? (
          <p className="muted">No structured timeline entries found.</p>
        ) : (
          filtered.map((entry) => (
            <article key={`${entry.date}-${entry.title}-${entry.source_file}`} className="dt-timeline-card">
              <div className="dt-timeline-meta">
                <span className="dt-date"><Calendar size={14} /> {entry.date}</span>
                <span className="dt-badge" style={{ borderColor: categoryColor(entry.category) }}>
                  {entry.category}
                </span>
                <span className="dt-source">{entry.source_file}</span>
              </div>
              <h4>{entry.title}</h4>
              <p>{entry.summary?.slice(0, 400)}{entry.summary?.length > 400 ? '…' : ''}</p>
            </article>
          ))
        )}
      </div>
    </div>
  );
}

export function DigitalTwinAbstracts({ dissemination, publications }) {
  const items = dissemination?.length ? dissemination : publications || [];
  if (!items.length) {
    return <p className="muted">No structured abstracts or publications indexed.</p>;
  }

  return (
    <table className="digital-twin-table">
      <thead>
        <tr>
          <th>Title</th>
          <th>Conference / Venue</th>
          <th>Year</th>
          <th>Author</th>
          <th>Source File</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.source_file || item.title}>
            <td><b>{item.title}</b></td>
            <td>{item.conference || item.source || '—'}</td>
            <td>{item.year || '—'}</td>
            <td>{item.author || '—'}</td>
            <td className="mono wrap">{item.source_file || '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function DigitalTwinCatalog({ dataAssets }) {
  if (!dataAssets) return null;
  const { storage_paths, repositories, folder_tree } = dataAssets;

  return (
    <div className="digital-twin-sections">
      <div className="grid-2col">
        <div className="panel">
          <h3 className="panel-title"><FolderOpen size={18} /> Storage Paths</h3>
          {storage_paths?.length ? (
            <ul className="digital-twin-path-list">
              {storage_paths.map((p) => (
                <li key={p}><code>{p}</code></li>
              ))}
            </ul>
          ) : <p className="muted">No storage paths extracted.</p>}
        </div>
        <div className="panel">
          <h3 className="panel-title"><GitBranch size={18} /> Code Repositories</h3>
          {repositories?.length ? (
            <ul className="digital-twin-path-list">
              {repositories.map((url) => (
                <li key={url}>
                  <a href={url} target="_blank" rel="noopener noreferrer" className="project-repo-link">{url}</a>
                </li>
              ))}
            </ul>
          ) : <p className="muted">No repositories indexed.</p>}
        </div>
      </div>

      {folder_tree?.length > 0 && (
        <div className="panel">
          <h3 className="panel-title"><FileText size={18} /> Folder Inventory</h3>
          <table className="digital-twin-table">
            <thead>
              <tr><th>Path</th><th>Files</th><th>Categories</th></tr>
            </thead>
            <tbody>
              {folder_tree.map((f) => (
                <tr key={f.path}>
                  <td><code>{f.path}</code></td>
                  <td>{f.file_count}</td>
                  <td>{f.categories?.join(', ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function DigitalTwinProtocols({ protocols }) {
  if (!protocols?.length) {
    return <p className="muted">No protocol documents indexed.</p>;
  }
  return (
    <table className="digital-twin-table">
      <thead>
        <tr><th>Protocol</th><th>Category</th><th>Steps</th><th>Source</th></tr>
      </thead>
      <tbody>
        {protocols.map((p) => (
          <tr key={p.source_file}>
            <td><b>{p.title}</b></td>
            <td className="wrap">{p.category}</td>
            <td>{p.steps?.length || 0}</td>
            <td className="mono wrap">{p.source_file}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ProjectDigitalTwinView({ twin, section = 'overview' }) {
  if (!twin) return null;

  switch (section) {
    case 'metrics':
      return <DigitalTwinMetrics metrics={twin.metrics} processedAt={twin.processed_at} />;
    case 'timeline':
      return <DigitalTwinTimeline timeline={twin.timeline} meetings={twin.meetings} />;
    case 'abstracts':
      return <DigitalTwinAbstracts dissemination={twin.dissemination} publications={twin.publications} />;
    case 'catalog':
      return <DigitalTwinCatalog dataAssets={twin.data_assets} />;
    case 'protocols':
      return <DigitalTwinProtocols protocols={twin.protocols} />;
    case 'overview':
    default:
      return <DigitalTwinOverview twin={twin} />;
  }
}
