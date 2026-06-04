import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import { Plus, CheckSquare } from 'lucide-react';

export default function TasksScreen({ dbProjects, API_URL, categoryFilter = null, hideHeader = false }) {
  const [tasks, setTasks] = useState([]);
  const [tProj, setTProj] = useState(dbProjects[0]?.project_code || 'SPACE');
  const [tTitle, setTTitle] = useState('');
  const [tDesc, setTDesc] = useState('');
  const [tCat, setTCat] = useState(categoryFilter || 'Data_Analysis');
  const [tAss, setTAss] = useState('Aleksandra');

  useEffect(() => {
    fetchTasks();
  }, []);

  useEffect(() => {
    if (dbProjects.length > 0 && !dbProjects.some((p) => p.project_code === tProj)) {
      setTProj(dbProjects[0].project_code);
    }
  }, [dbProjects, tProj]);

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${API_URL}/tasks`);
      if (res.ok) {
        setTasks(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_code: tProj,
          title: tTitle,
          description: tDesc,
          category: tCat,
          status: 'todo',
          assignee: tAss
        })
      });
      if (res.ok) {
        alert("Task registered successfully!");
        setTTitle('');
        setTDesc('');
        fetchTasks();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateStatus = async (task, nextStatus) => {
    try {
      const res = await fetch(`${API_URL}/tasks/${task.task_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...task,
          status: nextStatus
        })
      });
      if (res.ok) {
        fetchTasks();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const visibleTasks = categoryFilter
    ? tasks.filter((t) => (t.category || '').toLowerCase() === categoryFilter.toLowerCase())
    : tasks;

  return (
    <div>
      {!hideHeader && (
        <div className="page-header">
          <h1 className="page-title-gradient">Lab Tasks Planner</h1>
          <p className="page-subtitle">Delegate cell-phenotyping updates, image-registration mask reruns, and metadata checks.</p>
        </div>
      )}

      <div className="grid-2col">
        <div className="panel">
          <h3 className="panel-title"><Plus size={18} /> Create New Task</h3>
          <form onSubmit={handleCreateTask} className="stack-lg">
            <div className="form-group">
              <label className="form-label">Project Code</label>
              <select className="form-select" value={tProj} onChange={(e) => setTProj(e.target.value)}>
                {dbProjects.map(p => (
                  <option key={p.project_code} value={p.project_code}>{p.project_code}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Task Title</label>
              <input type="text" className="form-input" required value={tTitle} onChange={(e) => setTTitle(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea className="form-textarea" required value={tDesc} onChange={(e) => setTDesc(e.target.value)} style={{height: '90px'}} />
            </div>
            <div className="grid-2col" style={{marginBottom: 0}}>
              <div className="form-group">
                <label className="form-label">Category</label>
                <select className="form-select" value={tCat} onChange={(e) => setTCat(e.target.value)}>
                  <option value="Data_Analysis">Data Analysis</option>
                  <option value="Wet_Lab">Wet Lab</option>
                  <option value="Image_QC">Image QC</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Assignee</label>
                <select className="form-select" value={tAss} onChange={(e) => setTAss(e.target.value)}>
                  <option value="Aleksandra">Aleksandra</option>
                  <option value="Iga">Iga</option>
                  <option value="Saundarya">Saundarya</option>
                  <option value="Zhihan">Zhihan</option>
                  <option value="Elias">Elias</option>
                </select>
              </div>
            </div>
            <button type="submit" className="btn btn-primary">Create Task</button>
          </form>
        </div>

        <div className="panel">
          <h3 className="panel-title"><CheckSquare size={18} /> Tasks Checklist</h3>
          <div className="feed-scroll">
            {visibleTasks.map(t => (
              <div key={t.task_id} className="feed-item">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '0.35rem' }}>
                  <span className="feed-item-title">{t.title}</span>
                  <span className="text-caption">{t.project_code} · {t.assignee}</span>
                </div>
                <p className="feed-item-body" style={{ marginBottom: '0.75rem' }}>{t.description}</p>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <span className="text-subhead">Status: <strong>{t.status.replace('_', ' ')}</strong></span>
                  {t.status !== 'completed' && (
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleUpdateStatus(t, 'completed')}>Complete</button>
                  )}
                  {t.status === 'todo' && (
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleUpdateStatus(t, 'in_progress')}>Start</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
