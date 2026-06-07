import { useState } from 'react';
import { Play } from 'lucide-react';

export function RunPipelineTab({ dbProjects, API_URL }) {
  const [pipeline, setPipeline] = useState('stitching');
  const [project, setProject] = useState('SPACE');
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/run_checker`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          check_type: `run_${pipeline}_pipeline`,
          options: { project_code: project },
        }),
      });
      if (res.ok) {
        setResult(await res.json());
      }
    } catch (e) {
      setResult({ status: 'error', details: String(e) });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="panel" style={{ maxWidth: '650px' }}>
      <h3 className="panel-title"><Play size={18} /> Trigger spatial biology pipeline (LUMI)</h3>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Launch Ashlar stitching, Stardist segmentation, or Cylinter gating checks against a project cohort on cluster infrastructure.
      </p>
      <div className="form-group">
        <label className="form-label">Select pipeline action</label>
        <select className="form-select" value={pipeline} onChange={(e) => setPipeline(e.target.value)}>
          <option value="stitching">Ashlar image stitching &amp; registration</option>
          <option value="segmentation">Stardist segmentations &amp; mask extraction</option>
          <option value="gating">Cylinter ROI gating &amp; mask normalizations</option>
        </select>
      </div>
      <div className="form-group">
        <label className="form-label">Target cohort project</label>
        <select className="form-select" value={project} onChange={(e) => setProject(e.target.value)}>
          {dbProjects.map((p) => (
            <option key={p.project_code} value={p.project_code}>{p.project_code}</option>
          ))}
        </select>
      </div>
      <button type="button" className="btn btn-primary" onClick={handleRun} disabled={running}>
        {running ? 'Executing pipeline on cluster…' : '🚀 Launch pipeline run'}
      </button>

      {result && (
        <div className="surface-inset" style={{ marginTop: '1.5rem', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <h4 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>Execution result</h4>
          <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--color-success)', overflowX: 'auto' }}>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default RunPipelineTab;
