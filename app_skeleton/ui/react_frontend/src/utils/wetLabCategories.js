/**
 * Side-tab categories for Wet-lab database files (wet_lab_files twin).
 * CycIF files are shown under the CyCif section — see cycifCategories.js.
 * Protocol paths use micro-categories from wetLabProtocolCategories.js.
 */

import { humanizeFilenameLabel } from './textCleanup.js';
import { isCycifDocumentPath } from './cycifCategories.js';
import {
  categorizeWetLabProtocolPath,
  WET_LAB_PROTOCOL_MICRO_GROUPS,
  isWetLabProtocolPath,
} from './wetLabProtocolCategories.js';

const WET_LAB_NON_PROTOCOL_GROUPS = [
  {
    id: 'wet_platforms',
    label: 'Spatial & Platform Assays',
    categories: [
      {
        id: 'geomx',
        label: 'NanoString GeoMx',
        description: 'GeoMx project notes, protocols, and run documentation.',
      },
      {
        id: 'xenium',
        label: 'Xenium',
        description: 'Xenium experiment plans and spatial transcriptomics files.',
      },
    ],
  },
  {
    id: 'wet_ops',
    label: 'Inventory & Operations',
    categories: [
      {
        id: 'inventories',
        label: 'Reagents, Samples & Equipment',
        description: 'Inventory spreadsheets, reagent lists, and equipment records.',
      },
      {
        id: 'waste_mgmt',
        label: 'Waste & Chemical Inventory',
        description: 'Waste management, Fortum forms, and chemical inventory SOPs.',
      },
      {
        id: 'wet_spreadsheets',
        label: 'Registers & Spreadsheets',
        description: 'Vacation sample collection, legacy reagent lists, and misc. registers.',
      },
    ],
  },
];

export const WET_LAB_CATEGORY_GROUPS = [
  WET_LAB_PROTOCOL_MICRO_GROUPS[0],
  ...WET_LAB_NON_PROTOCOL_GROUPS,
];

export function categorizeWetLabPath(path) {
  const protocolCat = categorizeWetLabProtocolPath(path);
  if (protocolCat) return protocolCat;

  const p = (path || '').replace(/\\/g, '/').toLowerCase();
  if (p.includes('orders for slides')) return 'slide_orders';
  if (p.startsWith('nanostring geomx') || p.startsWith('geomx projects')) return 'geomx';
  if (p.startsWith('xenium')) return 'xenium';
  if (p.startsWith('inventories')) return 'inventories';
  if (p.startsWith('waste management')) return 'waste_mgmt';
  if (/\.xlsx$/i.test(p) || p.includes('reagents.xlsx') || p.includes('vacation')) {
    return 'wet_spreadsheets';
  }
  return 'proto_general';
}

export function wetLabDocumentTitle(doc) {
  const fileName = (doc?.path || '').split('/').pop() || '';
  return humanizeFilenameLabel(fileName);
}

export const WET_LAB_FILES_CONFIG = {
  sectionIds: ['wet_lab_files'],
  categoryGroups: WET_LAB_CATEGORY_GROUPS,
  defaultCategory: 'proto_sample_prep',
  categorizePath: categorizeWetLabPath,
  documentTitle: wetLabDocumentTitle,
  documentFilter: (path) => !isCycifDocumentPath(path),
};

export const WET_LAB_PROTOCOLS_CONFIG = {
  sectionIds: ['wet_lab_files'],
  categoryGroups: WET_LAB_PROTOCOL_MICRO_GROUPS,
  defaultCategory: 'proto_sample_prep',
  categorizePath: categorizeWetLabPath,
  documentTitle: wetLabDocumentTitle,
  documentFilter: isWetLabProtocolPath,
};
