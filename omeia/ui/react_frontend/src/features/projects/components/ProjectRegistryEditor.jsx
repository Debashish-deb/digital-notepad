import { forwardRef, useEffect, useImperativeHandle, useState } from 'react';
import { useGuiT } from '@/i18n/useGuiT.js';

const ProjectRegistryEditor = forwardRef(function ProjectRegistryEditor(
  { projectData, API_URL, onSaved },
  ref,
) {
  const { t } = useGuiT();
  const [shortTitle, setShortTitle] = useState('');
  const [question, setQuestion] = useState('');
  const [type, setType] = useState('spatial_profiling');
  const [priority, setPriority] = useState('medium');
  const [ethics, setEthics] = useState('');
  const [blockers, setBlockers] = useState('');
  const [nextActions, setNextActions] = useState('');
  const [summary, setSummary] = useState('');
  const [latestUpdate, setLatestUpdate] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!projectData) return;
    setShortTitle(projectData.project_short_title || '');
    setQuestion(projectData.research_question || '');
    setType(projectData.project_type || 'spatial_profiling');
    setPriority(projectData.priority || 'medium');
    setEthics(projectData.ethics_approval_reference || '');
    setBlockers(projectData.current_blockers || '');
    setNextActions(projectData.next_actions || '');
    setSummary(projectData.project_summary || '');
    setLatestUpdate(projectData.latest_update || '');
  }, [projectData]);

  const save = async () => {
    if (!projectData?.project_code) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/projects/${projectData.project_code}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_short_title: shortTitle,
          research_question: question,
          project_type: type,
          priority,
          ethics_approval_reference: ethics,
          current_blockers: blockers,
          next_actions: nextActions,
          project_summary: summary,
          latest_update: latestUpdate,
        }),
      });
      if (!res.ok) throw new Error('registry save failed');
      await onSaved?.();
    } finally {
      setSaving(false);
    }
  };

  useImperativeHandle(ref, () => ({ save, saving }), [saving, projectData, shortTitle, question, type, priority, ethics, blockers, nextActions, summary, latestUpdate]);

  return (
    <div className="project-registry-editor stack-lg">
      <p className="text-footnote muted" style={{ margin: 0 }}>
        {t(
          'taskbar.registryHint',
          'Database registry fields — priority, blockers, and status notes.',
        )}
      </p>

      <div className="grid-2col" style={{ marginBottom: 0 }}>
        <div className="form-group">
          <label className="form-label">{t('taskbar.shortTitle', 'Short title')}</label>
          <input
            type="text"
            className="form-input"
            value={shortTitle}
            onChange={(e) => setShortTitle(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label">{t('taskbar.ethicsRef', 'Ethics reference')}</label>
          <input
            type="text"
            className="form-input"
            value={ethics}
            onChange={(e) => setEthics(e.target.value)}
          />
        </div>
      </div>

      <div className="grid-2col" style={{ marginBottom: 0 }}>
        <div className="form-group">
          <label className="form-label">{t('taskbar.projectType', 'Project type')}</label>
          <select className="form-select" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="spatial_profiling">Spatial Profiling</option>
            <option value="clinical_trial">Clinical Trial</option>
            <option value="pilot_study">Pilot Study</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">{t('taskbar.priority', 'Priority')}</label>
          <select className="form-select" value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">{t('taskbar.researchQuestion', 'Research question')}</label>
        <textarea className="form-textarea" value={question} onChange={(e) => setQuestion(e.target.value)} />
      </div>

      <div className="form-group">
        <label className="form-label">{t('taskbar.projectSummary', 'Project summary')}</label>
        <textarea className="form-textarea" value={summary} onChange={(e) => setSummary(e.target.value)} />
      </div>

      <div className="grid-2col" style={{ marginBottom: 0 }}>
        <div className="form-group">
          <label className="form-label">{t('taskbar.blockers', 'Current blockers')}</label>
          <textarea className="form-textarea" value={blockers} onChange={(e) => setBlockers(e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label">{t('taskbar.nextActions', 'Next actions')}</label>
          <textarea className="form-textarea" value={nextActions} onChange={(e) => setNextActions(e.target.value)} />
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">{t('taskbar.latestUpdate', 'Latest activity update')}</label>
        <input
          type="text"
          className="form-input"
          value={latestUpdate}
          onChange={(e) => setLatestUpdate(e.target.value)}
        />
      </div>
    </div>
  );
});

export default ProjectRegistryEditor;
