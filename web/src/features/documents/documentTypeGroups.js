/**
 * Category groups derived from document type taxonomy — replaces folder-based grouping
 * in non-project document browsers.
 */

import {
  DOCUMENT_TYPES,
  enrichDocumentWithType,
  getDocumentType,
  sortByDocumentType,
} from './documentTypeRegistry.js';
import { groupDocumentsByCategory, flattenCategoryOrder } from '@/lib/documentBrowserUtils.js';

const GROUP_DEFS = [
  {
    id: 'correspondence_forms',
    label: 'Correspondence & compliance',
    typeIds: ['received', 'application'],
  },
  {
    id: 'lab_methods',
    label: 'Lab methods & procedures',
    typeIds: ['protocol', 'instruction', 'instruction_external'],
  },
  {
    id: 'procurement',
    label: 'Procurement & billing',
    typeIds: ['order', 'billing'],
  },
  {
    id: 'research_output',
    label: 'Research output',
    typeIds: ['report', 'publication', 'note', 'presentation'],
  },
  {
    id: 'operations',
    label: 'Operations & inventory',
    typeIds: ['inventory', 'data'],
  },
  {
    id: 'media_other',
    label: 'Media & other',
    typeIds: ['image', 'unknown'],
  },
];

export function buildDocumentTypeCategoryGroups() {
  return GROUP_DEFS.map((group) => ({
    id: group.id,
    label: group.label,
    categories: group.typeIds.map((typeId) => {
      const type = getDocumentType(typeId);
      return {
        id: typeId,
        label: type.label,
        description: type.description,
      };
    }),
  }));
}

export const DOCUMENT_TYPE_CATEGORY_GROUPS = buildDocumentTypeCategoryGroups();

export const DOCUMENT_TYPE_CATEGORY_ORDER = flattenCategoryOrder(DOCUMENT_TYPE_CATEGORY_GROUPS);

export function buildDocumentTypeCategoryIcons() {
  const icons = {};
  for (const type of Object.values(DOCUMENT_TYPES)) {
    icons[type.id] = type.icon;
  }
  return icons;
}

export const DOCUMENT_TYPE_CATEGORY_ICONS = buildDocumentTypeCategoryIcons();

/**
 * Enrich docs with type metadata and group by document type (not disk folders).
 */
export function groupDocumentsByDocumentType(docs) {
  const enriched = docs.map((doc) =>
    doc.documentTypeId ? doc : enrichDocumentWithType(doc),
  );
  const grouped = groupDocumentsByCategory(enriched, DOCUMENT_TYPE_CATEGORY_ORDER);
  for (const id of DOCUMENT_TYPE_CATEGORY_ORDER) {
    grouped[id]?.sort(sortByDocumentType);
  }
  return grouped;
}

export function enrichAndGroupByDocumentType(docs) {
  const enriched = docs.map((doc) =>
    doc.documentTypeId ? doc : enrichDocumentWithType(doc),
  );
  return {
    docs: enriched,
    grouped: groupDocumentsByDocumentType(enriched),
    categoryGroups: DOCUMENT_TYPE_CATEGORY_GROUPS,
    categoryOrder: DOCUMENT_TYPE_CATEGORY_ORDER,
    categoryIcons: DOCUMENT_TYPE_CATEGORY_ICONS,
  };
}
