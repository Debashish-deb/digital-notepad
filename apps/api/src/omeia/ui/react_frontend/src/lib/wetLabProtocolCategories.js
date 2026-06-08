/**
 * Path-based micro-categories for wet-lab protocols — flattens deep folder trees
 * into workflow-oriented chips (sample prep, spatial, staining, etc.).
 */

import { isCycifDocumentPath } from './cycifCategories.js';

const PROTOCOLS_ROOT = /^protocols(?:,\s*instructions)?\//i;
const PATIENT_ROOT = /^patient sample protocols\//i;

/** Workflow chips inside the Protocols & SOPs nav group. */
export const WET_LAB_PROTOCOL_MICRO_GROUPS = [
  {
    id: 'wet_protocols',
    label: 'Protocols & SOPs',
    categories: [
      {
        id: 'patient_omentum',
        label: 'Patient · Omentum',
        description: 'Per-sample protocols for omentum (pOme / pOva) specimens.',
      },
      {
        id: 'patient_adnexa',
        label: 'Patient · Adnexa',
        description: 'Per-sample protocols for adnexal (pAdn) specimens.',
      },
      {
        id: 'patient_other_sites',
        label: 'Patient · Other Sites',
        description: 'Protocols for bowel, spleen, vaginal, and other non-omentum sites.',
      },
      {
        id: 'patient_misc',
        label: 'Patient · Unsorted',
        description: 'Patient sample protocols without a clear site code in the filename.',
      },
      {
        id: 'proto_sample_prep',
        label: 'Sample Prep & Organoids',
        description: 'Tissue dissociation, organoid culture, iPDCs, and related medium recipes.',
      },
      {
        id: 'proto_tissue_processing',
        label: 'Tissue Fixation & FFPE',
        description: 'Fixation, processing, and FFPE block preparation SOPs.',
      },
      {
        id: 'proto_spatial',
        label: 'Spatial & CycIF',
        description: 'Spatial assays, t-CycIF, GeoMx slide prep, and imaging reports.',
      },
      {
        id: 'proto_staining',
        label: 'Staining & Flow',
        description: 'Immunofluorescence, flow cytometry, and immune profiling protocols.',
      },
      {
        id: 'proto_archive',
        label: 'Protocol Archive',
        description: 'Legacy bench protocols stored under Archive 2.0.',
      },
      {
        id: 'proto_imaging',
        label: 'Imaging & QC References',
        description: 'EVOS scale-bar references, counting chambers, and microscopy QC.',
      },
      {
        id: 'proto_lab_ops',
        label: 'Lab Operations',
        description: 'Sterilization, calibration, precipitation, and troubleshooting SOPs.',
      },
      {
        id: 'proto_scrna',
        label: 'scRNA-seq',
        description: 'Single-cell RNA sequencing protocols and notes.',
      },
      {
        id: 'proto_general',
        label: 'General Protocols',
        description: 'Root-level protocols and instructions not in a subfolder.',
      },
      {
        id: 'slide_orders',
        label: 'Slides & Sections Orders',
        description: 'Orders for slides, sections, and histology services.',
      },
    ],
  },
];

export function isWetLabProtocolCategory(categoryId) {
  return (
    categoryId?.startsWith('patient_')
    || categoryId?.startsWith('proto_')
    || categoryId === 'slide_orders'
  );
}

export function categorizeWetLabProtocolPath(path) {
  const p = (path || '').replace(/\\/g, '/');
  const lower = p.toLowerCase();

  if (PATIENT_ROOT.test(p)) {
    const fileName = p.split('/').pop() || '';
    if (/pome|pova/i.test(fileName)) return 'patient_omentum';
    if (/padn/i.test(fileName)) return 'patient_adnexa';
    if (/r(spl|bow|vagina|per|asc)/i.test(fileName)) return 'patient_other_sites';
    return 'patient_misc';
  }

  if (PROTOCOLS_ROOT.test(p) || lower.startsWith('protocols')) {
    const rest = p.includes('/') ? p.slice(p.indexOf('/') + 1) : p;
    const restLower = rest.toLowerCase();
    const topFolder = rest.split('/')[0].toLowerCase();

    if (topFolder.includes('spatial') || /cycif|geomx|pickseq|lc-ms|tcycif/i.test(restLower)) {
      return 'proto_spatial';
    }
    if (
      topFolder.includes('tissue dissociation')
      || topFolder.includes('organoid')
      || topFolder.includes('ipdc')
    ) {
      return 'proto_sample_prep';
    }
    if (
      topFolder === 'anastasia'
      || /tissue.fixation|tissue.processing|tissue_processing|ffpe/i.test(restLower)
    ) {
      return 'proto_tissue_processing';
    }
    if (topFolder.includes('archive')) return 'proto_archive';
    if (topFolder.includes('evos') || topFolder.includes('reference')) return 'proto_imaging';
    if (topFolder.includes('scrna')) return 'proto_scrna';
    if (/flowcytometry|flow cytometry|immunofluorescence|\bif\b|staining/i.test(restLower)) {
      return 'proto_staining';
    }
    if (/steriliz|calibration|precipitation|troubleshoot|ph meter/i.test(restLower)) {
      return 'proto_lab_ops';
    }
    return 'proto_general';
  }

  if (lower.includes('orders for slides')) return 'slide_orders';
  return null;
}

/** Human-readable folder trail for flattened protocol lists. */
export function wetLabProtocolPathHint(path) {
  const parts = String(path || '').replace(/\\/g, '/').split('/').filter(Boolean);
  if (parts.length <= 2) return null;
  return parts.slice(1, -1).join(' › ');
}

export function isWetLabProtocolPath(path) {
  return !isCycifDocumentPath(path) && categorizeWetLabProtocolPath(path) != null;
}
