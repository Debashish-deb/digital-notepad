/**
 * Central document type taxonomy for cancer-research-lab presentation.
 * Used by list browsers and viewers — same classifier everywhere.
 */

import {
  BookOpen,
  ClipboardList,
  FileInput,
  FileText,
  FlaskConical,
  Inbox,
  ListOrdered,
  Mail,
  Microscope,
  Package,
  Presentation,
  ScrollText,
  Shield,
  StickyNote,
} from 'lucide-react';

/** @typedef {'protocol'|'application'|'order'|'instruction'|'instruction_external'|'received'|'report'|'publication'|'note'|'presentation'|'inventory'|'billing'|'data'|'image'|'unknown'} DocumentTypeId */

export const DOCUMENT_TYPES = {
  received: {
    id: 'received',
    label: 'Received correspondence',
    shortLabel: 'Correspondence',
    icon: Mail,
    sortOrder: 10,
    layoutVariant: 'correspondence',
    description: 'Incoming letters, memos, and external communications.',
    printHint: 'letterhead',
  },
  application: {
    id: 'application',
    label: 'Applications & permits',
    shortLabel: 'Application',
    icon: FileInput,
    sortOrder: 20,
    layoutVariant: 'form',
    description: 'Permit applications, GMM forms, and compliance filings.',
    printHint: 'form',
  },
  protocol: {
    id: 'protocol',
    label: 'Protocols & methods',
    shortLabel: 'Protocol',
    icon: FlaskConical,
    sortOrder: 30,
    layoutVariant: 'protocol',
    description: 'Wet-lab protocols, CyCIF methods, and experimental procedures.',
    printHint: 'protocol',
  },
  order: {
    id: 'order',
    label: 'Orders & procurement',
    shortLabel: 'Order',
    icon: Package,
    sortOrder: 40,
    layoutVariant: 'order',
    description: 'Purchase orders, quotes, and vendor procurement records.',
    printHint: 'order',
  },
  billing: {
    id: 'billing',
    label: 'Billing & invoicing',
    shortLabel: 'Billing',
    icon: ClipboardList,
    sortOrder: 45,
    layoutVariant: 'order',
    description: 'Billing instructions, invoices, and payment records.',
    printHint: 'order',
  },
  instruction: {
    id: 'instruction',
    label: 'Internal instructions',
    shortLabel: 'Instruction',
    icon: ListOrdered,
    sortOrder: 50,
    layoutVariant: 'sop',
    description: 'Lab-internal procedures, checklists, and operating notes.',
    printHint: 'sop',
  },
  instruction_external: {
    id: 'instruction_external',
    label: 'SOPs & external instructions',
    shortLabel: 'SOP',
    icon: ScrollText,
    sortOrder: 55,
    layoutVariant: 'sop',
    description: 'Standard operating procedures and instructions for collaborators.',
    printHint: 'sop',
  },
  report: {
    id: 'report',
    label: 'Reports & summaries',
    shortLabel: 'Report',
    icon: Microscope,
    sortOrder: 60,
    layoutVariant: 'report',
    description: 'Progress reports, risk assessments, and study summaries.',
    printHint: 'report',
  },
  publication: {
    id: 'publication',
    label: 'Publications & manuscripts',
    shortLabel: 'Publication',
    icon: BookOpen,
    sortOrder: 70,
    layoutVariant: 'manuscript',
    description: 'Papers, preprints, and research articles.',
    printHint: 'manuscript',
  },
  note: {
    id: 'note',
    label: 'Notes & meeting records',
    shortLabel: 'Note',
    icon: StickyNote,
    sortOrder: 80,
    layoutVariant: 'note',
    description: 'Meeting notes, lab logs, and informal records.',
    printHint: 'note',
  },
  presentation: {
    id: 'presentation',
    label: 'Presentations & slides',
    shortLabel: 'Slides',
    icon: Presentation,
    sortOrder: 90,
    layoutVariant: 'presentation',
    description: 'Slide decks, seminar materials, and meeting presentations.',
    printHint: 'slides',
  },
  inventory: {
    id: 'inventory',
    label: 'Inventory & cleaning',
    shortLabel: 'Inventory',
    icon: Shield,
    sortOrder: 100,
    layoutVariant: 'inventory',
    description: 'Storage inventories, cleaning checklists, and equipment lists.',
    printHint: 'checklist',
  },
  data: {
    id: 'data',
    label: 'Data & spreadsheets',
    shortLabel: 'Data',
    icon: ClipboardList,
    sortOrder: 110,
    layoutVariant: 'data',
    description: 'Datasets, spreadsheets, and structured data files.',
    printHint: 'data',
  },
  image: {
    id: 'image',
    label: 'Images & figures',
    shortLabel: 'Image',
    icon: Inbox,
    sortOrder: 120,
    layoutVariant: 'media',
    description: 'Photos, microscopy images, and figure files.',
    printHint: 'figure',
  },
  unknown: {
    id: 'unknown',
    label: 'Other documents',
    shortLabel: 'Document',
    icon: FileText,
    sortOrder: 999,
    layoutVariant: 'default',
    description: 'Documents that could not be classified into a specific type.',
    printHint: 'default',
  },
};

const TYPE_IDS = Object.keys(DOCUMENT_TYPES);

function norm(value) {
  return String(value ?? '').trim().toLowerCase();
}

function basename(path) {
  return norm(path).split('/').pop() || '';
}

function joinSignals(doc) {
  const path = norm(doc.path || doc.logical_path || doc.relative_path);
  const name = norm(doc.name || doc.filename);
  const title = norm(doc.title || doc.display_title);
  const excerpt = norm(doc.excerpt || doc.summary || doc.inlineContent?.slice?.(0, 500));
  const category = norm(doc.categoryId || doc.category || doc.subcategory);
  const section = norm(doc.section_label || doc.sourceSection);
  const docType = norm(
    doc.document_type
    || doc.classification?.document_type
    || doc.metadata?.classification?.document_type,
  );
  const wikiType = norm(doc.wiki_type);
  const assetBucket = norm(doc.asset_bucket || doc.asset_type);

  return {
    path,
    name: name || basename(path),
    title,
    excerpt,
    category,
    section,
    docType,
    wikiType,
    assetBucket,
    haystack: [path, name, title, excerpt, category, section, docType, wikiType].join(' '),
  };
}

function scoreRule(typeId, weight, reason, signals) {
  signals.push({ typeId, weight, reason });
  return weight;
}

/**
 * Classify a document from metadata, filename, and content hints.
 * @returns {{ typeId: DocumentTypeId, confidence: number, signals: Array<{typeId: string, weight: number, reason: string}> }}
 */
export function classifyDocument(doc) {
  const signals = [];
  const s = joinSignals(doc);
  const scores = Object.fromEntries(TYPE_IDS.map((id) => [id, 0]));

  const add = (typeId, weight, reason) => {
    scores[typeId] = (scores[typeId] || 0) + scoreRule(typeId, weight, reason, signals);
  };

  // Explicit backend / metadata types
  if (s.docType) {
    const map = {
      protocol: 'protocol',
      wet_lab_protocol: 'protocol',
      method: 'protocol',
      order_form: 'order',
      purchase_order: 'order',
      billing_instruction: 'billing',
      invoice: 'billing',
      shipping_customs_statement: 'order',
      courier_service: 'order',
      application: 'application',
      permit: 'application',
      gmm_application: 'application',
      sop: 'instruction_external',
      instruction: 'instruction',
      meeting_note: 'note',
      presentation: 'presentation',
      publication: 'publication',
      manuscript: 'publication',
      report: 'report',
      correspondence: 'received',
      letter: 'received',
      memo: 'received',
      inventory: 'inventory',
      datasheet: 'report',
      msds: 'report',
    };
    for (const [key, typeId] of Object.entries(map)) {
      if (s.docType.includes(key)) add(typeId, 90, `metadata document_type: ${s.docType}`);
    }
  }

  if (s.wikiType) {
    if (s.wikiType.includes('sop')) add('instruction_external', 85, `wiki_type: ${s.wikiType}`);
    if (s.wikiType.includes('protocol')) add('protocol', 85, `wiki_type: ${s.wikiType}`);
  }

  // Asset bucket hints (weak)
  if (s.assetBucket === 'presentations') add('presentation', 40, 'asset_bucket: presentations');
  if (s.assetBucket === 'figures') add('image', 35, 'asset_bucket: figures');
  if (s.assetBucket === 'data_files') add('data', 30, 'asset_bucket: data_files');

  // Filename / title keyword heuristics
  const rules = [
    [/protocol|cycif.*method|wet.?lab|staining.*procedure/i, 'protocol', 55, 'filename/title: protocol'],
    [/\bsop\b|standard operating|operating procedure/i, 'instruction_external', 50, 'title: SOP'],
    [/instruction|checklist|how.?to|guide(?!line)/i, 'instruction', 40, 'title: instruction'],
    [/guideline|policy|manual|biosafety|bsl/i, 'instruction_external', 38, 'title: guideline/manual'],
    [/application|permit|gmm|biobank|luovutus|hakemus/i, 'application', 50, 'title: application'],
    [/purchase.?order|\bpo[_\s-]?\d|order.?form|quote|procurement/i, 'order', 50, 'title: order'],
    [/billing|invoice|invoic/i, 'billing', 50, 'title: billing'],
    [/received|incoming|correspondence|letter|memo|re:\s/i, 'received', 45, 'title: correspondence'],
    [/meeting|minutes|agenda|lab.?meeting/i, 'note', 45, 'title: meeting'],
    [/presentation|slides|deck|seminar/i, 'presentation', 45, 'title: presentation'],
    [/manuscript|preprint|publication|\.doi|journal|article/i, 'publication', 45, 'title: publication'],
    [/report|summary|risk.?assess|narviointi/i, 'report', 40, 'title: report'],
    [/inventory|cleaning|storage.?unit|allas|databank/i, 'inventory', 40, 'title: inventory'],
    [/msds|datasheet|sds/i, 'report', 35, 'title: datasheet'],
    [/onboarding|outboarding|orientation/i, 'instruction', 35, 'title: onboarding'],
  ];

  for (const [pattern, typeId, weight, reason] of rules) {
    if (pattern.test(s.haystack)) add(typeId, weight, reason);
  }

  // Extension-based hints
  const ext = (doc.extension || doc.name || doc.filename || s.path).match(/\.[^.]+$/i)?.[0]?.toLowerCase() || '';
  if (['.ppt', '.pptx', '.key'].includes(ext)) add('presentation', 35, `extension: ${ext}`);
  if (['.xls', '.xlsx', '.csv', '.tsv'].includes(ext)) add('data', 25, `extension: ${ext}`);
  if (['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.svg', '.gif', '.webp'].includes(ext)) {
    add('image', 30, `extension: ${ext}`);
  }

  // Section context (weak — not folder hierarchy)
  if (s.section.includes('orders')) add('order', 20, 'section: orders');
  if (s.section.includes('meetings')) add('note', 20, 'section: meetings');
  if (s.section.includes('wet_lab') || s.category.includes('proto')) add('protocol', 20, 'section: wet lab');

  let typeId = 'unknown';
  let confidence = 0;
  for (const id of TYPE_IDS) {
    if (scores[id] > confidence) {
      confidence = scores[id];
      typeId = id;
    }
  }

  if (confidence < 15) {
    typeId = 'unknown';
    confidence = 0;
  } else {
    confidence = Math.min(100, confidence);
  }

  return { typeId, confidence, signals };
}

export function getDocumentType(typeId) {
  return DOCUMENT_TYPES[typeId] || DOCUMENT_TYPES.unknown;
}

export function enrichDocumentWithType(doc) {
  const { typeId, confidence, signals } = classifyDocument(doc);
  const type = getDocumentType(typeId);
  return {
    ...doc,
    documentTypeId: typeId,
    documentTypeLabel: type.label,
    documentTypeConfidence: confidence,
    documentTypeSignals: signals,
    categoryId: typeId,
  };
}

export function sortByDocumentType(a, b) {
  const orderA = getDocumentType(a.documentTypeId || classifyDocument(a).typeId).sortOrder;
  const orderB = getDocumentType(b.documentTypeId || classifyDocument(b).typeId).sortOrder;
  if (orderA !== orderB) return orderA - orderB;
  const titleA = (a.display_title || a.title || a.path || '').toLowerCase();
  const titleB = (b.display_title || b.title || b.path || '').toLowerCase();
  return titleA.localeCompare(titleB);
}
