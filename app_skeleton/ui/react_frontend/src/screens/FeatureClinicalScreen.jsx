import './MacPlusVisualStyles.css';
import React, { useEffect, useState } from 'react';
import { Database, GitCompare, LineChart, Search, Sparkles, Play, RefreshCw } from 'lucide-react';

const FEATURES = [
  'tumor_cell_density',
  'immune_infiltration_score',
  'cd8_tcell_density',
  'tls_proximity_score',
  'stroma_caf_fraction',
  'hrd_signature_score',
];

const SAMPLES = [
  'SYNTH_SAMPLE_001', 'SYNTH_SAMPLE_002', 'SYNTH_SAMPLE_003',
  'SYNTH_SAMPLE_004', 'SYNTH_SAMPLE_005',
];

export default function FeatureClinicalScreen({ API_URL, dbProjects, hideHeader = false }) {
  const [tab, setTab] = useState('features');
  const [definitions, setDefinitions] = useState([]);
  const [matrices, setMatrices] = useState([]);
  const [variables, setVariables] = useState([]);
  const [runs, setRuns] = useState([]);
  const [projectCode, setProjectCode] = useState('SPACE');
  const [sampleCode, setSampleCode] = useState('SYNTH_SAMPLE_001');
  const [similar, setSimilar] = useState(null);
  const [survival, setSurvival] = useState(null);
  const [groupResult, setGroupResult] = useState(null);
  const [featureCol, setFeatureCol] = useState('immune_infiltration_score');
  const [groupCol, setGroupCol] = useState('hrd_status');
  const [loading, setLoading] = useState(false);
  const [seedMsg, setSeedMsg] = useState(null);

  const loadBase = async () => {
    try {
      const [d, m, v, r] = await Promise.all([
        fetch(`${API_URL}/features/definitions`).then((x) => x.ok ? x.json() : { features: [] }),
        fetch(`${API_URL}/features/matrices`).then((x) => x.ok ? x.json() : { matrices: [] }),
        fetch(`${API_URL}/clinical/variables`).then((x) => x.ok ? x.json() : { variables: [] }),
        fetch(`${API_URL}/analysis-runs`).then((x) => x.ok ? x.json() : { runs: [] }),
      ]);
      setDefinitions(d.features || []);
      setMatrices(m.matrices || []);
      setVariables(v.variables || []);
      setRuns(r.runs || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => { loadBase(); }, [API_URL]);

  const handleSeed = async () => {
    setLoading(true);
    setSeedMsg(null);
    try {
      const res = await fetch(`${API_URL}/features/seed`, { method: 'POST' });
      const data = await res.json();
      setSeedMsg(res.ok ? `Seeded ${data.features} features, ${data.vectors} vectors` : (data.detail || 'Seed failed'));
      loadBase();
    } catch (e) {
      setSeedMsg(String(e));
    } finally {
      setLoading(false);
    }
  };

  const runSimilarity = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/features/similarity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sample_code: sampleCode, project_code: projectCode, limit: 5 }),
      });
      setSimilar(res.ok ? await res.json() : null);
      loadBase();
    } finally {
      setLoading(false);
    }
  };

  const runSurvival = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/clinical/survival`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_code: projectCode, group_col: 'brca_status' }),
      });
      setSurvival(res.ok ? await res.json() : null);
      loadBase();
    } finally {
      setLoading(false);
    }
  };

  const runGroupCompare = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/clinical/group-compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feature_col: featureCol, group_col: groupCol, project_code: projectCode }),
      });
      setGroupResult(res.ok ? await res.json() : null);
      loadBase();
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'features', label: 'Feature registry', icon: Database },
    { id: 'similarity', label: 'Similarity search', icon: Search },
    { id: 'survival', label: 'Survival analysis', icon: LineChart },
    { id: 'compare', label: 'Group comparison', icon: GitCompare },
    { id: 'runs', label: 'Analysis runs', icon: Sparkles },
  ];

  return (
    <div>
      {!hideHeader ? (
        <div className="page-header-row">
          <div className="page-header">
            <h1 className="page-title-gradient">Feature Warehouse & Clinical Stats</h1>
            <p className="page-subtitle">
              Phase 3–4: sample-level spatial features, similarity search, survival curves, and group comparisons on the synthetic pilot cohort.
            </p>
          </div>
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleSeed} disabled={loading}>
            <RefreshCw size={14} /> Seed warehouse
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleSeed} disabled={loading}>
            <RefreshCw size={14} /> Seed warehouse
          </button>
        </div>
      )}

      {seedMsg && <p className="text-callout" style={{ marginBottom: '1rem' }}>{seedMsg}</p>}

      <div className="form-group" style={{ maxWidth: 280, marginBottom: '1rem' }}>
        <label className="form-label">Project scope</label>
        <select className="form-select" value={projectCode} onChange={(e) => setProjectCode(e.target.value)}>
          {[...new Set(['SPACE', 'EyeMT', 'KRAS', ...(dbProjects || []).map((p) => p.project_code)])].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="tab-bar">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" className={`btn btn-sm ${tab === id ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab(id)}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {tab === 'features' && (
        <div className="grid-2col">
          <div className="panel">
            <h3 className="panel-title">Feature definitions ({definitions.length})</h3>
            <div className="feed-scroll" style={{ maxHeight: 420 }}>
              {definitions.map((f) => (
                <div key={f.feature_name} className="feed-item">
                  <div className="feed-item-title">{f.display_name || f.feature_name}</div>
                  <div className="feed-item-meta">{f.feature_group} · {f.entity_level} · {f.source_modality}</div>
                  <div className="text-footnote">{f.unit ? `Unit: ${f.unit}` : ''}</div>
                </div>
              ))}
              {!definitions.length && <p className="text-footnote">No features loaded — click Seed warehouse.</p>}
            </div>
          </div>
          <div className="panel">
            <h3 className="panel-title">Feature matrices ({matrices.length})</h3>
            {matrices.map((m) => (
              <div key={m.matrix_code} className="feed-item" style={{ marginBottom: '0.75rem' }}>
                <div className="feed-item-title">{m.matrix_name || m.matrix_code}</div>
                <div className="feed-item-meta">{m.entity_level} · {m.row_count} rows · {m.feature_count} features · QC: {m.qc_status}</div>
              </div>
            ))}
            <h3 className="panel-title" style={{ marginTop: '1.5rem' }}>Clinical variables ({variables.length})</h3>
            <div className="feed-scroll" style={{ maxHeight: 200 }}>
              {variables.map((v) => (
                <div key={v.variable_name} className="text-subhead">{v.display_name || v.variable_name} <span className="text-caption">({v.data_type})</span></div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'similarity' && (
        <div className="panel">
          <h3 className="panel-title">Find similar samples (Qdrant spatial_feature_profiles)</h3>
          <div className="grid-2col" style={{ marginBottom: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Query sample</label>
              <select className="form-select" value={sampleCode} onChange={(e) => setSampleCode(e.target.value)}>
                {SAMPLES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <button type="button" className="btn btn-primary" onClick={runSimilarity} disabled={loading}>
            <Play size={14} /> Run similarity
          </button>
          {similar && (
            <table className="digital-twin-table" style={{ marginTop: '1rem' }}>
              <thead><tr><th>Sample</th><th>Project</th><th>Similarity</th></tr></thead>
              <tbody>
                {(similar.similar || []).map((s) => (
                  <tr key={s.sample_code}><td>{s.sample_code}</td><td>{s.project_code}</td><td>{s.similarity_score}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === 'survival' && (
        <div className="panel">
          <h3 className="panel-title">Kaplan-Meier survival (synthetic cohort)</h3>
          <p className="panel-lead">Grouped by BRCA status · PFS duration · results logged to analysis run registry.</p>
          <button type="button" className="btn btn-primary" onClick={runSurvival} disabled={loading}>
            <Play size={14} /> Run survival analysis
          </button>
          {survival && (
            <div style={{ marginTop: '1rem' }}>
              <pre className="prose-block text-mono" style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                {JSON.stringify(survival.groups, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {tab === 'compare' && (
        <div className="panel">
          <h3 className="panel-title">Spatial feature group comparison</h3>
          <div className="grid-2col" style={{ marginBottom: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Feature</label>
              <select className="form-select" value={featureCol} onChange={(e) => setFeatureCol(e.target.value)}>
                {FEATURES.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Group by</label>
              <select className="form-select" value={groupCol} onChange={(e) => setGroupCol(e.target.value)}>
                <option value="hrd_status">HRD status</option>
                <option value="brca_status">BRCA status</option>
                <option value="platinum_response">Platinum response</option>
              </select>
            </div>
          </div>
          <button type="button" className="btn btn-primary" onClick={runGroupCompare} disabled={loading}>
            <Play size={14} /> Compare groups
          </button>
          {groupResult && (
            <pre className="prose-block text-mono" style={{ marginTop: '1rem', whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
              {JSON.stringify(groupResult, null, 2)}
            </pre>
          )}
        </div>
      )}

      {tab === 'runs' && (
        <div className="panel">
          <h3 className="panel-title">Analysis run registry</h3>
          <div className="feed-scroll">
            {runs.map((r) => (
              <div key={r.run_code} className="feed-item">
                <div className="feed-item-title">{r.title || r.run_code}</div>
                <div className="feed-item-meta">{r.analysis_type} · {r.project_code || 'all'} · {r.created_at?.slice(0, 16)}</div>
              </div>
            ))}
            {!runs.length && <p className="text-footnote">No analysis runs yet — run survival or similarity above.</p>}
          </div>
        </div>
      )}
    </div>
  );
}
