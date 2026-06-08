/**
 * Path-based workflow categories for wet-lab protocols.
 * IDs align with backend document_library_service._categorize_wet_lab_protocol_path.
 */

import { isCycifDocumentPath } from './cycifCategories.js';

const PROTOCOLS_ROOT = /^protocols(?:,\s*instructions)?\//i;
const PATIENT_ROOT = /^patient sample protocols\//i;

/** Workflow categories inside Protocols & Methods (flat list — no duplicate group label). */
export const WET_LAB_PROTOCOL_CATEGORIES = [
  {
    id: 'patient_samples',
    label: 'Patient Sample Protocols',
    description: 'Per-patient tissue collection and processing protocols.',
  },
  {
    id: 'sample_preparation',
    label: 'Sample Preparation',
    description: 'Tissue dissociation, organoid culture, iPDCs, and medium recipes.',
  },
  {
    id: 'tissue_processing',
    label: 'Tissue Processing & FFPE',
    description: 'Fixation, processing, and FFPE block preparation SOPs.',
  },
  {
    id: 'spatial_assays',
    label: 'Spatial & Imaging Assays',
    description: 'Spatial assays, GeoMx slide prep, and imaging workflow SOPs.',
  },
  {
    id: 'staining_flow',
    label: 'Staining & Flow Cytometry',
    description: 'Immunofluorescence, flow cytometry, and immune profiling protocols.',
  },
  {
    id: 'lab_operations',
    label: 'Lab Operations',
    description: 'Sterilization, calibration, precipitation, and troubleshooting SOPs.',
  },
  {
    id: 'imaging_qc',
    label: 'Imaging & QC References',
    description: 'EVOS scale-bar references, counting chambers, and microscopy QC.',
  },
  {
    id: 'scrna',
    label: 'scRNA-seq',
    description: 'Single-cell RNA sequencing protocols and notes.',
  },
  {
    id: 'protocol_archive',
    label: 'Protocol Archive',
    description: 'Legacy bench protocols stored under Archive 2.0.',
  },
  {
    id: 'general_protocols',
    label: 'General Protocols',
    description: 'Root-level protocols and instructions not in a subfolder.',
  },
];

/** @deprecated Use WET_LAB_PROTOCOL_CATEGORIES — kept for callers expecting group shape. */
export const WET_LAB_PROTOCOL_MICRO_GROUPS = [
  {
    id: 'protocols_methods',
    label: 'Protocols & Methods',
    categories: WET_LAB_PROTOCOL_CATEGORIES,
  },
];

const PATIENT_CATEGORY_IDS = new Set(['patient_samples']);

export function isWetLabProtocolCategory(categoryId) {
  return (
    PATIENT_CATEGORY_IDS.has(categoryId)
    || WET_LAB_PROTOCOL_CATEGORIES.some((c) => c.id === categoryId)
    || categoryId === 'histology_services'
  );
}

export function categorizeWetLabProtocolPath(path) {
  const p = (path || '').replace(/\\/g, '/');
  const lower = p.toLowerCase();

  if (PATIENT_ROOT.test(p)) {
    return 'patient_samples';
  }

  if (PROTOCOLS_ROOT.test(p) || lower.startsWith('protocols')) {
    const rest = p.includes('/') ? p.slice(p.indexOf('/') + 1) : p;
    const restLower = rest.toLowerCase();
    const topFolder = rest.split('/')[0].toLowerCase();

    if (topFolder.includes('spatial') || /geomx|pickseq|lc-ms|tcycif/i.test(restLower)) {
      return 'spatial_assays';
    }
    if (
      topFolder.includes('tissue dissociation')
      || topFolder.includes('organoid')
      || topFolder.includes('ipdc')
    ) {
      return 'sample_preparation';
    }
    if (
      topFolder === 'anastasia'
      || /tissue.fixation|tissue.processing|tissue_processing|ffpe/i.test(restLower)
    ) {
      return 'tissue_processing';
    }
    if (topFolder.includes('archive')) return 'protocol_archive';
    if (topFolder.includes('evos') || topFolder.includes('reference')) return 'imaging_qc';
    if (topFolder.includes('scrna')) return 'scrna';
    if (/flowcytometry|flow cytometry|immunofluorescence|\bif\b|staining/i.test(restLower)) {
      return 'staining_flow';
    }
    if (/steriliz|calibration|precipitation|troubleshoot|ph meter/i.test(restLower)) {
      return 'lab_operations';
    }
    return 'general_protocols';
  }

  if (lower.includes('orders for slides')) return 'histology_services';
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
