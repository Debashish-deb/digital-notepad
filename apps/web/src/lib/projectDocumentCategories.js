/**
 * Smart categorization of project files for workspace tab side-nav browsers.
 * Maps numbered Drive folders (1_Management, 2_Methods, …) to workspace modules.
 */

import { humanizeFilenameLabel } from './textCleanup.js';
import { normalizeRelPath } from './folderBrowserUtils.js';
import { isProjectLogFile } from './projectLogUtils.js';

const NUMBERED_SECTION_PREFIX =
  /^\d+[_.\s-]?\s*(management|planning|methods?|experiments?|data|figures?|meetings?|updates?|writing|dissemination|archive)/i;

/** Strip duplicate nested project root (e.g. 38_ADC_project/1_Management/…). */
export function stripNestedProjectRoot(path, projectCode = '') {
  let norm = normalizeRelPath(path);
  const code = (projectCode || '').trim();
  if (code && norm.toLowerCase().startsWith(`${code.toLowerCase()}/`)) {
    norm = norm.slice(code.length + 1);
  }
  const firstSeg = norm.split('/')[0] || '';
  if (NUMBERED_SECTION_PREFIX.test(firstSeg)) return norm;

  const m = norm.match(/^\d{2,}_[A-Za-z0-9][A-Za-z0-9_-]*\/(.+)$/);
  if (m) return m[1];
  return norm;
}

const DOMAIN_PATTERNS = {
  plan: [
    /^(\d+)[_.\s-]?\s*(management|planning)/i,
    /management\s*(?:&|and)\s*planning/i,
  ],
  methods: [
    /^(\d+)[_.\s-]?\s*(methods?|experiments?)/i,
    /methods?\s*(?:&|and)\s*experiments?/i,
    /wet[_\s-]?lab/i,
    /dry[_\s-]?lab/i,
    /geomx|cycif|tcycif|spatial|protocol/i,
  ],
  data: [
    /^(\d+)[_.\s-]?\s*(data|figures)/i,
    /data\s*(?:&|and)\s*figures?/i,
  ],
  log: [
    /^(\d+)[_.\s-]?\s*(meetings?|updates?)/i,
    /meetings?\s*(?:&|and)\s*updates?/i,
    /lab_meeting/i,
  ],
  writing: [
    /^(\d+)[_.\s-]?\s*(writing|dissemination)/i,
    /writing\s*(?:&|and)\s*dissemination/i,
    /\/abstracts?\//i,
    /\/posters?\//i,
    /\/manuscript/i,
    /grant_application/i,
  ],
  archive: [/^(\d+)[_.\s-]?\s*archive/i, /\/archive\//i],
};

export function inferProjectDomain(path, projectCode = '') {
  const norm = stripNestedProjectRoot(path, projectCode);
  const lower = norm.toLowerCase();
  const parts = lower.split('/').filter(Boolean);

  if (isProjectLogFile(norm) || isProjectLogFile(parts[parts.length - 1] || '')) return 'log';
  if (!parts.length || parts[0] === '.') return 'overview';
  if (parts.length === 1 && /^readme/i.test(parts[0])) return 'overview';

  for (const [domain, patterns] of Object.entries(DOMAIN_PATTERNS)) {
    if (patterns.some((re) => re.test(lower))) return domain;
  }

  const top = parts[0];
  const numMatch = top.match(/^(\d+)/);
  if (numMatch) {
    const n = parseInt(numMatch[1], 10);
    if (n === 1) return 'plan';
    if (n === 2) return 'methods';
    if (n === 3) return 'data';
    if (n === 4) return 'log';
    if (n === 5) return 'writing';
    if (n >= 6) return 'archive';
  }

  return 'overview';
}

export function pathBelongsToWorkspaceTab(path, tabId, projectCode = '') {
  const domain = inferProjectDomain(path, projectCode);
  const tabDomains = {
    overview: ['overview'],
    plan: ['plan'],
    data: ['data'],
    methods: ['methods'],
    writing: ['writing'],
    archive: ['archive'],
    log: ['log'],
  };
  return (tabDomains[tabId] || []).includes(domain);
}

function subfolderAfterDomain(path, projectCode = '') {
  const norm = stripNestedProjectRoot(path, projectCode);
  const parts = norm.split('/').filter(Boolean);
  if (parts.length < 2) return null;
  const domainPart = parts.find((p) =>
    Object.values(DOMAIN_PATTERNS)
      .flat()
      .some((re) => re.test(p.toLowerCase()))
  );
  const idx = domainPart ? parts.indexOf(domainPart) : 0;
  const sub = parts[idx + 1];
  if (!sub) return null;
  return sub.replace(/[_-]+/g, ' ').trim();
}

function extOf(path) {
  const m = (path || '').match(/(\.[^./\\]+)$/);
  return (m?.[1] || '').toLowerCase();
}

export function categorizeProjectPath(path, tabId, projectCode = '') {
  const norm = stripNestedProjectRoot(path, projectCode);
  const lower = norm.toLowerCase();
  const name = lower.split('/').pop() || '';
  const ext = extOf(path);
  const sub = subfolderAfterDomain(path, projectCode);

  switch (tabId) {
    case 'overview':
      if (!lower.includes('/') || /^readme/i.test(name)) return 'root';
      return 'project_misc';

    case 'plan':
      if (/gantt|timetable|schedule|timeline|calendar/.test(lower)) return 'schedules';
      if (['.pptx', '.ppt', '.key'].includes(ext)) return 'plan_slides';
      if (['.xlsx', '.xls'].includes(ext)) return 'plan_spreadsheets';
      return 'planning_docs';

    case 'methods':
      if (/wet[_\s-]?lab/.test(lower)) return 'wet_lab';
      if (/dry[_\s-]?lab|computational|bioinfo|pipeline|script/.test(lower)) return 'dry_lab';
      if (['.py', '.r', '.sh', '.ipynb', '.js'].includes(ext)) return 'scripts';
      if (['.md', '.txt'].includes(ext) || /protocol|sop|method/i.test(name)) return 'protocols';
      if (['.xlsx', '.xls', '.csv'].includes(ext)) return 'experiment_logs';
      if (sub) return `methods_${slugify(sub)}`;
      return 'methods_other';

    case 'data':
      if (['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.svg', '.gif', '.webp'].includes(ext))
        return 'figures';
      if (['.pdf'].includes(ext)) return 'reports';
      if (['.xlsx', '.xls', '.csv', '.tsv', '.json', '.h5', '.rds'].includes(ext))
        return 'datasets';
      if (sub) return `data_${slugify(sub)}`;
      return 'data_other';

    case 'writing':
      if (/abstract/.test(lower)) return 'abstracts';
      if (/poster/.test(lower)) return 'posters';
      if (/manuscript/.test(lower)) return 'manuscripts';
      if (/grant/.test(lower)) return 'grants';
      if (['.pptx', '.ppt'].includes(ext)) return 'writing_slides';
      if (sub) return `writing_${slugify(sub)}`;
      return 'writing_other';

    case 'log':
      if (isProjectLogFile(name) || isProjectLogFile(norm)) return 'project_log';
      if (/meeting.?notes|notes\.md/i.test(lower)) return 'meeting_notes';
      if (/presentation|lab_meeting/.test(lower)) return 'meeting_slides';
      if (['.pptx', '.ppt', '.pdf'].includes(ext)) return 'meeting_decks';
      if (sub) return `log_${slugify(sub)}`;
      return 'meeting_other';

    case 'archive':
      if (sub) return `archive_${slugify(sub)}`;
      return 'archive_root';

    default:
      return 'other';
  }
}

function slugify(label) {
  return (label || 'other')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 40) || 'other';
}

function humanizeCategoryId(id) {
  if (!id) return 'Other';
  return id
    .replace(/^(methods|data|writing|log|archive)_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim() || 'Other';
}

const STATIC_TAB_CATEGORIES = {
  overview: [
    {
      id: 'intro',
      label: 'Project Files',
      categories: [
        { id: 'root', label: 'README', description: 'Top-level project overview and readme.' },
        { id: 'project_misc', label: 'Other Root Files', description: 'Miscellaneous project-level documents.' },
      ],
    },
  ],
  plan: [
    {
      id: 'planning',
      label: 'Management & Planning',
      categories: [
        { id: 'schedules', label: 'Timelines & Schedules', description: 'Gantt charts, timetables, calendars.' },
        { id: 'plan_slides', label: 'Planning Presentations', description: 'Aims, updates, and planning decks.' },
        { id: 'plan_spreadsheets', label: 'Planning Spreadsheets', description: 'Budgets, resource tables, trackers.' },
        { id: 'planning_docs', label: 'Planning Documents', description: 'Other management and planning files.' },
      ],
    },
  ],
  methods: [
    {
      id: 'lab',
      label: 'Lab Work',
      categories: [
        { id: 'wet_lab', label: 'Wet Lab', description: 'Sample sheets, CycIF, GeoMx, block selection.' },
        { id: 'dry_lab', label: 'Dry Lab & Pipelines', description: 'Computational methods and analysis pipelines.' },
        { id: 'protocols', label: 'Protocols & Methods Notes', description: 'SOPs, method write-ups, markdown protocols.' },
        { id: 'experiment_logs', label: 'Experiment Logs', description: 'Spreadsheets tracking experiments and samples.' },
        { id: 'scripts', label: 'Scripts & Code', description: 'Analysis scripts and notebooks.' },
        { id: 'methods_other', label: 'Other Methods', description: 'Additional methods files.' },
      ],
    },
  ],
  data: [
    {
      id: 'outputs',
      label: 'Data & Figures',
      categories: [
        { id: 'figures', label: 'Figures & Images', description: 'Plots, microscopy, and figure assets.' },
        { id: 'reports', label: 'Analysis Reports', description: 'PDF reports and result summaries.' },
        { id: 'datasets', label: 'Datasets & Tables', description: 'Spreadsheets, CSV, and structured data.' },
        { id: 'data_other', label: 'Other Data', description: 'Additional data folder files.' },
      ],
    },
  ],
  writing: [
    {
      id: 'dissemination',
      label: 'Writing & Dissemination',
      categories: [
        { id: 'abstracts', label: 'Abstracts', description: 'Conference and journal abstracts.' },
        { id: 'posters', label: 'Posters & Presentations', description: 'Poster files and talk decks.' },
        { id: 'manuscripts', label: 'Manuscripts', description: 'Draft papers and supplementary material.' },
        { id: 'peer_review', label: 'Peer Review', description: 'Manuscripts under peer review.' },
        { id: 'grants', label: 'Grant & PhD Applications', description: 'Funding proposals, doctoral school applications, and forms.' },
        { id: 'writing_slides', label: 'Writing Decks', description: 'Presentation files in writing folders.' },
        { id: 'writing_other', label: 'Other Writing', description: 'Additional dissemination files.' },
      ],
    },
  ],
  log: [
    {
      id: 'meetings',
      label: 'Meetings & Updates',
      categories: [
        {
          id: 'project_log',
          label: 'Project Log',
          description: 'Living project log — fully editable in Taskpad.',
        },
        { id: 'meeting_notes', label: 'Meeting Notes', description: 'Written notes and minutes.' },
        { id: 'meeting_slides', label: 'Lab Meeting Decks', description: 'Slides from lab meetings and updates.' },
        { id: 'meeting_decks', label: 'Presentations', description: 'PDF and slide decks from meetings.' },
        { id: 'meeting_other', label: 'Other Meetings', description: 'Additional meeting materials.' },
      ],
    },
  ],
  archive: [
    {
      id: 'archive',
      label: 'Archive',
      categories: [{ id: 'archive_root', label: 'Archived Files', description: 'Superseded and archived materials.' }],
    },
  ],
};

/** Build category groups for a tab, adding dynamic subfolder categories when files exist. */
export function buildProjectTabCategoryGroups(tabId, docs = []) {
  const base = STATIC_TAB_CATEGORIES[tabId] || [];
  const baseIds = new Set(
    base.flatMap((g) => g.categories.map((c) => c.id))
  );

  const dynamicIds = new Set();
  for (const doc of docs) {
    const cat = categorizeProjectPath(doc.path, tabId);
    if (!baseIds.has(cat) && cat.startsWith(`${tabId === 'methods' ? 'methods' : tabId}_`)) {
      dynamicIds.add(cat);
    }
    if (cat.startsWith('data_') && !baseIds.has(cat)) dynamicIds.add(cat);
    if (cat.startsWith('archive_') && cat !== 'archive_root') dynamicIds.add(cat);
    if (cat.startsWith('log_') && !baseIds.has(cat)) dynamicIds.add(cat);
    if (cat.startsWith('writing_') && !baseIds.has(cat)) dynamicIds.add(cat);
  }

  const dynamicCategories = [...dynamicIds].sort().map((id) => ({
    id,
    label: humanizeCategoryId(id),
    description: `Files in ${humanizeCategoryId(id)}.`,
  }));

  if (!dynamicCategories.length) return base;

  const groups = base.map((g) => ({ ...g, categories: [...g.categories] }));
  const last = groups[groups.length - 1];
  last.categories = [...last.categories, ...dynamicCategories];
  return groups;
}

export function getProjectTabDocumentConfig(tabId, docs = [], projectCode = '') {
  const categoryGroups = buildProjectTabCategoryGroups(tabId, docs);
  const defaultCategory = categoryGroups[0]?.categories[0]?.id || 'other';

  const meta = {
    overview: {
      title: 'Project Overview Files',
      description: 'README and top-level reference documents.',
    },
    plan: {
      title: 'Planning Documents',
      description: 'Timelines, gantt charts, and management materials.',
    },
    data: {
      title: 'Data & Figures',
      description: 'Analysis outputs, figures, datasets, and result reports.',
    },
    methods: {
      title: 'Methods & Experiments',
      description: 'Wet lab logs, protocols, pipelines, and method notes.',
    },
    writing: {
      title: 'Writing & Dissemination',
      description: 'Abstracts, posters, manuscripts, and grant applications.',
    },
    log: {
      title: 'Meetings & Updates',
      description: 'Project log, meeting notes, lab meeting decks, and updates.',
    },
    archive: {
      title: 'Archive',
      description: 'Archived and superseded project materials.',
    },
  };

  return {
    categoryGroups,
    defaultCategory,
    ...(meta[tabId] || { title: 'Project Files', description: 'Project documents.' }),
    tabFilter: (path) => pathBelongsToWorkspaceTab(path, tabId, projectCode),
    categorizePath: (path) => categorizeProjectPath(path, tabId, projectCode),
  };
}

export function projectDocumentTitle(doc) {
  const path = (doc?.path || '').replace(/\\/g, '/');
  const fileName = path.split('/').pop() || '';
  return humanizeFilenameLabel(fileName);
}
