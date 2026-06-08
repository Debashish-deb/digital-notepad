/**
 * t-CycIF documents — sourced from wet_lab_files twin, shown under CyCif nav.
 */

import { humanizeFilenameLabel } from './textCleanup.js';
import { smartDocumentTitle } from './smartDocumentTitle.js';

export function isCycifAntibodyInventoryPath(path) {
  const lower = (typeof path === 'string' ? path : (path?.path || ''))
    .replace(/\\/g, '/')
    .toLowerCase();
  if (lower.includes('cycif antibody inventory')) return true;
  if (lower.includes('antibody inventory') && /cycif|tcycif/i.test(lower)) return true;
  if (lower.includes('inventories') && lower.includes('antibody inventory')) return true;
  return false;
}

export function isCycifDocumentPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/');
  const lower = p.toLowerCase();
  if (lower.startsWith('tcycif projects')) return true;
  if (isCycifAntibodyInventoryPath(p)) return true;
  if (lower.includes('h&e of sldies after tcycif')) return true;
  if (/sectioning_order.*tcycif|tcycif.*sectioning_order/i.test(lower)) return true;
  if (lower.includes('geomx and cycif experiments')) return true;
  if (lower.startsWith('protocols, instructions/spatial protocols') && /cycif/i.test(p)) {
    return true;
  }
  return /tcycif/i.test(lower);
}

export function categorizeCycifPrimary(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/');
  const lower = p.toLowerCase();
  if (lower.includes('tcycif_individual_projects')) return 'cycif_projects';
  if (lower.startsWith('tcycif projects/instructions')) return 'cycif_instructions';
  if (
    lower.includes('h&e of sldies after tcycif') ||
    /sectioning_order.*tcycif|tcycif.*sectioning_order/i.test(lower)
  ) {
    return 'cycif_sectioning';
  }
  if (isCycifAntibodyInventoryPath(p)) return 'cycif_inventory';
  if (lower.startsWith('protocols, instructions/spatial protocols')) return 'cycif_protocols';
  if (lower.includes('geomx and cycif experiments')) return 'cycif_protocols';
  return 'cycif_other';
}

/** Sub-categories within each CyCif document tab */
export function categorizeCycifProjectSub(path) {
  const lower = (typeof path === 'string' ? path : (path?.path || '')).toLowerCase();
  if (lower.includes('template') || lower.includes('donotoverwrite')) return 'project_templates';
  if (lower.includes('validation') || lower.includes('antibody')) return 'project_validation';
  return 'project_runs';
}

export function categorizeCycifInstructionSub(path) {
  const lower = (typeof path === 'string' ? path : (path?.path || '')).toLowerCase();
  if (lower.includes('experiment planning')) return 'cycif_planning';
  if (lower.includes('antibodies and scanning')) return 'cycif_antibody_scan';
  return 'cycif_instruction_other';
}

export function categorizeCycifSectioningSub(path) {
  const lower = (typeof path === 'string' ? path : (path?.path || '')).toLowerCase();
  if (lower.includes('h&e')) return 'he_after_cycif';
  if (lower.includes('sectioning')) return 'sectioning_orders';
  return 'sectioning_other';
}

export function categorizeCycifInventorySub() {
  return 'antibody_inventory';
}

export function categorizeCycifProtocolSub(path) {
  const lower = (typeof path === 'string' ? path : (path?.path || '')).toLowerCase();
  if (lower.includes('geomx')) return 'geomx_cycif';
  if (lower.includes('spatial protocols')) return 'spatial_protocols';
  return 'cycif_other';
}

/** @deprecated Use categorizeCycifPrimary for tab routing */
export function categorizeCycifPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/');
  const lower = p.toLowerCase();
  if (lower.includes('tcycif_individual_projects')) return 'individual_projects';
  if (lower.startsWith('tcycif projects/instructions')) return 'instructions';
  if (lower.includes('h&e of sldies after tcycif') || /sectioning_order.*tcycif/i.test(lower)) {
    return 'sectioning';
  }
  if (isCycifAntibodyInventoryPath(p)) return 'antibody_inventory';
  if (lower.startsWith('protocols, instructions/spatial protocols')) return 'spatial_protocols';
  if (lower.includes('geomx and cycif experiments')) return 'geomx_cycif';
  return 'cycif_other';
}

export function cycifDocumentTitle(doc) {
  if (doc?.display_title) {
    return smartDocumentTitle(doc);
  }
  const fileName = (doc?.path || doc?.filename || '').split('/').pop() || '';
  return humanizeFilenameLabel(fileName);
}

const PROJECT_GROUPS = [
  {
    id: 'tcycif_projects',
    label: 'Individual Projects',
    categories: [
      {
        id: 'project_runs',
        label: 'Experiment Runs',
        description: 'Per-project staining plans and run spreadsheets.',
      },
      {
        id: 'project_validation',
        label: 'Antibody Validation',
        description: 'Validation experiments and antibody screening files.',
      },
      {
        id: 'project_templates',
        label: 'Templates',
        description: 'Project templates and planning spreadsheets.',
      },
    ],
  },
];

const INSTRUCTION_GROUPS = [
  {
    id: 'tcycif_instructions',
    label: 'Instructions & SOPs',
    categories: [
      {
        id: 'cycif_planning',
        label: 'Experiment Planning',
        description: 'Protocols, planning templates, and Cyclops auto-plan files.',
      },
      {
        id: 'cycif_antibody_scan',
        label: 'Antibodies & Scanning',
        description: 'Antibody database exports and scanning references.',
      },
      {
        id: 'cycif_instruction_other',
        label: 'Other Instructions',
        description: 'Additional instruction documents.',
      },
    ],
  },
];

const SECTIONING_GROUPS = [
  {
    id: 'tcycif_sectioning',
    label: 'Sectioning & H&E',
    categories: [
      {
        id: 'sectioning_orders',
        label: 'Sectioning Orders',
        description: 't-CycIF sectioning order spreadsheets.',
      },
      {
        id: 'he_after_cycif',
        label: 'H&E After t-CycIF',
        description: 'H&E staining records after CycIF runs.',
      },
      {
        id: 'sectioning_other',
        label: 'Other Sectioning Files',
        description: 'Additional sectioning-related documents.',
      },
    ],
  },
];

const INVENTORY_GROUPS = [
  {
    id: 'tcycif_inventory',
    label: 'Antibody Inventory',
    categories: [
      {
        id: 'antibody_inventory',
        label: 'CyCIF Antibody Inventory',
        description: 'Antibody panels and inventory spreadsheets for CycIF.',
      },
    ],
  },
];

const PROTOCOL_GROUPS = [
  {
    id: 'tcycif_protocols',
    label: 'Protocols & Resources',
    categories: [
      {
        id: 'spatial_protocols',
        label: 'Spatial CycIF Protocols',
        description: 'Spatial protocol docs and CycIF processing templates.',
      },
      {
        id: 'geomx_cycif',
        label: 'GeoMx & CycIF Resources',
        description: 'Combined GeoMx / CycIF experiment planning resources.',
      },
      {
        id: 'cycif_other',
        label: 'Other CycIF Files',
        description: 'Additional CycIF-related documents.',
      },
    ],
  },
];

function cycifTabConfig(tabId, categoryGroups, categorizePath, defaultCategory) {
  return {
    sectionIds: ['wet_lab_files'],
    categoryGroups,
    defaultCategory,
    categorizePath,
    documentTitle: cycifDocumentTitle,
    documentFilter: (path) =>
      isCycifDocumentPath(path) && categorizeCycifPrimary(path) === tabId,
  };
}

export const CYCIF_SECTION_CONFIG = {
  cycif_projects: cycifTabConfig(
    'cycif_projects',
    PROJECT_GROUPS,
    categorizeCycifProjectSub,
    'project_runs'
  ),
  cycif_instructions: cycifTabConfig(
    'cycif_instructions',
    INSTRUCTION_GROUPS,
    categorizeCycifInstructionSub,
    'cycif_planning'
  ),
  cycif_sectioning: cycifTabConfig(
    'cycif_sectioning',
    SECTIONING_GROUPS,
    categorizeCycifSectioningSub,
    'sectioning_orders'
  ),
  cycif_inventory: cycifTabConfig(
    'cycif_inventory',
    INVENTORY_GROUPS,
    categorizeCycifInventorySub,
    'antibody_inventory'
  ),
  cycif_protocols: cycifTabConfig(
    'cycif_protocols',
    PROTOCOL_GROUPS,
    categorizeCycifProtocolSub,
    'spatial_protocols'
  ),
};

export function getCycifConfig(subId) {
  return CYCIF_SECTION_CONFIG[subId] || null;
}

/** Legacy single knowledge-tab config */
export const CYCIF_CATEGORY_GROUPS = [
  {
    id: 'tcycif_core',
    label: 't-CycIF Projects',
    categories: PROJECT_GROUPS[0].categories.concat(INSTRUCTION_GROUPS[0].categories),
  },
  {
    id: 'tcycif_support',
    label: 'Supporting Materials',
    categories: SECTIONING_GROUPS[0].categories.concat(
      INVENTORY_GROUPS[0].categories,
      PROTOCOL_GROUPS[0].categories
    ),
  },
];

export const CYCIF_FILES_CONFIG = {
  sectionIds: ['wet_lab_files'],
  categoryGroups: CYCIF_CATEGORY_GROUPS,
  defaultCategory: 'project_runs',
  categorizePath: categorizeCycifPath,
  documentTitle: cycifDocumentTitle,
  documentFilter: isCycifDocumentPath,
};
