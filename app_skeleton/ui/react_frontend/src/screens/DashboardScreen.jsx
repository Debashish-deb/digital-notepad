
import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Database,
  FolderOpen,
  Layers,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sparkles,
  Terminal,
  Users,
  X,
} from 'lucide-react';

import MetricCard from '../components/MetricCard';
import LabTeamRoster from '../components/LabTeamRoster.jsx';
import { normalizeTeamMember, sortLabTeamMembers } from '../utils/teamRoster.js';
import { apiGet } from '../api/client.js';

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

  try {
    return JSON.stringify(value);
  } catch {
    return fallback;
  }
}

function compactText(value, fallback = '') {
  return toText(value, fallback).replace(/\s+/g, ' ').trim();
}

function safeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function buildApiUrl(baseUrl, path) {
  const cleanBase = compactText(baseUrl).replace(/\/+$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

function formatDateTime(value) {
  const raw = compactText(value);
  if (!raw) return 'No timestamp';

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return raw.replace('T', ' ').slice(0, 16);
  }

  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  } catch {
    return raw.replace('T', ' ').slice(0, 16);
  }
}

function getInitials(name) {
  const cleanName = compactText(name, '?');
  const parts = cleanName.split(/\s+/).filter(Boolean);

  if (!parts.length) return '?';
  if (parts.length === 1) return parts[0].slice(0, 1).toUpperCase();

  return `${parts[0].slice(0, 1)}${parts[parts.length - 1].slice(0, 1)}`.toUpperCase();
}

function getProjectCode(project, index) {
  return compactText(
    project?.project_code ||
      project?.code ||
      project?.id ||
      project?.project_id ||
      `PROJECT-${index + 1}`,
  );
}

function getProjectName(project, index) {
  return compactText(
    project?.project_name ||
      project?.name ||
      project?.title ||
      getProjectCode(project, index),
  );
}

function getProjectStatus(project) {
  return compactText(project?.status || 'active').toLowerCase();
}

function getAuditTitle(log) {
  return compactText(
    log?.event_type ||
      log?.action ||
      log?.type ||
      log?.event ||
      'System event',
  );
}

function getAuditActor(log) {
  return compactText(
    log?.actor ||
      log?.username ||
      log?.user ||
      log?.created_by ||
      'System',
  );
}

function getAuditDescription(log) {
  return compactText(
    log?.description ||
      log?.message ||
      log?.details ||
      'No additional audit description was provided.',
  );
}

function getReadinessTone(score) {
  if (score >= 85) return 'excellent';
  if (score >= 65) return 'good';
  if (score >= 40) return 'warning';
  return 'danger';
}

function DashboardStatTile({ icon: Icon, label, value, helper }) {
  return (
    <div className="projects-stat dashboard-stat-tile">
      <span className="projects-stat-icon" aria-hidden="true">
        <Icon size={16} />
      </span>
      <span className="projects-stat-value">{value}</span>
      <span className="projects-stat-label">{label}</span>
      {helper ? <span className="projects-stat-helper">{helper}</span> : null}
    </div>
  );
}

function ReadinessPanel({ gap, loading }) {
  if (loading) {
    return (
      <div className="panel dashboard-readiness-panel" aria-busy="true">
        <h3 className="panel-title">
          <Activity size={18} /> Platform Readiness
        </h3>
        <p className="text-body-secondary">Loading readiness analysis…</p>
      </div>
    );
  }

  if (!gap) return null;

  const readinessScore = safeNumber(gap.readiness_score, 0);
  const tone = getReadinessTone(readinessScore);
  const recommendations = asArray(gap.recommendations);

  return (
    <section className={`panel dashboard-readiness-panel readiness-${tone}`}>
      <div className="dashboard-panel-heading">
        <div>
          <p className="text-caption">Operational intelligence</p>
          <h3 className="panel-title">
            <Activity size={18} /> Platform Readiness
          </h3>
        </div>

        <span className={`obp-badge obp-badge--${tone === 'danger' ? 'amber' : 'green'}`}>
          {readinessScore >= 70 ? 'Stable' : 'Needs attention'}
        </span>
      </div>

      <div className="projects-stats-bar dashboard-readiness-grid">
        <DashboardStatTile
          icon={ShieldCheck}
          value={`${readinessScore}%`}
          label="Checklist readiness"
          helper="Current platform score"
        />
        <DashboardStatTile
          icon={Sparkles}
          value={safeNumber(gap.ai_models_count, 0)}
          label="AI models"
        />
        <DashboardStatTile
          icon={ClipboardList}
          value={safeNumber(gap.documents_count, 0)}
          label="Ingested docs"
        />
        <DashboardStatTile
          icon={Database}
          value={safeNumber(gap.datasets_count, 0)}
          label="Datasets"
        />
      </div>

      {recommendations.length > 0 ? (
        <div className="dashboard-recommendations">
          <h4 className="text-title-3">Recommended next actions</h4>
          <ul className="stack-sm dashboard-recommendation-list">
            {recommendations.slice(0, 6).map((recommendation, index) => (
              <li key={`${recommendation}-${index}`} className="dashboard-recommendation-item">
                <CheckCircle2 size={15} aria-hidden="true" />
                <span>{compactText(recommendation)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-body-secondary">
          No platform recommendations were returned.
        </p>
      )}
    </section>
  );
}

function ProjectScopeSelector({
  projects,
  projectCodes,
  setProjectCodes,
}) {
  const selectedCodes = useMemo(
    () => new Set(asArray(projectCodes).map(String)),
    [projectCodes],
  );

  const activeProjects = useMemo(
    () => projects.filter((project) => getProjectStatus(project.raw) === 'active'),
    [projects],
  );

  const selectedCount = projects.filter((project) => selectedCodes.has(project.code)).length;

  const toggleProject = useCallback(
    (code) => {
      if (typeof setProjectCodes !== 'function') return;

      setProjectCodes((currentValue) => {
        const current = asArray(currentValue).map(String);
        const exists = current.includes(code);

        if (exists) {
          return current.filter((item) => item !== code);
        }

        return [...current, code];
      });
    },
    [setProjectCodes],
  );

  const selectActive = useCallback(() => {
    if (typeof setProjectCodes !== 'function') return;

    const activeCodes = activeProjects.map((project) => project.code);
    setProjectCodes(activeCodes);
  }, [activeProjects, setProjectCodes]);

  const clearSelection = useCallback(() => {
    if (typeof setProjectCodes !== 'function') return;
    setProjectCodes([]);
  }, [setProjectCodes]);

  return (
    <section className="panel dashboard-scope-panel">
      <div className="dashboard-panel-heading">
        <div>
          <p className="text-caption">Copilot context</p>
          <h3 className="panel-title">
            <Settings size={18} /> Project Scope Selector
          </h3>
        </div>

        <span className="projects-category-count">
          {selectedCount}/{projects.length} selected
        </span>
      </div>

      <p className="panel-lead">
        Select active research projects to scope LLM Copilot queries, summaries,
        document retrieval, and global metric coordination.
      </p>

      <div className="dashboard-scope-actions">
        <button type="button" className="btn btn-secondary" onClick={selectActive}>
          Select active
        </button>
        <button type="button" className="btn btn-secondary" onClick={clearSelection}>
          <X size={14} /> Clear
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="obp-empty">
          <p className="text-caption">No projects</p>
          <h4 className="text-title-3">No project catalog loaded</h4>
          <p className="text-body-secondary">
            Project scope chips will appear once the database returns projects.
          </p>
        </div>
      ) : (
        <div className="dashboard-scope-chip-grid">
          {projects.map((project) => {
            const isChecked = selectedCodes.has(project.code);
            const isActive = getProjectStatus(project.raw) === 'active';

            return (
              <label
                key={project.code}
                className={`scope-chip dashboard-scope-chip${isChecked ? ' is-checked' : ''}${isActive ? ' is-active-project' : ''}`}
                title={project.name}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggleProject(project.code)}
                />
                <span>{project.code}</span>
                {isActive ? <small>Active</small> : null}
              </label>
            );
          })}
        </div>
      )}
    </section>
  );
}

function AuditTrailPanel({ auditLogs }) {
  const logs = asArray(auditLogs).slice(0, 15);

  return (
    <section className="panel dashboard-audit-panel">
      <div className="dashboard-panel-heading">
        <div>
          <p className="text-caption">Governance trail</p>
          <h3 className="panel-title">
            <Terminal size={18} /> System Audit Trail
          </h3>
        </div>

        <span className="projects-category-count">
          {logs.length} event{logs.length === 1 ? '' : 's'}
        </span>
      </div>

      {logs.length === 0 ? (
        <div className="obp-empty">
          <p className="text-caption">No audit events</p>
          <h4 className="text-title-3">No recent system activity loaded</h4>
          <p className="text-body-secondary">
            Audit events will appear here when the backend returns platform actions.
          </p>
        </div>
      ) : (
        <div className="feed-scroll dashboard-audit-scroll">
          {logs.map((log, index) => {
            const actor = getAuditActor(log);
            const event = getAuditTitle(log);
            const createdAt = formatDateTime(log?.created_at || log?.timestamp);
            const description = getAuditDescription(log);

            return (
              <article key={log?.id || log?.event_id || index} className="audit-log-item">
                <div className="audit-log-meta">
                  <span>
                    <strong>{actor}</strong> · {event}
                  </span>
                  <span>{createdAt}</span>
                </div>
                <div className="audit-log-body">{description}</div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function ResearchTeamPanel({
  roster,
  team,
  onNavigate,
}) {
  const hasTeamApi = asArray(team).length > 0;

  return (
    <section className="panel dashboard-team-panel">
      <div className="dashboard-panel-heading">
        <div>
          <p className="text-caption">People and personnel index</p>
          <h3 className="panel-title section-divider-title">
            <Users size={18} /> Research Team
          </h3>
        </div>

        <span className="projects-category-count">
          {roster.length} record{roster.length === 1 ? '' : 's'}
        </span>
      </div>

      <p className="panel-lead">
        {hasTeamApi
          ? 'Roster from the platform database.'
          : 'Team API unavailable — showing personnel documents from the processed lab twin.'}
      </p>

      {!roster.length ? (
        <div className="obp-empty">
          <p className="text-caption">No personnel records</p>
          <h4 className="text-title-3">No team or personnel files found</h4>
          <p className="text-body-secondary">
            Add documents under database/Overview/PERSONNEL or connect the team API.
          </p>
        </div>
      ) : hasTeamApi ? (
        <LabTeamRoster members={sortLabTeamMembers(roster)} className="dashboard-team-roster" />
      ) : (
        <div className="roster-grid dashboard-roster-grid">
          {roster.map((member) => (
            <article key={member.key} className="roster-card dashboard-roster-card">
              <div className={`roster-avatar${member.photoUrl ? ' roster-avatar--photo' : ''}`}>
                {member.photoUrl ? (
                  <img className="lab-team-card__photo" src={member.photoUrl} alt="" />
                ) : (
                  getInitials(member.name)
                )}
              </div>
              <h4 className="roster-name">{member.name}</h4>
              <span className="roster-role">{member.role}</span>
              <p className="roster-focus">{member.focus}</p>
            </article>
          ))}
        </div>
      )}

      {typeof onNavigate === 'function' ? (
        <button
          type="button"
          className="btn btn-secondary dashboard-folder-button"
          onClick={() => onNavigate('overview', 'personnel')}
        >
          <FolderOpen size={16} /> Open personnel folder
        </button>
      ) : null}
    </section>
  );
}

export default function DashboardScreen({
  stats = {},
  team = [],
  auditLogs = [],
  projectCodes = [],
  setProjectCodes,
  dbProjects = [],
  API_URL,
  hideHeader = false,
  onNavigate,
}) {
  const [gap, setGap] = useState(null);
  const [gapLoading, setGapLoading] = useState(false);
  const [personnelFiles, setPersonnelFiles] = useState([]);
  const [personnelLoading, setPersonnelLoading] = useState(false);

  const safeStats = isObject(stats) ? stats : {};
  const safeDbProjects = asArray(dbProjects);
  const safeTeam = asArray(team);

  const activeProjCount = useMemo(
    () => Object.keys(safeStats.project_samples || {}).length,
    [safeStats.project_samples],
  );

  const normalizedProjects = useMemo(
    () =>
      safeDbProjects
        .map((project, index) => ({
          raw: project,
          code: getProjectCode(project, index),
          name: getProjectName(project, index),
          status: getProjectStatus(project),
          index: safeNumber(project?.project_index, index + 1),
        }))
        .sort((a, b) => {
          const indexDiff = a.index - b.index;
          if (indexDiff !== 0) return indexDiff;
          return a.code.localeCompare(b.code, undefined, { numeric: true });
        }),
    [safeDbProjects],
  );

  const activeDbProjectsCount = useMemo(
    () => normalizedProjects.filter((project) => project.status === 'active').length,
    [normalizedProjects],
  );

  const personnelDocumentRoster = useMemo(
    () =>
      personnelFiles.map((file) => ({
        key: file.path || file.name,
        name: file.name || file.path || 'Personnel document',
        role: 'Personnel document',
        focus: 'Open under Overview → Personnel',
      })),
    [personnelFiles],
  );

  const roster = useMemo(() => {
    if (safeTeam.length) {
      return safeTeam.map((member, index) =>
        normalizeTeamMember({
          ...member,
          username: compactText(
            member?.username || member?.email || `team-member-${index}`,
          ),
          name: compactText(member?.full_name || member?.name || member?.username, 'Unnamed member'),
          full_name: compactText(member?.full_name || member?.name || member?.username, 'Unnamed member'),
          role: compactText(member?.role || member?.title || 'Researcher'),
          focus: asArray(member?.allowed_projects).length
            ? asArray(member.allowed_projects).join(', ')
            : compactText(member?.focus || member?.speciality || '—'),
        }),
      );
    }

    return personnelDocumentRoster.map((member) => normalizeTeamMember(member));
  }, [personnelDocumentRoster, safeTeam]);

  const researcherCount = safeTeam.length || personnelFiles.length;

  useEffect(() => {
    if (!API_URL) {
      setGap(null);
      setGapLoading(false);
      return undefined;
    }

    const controller = new AbortController();
    const endpoint = buildApiUrl(API_URL, '/gap-analysis');

    setGapLoading(true);

    fetch(endpoint, {
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Gap analysis unavailable (${response.status})`);
        }
        return response.json();
      })
      .then((data) => {
        setGap(isObject(data) ? data : null);
      })
      .catch((error) => {
        if (error?.name !== 'AbortError') {
          setGap(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setGapLoading(false);
        }
      });

    return () => controller.abort();
  }, [API_URL]);

  useEffect(() => {
    let alive = true;

    setPersonnelLoading(true);

    apiGet('/api/lab/section/overview_personnel')
      .then((data) => {
        if (!alive) return;

        const docs = asArray(data?.document_index_preview || data?.document_index)
          .slice(0, 12)
          .map((document, index) => ({
            path: compactText(document?.path || document?.relative_path || `personnel-${index}`),
            name: compactText(
              document?.title ||
                document?.name ||
                document?.path ||
                document?.relative_path ||
                'Document',
            ),
          }));

        setPersonnelFiles(docs);
      })
      .catch(() => {
        if (alive) setPersonnelFiles([]);
      })
      .finally(() => {
        if (alive) setPersonnelLoading(false);
      });

    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="dashboard-page">
      {!hideHeader ? (
        <header className="page-header dashboard-hero-header">
          <div>
            <p className="text-caption">Command overview</p>
            <h1 className="page-title-gradient">Lab Overview Dashboard</h1>
            <p className="page-subtitle">
              Clinical-spatial research status, project scope, platform readiness,
              audit trails, and multiomic data metrics.
            </p>
          </div>

          <div className="dashboard-hero-badge">
            <Layers size={18} />
            <span>{normalizedProjects.length} project records</span>
          </div>
        </header>
      ) : null}

      <section className="metrics-grid dashboard-metrics-grid" aria-label="Dashboard metrics">
        <MetricCard
          label="Total Patients"
          value={safeNumber(safeStats.patient_count, 0)}
        />
        <MetricCard
          label="Total Samples"
          value={safeNumber(safeStats.sample_count, 0)}
          variant="success"
        />
        <MetricCard
          label="Active Scoped Projects"
          value={activeDbProjectsCount || activeProjCount}
          variant="accent"
        />
        <MetricCard
          label="Team Records"
          value={researcherCount}
          variant="warning"
        />
      </section>

      <ReadinessPanel gap={gap} loading={gapLoading} />

      <section className="grid-2col dashboard-control-grid">
        <ProjectScopeSelector
          projects={normalizedProjects}
          projectCodes={projectCodes}
          setProjectCodes={setProjectCodes}
        />

        <AuditTrailPanel auditLogs={auditLogs} />
      </section>

      {personnelLoading && !safeTeam.length ? (
        <section className="panel dashboard-team-panel" aria-busy="true">
          <h3 className="panel-title">
            <RefreshCw size={18} className="projects-spin" /> Research Team
          </h3>
          <p className="text-body-secondary">Loading personnel document index…</p>
        </section>
      ) : (
        <ResearchTeamPanel
          roster={roster}
          team={safeTeam}
          onNavigate={onNavigate}
        />
      )}
    </div>
  );
}