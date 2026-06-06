/**
 * Side-tab categories for Billing & ordering instructions (orders_billing twin).
 * Mirrors the Google Drive folder layout with clearer labels.
 */

import {
  collectSectionDocuments,
  groupDocumentsByCategory,
  findCategoryMeta,
} from './documentBrowserUtils.js';

/** Human-readable titles for every file in this section. */
export const BILLING_DISPLAY_TITLES = {
  'BIlling_and_delivery_information_FÄRKKILÄ.docx':
    'Billing & Delivery Information (Färkkilä Lab)',
  'Booking_the_seminar_room.docx': 'Seminar Room Booking Instructions',
  'Laskulomake FI EN 05072017.docx': 'University of Helsinki Invoice Form (FI/EN)',
  'USERNAMES_and_PASSWORDS_to_websites_Färkkilä lab.docx':
    'Vendor Usernames & Passwords',
  'HUS_money/HUS EVO money Anniina, 2022.docx':
    'HUS EVO Budget & Billing Contacts (2022)',
  'HUS_money/HUS Laskutusohje 2024-2026.docx': 'HUS Billing Instructions 2024–2026',
  'HUS_money/HUSLAB_order_form.xls': 'HUSLAB Order Form',
  'Shipments_FedEx_UPS_Färkkilä_lab/FedEx account info.docx': 'FedEx Account Information',
  'Shipments_FedEx_UPS_Färkkilä_lab/Air Waybills FedEx/FedEx Air waybill 3 11 2020NC Abcam NL return of abs.pdf':
    'FedEx Waybill — Abcam NL Antibody Return (Nov 2020)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Air Waybills FedEx/FedEx Air waybill 24 5 2021  DNA S052 to Maria Rossing Copenhagen.pdf':
    'FedEx Waybill — DNA S052 to Maria Rossing, Copenhagen (May 2021)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Air Waybills FedEx/FedEx Denmark Maria Rossing 28 4 2021NC.pdf':
    'FedEx Waybill — Maria Rossing, Denmark (Apr 2021)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Air Waybills FedEx/FedEx Myriad DNAs to Copenhagen 8 3 21NC.pdf':
    'FedEx Waybill — Myriad DNAs to Copenhagen (Mar 2021)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Air Waybills FedEx/DNA_to_Tartu_Matilda_7_04_2025_AL_UPS CampusShip _ UPS - Finland.pdf':
    'UPS Waybill — DNA to Tartu, Matilda (Apr 2025)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment of DNA samples to Copenhagen, same as for Myriad test, 8.3.2021NC/FF DNAs sent to Denmark same as Myriad March 2021.xlsx':
    'DNA Shipment List — Denmark / Myriad (Mar 2021)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/Shipment to US advices.docx':
    'Shipment to US — Instructions & Advice',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/USDA_Statement_Human non hazardous.doc':
    'USDA Statement — Human Non-Hazardous Samples',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/CI&USDA Bente HalvorsenEllen Lund Sagen070622.docx':
    'Commercial Invoice & USDA — Bente Halvorsen / Ellen Lund Sagen',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/CI&USDA from Tapio Tainola.doc':
    'Commercial Invoice & USDA — Tapio Tainola',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/ProForma Anton Popov ESRF Magasin 060622.doc':
    'Proforma Invoice — Anton Popov, ESRF Magasin',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/ProForma Nadezhda Zinovkina-November University 261119.doc':
    'Proforma Invoice — Nadezhda Zinovkina, November University',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/Contour-Cut-Printed-Fragile-Decal-Sign.png':
    'Fragile Shipping Label (Decal)',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/RareCyte slides shipment USDA and Customs invoice, Anastasiya/Customs Invoice Slides to RareCyte Customs Invoice.doc':
    'Customs Invoice — RareCyte Slides Shipment',
  'Shipments_FedEx_UPS_Färkkilä_lab/Shipment to US, advices, examples of proforma/RareCyte slides shipment USDA and Customs invoice, Anastasiya/USDA Statement Slides to RareCyte.doc':
    'USDA Statement — RareCyte Slides Shipment',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/UPS from 1 2 2022.docx':
    'UPS Courier Service — Setup & Instructions (from Feb 2022)',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/image007.png': 'UPS Setup Screenshot 1',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/image008.png': 'UPS Setup Screenshot 2',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/image009.png': 'UPS Setup Screenshot 3',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/Air waybills UPS/18.8.2025_Tartu_SNParray_Matilda_4_IDS_FF_DNAs_UPS CampusShip _ UPS - Finland.pdf':
    'UPS Waybill — SNParray DNAs to Tartu, Matilda (Aug 2025)',
  'Shipments_FedEx_UPS_Färkkilä_lab/UPS/Air waybills UPS/DNA_to_Tartu_Matilda_7_04_2025_AL_UPS CampusShip _ UPS - Finland.pdf':
    'UPS Waybill — DNA to Tartu, Matilda (Apr 2025)',
};

export function billingDocumentTitle(doc) {
  if (doc?.display_title) return doc.display_title;
  const path = (doc?.path || '').replace(/\\/g, '/');
  if (BILLING_DISPLAY_TITLES[path]) return BILLING_DISPLAY_TITLES[path];
  const fileName = path.split('/').pop() || '';
  return fileName.replace(/\.[^.]+$/, '').replace(/_/g, ' ').replace(/^BIlling/i, 'Billing');
}

export const BILLING_CATEGORY_GROUPS = [
  {
    id: 'billing',
    label: 'Billing & Finance',
    categories: [
      {
        id: 'general_reference',
        label: 'General Reference',
        description: 'Core billing addresses, delivery info, and university invoice forms.',
      },
      {
        id: 'hus_finance',
        label: 'HUS Finance & Billing',
        description: 'HUS billing instructions, EVO budgets, and HUSLAB order forms.',
      },
      {
        id: 'credentials',
        label: 'Credentials & Access',
        description: 'Vendor website logins and account credentials (sensitive).',
        sensitive: true,
      },
    ],
  },
  {
    id: 'logistics',
    label: 'Logistics & Shipping',
    categories: [
      {
        id: 'fedex',
        label: 'FedEx',
        description: 'FedEx account details and archived air waybills.',
      },
      {
        id: 'ups',
        label: 'UPS',
        description: 'UPS courier setup, screenshots, and air waybills.',
      },
      {
        id: 'dna_shipments',
        label: 'DNA Sample Shipments',
        description: 'International DNA shipments (Copenhagen, Myriad, Denmark).',
      },
      {
        id: 'us_customs',
        label: 'US Customs & Proforma',
        description: 'USDA statements, proforma invoices, and customs examples.',
      },
    ],
  },
  {
    id: 'other',
    label: 'Other',
    categories: [
      {
        id: 'other_admin',
        label: 'Admin & Facilities',
        description: 'Room booking and other administrative references.',
      },
    ],
  },
];

export const BILLING_CATEGORY_ORDER = BILLING_CATEGORY_GROUPS.flatMap((g) =>
  g.categories.map((c) => c.id)
);

export function categorizeBillingPath(path) {
  const p = (typeof path === 'string' ? path : (path?.path || '')).replace(/\\/g, '/');
  const lower = p.toLowerCase();
  const fileName = p.split('/').pop().toLowerCase();

  if (lower.includes('usernames_and_passwords')) return 'credentials';
  if (p.startsWith('HUS_money/')) return 'hus_finance';
  // Filename carrier hint (e.g. UPS CampusShip PDF stored under FedEx folder)
  if (fileName.includes('ups') || fileName.includes('campusship')) return 'ups';
  if (fileName.includes('fedex') || lower.endsWith('fedex account info.docx')) return 'fedex';
  if (lower.includes('air waybills fedex')) return 'fedex';
  if (lower.includes('/ups/')) return 'ups';
  if (lower.includes('dna samples to copenhagen') || lower.includes('myriad')) {
    return 'dna_shipments';
  }
  if (
    lower.includes('shipment to us') ||
    lower.includes('rarecyte') ||
    lower.includes('usda') ||
    lower.includes('proforma')
  ) {
    return 'us_customs';
  }
  if (lower.includes('booking_the_seminar_room')) return 'other_admin';
  if (
    lower.includes('billing_and_delivery') ||
    lower.includes('laskulomake')
  ) {
    return 'general_reference';
  }
  return 'general_reference';
}

export function collectBillingDocuments(twin) {
  return collectSectionDocuments(twin, {
    categorizePath: categorizeBillingPath,
    documentTitle: billingDocumentTitle,
  });
}

export function groupBillingDocuments(docs) {
  return groupDocumentsByCategory(docs, BILLING_CATEGORY_ORDER);
}

export function findBillingCategoryMeta(categoryId) {
  return findCategoryMeta(BILLING_CATEGORY_GROUPS, categoryId);
}
