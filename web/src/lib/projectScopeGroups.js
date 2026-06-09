const STATUS_ORDER = ['active', 'completed', 'discontinued', 'archived'];
const STATUS_LABELS = {
  active: 'Active projects',
  completed: 'Completed',
  discontinued: 'Discontinued',
  archived: 'Archived',
};

function normalizeQuery(query) {
  return String(query || '').trim().toLowerCase();
}

function projectMatchesQuery(project, query) {
  if (!query) return true;
  const haystack = [
    project.code,
    project.name,
    project.categoryLabel,
    project.diseaseFocus,
    project.lead,
    project.status,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return haystack.includes(query);
}

/**
 * Group dashboard projects for the scope selector: status → category → rows.
 * @param {Array<object>} projects normalized project rows
 * @param {{ query?: string, filter?: 'all'|'active'|'selected', selectedCodes?: Set<string> }} options
 */
export function groupProjectsForScope(projects = [], options = {}) {
  const query = normalizeQuery(options.query);
  const filter = options.filter || 'all';
  const selectedCodes = options.selectedCodes || new Set();

  let filtered = projects.filter((project) => projectMatchesQuery(project, query));

  if (filter === 'active') {
    filtered = filtered.filter((project) => project.status === 'active');
  } else if (filter === 'selected') {
    filtered = filtered.filter((project) => selectedCodes.has(project.code));
  }

  const byStatus = new Map();
  filtered.forEach((project) => {
    const status = project.status || 'active';
    if (!byStatus.has(status)) byStatus.set(status, []);
    byStatus.get(status).push(project);
  });

  const statusKeys = [
    ...STATUS_ORDER.filter((key) => byStatus.has(key)),
    ...[...byStatus.keys()].filter((key) => !STATUS_ORDER.includes(key)),
  ];

  return statusKeys.map((status) => {
    const statusProjects = byStatus.get(status) || [];
    const byCategory = new Map();

    statusProjects.forEach((project) => {
      const category = project.categoryLabel || 'Uncategorized';
      if (!byCategory.has(category)) byCategory.set(category, []);
      byCategory.get(category).push(project);
    });

    const categories = [...byCategory.entries()]
      .sort(([a], [b]) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
      .map(([label, items]) => ({
        label,
        projects: items.sort((a, b) => a.index - b.index || a.code.localeCompare(b.code)),
        selectedCount: items.filter((p) => selectedCodes.has(p.code)).length,
      }));

    const totalSelected = statusProjects.filter((p) => selectedCodes.has(p.code)).length;

    return {
      status,
      label: STATUS_LABELS[status] || status.replace(/_/g, ' '),
      categories,
      projectCount: statusProjects.length,
      selectedCount: totalSelected,
    };
  });
}

export function statusTone(status) {
  switch (status) {
    case 'active':
      return 'success';
    case 'completed':
      return 'info';
    case 'discontinued':
      return 'muted';
    case 'archived':
      return 'muted';
    default:
      return 'neutral';
  }
}
