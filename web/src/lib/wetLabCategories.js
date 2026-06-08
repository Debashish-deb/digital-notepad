/**
 * Wet-lab library categories (wet_lab_files twin).
 * Single group, flat leaf categories — avoids duplicate parent/child labels in the UI.
 * CyCIF paths are excluded; see cycifCategories.js.
 */

import { humanizeFilenameLabel } from './textCleanup.js';
import { smartDocumentTitle } from './smartDocumentTitle.js';
import { isCycifDocumentPath } from './cycifCategories.js';
import {
  categorizeWetLabProtocolPath,
  WET_LAB_PROTOCOL_CATEGORIES,
  isWetLabProtocolPath,
} from './wetLabProtocolCategories.js';

const WET_LAB_SUPPORT_CATEGORIES = [
  {
    id: 'reagents_inventory',
    label: 'Reagent Inventories',
    description: 'Reagent lists, antibody panels, and sample inventory spreadsheets.',
  },
  {
    id: 'spatial_geomx',
    label: 'GeoMx Resources',
    description: 'GeoMx project notes, run documentation, and platform files.',
  },
  {
    id: 'spatial_xenium',
    label: 'Xenium Resources',
    description: 'Xenium experiment plans and spatial transcriptomics files.',
  },
  {
    id: 'registers_data',
    label: 'Registers & Spreadsheets',
    description: 'Vacation sample collection, legacy reagent lists, and misc. registers.',
  },
  {
    id: 'chemical_safety',
    label: 'Chemical Safety & Waste',
    description: 'Waste management, Fortum forms, and chemical inventory SOPs.',
  },
  {
    id: 'histology_services',
    label: 'Histology & Slide Orders',
    description: 'Orders for slides, sections, and histology services.',
  },
];

/** One library group — section headers use category labels only (no repeated group name). */
export const WET_LAB_CATEGORY_GROUPS = [
  {
    id: 'wet_lab_library',
    label: 'Lab Operations',
    categories: [...WET_LAB_PROTOCOL_CATEGORIES, ...WET_LAB_SUPPORT_CATEGORIES],
  },
];

export function categorizeWetLabPath(path) {
  const protocolCat = categorizeWetLabProtocolPath(path);
  if (protocolCat) return protocolCat;

  const p = (path || '').replace(/\\/g, '/').toLowerCase();
  if (p.startsWith('inventories')) return 'reagents_inventory';
  if (p.startsWith('nanostring geomx') || p.startsWith('geomx projects')) return 'spatial_geomx';
  if (p.startsWith('xenium')) return 'spatial_xenium';
  if (p.startsWith('waste management')) return 'chemical_safety';
  if (/\.xlsx$/i.test(p) || p.includes('reagents.xlsx') || p.includes('vacation')) {
    return 'registers_data';
  }
  return 'general_protocols';
}

export function wetLabDocumentTitle(doc) {
  if (doc?.display_title || doc?.title) {
    return smartDocumentTitle(doc);
  }
  const fileName = (doc?.path || '').split('/').pop() || '';
  return humanizeFilenameLabel(fileName);
}

export const WET_LAB_FILES_CONFIG = {
  sectionIds: ['wet_lab_files'],
  categoryGroups: WET_LAB_CATEGORY_GROUPS,
  defaultCategory: 'general_protocols',
  categorizePath: categorizeWetLabPath,
  documentTitle: wetLabDocumentTitle,
  documentFilter: (path) => !isCycifDocumentPath(path),
};

export const WET_LAB_PROTOCOLS_CONFIG = {
  sectionIds: ['wet_lab_files'],
  categoryGroups: [
    {
      id: 'protocols_methods',
      label: 'Protocols & Methods',
      categories: WET_LAB_PROTOCOL_CATEGORIES,
    },
  ],
  defaultCategory: 'general_protocols',
  categorizePath: categorizeWetLabPath,
  documentTitle: wetLabDocumentTitle,
  documentFilter: isWetLabProtocolPath,
};
