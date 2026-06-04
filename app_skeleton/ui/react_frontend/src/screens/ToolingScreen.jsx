import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import { Play } from 'lucide-react';
import {
  InstallSoftwareTab,
  LumiJobTab,
  DiagnosticsTab,
  TroubleshooterTab,
} from './BioinformaticsHubScreen';

export default function ToolingScreen({
  dbProjects,
  API_URL,
  embedded = false,
  initialSubTab = 'pipeline',
  titleOverride,
  subtitleOverride,
}) {
  const [subTab, setSubTab] = useState(initialSubTab);

  useEffect(() => {
    setSubTab(initialSubTab);
  }, [initialSubTab]);

  return (
    <div>
      {!embedded && (
        <div className="page-header">
          <h1 className="page-title-gradient">{titleOverride || 'System Tools & Utility Console'}</h1>
          <p className="page-subtitle">
            {subtitleOverride || 'Configure Slurm scheduling, trigger registration scripts, diagnostic checks, and troubleshooting.'}
          </p>
        </div>
      )}

      {!embedded && (
      <div className="tabs-header">
        <button className={`tab-button ${subTab === 'pipeline' ? 'active' : ''}`} onClick={() => setSubTab('pipeline')}>
          🚀 Trigger Pipeline
        </button>
        <button className={`tab-button ${subTab === 'install' ? 'active' : ''}`} onClick={() => setSubTab('install')}>
          ⚙️ Install SOP Software
        </button>
        <button className={`tab-button ${subTab === 'lumi' ? 'active' : ''}`} onClick={() => setSubTab('lumi')}>
          💻 Slurm Job Script
        </button>
        <button className={`tab-button ${subTab === 'diagnostics' ? 'active' : ''}`} onClick={() => setSubTab('diagnostics')}>
          🩺 Env Diagnostic
        </button>
        <button className={`tab-button ${subTab === 'troubleshoot' ? 'active' : ''}`} onClick={() => setSubTab('troubleshoot')}>
          🔍 Troubleshoot Logs
        </button>
      </div>
      )}

      <div style={{ marginTop: embedded ? 0 : '1.5rem' }}>
        {subTab === 'pipeline' && <RunPipelineTab dbProjects={dbProjects} API_URL={API_URL} />}
        {subTab === 'install' && <InstallSoftwareTab API_URL={API_URL} />}
        {subTab === 'lumi' && <LumiJobTab dbProjects={dbProjects} API_URL={API_URL} />}
        {subTab === 'diagnostics' && <DiagnosticsTab API_URL={API_URL} />}
        {subTab === 'troubleshoot' && <TroubleshooterTab API_URL={API_URL} />}
      </div>
    </div>
  );
}

// --- SUB-TABS ---

function RunPipelineTab({ dbProjects, API_URL }) {
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
          options: { project_code: project }
        })
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
    <div className="panel" style={{maxWidth: '650px'}}>
      <h3 className="panel-title"><Play size={18} /> Trigger Spatial Biology Image Pipeline</h3>
      <div className="form-group">
        <label className="form-label">Select Pipeline Action</label>
        <select className="form-select" value={pipeline} onChange={(e) => setPipeline(e.target.value)}>
          <option value="stitching">Ashlar Image Stitching & Registration</option>
          <option value="segmentation">Stardist Segmentations & Mask extraction</option>
          <option value="gating">Cylinter ROI Gating & Mask normalizations</option>
        </select>
      </div>
      <div className="form-group">
        <label className="form-label">Target Cohort Project</label>
        <select className="form-select" value={project} onChange={(e) => setProject(e.target.value)}>
          {dbProjects.map(p => (
            <option key={p.project_code} value={p.project_code}>{p.project_code}</option>
          ))}
        </select>
      </div>
      <button className="btn btn-primary" onClick={handleRun} disabled={running}>
        {running ? "Executing pipeline on local cluster..." : "🚀 Launch Pipeline Run"}
      </button>

      {result && (
        <div style={{marginTop: '1.5rem', background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
          <h4 style={{fontSize: '0.95rem', color: '#ffffff', marginBottom: '0.5rem'}}>Execution Result</h4>
          <pre style={{fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--color-success)', overflowX: 'auto'}}>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
