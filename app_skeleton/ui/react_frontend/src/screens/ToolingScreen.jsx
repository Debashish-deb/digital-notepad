
import React, { useState, useEffect } from 'react';
import {
  InstallSoftwareTab,
  LumiJobTab,
  DiagnosticsTab,
  TroubleshooterTab,
  RunPipelineTab,
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

