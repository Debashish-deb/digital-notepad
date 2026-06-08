/**
 * Side-tab categories for Orders archive (orders_archive twin).
 * Smart path/folder rules for historical procurement records.
 */

import {
  collectSectionDocuments,
  groupDocumentsByCategory,
  findCategoryMeta,
} from './documentBrowserUtils.js';
import { humanizeFilenameLabel } from './textCleanup.js';

/** Human-readable titles for archive files. */
export const ARCHIVE_DISPLAY_TITLES = {
  'Anni_Virtanen_HUS_LAB_account_2019_purchases.xlsx':
    'HUS Lab Account Purchases — Anni Virtanen (2019)',
  'FICAN_SOUTH_Färkkilä_lab.xlsx': 'FiCAN South Funding — Färkkilä Lab',
  'FiCAN_South_money_from_2019_AF_lab_debt_to_AV_lab.xlsx':
    'FiCAN South Inter-lab Debt Transfer (2019)',
  'ONCOSYS COMMON EQUIPMENT 2019_UUD_VAHVISTUS_1060102408_20190627032435.pdf':
    'Fisher Scientific Order Confirmation — ONCOSYS Common Equipment (Jun 2019)',
  'Orders_for_Kauppi_lab_TERVA_collaboration.xlsx':
    'Kauppi Lab & TERVA Collaboration Orders',
  'Computers_orders/Bill Anniinas computer 2 6 2020.pdf':
    'Dustin Invoice — Anniina Computer Order (Jun 2020)',
  'Computers_orders/Tietokonetilaus for Anniina 31 3 2020.rtf':
    'Computer Order Form — Anniina (Mar 2020)',
};

/** Top-level folder → category (extensible as archive grows). */
const FOLDER_CATEGORY = {
  computers_orders: 'computer_orders',
  computer_orders: 'computer_orders',
  it_orders: 'computer_orders',
  equipment_orders: 'equipment_orders',
  hus: 'hus_purchases',
  fican: 'fican_funding',
  collaboration: 'collaboration_orders',
};

export const ARCHIVE_CATEGORY_GROUPS = [
  {
    id: 'archive_finance',
    label: 'Lab Finance & Accounts',
    categories: [
      {
        id: 'hus_purchases',
        label: 'HUS Lab Purchases',
        description: 'HUSLAB account purchases and lab procurement spreadsheets.',
      },
      {
        id: 'fican_funding',
        label: 'FiCAN South Funding',
        description: 'FiCAN South programme funding and budget registers.',
      },
      {
        id: 'lab_transfers',
        label: 'Inter-lab Transfers & Debt',
        description: 'Money transfers and debt settlements between lab accounts.',
      },
    ],
  },
  {
    id: 'archive_procurement',
    label: 'Procurement Records',
    categories: [
      {
        id: 'equipment_orders',
        label: 'Equipment Order Confirmations',
        description: 'Vendor order confirmations (Fisher Scientific, ONCOSYS equipment, etc.).',
      },
      {
        id: 'collaboration_orders',
        label: 'Collaboration Orders',
        description: 'Cross-lab and programme collaboration procurement (Kauppi, TERVA).',
      },
      {
        id: 'purchase_registers',
        label: 'Purchase Registers',
        description: 'Historical purchase spreadsheets and uncategorized registers.',
      },
    ],
  },
  {
    id: 'archive_it',
    label: 'IT & Infrastructure',
    categories: [
      {
        id: 'computer_orders',
        label: 'Computer & IT Orders',
        description: 'Workstation orders, Dustin invoices, and IT procurement forms.',
      },
    ],
  },
];

export const ARCHIVE_CATEGORY_ORDER = ARCHIVE_CATEGORY_GROUPS.flatMap((g) =>
  g.categories.map((c) => c.id)
);

export function archiveDocumentTitle(doc) {
  if (doc?.display_title) return doc.display_title;
  const path = (doc?.path || '').replace(/\\/g, '/');
  if (ARCHIVE_DISPLAY_TITLES[path]) return ARCHIVE_DISPLAY_TITLES[path];
  const fileName = path.split('/').pop() || '';
  return humanizeFilenameLabel(fileName);
}

export function categorizeArchivePath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/');
  const lower = p.toLowerCase();
  const fileName = p.split('/').pop() || '';
  const fileLower = fileName.toLowerCase();
  const topFolder = lower.includes('/') ? lower.split('/')[0] : '';

  if (FOLDER_CATEGORY[topFolder]) return FOLDER_CATEGORY[topFolder];

  if (
    topFolder.includes('computer') ||
    fileLower.includes('tietokone') ||
    fileLower.includes('computer') ||
    fileLower.includes('dustin') ||
    fileLower.includes('macbook') ||
    fileLower.includes('bill anniina')
  ) {
    return 'computer_orders';
  }

  if (
    fileLower.includes('hus_lab') ||
    fileLower.includes('hus lab') ||
    (fileLower.includes('hus') && fileLower.includes('purchase')) ||
    fileLower.includes('anni_virtanen')
  ) {
    return 'hus_purchases';
  }

  if (
    fileLower.includes('debt') ||
    fileLower.includes('transfer') ||
    (fileLower.includes('money') && fileLower.includes('lab'))
  ) {
    return 'lab_transfers';
  }

  if (fileLower.includes('fican')) return 'fican_funding';

  if (
    fileLower.includes('uud_vahvistus') ||
    fileLower.includes('vahvistus') ||
    fileLower.includes('oncosys common') ||
    fileLower.includes('fisher') ||
    fileLower.includes('thermo') ||
    fileLower.includes('equipment')
  ) {
    return 'equipment_orders';
  }

  if (
    fileLower.includes('kauppi') ||
    fileLower.includes('terva') ||
    fileLower.includes('collaboration')
  ) {
    return 'collaboration_orders';
  }

  if (/\.(xlsx|xls|csv)$/i.test(fileName)) return 'purchase_registers';

  return 'purchase_registers';
}

export function collectArchiveDocuments(twin) {
  return collectSectionDocuments(twin, {
    categorizePath: categorizeArchivePath,
    documentTitle: archiveDocumentTitle,
  });
}

export function groupArchiveDocuments(docs) {
  return groupDocumentsByCategory(docs, ARCHIVE_CATEGORY_ORDER);
}

export function findArchiveCategoryMeta(categoryId) {
  return findCategoryMeta(ARCHIVE_CATEGORY_GROUPS, categoryId);
}
