/**
 * Lab documents hub — Data & Storage → Lab documents tab.
 * Storage inventories, orders, meetings, and platform setup only.
 * Overview topics (onboarding, guidelines, permits, personnel) are on the Overview module.
 */

import { overviewDocumentTitle } from './overviewCategories.js';
import { isStorageRelatedPath, STORAGE_REPO_DOCS } from './storageDocumentsConfig.js';

export const LAB_HUB_SECTION_IDS = [
  'overview_cleaning',
  'orders_billing',
  'orders_archive',
  'meetings',
];

const SECTION_LABELS = {
  overview_cleaning: 'Lab cleaning',
  orders_billing: 'Billing & ordering',
  orders_archive: 'Orders archive',
  meetings: 'Lab meetings',
};

export function categorizeLabHubDocument(path, sourceSection) {
  const p = (path || '').replace(/\\/g, '/').toLowerCase();

  if (sourceSection === 'overview_cleaning' || p.includes('cleaning day')) {
    if (p.includes('251205')) return 'storage_cleaning_dec25';
    if (p.includes('20250528') || p.includes('28052025')) return 'storage_cleaning_may25';
    return 'storage_cleaning_other';
  }
  if (p.includes('allas') || p.includes('databank')) return 'storage_allas_databank';
  if (p.includes('external drive') || (p.includes('inventory') && p.includes('drive'))) {
    return 'storage_disks';
  }
  if (p.includes('storage unit')) return 'storage_units';
  if (p.includes('it important') || (p.includes('it') && p.includes('role description'))) {
    return 'storage_it';
  }

  if (sourceSection === 'orders_billing') return 'orders_billing';
  if (sourceSection === 'orders_archive') return 'orders_archive';
  if (sourceSection === 'meetings') return 'meetings';

  return `section_${sourceSection}`;
}

export const LAB_HUB_CATEGORY_GROUPS = [
  {
    id: 'cleaning_storage',
    label: 'Cleaning & storage inventory',
    categories: [
      { id: 'storage_cleaning_dec25', label: 'Cleaning Dec 2025', description: 'Dry lab, Allas/Databank inventory.' },
      { id: 'storage_cleaning_may25', label: 'Cleaning May 2025', description: 'Storage unit and checklist tasks.' },
      { id: 'storage_cleaning_other', label: 'Other cleaning docs', description: 'Additional cleaning-day materials.' },
      { id: 'storage_allas_databank', label: 'Allas & Databank', description: 'Upload inventory spreadsheets.' },
      { id: 'storage_disks', label: 'Disks & hardware', description: 'External drives and IT inventory.' },
      { id: 'storage_units', label: 'Storage units', description: 'Storage unit tasks and comments.' },
      { id: 'storage_it', label: 'IT roles & actions', description: 'IT specialist docs and action lists.' },
    ],
  },
  {
    id: 'orders',
    label: 'Orders',
    categories: [
      { id: 'orders_billing', label: 'Billing & ordering', description: 'Vendors, HUS ordering, billing instructions.' },
      { id: 'orders_archive', label: 'Archive', description: 'Historical quotes and procurement.' },
    ],
  },
  {
    id: 'meetings',
    label: 'Meetings',
    categories: [
      { id: 'meetings', label: 'Lab meetings', description: 'Notes, slides, and meeting decks.' },
    ],
  },
  {
    id: 'platform',
    label: 'Platform setup',
    categories: [
      { id: 'repo_setup', label: 'Connector setup guides', description: 'P-drive mount and DataCloud WebDAV — readable below.' },
    ],
  },
];

/** Orders/meetings pass through; cleaning corpus is limited to storage-infrastructure files. */
export function labHubDocumentFilter(doc) {
  const section = doc?.sourceSection || '';
  if (section.startsWith('orders_') || section === 'meetings' || doc?.isSynthetic) return true;
  return isStorageRelatedPath(doc?.path || '');
}

export function getLabDocumentsHubConfig() {
  return {
    sectionIds: LAB_HUB_SECTION_IDS,
    categoryGroups: LAB_HUB_CATEGORY_GROUPS,
    defaultCategory: 'storage_allas_databank',
    categorizePath: categorizeLabHubDocument,
    documentTitle: overviewDocumentTitle,
    documentFilter: labHubDocumentFilter,
    repoDocs: STORAGE_REPO_DOCS.filter((d) => d.tabs.includes('documents')),
  };
}

export function sectionLabelForHub(sourceSection) {
  return SECTION_LABELS[sourceSection] || sourceSection?.replace(/_/g, ' ') || 'Lab files';
}
