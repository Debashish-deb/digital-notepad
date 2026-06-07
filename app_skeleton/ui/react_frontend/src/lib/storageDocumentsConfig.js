/**
 * Storage-related lab documents — mapped to Data & Storage tabs.
 * Overview topics (onboarding, guidelines, permits, personnel) live under Overview only.
 */

import { overviewDocumentTitle } from './overviewCategories.js';

/** Only cleaning inventories that mention storage infrastructure — not general onboarding/guidelines. */
export function isStorageRelatedPath(path) {
  const p = (path || '').replace(/\\/g, '/').toLowerCase();
  return (
    p.includes('allas') ||
    p.includes('databank') ||
    p.includes('storage unit') ||
    p.includes('external drive') ||
    (p.includes('dry lab cleaning') &&
      (p.includes('allas') || p.includes('inventory') || p.includes('drive') || p.includes('databank'))) ||
    (p.includes('wet lab cleaning') && (p.includes('inventory') || p.includes('drive'))) ||
    (p.includes('inventory') &&
      (p.includes('drive') || p.includes('computer') || p.includes('external') || p.includes('disk'))) ||
    (p.includes('it important') &&
      (p.includes('storage') ||
        p.includes('allas') ||
        p.includes('drive') ||
        p.includes('backup') ||
        p.includes('datacloud') ||
        p.includes('mount'))) ||
    (p.includes('role description') && p.includes('it'))
  );
}

export function categorizeStorageDocumentPath(path, sourceSection) {
  const p = (path || '').replace(/\\/g, '/').toLowerCase();
  if (sourceSection === 'overview_cleaning' || p.includes('cleaning day')) {
    if (p.includes('251205')) return 'cleaning_251205';
    if (p.includes('20250528') || p.includes('28052025')) return 'cleaning_20250528';
    return 'cleaning_other';
  }
  if (p.includes('allas') || p.includes('databank')) return 'allas_databank';
  if (p.includes('external drive') || p.includes('inventory')) return 'inventory_disks';
  if (p.includes('storage unit')) return 'storage_units';
  if (p.includes('it important') || (p.includes('it') && p.includes('role description'))) {
    return 'it_roles';
  }
  return 'general_storage';
}

export const STORAGE_DOCUMENT_CATEGORY_GROUPS = [
  {
    id: 'storage_docs',
    label: 'Storage documents',
    categories: [
      {
        id: 'cleaning_251205',
        label: 'Cleaning day Dec 2025',
        description: 'Dry lab, Allas/Databank inventory, external drives.',
      },
      {
        id: 'cleaning_20250528',
        label: 'Cleaning day May 2025',
        description: 'Storage unit tasks and data cleaning checklists.',
      },
      {
        id: 'allas_databank',
        label: 'Allas & archive inventory',
        description: 'Upload inventory spreadsheets (Allas buckets and Databank transfers).',
      },
      {
        id: 'inventory_disks',
        label: 'Disks & inventory',
        description: 'External drive listings and IT hardware inventory.',
      },
      {
        id: 'storage_units',
        label: 'Storage units',
        description: 'Storage unit tasks and comments from cleaning days.',
      },
      {
        id: 'it_roles',
        label: 'IT roles & actions',
        description: 'IT Specialist role, important actions, hiring docs.',
      },
      {
        id: 'general_storage',
        label: 'Other storage references',
        description: 'Additional files mentioning lab storage.',
      },
    ],
  },
];

/** Repo config docs (not in processed corpus) */
export const STORAGE_REPO_DOCS = [
  {
    id: 'pdrive_setup',
    label: 'P-drive mount setup',
    path: 'configs/PDRIVE_SETUP.md',
    tabs: ['network_drives', 'documents'],
    summary: 'PDRIVE_MOUNT_PATH, connector API, CyCIF secondary storage.',
  },
  {
    id: 'datacloud_setup',
    label: 'DataCloud WebDAV setup',
    path: 'configs/DATACLOUD_WEBDAV_SETUP.md',
    tabs: ['datacloud', 'documents'],
    summary: 'WebDAV base URL, /farkkila/LAB-ASSISTANT-PLATFORM, env vars.',
  },
];

/**
 * Corpus-backed storage tabs were removed — onboarding, guidelines, and permits
 * belong on Overview. Only the Lab documents hub lists storage-inventory files.
 */
export function getStorageDocumentsConfig(tabId) {
  if (tabId !== 'documents') return null;

  return {
    sectionIds: ['overview_cleaning'],
    categoryGroups: STORAGE_DOCUMENT_CATEGORY_GROUPS,
    defaultCategory: 'allas_databank',
    categorizePath: categorizeStorageDocumentPath,
    documentTitle: overviewDocumentTitle,
    documentFilter: isStorageRelatedPath,
  };
}

export function getRepoDocsForTab(tabId) {
  return STORAGE_REPO_DOCS.filter((d) => d.tabs.includes(tabId));
}

/** Capacity rows shown in right rail per tab */
export const TAB_RAIL_CAPACITY_IDS = {
  landscape: null,
  network_drives: ['l_drive', 'p_drive'],
  datacloud: ['datacloud', 'databank'],
  cloud_archive: ['allas'],
  google_drive: [],
  local_storage: ['cpouta_nfs', 'l_drive'],
  guidelines: [],
  tools: ['allas', 'datacloud'],
  documents: null,
};
