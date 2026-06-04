import './MacPlusVisualStyles.css';
import React, { useState, useMemo } from 'react';
import { Search, ChevronRight, FolderOpen, GitBranch, Users, Dna, Filter } from 'lucide-react';
import WorkspaceScreen from './WorkspaceScreen';
import { PROJECT_CATEGORIES } from '../data/projectsCatalog.js';

const STATUS_STYLES = {
  active: { bg: 'rgba(45,212,191,0.12)', color: 'var(--color-success)', label: 'Active' },
  completed: { bg: 'rgba(96,165,250,0.12)', color: '#60a5fa', label: 'Completed' },
  discontinued: { bg: 'rgba(148,163,184,0.12)', color: 'var(--text-muted)', label: 'Discontinued' },
};

const PRIORITY_DOT = {
  high: 'var(--color-danger)',
  medium: 'var(--color-warning)',
  low: 'var(--text-muted)',
  critical: 'var(--color-danger)',
};

function ProjectCard({ project, onOpen }) {
  const statusStyle = STATUS_STYLES[project.status] || STATUS_STYLES.active;
  const hasFolder = Boolean(project.folder_path);

  return (
    <div className="project-card">
      <div className="project-card-header">
        <div className="project-card-code-row">
          <span className="project-card-index">#{project.project_index}</span>
          <span className="project-card-code">{project.project_code}</span>
          <span
            className="project-card-priority"
            style={{ background: PRIORITY_DOT[project.priority] || PRIORITY_DOT.medium }}
            title={`${project.priority} priority`}
          />
        </div>
        <span className="project-card-status" style={{ background: statusStyle.bg, color: statusStyle.color }}>
          {statusStyle.label}
        </span>
      </div>

      <h4 className="project-card-title">{project.project_name}</h4>

      <p className="project-card-summary">
        {project.project_summary || project.research_question}
      </p>

      {project.modalities?.length > 0 && (
        <div className="project-card-tags">
          {project.modalities.slice(0, 4).map((m) => (
            <span key={m} className="project-tag modality">{m}</span>
          ))}
          {project.modalities.length > 4 && (
            <span className="project-tag">+{project.modalities.length - 4}</span>
          )}
        </div>
      )}

      <div className="project-card-meta">
        <div className="project-card-meta-row">
          <Dna size={13} />
          <span>{project.disease_focus}</span>
        </div>
        <div className="project-card-meta-row">
          <Users size={13} />
          <span>Lead: <strong>{project.project_lead}</strong></span>
        </div>
        {project.cohort_size && (
          <div className="project-card-meta-row">
            <Filter size={13} />
            <span>{project.cohort_size}</span>
          </div>
        )}
        {hasFolder ? (
          <div className="project-card-meta-row">
            <FolderOpen size={13} />
            <span className="project-folder-indicator">Workspace on disk</span>
          </div>
        ) : (
          <div className="project-card-meta-row">
            <FolderOpen size={13} />
            <span className="text-caption">Catalog only — no disk folder</span>
          </div>
        )}
        {project.repository && (
          <div className="project-card-meta-row">
            <GitBranch size={13} />
            <a href={project.repository} target="_blank" rel="noopener noreferrer" className="project-repo-link">
              Repository
            </a>
          </div>
        )}
      </div>

      <button className="btn btn-primary project-card-action" onClick={() => onOpen(project.project_code)}>
        Open Workspace <ChevronRight size={14} />
      </button>
    </div>
  );
}

export default function ProjectsScreen({ dbProjects, selectedProject, setSelectedProject, fetchProjects, API_URL }) {
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('All');
  const [filterCategory, setFilterCategory] = useState('All');
  const [viewMode, setViewMode] = useState('grouped');
  const [processing, setProcessing] = useState(false);
  const [processMsg, setProcessMsg] = useState(null);

  const filtered = useMemo(() => {
    return dbProjects.filter((p) => {
      const q = search.toLowerCase();
      const matchesSearch = !q ||
        p.project_code?.toLowerCase().includes(q) ||
        p.project_name?.toLowerCase().includes(q) ||
        p.project_lead?.toLowerCase().includes(q) ||
        p.principal_investigator?.toLowerCase().includes(q) ||
        (p.disease_focus || '').toLowerCase().includes(q) ||
        (p.project_summary || '').toLowerCase().includes(q) ||
        (p.modalities || []).some((m) => m.toLowerCase().includes(q));
      const matchesStatus = filterStatus === 'All' || p.status === filterStatus;
      const matchesCategory = filterCategory === 'All' || p.category === filterCategory;
      return matchesSearch && matchesStatus && matchesCategory;
    });
  }, [dbProjects, search, filterStatus, filterCategory]);

  const stats = useMemo(() => ({
    total: dbProjects.length,
    active: dbProjects.filter((p) => p.status === 'active').length,
    completed: dbProjects.filter((p) => p.status === 'completed').length,
    withFolder: dbProjects.filter((p) => p.folder_path).length,
  }), [dbProjects]);

  const grouped = useMemo(() => {
    const groups = {};
    for (const p of filtered) {
      const cat = p.category || 'spatial_omics';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(p);
    }
    for (const cat of Object.keys(groups)) {
      groups[cat].sort((a, b) => (a.project_index || 999) - (b.project_index || 999));
    }
    const order = ['flagship', 'spatial_omics', 'computational_tool', 'platform_model', 'clinical_collaboration', 'external_collaboration', 'genomics', 'infrastructure', 'support'];
    return order.filter((c) => groups[c]?.length).map((c) => ({ category: c, projects: groups[c] }));
  }, [filtered]);

  const categories = Object.entries(PROJECT_CATEGORIES);

  const handleProcessAll = async () => {
    setProcessing(true);
    setProcessMsg(null);
    try {
      const res = await fetch(`${API_URL}/api/projects/process-all`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setProcessMsg(`Processed ${data.processed} projects · synced ${data.synced_to_public} to frontend`);
        fetchProjects();
      } else {
        setProcessMsg(data.detail || 'Processing failed');
      }
    } catch (e) {
      setProcessMsg(String(e));
    } finally {
      setProcessing(false);
    }
  };

  if (selectedProject) {
    return (
      <WorkspaceScreen
        projectCode={selectedProject}
        onBack={() => { setSelectedProject(null); fetchProjects(); }}
        API_URL={API_URL}
        dbProjects={dbProjects}
      />
    );
  }

  return (
    <div className="projects-page">
      <div className="page-header">
        <h1 className="page-title-gradient">Research Project Portfolio</h1>
        <p className="page-subtitle">
          {stats.total} lab projects across spatial multi-omics, computational tools, patient-derived models, and external collaborations.
        </p>
      </div>

      <div className="projects-stats-bar">
        <div className="projects-stat"><span className="projects-stat-value">{stats.total}</span><span className="projects-stat-label">Total Projects</span></div>
        <div className="projects-stat"><span className="projects-stat-value">{stats.active}</span><span className="projects-stat-label">Active</span></div>
        <div className="projects-stat"><span className="projects-stat-value">{stats.completed}</span><span className="projects-stat-label">Completed</span></div>
        <div className="projects-stat"><span className="projects-stat-value">{stats.withFolder}</span><span className="projects-stat-label">With Workspace</span></div>
      </div>

      <div className="projects-toolbar">
        <div className="projects-search-wrap">
          <Search size={18} className="projects-search-icon" />
          <input
            type="text"
            placeholder="Search by code, title, lead, disease, modality..."
            className="form-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="form-select projects-filter" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="All">All Statuses</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="discontinued">Discontinued</option>
        </select>
        <select className="form-select projects-filter" value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}>
          <option value="All">All Categories</option>
          {categories.map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
        <div className="projects-view-toggle">
          <button className={`btn ${viewMode === 'grouped' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setViewMode('grouped')}>Grouped</button>
          <button className={`btn ${viewMode === 'flat' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setViewMode('flat')}>Flat List</button>
          <button className="btn btn-secondary" onClick={handleProcessAll} disabled={processing}>
            {processing ? 'Processing…' : '↻ Reprocess all twins'}
          </button>
        </div>
      </div>

      {processMsg && (
        <p className="text-callout" style={{ marginBottom: '1rem' }}>{processMsg}</p>
      )}

      {filtered.length === 0 && (
        <div className="panel text-empty" style={{ padding: '2rem' }}>
          <p>No projects match your search criteria.</p>
        </div>
      )}

      {viewMode === 'grouped' ? (
        grouped.map(({ category, projects }) => (
          <section key={category} className="projects-category-section">
            <div className="projects-category-header">
              <h2 className="projects-category-title">{PROJECT_CATEGORIES[category] || category}</h2>
              <span className="projects-category-count">{projects.length} project{projects.length !== 1 ? 's' : ''}</span>
            </div>
            <div className="projects-grid">
              {projects.map((p) => (
                <ProjectCard key={p.project_code} project={p} onOpen={setSelectedProject} />
              ))}
            </div>
          </section>
        ))
      ) : (
        <div className="projects-grid">
          {filtered
            .sort((a, b) => (a.project_index || 999) - (b.project_index || 999))
            .map((p) => (
              <ProjectCard key={p.project_code} project={p} onOpen={setSelectedProject} />
            ))}
        </div>
      )}
    </div>
  );
}
