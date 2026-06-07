/**
 * Route Overview "Research materials" files into project workspace document browsers.
 */

import { projectsCatalog } from '../data/projectsCatalog.js';
import { overviewDocumentTitle } from './overviewCategories.js';
import { collectSectionDocuments } from './documentBrowserUtils.js';
import { fetchLabSectionProcessed } from './labDatabaseUtils.js';

export const RESEARCH_MATERIALS_SECTION_ID = 'overview_research_materials';
export const RESEARCH_MATERIAL_VIRTUAL_PREFIX = '__research_materials__/';

const APPLICANT_FOLDER_HINTS = {
  ada: ['junquera'],
  aleksandra: ['shabanova'],
  maria: ['elomaa', 'mh'],
  'maría': ['elomaa', 'mh'],
  pablo: ['siliceo'],
  wenqing: ['chen'],
  zhihan: ['liang'],
  ziqi: ['kang'],
};

const TOPIC_PROJECT_HINTS = [
  { re: /\besgo\b|ovca|ovarian|hgsoc|oncosys/i, codes: ['Sequencing', 'HGSC_scRNAseq', 'SPACE', 'Organoids', 'Mesenchymal_Ovca', 'KRAS'] },
  { re: /\bican\b|icandoc/i, codes: ['NKI', 'HGSC_scRNAseq', 'Sequencing', 'Organoids'] },
  { re: /spatial biology|spacestat/i, codes: ['SPACE', 'SPACEstat', 'SPACEjoint'] },
  { re: /geomx|cycif|spatial/i, codes: ['SPACE', 'Myelonets', 'EMT', 'TLS'] },
  { re: /embl|multi-omic/i, codes: ['SC_Integration', 'SPACEstat', 'HGSC_scRNAseq'] },
  { re: /cytodata/i, codes: ['Tribus', 'Pixel_AI'] },
  { re: /\bkras\b/i, codes: ['KRAS'] },
  { re: /eyemt|\beye\b/i, codes: ['EyeMT'] },
  { re: /endometrial/i, codes: ['Endometrial_HRD'] },
  { re: /mesenchymal/i, codes: ['Mesenchymal_Ovca'] },
  { re: /myelonet/i, codes: ['Myelonets'] },
  { re: /fanconi/i, codes: ['Fanconi'] },
  { re: /proteomic/i, codes: ['Proteomics'] },
];

const DEFAULT_LAB_WIDE_PROJECT = 'SideProjects';

let twinCache = null;
let assignmentCache = null;

export function categorizeResearchMaterialPath(path) {
  const p = (path || '').replace(/\\/g, '/').toLowerCase();
  if (p.startsWith('conference')) return 'conference';
  if (p.startsWith('peer-review') || p.includes('peer-review')) return 'peer_review';
  if (p.startsWith('phd')) return 'phd_apps';
  if (p.startsWith('presentations')) return 'presentations';
  return 'presentations';
}

export function researchMaterialWritingCategory(path, materialType = categorizeResearchMaterialPath(path)) {
  const lower = (path || '').toLowerCase();
  if (materialType === 'peer_review') return 'peer_review';
  if (materialType === 'phd_apps') return 'grants';
  if (lower.includes('poster')) return 'posters';
  if (materialType === 'conference') {
    return lower.includes('abstract') ? 'abstracts' : 'posters';
  }
  if (lower.includes('abstract')) return 'abstracts';
  return 'posters';
}

function normalizeToken(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function buildProjectSearchIndex(catalog = projectsCatalog) {
  return catalog.map((project) => {
    const tokens = new Set();
    const add = (value) => {
      const norm = normalizeToken(value);
      if (!norm || norm.length < 2) return;
      norm.split(/\s+/).forEach((part) => {
        if (part.length >= 3) tokens.add(part);
      });
      tokens.add(norm.replace(/\s+/g, ''));
    };

    add(project.project_code);
    add(project.project_name);
    add(project.project_short_title);
    add(project.disease_focus);
    add(project.research_question);
    add(project.project_summary);
    add(project.project_lead);
    for (const person of project.members || []) add(person.name);
    for (const person of project.collaborators || []) add(person);

    return { project, tokens: [...tokens] };
  });
}

function scoreProjectMatch(searchText, indexEntry) {
  const hay = normalizeToken(searchText);
  if (!hay) return 0;
  let score = 0;
  for (const token of indexEntry.tokens) {
    if (token.length < 3) continue;
    if (hay.includes(token)) {
      score += Math.min(12, 4 + token.length);
    }
  }
  if (hay.includes(normalizeToken(indexEntry.project.project_code))) {
    score += 20;
  }
  return score;
}

function inferFromApplicantFolder(path, catalog) {
  const match = path.match(/iCANDOC\/([^/]+)/i);
  if (!match) return null;
  const folder = match[1].toLowerCase();
  const hints = APPLICANT_FOLDER_HINTS[folder] || [folder];

  let best = null;
  let bestScore = 0;

  for (const project of catalog) {
    let score = 0;
    const lead = normalizeToken(project.project_lead);
    const names = [
      lead,
      ...(project.members || []).map((m) => normalizeToken(m.name)),
      ...(project.collaborators || []).map((c) => normalizeToken(c)),
    ].filter(Boolean);

    for (const hint of hints) {
      for (const name of names) {
        if (name.includes(hint)) {
          score += name === lead || project.project_lead?.toLowerCase().includes(hint) ? 18 : 10;
        }
      }
    }

    if (score > bestScore) {
      bestScore = score;
      best = project.project_code;
    }
  }

  return bestScore >= 10 ? best : null;
}

function inferFromTopicHints(path) {
  const text = path.replace(/\\/g, '/');
  for (const hint of TOPIC_PROJECT_HINTS) {
    if (hint.re.test(text)) return hint.codes[0];
  }
  return null;
}

function inferFromProjectIndex(path, doc, index) {
  const text = [path, doc?.excerpt, doc?.title, doc?.name].filter(Boolean).join(' ');
  let best = null;
  let bestScore = 0;

  for (const entry of index) {
    const score = scoreProjectMatch(text, entry);
    if (score > bestScore) {
      bestScore = score;
      best = entry.project.project_code;
    }
  }

  return bestScore >= 12 ? best : null;
}

export function inferResearchMaterialProject(path, doc, catalog = projectsCatalog) {
  const index = buildProjectSearchIndex(catalog);

  return (
    inferFromApplicantFolder(path, catalog) ||
    inferFromTopicHints(path) ||
    inferFromProjectIndex(path, doc, index) ||
    DEFAULT_LAB_WIDE_PROJECT
  );
}

export async function loadResearchMaterialsTwin() {
  if (twinCache) return twinCache;
  twinCache = await fetchLabSectionProcessed(RESEARCH_MATERIALS_SECTION_ID);
  return twinCache;
}

export function toVirtualResearchDoc(doc, twin, projectCode) {
  const originalPath = doc.path;
  const materialType = categorizeResearchMaterialPath(originalPath);
  return {
    ...doc,
    path: `${RESEARCH_MATERIAL_VIRTUAL_PREFIX}${originalPath}`,
    researchMaterialOriginalPath: originalPath,
    researchMaterialRoot: twin?.relative_root || 'Overview/RESEARCH MATERIALS',
    isResearchMaterial: true,
    routedProjectCode: projectCode,
    sourceSection: RESEARCH_MATERIALS_SECTION_ID,
    display_title: overviewDocumentTitle(doc),
    categoryId: researchMaterialWritingCategory(originalPath, materialType),
    asset_bucket: 'documents',
    section_label: 'Research materials (routed)',
  };
}

export async function buildResearchMaterialAssignments(catalog = projectsCatalog) {
  if (assignmentCache) return assignmentCache;

  const twin = await loadResearchMaterialsTwin();
  if (!twin?.content_library?.sections?.length) {
    assignmentCache = { twin, byProject: {} };
    return assignmentCache;
  }

  const docs = collectSectionDocuments(twin, {
    categorizePath: categorizeResearchMaterialPath,
    documentTitle: overviewDocumentTitle,
  });

  const byProject = {};
  for (const doc of docs) {
    const code = inferResearchMaterialProject(doc.path, doc, catalog);
    if (!byProject[code]) byProject[code] = [];
    byProject[code].push(toVirtualResearchDoc(doc, twin, code));
  }

  assignmentCache = { twin, byProject };
  return assignmentCache;
}

export async function getResearchMaterialsForProject(projectCode, catalog = projectsCatalog) {
  const { byProject } = await buildResearchMaterialAssignments(catalog);
  return byProject[projectCode] || [];
}

export function clearResearchMaterialsCache() {
  twinCache = null;
  assignmentCache = null;
}
