import { forwardRef, useEffect, useImperativeHandle, useMemo, useState } from 'react';
import {
  Database, Users, FlaskConical, Calendar, FileText, GitBranch,
  FolderOpen, Edit3, Save, X, Plus, Trash2, ChevronDown, ChevronRight, Images,
} from 'lucide-react';
import { categoryColor, cloneTwin, formatSampleCount } from '@/lib/digitalTwinUtils.js';
import ProjectContentLibrary from './ProjectContentLibrary.jsx';
import SmartLink from '@/shared/ui/SmartLink.jsx';
import ExpandableText from '@/shared/ui/ExpandableText.jsx';
import DocumentFormatter from '@/features/documents/components/DocumentFormatter.jsx';
import { useTaskpad } from '@/contexts/TaskpadContext.jsx';

const GROUPS = [
  { id: 'research', label: 'Research Profile', icon: FileText },
  { id: 'team', label: 'Team & Cohorts', icon: Users },
  { id: 'methods', label: 'Methods & Data Assets', icon: Database },
  { id: 'outputs', label: 'Publications & Abstracts', icon: BookIcon },
  { id: 'content', label: 'Project Files & Figures', icon: Images },
  { id: 'activity', label: 'Activity Log', icon: Calendar },
];

function BookIcon(props) {
  return <FileText {...props} />;
}

function Field({ label, value, editing, onChange, multiline = false, readOnly = false }) {
  if (!editing || readOnly) {
    return (
      <div className="dt-field">
        <span className="dt-field-label">{label}</span>
        <div className="dt-field-value prose-block">{value || '—'}</div>
      </div>
    );
  }
  if (multiline) {
    return (
      <div className="dt-field">
        <label className="dt-field-label">{label}</label>
        <textarea className="form-input dt-input" rows={3} value={value || ''} onChange={(e) => onChange(e.target.value)} />
      </div>
    );
  }
  return (
    <div className="dt-field">
      <label className="dt-field-label">{label}</label>
      <input className="form-input dt-input" value={value || ''} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function GroupHeader({ group, open, onToggle, count }) {
  const Icon = group.icon;
  return (
    <button type="button" className="dt-group-header" onClick={onToggle}>
      {open ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
      <Icon size={18} />
      <span>{group.label}</span>
      {count != null && <span className="dt-group-count">{count}</span>}
    </button>
  );
}

const DigitalTwinPanel = forwardRef(function DigitalTwinPanel({
  twin,
  onSave,
  saving = false,
  section = 'all',
  projectCode,
  API_URL,
  hideToolbar = false,
  editing: controlledEditing,
  onEditingChange,
}, ref) {
  const [internalEditing, setInternalEditing] = useState(false);
  const editing = controlledEditing !== undefined ? controlledEditing : internalEditing;
  const setEditing = onEditingChange || setInternalEditing;
  const [draft, setDraft] = useState(null);
  const { openTaskpad } = useTaskpad();
  const [openGroups, setOpenGroups] = useState(() => {
    const initial = new Set(['content', 'research', 'methods', 'outputs', 'activity']);
    if (section !== 'overview') initial.add('team');
    return initial;
  });
  const [saveMsg, setSaveMsg] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [filePreviewLoading, setFilePreviewLoading] = useState(false);

  useEffect(() => {
    setEditing(false);
    setDraft(null);
    setSaveMsg(null);
  }, [twin?.project_code, twin?.edited_at, setEditing]);

  const display = editing && draft ? draft : twin;
  const outputs = display?.outputs?.length
    ? display.outputs
    : [...(display?.dissemination || []), ...(display?.publications || [])];
  const libTotal = display?.content_library?.totals?.all || display?.total_assets_count || 0;

  const visibleGroups = useMemo(() => {
    if (section === 'all') return GROUPS;
    const map = {
      overview: ['research', 'team', 'content'],
      content: ['content'],
      metrics: [],
      timeline: ['activity'],
      abstracts: ['outputs'],
      catalog: ['methods', 'content'],
      protocols: ['methods'],
    };
    return GROUPS.filter((g) => (map[section] || GROUPS.map((x) => x.id)).includes(g.id));
  }, [section]);

  if (!twin || !display) return null;

  const startEdit = () => {
    setDraft(cloneTwin(twin));
    setEditing(true);
    setSaveMsg(null);
  };

  const cancelEdit = () => {
    setDraft(null);
    setEditing(false);
    setSaveMsg(null);
  };

  const handleSave = async () => {
    if (!draft || !onSave) return;
    try {
      await onSave(draft);
      setEditing(false);
      setDraft(null);
      setSaveMsg('Changes saved.');
    } catch {
      setSaveMsg('Save failed — please try again.');
      throw new Error('save failed');
    }
  };

  useImperativeHandle(ref, () => ({
    startEdit,
    cancelEdit,
    save: handleSave,
    isEditing: editing,
  }), [editing, draft, onSave]);

  const patchIdentity = (key, val) => {
    setDraft((d) => ({ ...d, identity: { ...d.identity, [key]: val } }));
  };

  const patchList = (key, val) => setDraft((d) => ({ ...d, [key]: val }));

  const patchAssets = (key, val) => {
    setDraft((d) => ({ ...d, data_assets: { ...d.data_assets, [key]: val } }));
  };

  const toggleGroup = (id) => {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const showToolbar = !hideToolbar && section !== 'timeline';

  const previewSourceFile = async (relativePath) => {
    if (!projectCode || !API_URL || !relativePath) return;
    setFilePreviewLoading(true);
    setFilePreview({ path: relativePath, content: null, error: null });
    try {
      const res = await fetch(
        `${API_URL}/api/project-files/read?project_code=${encodeURIComponent(projectCode)}&relative_path=${encodeURIComponent(relativePath)}`
      );
      if (res.ok) {
        const data = await res.json();
        setFilePreview({ path: relativePath, content: data.content || '', error: null });
      } else {
        const err = await res.json().catch(() => ({}));
        setFilePreview({ path: relativePath, content: null, error: err.detail || 'Could not load file.' });
      }
    } catch (e) {
      setFilePreview({ path: relativePath, content: null, error: String(e.message || e) });
    } finally {
      setFilePreviewLoading(false);
    }
  };

  return (
    <div className={`digital-twin-panel ${editing ? 'is-editing' : ''}`}>
      {showToolbar && (
        <div className="dt-toolbar">
          <div className="dt-toolbar-left">
            {!editing ? (
              <button type="button" className="btn btn-secondary btn-sm" onClick={startEdit}>
                <Edit3 size={14} /> Edit
              </button>
            ) : (
              <>
                <button type="button" className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
                  <Save size={14} /> {saving ? 'Saving…' : 'Save'}
                </button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={cancelEdit} disabled={saving}>
                  <X size={14} /> Cancel
                </button>
                <span className="dt-edit-hint">Unsaved changes — click Save to persist</span>
              </>
            )}
          </div>
          {saveMsg && <span className="dt-save-msg">{saveMsg}</span>}
        </div>
      )}

      {visibleGroups.map((group) => {
        const open = openGroups.has(group.id);
        let count = null;
        if (group.id === 'content') count = twin.total_assets_count || libTotal;
        if (group.id === 'team') count = (display.personnel?.length || 0) + (display.cohorts?.length || 0);
        if (group.id === 'outputs') count = outputs.length;
        if (group.id === 'activity') count = display.timeline?.length;

        return (
          <section key={group.id} className="dt-group panel">
            <GroupHeader group={group} open={open} onToggle={() => toggleGroup(group.id)} count={count} />
            {!open ? null : (
              <div className="dt-group-body">
                {group.id === 'content' && projectCode && API_URL && (
                  <ProjectContentLibrary twin={display} projectCode={projectCode} API_URL={API_URL} />
                )}

                {group.id === 'research' && (
                  <>
                    <div className="dt-field-grid">
                      <Field label="Project code" value={display.identity?.project_code} readOnly />
                      <Field label="Project lead" value={display.identity?.project_lead} editing={editing} onChange={(v) => patchIdentity('project_lead', v)} />
                      <Field label="Principal investigator" value={display.identity?.principal_investigator} editing={editing} onChange={(v) => patchIdentity('principal_investigator', v)} />
                      <Field label="Disease focus" value={display.identity?.disease_focus} editing={editing} onChange={(v) => patchIdentity('disease_focus', v)} />
                      <Field label="Status" value={display.identity?.status} editing={editing} onChange={(v) => patchIdentity('status', v)} />
                      <Field label="Priority" value={display.identity?.priority} editing={editing} onChange={(v) => patchIdentity('priority', v)} />
                      <Field label="Category" value={display.identity?.category_label || display.identity?.category} readOnly />
                      <Field label="Timeline" value={display.identity?.timeline} editing={editing} onChange={(v) => patchIdentity('timeline', v)} />
                    </div>
                    {(display.identity?.research_question || editing) && (
                      <Field label="Research question" value={display.identity?.research_question} editing={editing} onChange={(v) => patchIdentity('research_question', v)} multiline />
                    )}
                    <Field label="Summary" value={display.identity?.project_summary} editing={editing} onChange={(v) => patchIdentity('project_summary', v)} multiline />
                  </>
                )}

                {group.id === 'team' && (
                  <>
                    {section === 'overview' && !editing ? (
                      <p className="text-footnote muted">
                        Team and cohort batches are shown in the project vitals card above. Expand Edit to update roster data.
                      </p>
                    ) : (
                      <>
                    <h4 className="dt-subheading"><Users size={16} /> Team</h4>
                    <table className="digital-twin-table">
                      <thead><tr><th>Name</th><th>Role</th>{editing && <th />}</tr></thead>
                      <tbody>
                        {(display.personnel || []).map((p, i) => (
                          <tr key={i}>
                            <td>{editing ? <input className="form-input dt-input-sm" value={p.name} onChange={(e) => { const next = [...draft.personnel]; next[i] = { ...p, name: e.target.value }; patchList('personnel', next); }} /> : <b>{p.name}</b>}</td>
                            <td>{editing ? <input className="form-input dt-input-sm" value={p.role} onChange={(e) => { const next = [...draft.personnel]; next[i] = { ...p, role: e.target.value, focus: e.target.value }; patchList('personnel', next); }} /> : p.role}</td>
                            {editing && (
                              <td>
                                <button type="button" className="btn-icon danger" onClick={() => patchList('personnel', draft.personnel.filter((_, j) => j !== i))}><Trash2 size={14} /></button>
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {editing && (
                      <button type="button" className="btn btn-secondary btn-sm dt-add-row" onClick={() => patchList('personnel', [...(draft.personnel || []), { name: '', role: '', focus: '' }])}>
                        <Plus size={14} /> Add member
                      </button>
                    )}

                    <h4 className="dt-subheading"><Database size={16} /> Cohort batches</h4>
                    <table className="digital-twin-table">
                      <thead><tr><th>Batch</th><th>Samples</th><th>Description</th>{editing && <th />}</tr></thead>
                      <tbody>
                        {(display.cohorts || []).map((c, i) => (
                          <tr key={i}>
                            <td>{editing ? <input className="form-input dt-input-sm" value={c.batch_id} onChange={(e) => { const next = [...draft.cohorts]; next[i] = { ...c, batch_id: e.target.value }; patchList('cohorts', next); }} /> : <b>{c.batch_id}</b>}</td>
                            <td>{editing ? <input className="form-input dt-input-sm" type="number" value={c.sample_count ?? ''} onChange={(e) => { const next = [...draft.cohorts]; next[i] = { ...c, sample_count: e.target.value ? Number(e.target.value) : null }; patchList('cohorts', next); }} /> : formatSampleCount(c.sample_count)}</td>
                            <td className="wrap">{editing ? <input className="form-input dt-input-sm" value={c.description || ''} onChange={(e) => { const next = [...draft.cohorts]; next[i] = { ...c, description: e.target.value }; patchList('cohorts', next); }} /> : (c.description?.slice(0, 120) || '—')}</td>
                            {editing && (
                              <td><button type="button" className="btn-icon danger" onClick={() => patchList('cohorts', draft.cohorts.filter((_, j) => j !== i))}><Trash2 size={14} /></button></td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {editing && (
                      <button type="button" className="btn btn-secondary btn-sm dt-add-row" onClick={() => patchList('cohorts', [...(draft.cohorts || []), { batch_id: 'New batch', sample_count: null, description: '', exclusions: [] }])}>
                        <Plus size={14} /> Add cohort
                      </button>
                    )}
                      </>
                    )}
                  </>
                )}

                {group.id === 'methods' && (
                  <>
                    <h4 className="dt-subheading"><FlaskConical size={16} /> Modalities</h4>
                    {editing ? (
                      <textarea
                        className="form-input dt-input"
                        rows={2}
                        value={(display.modalities || []).map((m) => (typeof m === 'string' ? m : m.name)).join(', ')}
                        onChange={(e) => patchList('modalities', e.target.value.split(',').map((s) => s.trim()).filter(Boolean).map((name) => ({ name, type: 'assay', description: '' })))}
                        placeholder="tCycIF, GeoMx, WES"
                      />
                    ) : (
                      <div className="project-card-tags">
                        {(display.modalities || []).map((m) => (
                          <span key={m.name || m} className="project-tag modality">{m.name || m}</span>
                        ))}
                      </div>
                    )}

                    <div className="grid-2col dt-assets-grid" style={{ marginTop: '1rem' }}>
                      <div className="panel" style={{ padding: '1.25rem' }}>
                        <h4 className="dt-subheading" style={{ marginTop: 0 }}><FolderOpen size={16} /> Storage paths</h4>
                        {editing ? (
                          <textarea className="form-input dt-input" rows={4} value={(display.data_assets?.storage_paths || []).join('\n')} onChange={(e) => patchAssets('storage_paths', e.target.value.split('\n').map((s) => s.trim()).filter(Boolean))} />
                        ) : (
                          <ul className="smart-link-list">
                            {(display.data_assets?.storage_paths || []).map((p) => (
                              <li key={p} style={{ marginBottom: '0.4rem', wordBreak: 'break-all' }}>
                                <SmartLink href={p} showCopy maxLabelLen={56} />
                              </li>
                            ))}
                            {!display.data_assets?.storage_paths?.length && <li className="muted">None</li>}
                          </ul>
                        )}
                      </div>
                      <div className="panel" style={{ padding: '1.25rem' }}>
                        <h4 className="dt-subheading" style={{ marginTop: 0 }}><GitBranch size={16} /> Repositories</h4>
                        {editing ? (
                          <textarea className="form-input dt-input" rows={4} value={(display.data_assets?.repositories || []).join('\n')} onChange={(e) => patchAssets('repositories', e.target.value.split('\n').map((s) => s.trim()).filter(Boolean))} />
                        ) : (
                          <ul className="smart-link-list">
                            {(display.data_assets?.repositories || []).map((url) => (
                              <li key={url} style={{ marginBottom: '0.4rem', wordBreak: 'break-all' }}>
                                <SmartLink href={url} showCopy maxLabelLen={56} />
                              </li>
                            ))}
                            {!display.data_assets?.repositories?.length && <li className="muted">None</li>}
                          </ul>
                        )}
                      </div>
                    </div>

                    {(display.data_assets?.folder_tree?.length > 0) && (
                      <>
                        <h4 className="dt-subheading"><FolderOpen size={16} /> Folder inventory</h4>
                        <table className="digital-twin-table compact">
                          <thead><tr><th>Path</th><th>Files</th><th>Categories</th></tr></thead>
                          <tbody>
                            {(display.data_assets.folder_tree || []).filter((f) => f.path !== '.').map((f) => (
                              <tr key={f.path}>
                                <td className="mono wrap">{f.path}</td>
                                <td>{f.file_count}</td>
                                <td>{f.categories?.join(', ') || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </>
                    )}

                    {(display.protocols?.length > 0 || section === 'protocols') && (
                      <>
                        <h4 className="dt-subheading">Protocol index</h4>
                        <table className="digital-twin-table compact">
                          <thead><tr><th>Protocol</th><th>Category</th><th>Source</th></tr></thead>
                          <tbody>
                            {(display.protocols || []).map((p) => (
                              <tr key={p.source_file}>
                                <td><b>{p.title}</b></td>
                                <td className="wrap">{p.category}</td>
                                <td className="wrap">
                                  <SmartLink href={p.source_file} onFileClick={previewSourceFile} showCopy />
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </>
                    )}
                  </>
                )}

                {group.id === 'outputs' && (
                  outputs.length === 0 ? (
                    <p className="muted">No publications or abstracts indexed.</p>
                  ) : (
                    <table className="digital-twin-table">
                      <thead><tr><th>Title</th><th>Venue</th><th>Year</th><th>Type</th>{editing && <th />}</tr></thead>
                      <tbody>
                        {outputs.map((item, i) => (
                          <tr key={item.source_file || item.title || i}>
                            <td>{editing ? <input className="form-input dt-input-sm" value={item.title} onChange={(e) => { const next = [...(draft.outputs || outputs)]; next[i] = { ...item, title: e.target.value }; patchList('outputs', next); }} /> : <b>{item.title}</b>}</td>
                            <td>{editing ? <input className="form-input dt-input-sm" value={item.conference || ''} onChange={(e) => { const next = [...(draft.outputs || outputs)]; next[i] = { ...item, conference: e.target.value }; patchList('outputs', next); }} /> : (item.conference || '—')}</td>
                            <td>{editing ? <input className="form-input dt-input-sm" type="number" value={item.year ?? ''} onChange={(e) => { const next = [...(draft.outputs || outputs)]; next[i] = { ...item, year: e.target.value ? Number(e.target.value) : null }; patchList('outputs', next); }} /> : (item.year || '—')}</td>
                            <td><span className="dt-badge">{item.type || 'abstract'}</span></td>
                            {editing && (
                              <td><button type="button" className="btn-icon danger" onClick={() => patchList('outputs', (draft.outputs || outputs).filter((_, j) => j !== i))}><Trash2 size={14} /></button></td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )
                )}

                {group.id === 'activity' && (
                  <ActivityLog timeline={display.timeline || []} onOpenFile={previewSourceFile} />
                )}
              </div>
            )}
          </section>
        );
      })}

      {filePreview && (
        <div className="panel dt-file-preview-panel">
          <h4 className="dt-subheading">
            File preview: <SmartLink href={filePreview.path} showCopy />
          </h4>
          {filePreviewLoading && <p className="text-loading">Loading…</p>}
          {filePreview.error && <p className="text-callout">{filePreview.error}</p>}
          {filePreview.content && (
            <div style={{ marginTop: '1rem', padding: '1.5rem', background: 'var(--mac-bg-primary)', border: '1px solid var(--mac-border)', borderRadius: '6px' }}>
              <DocumentFormatter 
                text={filePreview.content.slice(0, 8000) + (filePreview.content.length > 8000 ? '…' : '')} 
                onCreateTask={(text) =>
                  openTaskpad(text, {
                    projectCode,
                    section:
                      section === 'overview'
                        ? 'overview'
                        : section === 'abstracts'
                          ? 'writing'
                          : section === 'catalog'
                            ? 'data'
                            : section === 'protocols' || section === 'content'
                              ? 'methods'
                              : section === 'timeline'
                                ? 'log'
                                : 'overview',
                    filePath: filePreview?.path,
                    fileName: filePreview?.path?.split('/').pop(),
                  })
                }
              />
            </div>
          )}
          <button type="button" className="btn btn-secondary btn-sm" style={{ marginTop: '1rem' }} onClick={() => setFilePreview(null)}>Close preview</button>
        </div>
      )}
    </div>
  );
});

export default DigitalTwinPanel;

function ActivityLog({ timeline, onOpenFile }) {
  const [filter, setFilter] = useState('all');
  const categories = useMemo(() => {
    const set = new Set(timeline.map((e) => e.category).filter(Boolean));
    return ['all', ...Array.from(set).sort()];
  }, [timeline]);

  const filtered = filter === 'all' ? timeline : timeline.filter((e) => e.category === filter);

  return (
    <>
      <div className="digital-twin-filter-bar">
        {categories.map((cat) => (
          <button key={cat} type="button" className={`btn btn-sm ${filter === cat ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setFilter(cat)}>
            {cat === 'all' ? 'All' : cat}
          </button>
        ))}
      </div>
      <div className="digital-twin-timeline">
        {filtered.length === 0 ? (
          <p className="muted">No timeline entries.</p>
        ) : (
          filtered.map((entry) => (
            <article key={`${entry.date}-${entry.title}-${entry.source_file}`} className="dt-timeline-card">
              <div className="dt-timeline-meta">
                <span className="dt-date"><Calendar size={14} /> {entry.date}</span>
                <span className="dt-badge" style={{ borderColor: categoryColor(entry.category) }}>{entry.category}</span>
              </div>
              <h4 className="dt-timeline-title">{entry.title}</h4>
              {entry.summary ? (
                <ExpandableText maxLength={280} className="dt-timeline-summary">
                  {entry.summary}
                </ExpandableText>
              ) : null}
              {entry.source_file && onOpenFile && (
                <div className="dt-timeline-source">
                  <span className="text-footnote muted">Source</span>
                  <SmartLink href={entry.source_file} onFileClick={onOpenFile} showCopy />
                </div>
              )}
            </article>
          ))
        )}
      </div>
    </>
  );
}
