/**
 * Overview tab categories — mirrors Google Drive GENERAL LAB INFORMATION layout.
 */

import { humanizeFilenameLabel } from './textCleanup.js';
import {
  collectSectionDocuments,
  flattenCategoryOrder,
  groupDocumentsByCategory,
  findCategoryMeta,
} from './documentBrowserUtils.js';

const OVERVIEW_DISPLAY_TITLES = {
  'BSL2_documents_Färkkilä_lab/GMM Ilmoitis Hakemus Täyttöohje2018.doc':
    'GMM Application Form — Filling Instructions (2018)',
  'BSL2_documents_Färkkilä_lab/GMM riskiarviounti Tayttoohje.doc':
    'GMM Risk Assessment — Filling Instructions',
  'BSL2_documents_Färkkilä_lab/Riskinarviointipohja_BSL-2.pdf':
    'Risk Assessment Template (BSL-2)',
  'BSL2_documents_Färkkilä_lab/BSL1 and 2/THL_Riskinarviointipohja_BSL-2.pdf':
    'THL Risk Assessment Template (BSL-2)',
  'BSL2_documents_Färkkilä_lab/BSL1 and 2/Action Plan in case of an emergency _Färkkilä_Vähärautio_Cell Culture.docx':
    'Emergency Action Plan — Cell Culture Rooms',
  'BSL2_documents_Färkkilä_lab/BSL1 and 2/Biosafety Manual for cell culture rooms B324a1a2.docx':
    'Biosafety Manual — Cell Culture Rooms B324a1/a2',
  'BSL2_documents_Färkkilä_lab/BSL1 and 2/Toimintasuunnitelma_Färkkilä_Cell Culture.docx':
    'Action Plan — Färkkilä Cell Culture',
  'BSL2_documents_Färkkilä_lab/GMO Application drafts of Application and risk assessment /GMMlomake2018.doc':
    'GMM Application Form 2018',
  'BSL2_documents_Färkkilä_lab/GMO Application drafts of Application and risk assessment /GMMriskarvlomake.doc':
    'GMM Risk Assessment Form',
  'GSK_papers_2021/MSDS - GSK3745417C.pdf': 'MSDS — GSK3745417C',
  'ROOM_NUMBERS_Oncosys.jpg': 'Oncosys Room Numbers',
  'Article_FFPE_DNA_isolation.pdf': 'FFPE DNA Isolation — Research Article',
  'FFPE_sequensing_artifacts_miniReview.pdf': 'FFPE Sequencing Artifacts — Mini Review',
  'Färkkilä_Lab_ ONBOARDING.docx': 'Färkkilä Lab Onboarding',
  'Färkkilä_Lab_OUTBOARDING_UPD30.6.2025.docx': 'Färkkilä Lab Outboarding (Jun 2025)',
  'IMPORTANT_PHONE_NUMBERS_Links_and_EMAILS.docx': 'Important Phone Numbers, Links & Emails',
  'Biobank requests/Biopankki luovotuspyyntö.docx': 'Biobank Transfer Request',
  'Biobank requests/Biopankki luovotuspyyntö.pdf': 'Biobank Transfer Request (PDF)',
  'Biobank requests/Ennakoiva pyyntö.pdf': 'Advance Biobank Request',
};

export function overviewDocumentTitle(doc) {
  const path = (doc?.path || '').replace(/\\/g, '/');
  if (OVERVIEW_DISPLAY_TITLES[path]) return OVERVIEW_DISPLAY_TITLES[path];
  const fileName = path.split('/').pop() || '';
  return humanizeFilenameLabel(fileName);
}

// ——— Documents & Permits ———

export const DOCUMENTS_CATEGORY_GROUPS = [
  {
    id: 'permits',
    label: 'Permits & Compliance',
    categories: [
      {
        id: 'biobank',
        label: 'Biobank Requests & Templates',
        description: 'Transfer requests, advance requests, and biobank agreement templates.',
      },
      {
        id: 'bsl_forms',
        label: 'BSL-2 Forms & Templates',
        description: 'GMM forms, risk assessment templates, and THL filing instructions.',
      },
      {
        id: 'bsl1_2',
        label: 'Biosafety Manuals (BSL-1 & BSL-2)',
        description: 'Biosafety manuals, emergency action plans, insurance, and THL templates.',
      },
      {
        id: 'bsl_drafts',
        label: 'Modification Drafts',
        description: 'Draft biosafety manuals and cell-culture rule updates pending approval.',
      },
      {
        id: 'bsl_gmo',
        label: 'GMO Application Drafts',
        description: 'GMM application forms and risk assessment drafts.',
      },
      { id: 'ethanol', label: 'Ethanol Permission (Valvira 2019)', description: 'Valvira permits, appeals, and inventory records.' },
    ],
  },
  {
    id: 'reference',
    label: 'Reference & Equipment',
    categories: [
      { id: 'datasheets', label: 'Datasheets & Handbooks', description: 'Product datasheets and lab handbooks.' },
      { id: 'qiagen', label: 'Qiagen Handbooks', description: 'Qiagen kit handbooks and protocols.' },
      { id: 'equipment_barcodes', label: 'Equipment Barcodes', description: 'Barcode photos for REVCO, incubators, etc.' },
      { id: 'root_docs', label: 'General Reference', description: 'FFPE articles, room numbers, and misc. reference PDFs.' },
    ],
  },
  {
    id: 'pharma',
    label: 'GSK Papers',
    categories: [
      { id: 'gsk_nov2021', label: 'GSK Nov 2021 (GSK3859856B)', description: 'Proforma invoices, customs, and purpose forms.' },
      { id: 'gsk_filled', label: 'GSK Filled Forms (Drafts)', description: 'Completed RFI forms — Ashwini & Anastasiya.' },
      { id: 'gsk_unfilled', label: 'GSK Unfilled Forms', description: 'Blank University of Helsinki RFI templates.' },
      { id: 'gsk_root', label: 'GSK Other', description: 'MSDS and other GSK reference files.' },
    ],
  },
];

export function categorizeDocumentsPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/');
  const lower = p.toLowerCase();

  if (lower.startsWith('biobank requests')) return 'biobank';
  if (lower.includes('bsl2_documents')) {
    if (lower.includes('bsl1 and 2')) return 'bsl1_2';
    if (lower.includes('drafts for modification')) return 'bsl_drafts';
    if (lower.includes('gmo application')) return 'bsl_gmo';
    return 'bsl_forms';
  }
  if (lower.startsWith('ethanol_permission')) return 'ethanol';
  if (lower.includes('qiagen handbooks')) return 'qiagen';
  if (lower.startsWith('datasheets&handbooks')) return 'datasheets';
  if (lower.startsWith('equipment_barcodes')) return 'equipment_barcodes';
  if (lower.startsWith('gsk_papers')) {
    if (lower.includes('not filled forms')) return 'gsk_unfilled';
    if (lower.includes('filled forms')) return 'gsk_filled';
    if (lower.includes('nov2021')) return 'gsk_nov2021';
    return 'gsk_root';
  }
  return 'root_docs';
}

// ——— Guidelines ———

export const GUIDELINES_CATEGORY_GROUPS = [
  {
    id: 'guidelines',
    label: 'Lab Guidelines',
    categories: [
      {
        id: 'research',
        label: 'Research-related',
        description: 'Abstracts, presentations, theses, meetings, grants, and affiliations.',
      },
      {
        id: 'work',
        label: 'Work-related',
        description: 'Holidays, sick leave, and day-to-day work guidelines.',
      },
    ],
  },
];

export function categorizeGuidelinesPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/').toLowerCase();
  if (p.startsWith('work-related')) return 'work';
  return 'research';
}

// ——— Onboarding ———

export const ONBOARDING_CATEGORY_GROUPS = [
  {
    id: 'onboarding',
    label: 'Onboarding & Outboarding',
    categories: [
      {
        id: 'orientation',
        label: 'Orientation & Safety',
        description: 'Onboarding decks, orientation PDFs, and lab safety from Kauppi lab.',
      },
      {
        id: 'contacts',
        label: 'Contacts & Procedures',
        description: 'Onboarding/outboarding checklists and important contacts.',
      },
    ],
  },
];

export function categorizeOnboardingPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/').toLowerCase();
  if (
    p.includes('phone') ||
    p.includes('email') ||
    p.includes('onboarding') ||
    p.includes('outboarding') ||
    p.includes('important_phone')
  ) {
    return 'contacts';
  }
  return 'orientation';
}

// ——— Lab cleaning ———

export const CLEANING_CATEGORY_GROUPS = [
  {
    id: 'cleaning',
    label: 'Lab Cleaning',
    categories: [
      {
        id: 'cleaning_20250528',
        label: 'Cleaning Day — 28 May 2025',
        description: 'Data cleaning day tasks and storage unit comments.',
      },
      {
        id: 'cleaning_251205',
        label: 'Cleaning Day — 5 Dec 2025',
        description: 'Wet lab, dry lab, and external drive cleaning inventories.',
      },
    ],
  },
];

export function categorizeCleaningPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/').toLowerCase();
  if (p.includes('251205')) return 'cleaning_251205';
  return 'cleaning_20250528';
}

// ——— Personnel ———

export const PERSONNEL_CATEGORY_GROUPS = [
  {
    id: 'personnel',
    label: 'Personnel',
    categories: [
      { id: 'roster', label: 'Current Personnel', description: 'Active lab member records.' },
      { id: 'hiring', label: 'Hiring & Recruitment', description: 'Job ads, interview materials, and scoring matrices.' },
      { id: 'lab_management', label: 'Lab Management', description: 'Management structure, role descriptions, and instructions.' },
    ],
  },
];

export function categorizePersonnelPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/').toLowerCase();
  if (p.startsWith('hiring')) return 'hiring';
  if (
    p.startsWith('lab management') ||
    p.includes('it important') ||
    (p.includes('it') && p.includes('role description'))
  ) {
    return 'lab_management';
  }
  return 'roster';
}

// ——— Research materials ———

export const RESEARCH_CATEGORY_GROUPS = [
  {
    id: 'research',
    label: 'Research Materials',
    categories: [
      {
        id: 'conference',
        label: 'Conference Abstracts & Posters',
        description: 'ESGO, AACR, European Ovarian Cancer Symposium, EMBL, etc.',
      },
      {
        id: 'phd_apps',
        label: 'PhD & Doctoral School',
        description: 'Doctoral school applications and related materials.',
      },
      {
        id: 'peer_review',
        label: 'Peer Review',
        description: 'Papers under peer review.',
      },
      {
        id: 'presentations',
        label: 'Presentations & Posters Archive',
        description: 'Archived presentations and poster files.',
      },
    ],
  },
];

export function categorizeResearchPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/').toLowerCase();
  if (p.startsWith('conference')) return 'conference';
  if (p.startsWith('phd')) return 'phd_apps';
  if (p.startsWith('peer-review')) return 'peer_review';
  return 'presentations';
}

/** Section configs keyed by navigation sub-id (get_started is intro-only — no files). */
export const OVERVIEW_SECTION_CONFIG = {
  onboarding: {
    sectionIds: ['overview_onboarding'],
    categoryGroups: ONBOARDING_CATEGORY_GROUPS,
    defaultCategory: 'orientation',
    categorizePath: categorizeOnboardingPath,
  },
  guidelines: {
    sectionIds: ['overview_guidelines'],
    categoryGroups: GUIDELINES_CATEGORY_GROUPS,
    defaultCategory: 'research',
    categorizePath: categorizeGuidelinesPath,
  },
  documents_permits: {
    sectionIds: ['overview_documents'],
    categoryGroups: DOCUMENTS_CATEGORY_GROUPS,
    defaultCategory: 'bsl1_2',
    categorizePath: categorizeDocumentsPath,
  },
  cleaning: {
    sectionIds: ['overview_cleaning'],
    categoryGroups: CLEANING_CATEGORY_GROUPS,
    defaultCategory: 'cleaning_251205',
    categorizePath: categorizeCleaningPath,
  },
  personnel: {
    sectionIds: ['overview_personnel'],
    categoryGroups: PERSONNEL_CATEGORY_GROUPS,
    defaultCategory: 'roster',
    categorizePath: categorizePersonnelPath,
  },
  research: {
    sectionIds: ['overview_research_materials'],
    categoryGroups: RESEARCH_CATEGORY_GROUPS,
    defaultCategory: 'conference',
    categorizePath: categorizeResearchPath,
  },
};

export function getOverviewConfig(subId) {
  return OVERVIEW_SECTION_CONFIG[subId] || OVERVIEW_SECTION_CONFIG.documents_permits;
}

export function collectOverviewDocuments(twins, config) {
  const all = [];

  for (const [sectionId, twin] of Object.entries(twins)) {
    if (!twin || !config.categorizePath) continue;

    const docs = collectSectionDocuments(twin, {
      categorizePath: (path) => config.categorizePath(path, sectionId),
      documentTitle: overviewDocumentTitle,
    });

    for (const doc of docs) {
      all.push({
        ...doc,
        sourceSection: sectionId,
      });
    }
  }

  return all;
}

export function groupOverviewDocuments(docs, config) {
  const order = flattenCategoryOrder(config.categoryGroups);
  return groupDocumentsByCategory(docs, order);
}

export function findOverviewCategoryMeta(config, categoryId) {
  return findCategoryMeta(config.categoryGroups, categoryId);
}
