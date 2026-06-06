
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Dna,
  Filter,
  FolderCheck,
  FolderOpen,
  GitBranch,
  LayoutGrid,
  List,
  RefreshCw,
  Search,
  Users,
  X,
} from 'lucide-react';
import ProjectBrandMark from '../components/ProjectBrandMark.jsx';

import WorkspaceScreen from './WorkspaceScreen';
import { PROJECT_CATEGORIES } from '../data/projectsCatalog.js';

const STATUS_STYLES = {
  active: {
    bg: 'rgba(45,212,191,0.12)',
    color: 'var(--color-success)',
    label: 'Active',
    icon: Activity,
  },
  completed: {
    bg: 'rgba(96,165,250,0.12)',
    color: '#60a5fa',
    label: 'Completed',
    icon: CheckCircle2,
  },
  discontinued: {
    bg: 'rgba(148,163,184,0.12)',
    color: 'var(--text-muted)',
    label: 'Discontinued',
    icon: AlertCircle,
  },
  archived: {
    bg: 'rgba(148,163,184,0.12)',
    color: 'var(--text-muted)',
    label: 'Archived',
    icon: FolderOpen,
  },
};

const PRIORITY_DOT = {
  critical: 'var(--color-danger)',
  high: 'var(--color-danger)',
  medium: 'var(--color-warning)',
  low: 'var(--text-muted)',
};

const PRIORITY_LABEL = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

const CATEGORY_ORDER = [
  'flagship',
  'spatial_omics',
  'computational_tool',
  'platform_model',
  'clinical_collaboration',
  'external_collaboration',
  'genomics',
  'infrastructure',
  'support',
];

const VIEW_MODES = {
  GROUPED: 'grouped',
  FLAT: 'flat',
};

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function toText(value, fallback = '') {
  if (value == null) return fallback;
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);

  if (Array.isArray(value)) {
    return value.map((item) => toText(item)).filter(Boolean).join(', ');
  }

  try {
    return JSON.stringify(value);
  } catch {
    return fallback;
  }
}

function compactText(value, fallback = '') {
  return toText(value, fallback).replace(/\s+/g, ' ').trim();
}

function normalizeKey(value, fallback = '') {
  return compactText(value, fallback).toLowerCase().trim();
}

function titleCaseFromKey(value) {
  return compactText(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function buildApiUrl(baseUrl, path) {
  const cleanBase = compactText(baseUrl).replace(/\/+$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

function isSafeExternalUrl(value) {
  const text = compactText(value);
  if (!text) return false;

  try {
    const url = new URL(text);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

function getCategoryLabel(categoryKey) {
  const key = compactText(categoryKey, 'spatial_omics');
  const catalogValue = PROJECT_CATEGORIES?.[key];

  if (typeof catalogValue === 'string') return catalogValue;

  if (isObject(catalogValue)) {
    return (
      compactText(catalogValue.label) ||
      compactText(catalogValue.title) ||
      compactText(catalogValue.name) ||
      titleCaseFromKey(key)
    );
  }

  return titleCaseFromKey(key);
}

function getStatusMeta(status) {
  const key = normalizeKey(status, 'active');
  return STATUS_STYLES[key] || {
    bg: 'rgba(148,163,184,0.12)',
    color: 'var(--text-muted)',
    label: titleCaseFromKey(key || 'Unknown'),
    icon: Activity,
  };
}

function getProjectIndex(project, fallbackIndex) {
  const value = Number(project?.project_index ?? project?.index ?? fallbackIndex + 1);
  return Number.isFinite(value) ? value : fallbackIndex + 1;
}

function getProjectCode(project, fallbackIndex) {
  return compactText(
    project?.project_code ||
      project?.code ||
      project?.id ||
      project?.project_id ||
      `PROJECT-${fallbackIndex + 1}`,
  );
}

function getProjectName(project, fallbackIndex) {
  return compactText(
    project?.project_name ||
      project?.name ||
      project?.title ||
      getProjectCode(project, fallbackIndex),
    `Untitled Project ${fallbackIndex + 1}`,
  );
}

function getProjectSummary(project) {
  return compactText(
    project?.project_summary ||
      project?.summary ||
      project?.description ||
      project?.research_question ||
      'No project summary has been added yet.',
  );
}

function getProjectLead(project) {
  return compactText(
    project?.project_lead ||
      project?.lead ||
      project?.owner ||
      project?.principal_investigator ||
      'Unassigned',
  );
}

function normalizeModalities(project) {
  const modalities = asArray(project?.modalities || project?.methods || project?.assays);
  return modalities.map((item) => compactText(item)).filter(Boolean);
}

function flattenSearchable(value, depth = 0) {
  if (depth > 4 || value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);

  if (Array.isArray(value)) {
    return value.map((item) => flattenSearchable(item, depth + 1)).join(' ');
  }

  if (isObject(value)) {
    return Object.values(value)
      .map((item) => flattenSearchable(item, depth + 1))
      .join(' ');
  }

  return '';
}

function compareProjects(a, b) {
  const indexDiff = (a.project_index || 9999) - (b.project_index || 9999);
  if (indexDiff !== 0) return indexDiff;

  return a.project_name.localeCompare(b.project_name, undefined, {
    sensitivity: 'base',
    numeric: true,
  });
}

function normalizeProject(rawProject, index) {
  const project = isObject(rawProject) ? rawProject : {};
  const projectCode = getProjectCode(project, index);
  const projectName = getProjectName(project, index);
  const category = compactText(project.category || project.project_category || 'spatial_omics');
  const status = normalizeKey(project.status, 'active');
  const priority = normalizeKey(project.priority, 'medium');
  const modalities = normalizeModalities(project);
  const projectLead = getProjectLead(project);
  const principalInvestigator = compactText(project.principal_investigator || project.pi || '');
  const diseaseFocus = compactText(
    project.disease_focus ||
      project.disease ||
      project.indication ||
      project.research_area ||
      'Disease focus not specified',
  );
  const cohortSize = compactText(project.cohort_size || project.cohort || project.sample_size || '');
  const folderPath = compactText(project.folder_path || project.workspace_path || project.path || '');
  const repository = compactText(project.repository || project.repo_url || project.github || '');

  const normalized = {
    ...project,
    project_index: getProjectIndex(project, index),
    project_code: projectCode,
    project_name: projectName,
    project_summary: getProjectSummary(project),
    research_question: compactText(project.research_question || ''),
    project_lead: projectLead,
    principal_investigator: principalInvestigator,
    disease_focus: diseaseFocus,
    cohort_size: cohortSize,
    folder_path: folderPath,
    repository,
    category,
    category_label: getCategoryLabel(category),
    status,
    priority,
    modalities,
    has_workspace: Boolean(folderPath),
    has_repository: isSafeExternalUrl(repository),
    raw_project: project,
  };

  normalized.searchable_text = [
    normalized.project_code,
    normalized.project_name,
    normalized.project_summary,
    normalized.research_question,
    normalized.project_lead,
    normalized.principal_investigator,
    normalized.disease_focus,
    normalized.cohort_size,
    normalized.folder_path,
    normalized.repository,
    normalized.category,
    normalized.category_label,
    normalized.status,
    normalized.priority,
    normalized.modalities.join(' '),
    flattenSearchable(project.tags),
    flattenSearchable(project.keywords),
  ]
    .map((item) => compactText(item).toLowerCase())
    .join(' ');

  return normalized;
}

function StatCard({ icon: Icon, value, label, helper }) {
  return (
    <div className="projects-stat">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', marginBottom: '0.1rem' }}>
        <span className="projects-stat-icon" aria-hidden="true" style={{ display: 'flex', alignItems: 'center', color: 'var(--color-primary)' }}>
          {Icon ? <Icon size={18} /> : null}
        </span>
        <span className="projects-stat-value">{value}</span>
      </div>
      <span className="projects-stat-label">{label}</span>
      {helper ? <span className="projects-stat-helper">{helper}</span> : null}
    </div>
  );
}

function EmptyState({ hasFilters, onClearFilters }) {
  return (
    <div className="panel text-empty projects-empty-state">
      <div className="projects-empty-orb" aria-hidden="true">
        <Search size={28} />
      </div>

      <h3 className="text-title-2">
        {hasFilters ? 'No projects match your filters' : 'No projects loaded yet'}
      </h3>

      <p className="text-body-secondary">
        {hasFilters
          ? 'Try a different keyword, status, or category. Search supports project code, title, lead, disease, modality, PI, summary, and workspace path.'
          : 'Project cards will appear here once the project catalog or backend database returns records.'}
      </p>

      {hasFilters ? (
        <button type="button" className="btn btn-secondary" onClick={onClearFilters}>
          Clear filters
        </button>
      ) : null}
    </div>
  );
}

function ProcessMessage({ message }) {
  if (!message?.text) return null;

  const isSuccess = message.type === 'success';
  const isError = message.type === 'error';

  return (
    <div
      className={`text-callout projects-process-message${
        isSuccess ? ' is-success' : ''
      }${isError ? ' is-error' : ''}`}
      role={isError ? 'alert' : 'status'}
    >
      {isSuccess ? <CheckCircle2 size={16} aria-hidden="true" /> : null}
      {isError ? <AlertCircle size={16} aria-hidden="true" /> : null}
      <span>{message.text}</span>
    </div>
  );
}

function ProjectCard({ project, onOpen }) {
  const statusStyle = getStatusMeta(project.status);
  const StatusIcon = statusStyle.icon;
  const priorityColor = PRIORITY_DOT[project.priority] || PRIORITY_DOT.medium;
  const priorityLabel = PRIORITY_LABEL[project.priority] || titleCaseFromKey(project.priority || 'Medium');
  const hasFolder = Boolean(project.folder_path);

  return (
    <article className="project-card" aria-labelledby={`project-title-${project.project_code}`}>
      <div className="project-card-header">
        <ProjectBrandMark
          code={project.project_code}
          index={project.project_index}
          name={project.project_name}
          variant="card"
        />
        <div className="project-card-header-meta">
          <span
            className="project-card-priority"
            style={{ background: priorityColor }}
            title={`${priorityLabel} priority`}
            aria-label={`${priorityLabel} priority`}
          />
          <span
            className="project-card-status"
            style={{ background: statusStyle.bg, color: statusStyle.color }}
          >
            <StatusIcon size={12} aria-hidden="true" />
            {statusStyle.label}
          </span>
        </div>
      </div>

      <h4 id={`project-title-${project.project_code}`} className="sr-only">
        {project.project_name || project.project_code}
      </h4>

      <p className="project-card-summary">
        {project.project_summary || project.research_question}
      </p>

      {project.modalities.length > 0 ? (
        <div className="project-card-tags" aria-label="Project modalities">
          {project.modalities.slice(0, 4).map((modality) => (
            <span key={modality} className="project-tag modality">
              {modality}
            </span>
          ))}
          {project.modalities.length > 4 ? (
            <span className="project-tag">+{project.modalities.length - 4}</span>
          ) : null}
        </div>
      ) : (
        <div className="project-card-tags">
          <span className="project-tag">No modalities listed</span>
        </div>
      )}

      <div className="project-card-meta">
        <div className="project-card-meta-row">
          <Dna size={13} aria-hidden="true" />
          <span>{project.disease_focus}</span>
        </div>

        <div className="project-card-meta-row">
          <Users size={13} aria-hidden="true" />
          <span>
            Lead: <strong>{project.project_lead}</strong>
          </span>
        </div>

        {project.principal_investigator ? (
          <div className="project-card-meta-row">
            <Users size={13} aria-hidden="true" />
            <span>
              PI: <strong>{project.principal_investigator}</strong>
            </span>
          </div>
        ) : null}

        {project.cohort_size ? (
          <div className="project-card-meta-row">
            <Filter size={13} aria-hidden="true" />
            <span>{project.cohort_size}</span>
          </div>
        ) : null}

        {hasFolder ? (
          <div className="project-card-meta-row">
            <FolderCheck size={13} aria-hidden="true" />
            <span className="project-folder-indicator">Workspace on disk</span>
          </div>
        ) : (
          <div className="project-card-meta-row">
            <FolderOpen size={13} aria-hidden="true" />
            <span className="text-caption">Catalog only — no disk folder</span>
          </div>
        )}

        {project.has_repository ? (
          <div className="project-card-meta-row">
            <GitBranch size={13} aria-hidden="true" />
            <a
              href={project.repository}
              target="_blank"
              rel="noopener noreferrer"
              className="project-repo-link"
              onClick={(event) => event.stopPropagation()}
            >
              Repository
            </a>
          </div>
        ) : null}
      </div>

      <button
        type="button"
        className="btn btn-primary project-card-action"
        onClick={() => onOpen(project.project_code)}
        aria-label={`Open workspace for ${project.project_name}`}
      >
        Open Workspace <ChevronRight size={14} aria-hidden="true" />
      </button>
    </article>
  );
}

export default function ProjectsScreen({
  dbProjects = [],
  selectedProject,
  setSelectedProject,
  fetchProjects,
  API_URL,
}) {
  const mountedRef = useRef(false);

  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('All');
  const [filterCategory, setFilterCategory] = useState('All');
  const [viewMode, setViewMode] = useState(VIEW_MODES.GROUPED);
  const [processing, setProcessing] = useState(false);
  const [processMsg, setProcessMsg] = useState(null);

  const processEndpoint = useMemo(
    () => buildApiUrl(API_URL || '', '/api/projects/process-all'),
    [API_URL],
  );

  const projects = useMemo(
    () => asArray(dbProjects).map((project, index) => normalizeProject(project, index)),
    [dbProjects],
  );

  const searchTokens = useMemo(
    () =>
      search
        .trim()
        .toLowerCase()
        .split(/\s+/)
        .filter(Boolean),
    [search],
  );

  const availableStatuses = useMemo(() => {
    const statuses = new Set(projects.map((project) => project.status).filter(Boolean));
    Object.keys(STATUS_STYLES).forEach((status) => statuses.add(status));

    return Array.from(statuses).sort((a, b) => {
      const preferred = ['active', 'completed', 'discontinued', 'archived'];
      const aIndex = preferred.indexOf(a);
      const bIndex = preferred.indexOf(b);

      if (aIndex !== -1 || bIndex !== -1) {
        return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
      }

      return a.localeCompare(b);
    });
  }, [projects]);

  const availableCategories = useMemo(() => {
    const categoryKeys = new Set([
      ...Object.keys(PROJECT_CATEGORIES || {}),
      ...projects.map((project) => project.category).filter(Boolean),
    ]);

    return Array.from(categoryKeys).sort((a, b) => {
      const aIndex = CATEGORY_ORDER.indexOf(a);
      const bIndex = CATEGORY_ORDER.indexOf(b);

      if (aIndex !== -1 || bIndex !== -1) {
        return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
      }

      return getCategoryLabel(a).localeCompare(getCategoryLabel(b));
    });
  }, [projects]);

  const filtered = useMemo(() => {
    return projects.filter((project) => {
      const matchesSearch =
        searchTokens.length === 0 ||
        searchTokens.every((token) => project.searchable_text.includes(token));

      const matchesStatus = filterStatus === 'All' || project.status === filterStatus;
      const matchesCategory = filterCategory === 'All' || project.category === filterCategory;

      return matchesSearch && matchesStatus && matchesCategory;
    });
  }, [projects, searchTokens, filterStatus, filterCategory]);

  const sortedFiltered = useMemo(
    () => [...filtered].sort(compareProjects),
    [filtered],
  );

  const stats = useMemo(() => {
    const total = projects.length;
    const active = projects.filter((project) => project.status === 'active').length;
    const completed = projects.filter((project) => project.status === 'completed').length;
    const withFolder = projects.filter((project) => project.folder_path).length;
    const withRepo = projects.filter((project) => project.has_repository).length;

    return {
      total,
      active,
      completed,
      withFolder,
      withRepo,
      visible: filtered.length,
    };
  }, [projects, filtered.length]);

  const grouped = useMemo(() => {
    const groups = new Map();

    sortedFiltered.forEach((project) => {
      const category = project.category || 'spatial_omics';
      if (!groups.has(category)) groups.set(category, []);
      groups.get(category).push(project);
    });

    const sortedCategories = Array.from(groups.keys()).sort((a, b) => {
      const aIndex = CATEGORY_ORDER.indexOf(a);
      const bIndex = CATEGORY_ORDER.indexOf(b);

      if (aIndex !== -1 || bIndex !== -1) {
        return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
      }

      return getCategoryLabel(a).localeCompare(getCategoryLabel(b));
    });

    return sortedCategories.map((category) => ({
      category,
      categoryLabel: getCategoryLabel(category),
      projects: groups.get(category) || [],
    }));
  }, [sortedFiltered]);

  const hasFilters =
    Boolean(search.trim()) ||
    filterStatus !== 'All' ||
    filterCategory !== 'All';

  const clearFilters = useCallback(() => {
    setSearch('');
    setFilterStatus('All');
    setFilterCategory('All');
  }, []);

  const handleOpenProject = useCallback(
    (projectCode) => {
      if (typeof setSelectedProject === 'function') {
        setSelectedProject(projectCode);
      }
    },
    [setSelectedProject],
  );

  const handleBackFromWorkspace = useCallback(() => {
    if (typeof setSelectedProject === 'function') {
      setSelectedProject(null);
    }

    if (typeof fetchProjects === 'function') {
      fetchProjects();
    }
  }, [fetchProjects, setSelectedProject]);

  const handleProcessAll = useCallback(async () => {
    if (processing) return;

    setProcessing(true);
    setProcessMsg(null);

    try {
      const response = await fetch(processEndpoint, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
        },
      });

      const contentType = response.headers.get('content-type') || '';
      const payload = contentType.includes('application/json')
        ? await response.json()
        : { detail: await response.text() };

      if (!response.ok) {
        throw new Error(
          payload?.detail ||
            payload?.message ||
            `Processing failed (${response.status} ${response.statusText || 'HTTP error'})`,
        );
      }

      const processed = Number(payload?.processed ?? payload?.processed_projects ?? 0);
      const synced = Number(payload?.synced_to_public ?? payload?.synced ?? 0);

      if (mountedRef.current) {
        setProcessMsg({
          type: 'success',
          text: `Processed ${processed} project${processed === 1 ? '' : 's'} · synced ${synced} to frontend`,
        });
      }

      if (typeof fetchProjects === 'function') {
        await fetchProjects();
      }
    } catch (error) {
      console.error('[ProjectsScreen] Failed to process project twins:', error);

      if (mountedRef.current) {
        setProcessMsg({
          type: 'error',
          text: error?.message || 'Processing failed.',
        });
      }
    } finally {
      if (mountedRef.current) {
        setProcessing(false);
      }
    }
  }, [fetchProjects, processEndpoint, processing]);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!processMsg) return undefined;

    const timer = window.setTimeout(() => {
      if (mountedRef.current) setProcessMsg(null);
    }, 9000);

    return () => window.clearTimeout(timer);
  }, [processMsg]);

  if (selectedProject) {
    return (
      <WorkspaceScreen
        projectCode={selectedProject}
        onBack={handleBackFromWorkspace}
        API_URL={API_URL}
        dbProjects={dbProjects}
      />
    );
  }

  return (
    <div className="projects-page">
      <section className="projects-stats-bar" aria-label="Project portfolio statistics">
        <StatCard
          icon={LayoutGrid}
          value={stats.total}
          label="Total Projects"
          helper={`${stats.visible} visible`}
        />
        <StatCard
          icon={Activity}
          value={stats.active}
          label="Active"
        />
        <StatCard
          icon={CheckCircle2}
          value={stats.completed}
          label="Completed"
        />
        <StatCard
          icon={FolderCheck}
          value={stats.withFolder}
          label="With Workspace"
        />
        <StatCard
          icon={GitBranch}
          value={stats.withRepo}
          label="With Repository"
        />
      </section>

      <section className="projects-toolbar" aria-label="Project filters and controls">
        <div className="projects-search-wrap">
          <Search size={18} className="projects-search-icon" aria-hidden="true" />

          <label className="sr-only" htmlFor="projects-search-input">
            Search projects
          </label>

          <input
            id="projects-search-input"
            type="search"
            placeholder="Search by code, title, lead, disease, modality, PI, folder..."
            className="form-input"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            autoComplete="off"
          />

          {search ? (
            <button
              type="button"
              className="projects-search-clear"
              onClick={() => setSearch('')}
              aria-label="Clear project search"
            >
              <X size={15} aria-hidden="true" />
            </button>
          ) : null}
        </div>

        <label className="sr-only" htmlFor="projects-status-filter">
          Filter by status
        </label>
        <select
          id="projects-status-filter"
          className="form-select projects-filter"
          value={filterStatus}
          onChange={(event) => setFilterStatus(event.target.value)}
        >
          <option value="All">All Statuses</option>
          {availableStatuses.map((status) => (
            <option key={status} value={status}>
              {getStatusMeta(status).label}
            </option>
          ))}
        </select>

        <label className="sr-only" htmlFor="projects-category-filter">
          Filter by category
        </label>
        <select
          id="projects-category-filter"
          className="form-select projects-filter"
          value={filterCategory}
          onChange={(event) => setFilterCategory(event.target.value)}
        >
          <option value="All">All Categories</option>
          {availableCategories.map((categoryKey) => (
            <option key={categoryKey} value={categoryKey}>
              {getCategoryLabel(categoryKey)}
            </option>
          ))}
        </select>

        <div className="projects-view-toggle" role="group" aria-label="Project view mode">
          <button
            type="button"
            className={`btn ${viewMode === VIEW_MODES.GROUPED ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setViewMode(VIEW_MODES.GROUPED)}
            aria-pressed={viewMode === VIEW_MODES.GROUPED}
          >
            <LayoutGrid size={15} aria-hidden="true" />
            Grouped
          </button>

          <button
            type="button"
            className={`btn ${viewMode === VIEW_MODES.FLAT ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setViewMode(VIEW_MODES.FLAT)}
            aria-pressed={viewMode === VIEW_MODES.FLAT}
          >
            <List size={15} aria-hidden="true" />
            Flat List
          </button>
        </div>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleProcessAll}
          disabled={processing}
          aria-busy={processing ? 'true' : 'false'}
          style={{ marginLeft: 'auto' }}
        >
          <RefreshCw
            size={15}
            aria-hidden="true"
            className={processing ? 'projects-spin' : undefined}
          />
          {processing ? 'Processing twins…' : 'Reprocess all twins'}
        </button>
      </section>

      <ProcessMessage message={processMsg} />

      {sortedFiltered.length === 0 ? (
        <EmptyState
          hasFilters={hasFilters}
          onClearFilters={clearFilters}
        />
      ) : viewMode === VIEW_MODES.GROUPED ? (
        grouped.map(({ category, categoryLabel, projects: categoryProjects }) => (
          <section key={category} className="projects-category-section">
            <div className="projects-category-header">
              <div>
                <p className="text-caption">Project category</p>
                <h2 className="projects-category-title">{categoryLabel}</h2>
              </div>

              <span className="projects-category-count">
                {categoryProjects.length} project{categoryProjects.length === 1 ? '' : 's'}
              </span>
            </div>

            <div className="projects-grid">
              {categoryProjects.map((project) => (
                <ProjectCard
                  key={project.project_code}
                  project={project}
                  onOpen={handleOpenProject}
                />
              ))}
            </div>
          </section>
        ))
      ) : (
        <section className="projects-category-section">
          <div className="projects-category-header">
            <div>
              <p className="text-caption">Flat portfolio view</p>
              <h2 className="projects-category-title">All Visible Projects</h2>
            </div>

            <span className="projects-category-count">
              {sortedFiltered.length} project{sortedFiltered.length === 1 ? '' : 's'}
            </span>
          </div>

          <div className="projects-grid">
            {sortedFiltered.map((project) => (
              <ProjectCard
                key={project.project_code}
                project={project}
                onOpen={handleOpenProject}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}