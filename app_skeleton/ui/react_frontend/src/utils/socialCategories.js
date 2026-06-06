/**
 * Social & miscellaneous — navigation sub-tabs and smart file categorization.
 */

import { humanizeFilenameLabel } from './textCleanup.js';

export function categorizeSocialPrimary(docOrPath) {
  const p = typeof docOrPath === 'string' ? docOrPath : (docOrPath?.path || '');
  const lower = p.replace(/\\/g, '/').toLowerCase();
  if (lower.startsWith('lab parties')) return 'lab_parties';
  if (lower.startsWith('lab winter day')) return 'winter_events';
  if (lower.startsWith('lab retreats')) return 'lab_retreats';
  if (lower.startsWith('lab_photos')) return 'lab_photos';
  if (lower.startsWith('researchers visit')) return 'researcher_visits';
  if (lower.startsWith('outreach')) return 'outreach';
  return 'social_misc';
}

/** @deprecated Use categorizeSocialPrimary — kept for grouped overview configs */
export function categorizeSocialPath(path) {
  return categorizeSocialPrimary(path);
}

export function socialDocumentTitle(doc) {
  const fileName = (doc?.path || '').split('/').pop() || '';
  return humanizeFilenameLabel(fileName);
}

function categorizePartySub(docOrPath) {
  const p = typeof docOrPath === 'string' ? docOrPath : (docOrPath?.path || '');
  const lower = p.toLowerCase();
  if (lower.includes('halloween')) return 'party_halloween';
  if (lower.includes('grilling')) return 'party_grilling';
  return 'party_planning';
}

function categorizeWinterSub(docOrPath) {
  const p = typeof docOrPath === 'string' ? docOrPath : (docOrPath?.path || '');
  const lower = p.toLowerCase();
  if (/\.(jpg|jpeg|png|gif|webp|heic)$/i.test(lower)) return 'winter_photos';
  return 'winter_docs';
}

function categorizeRetreatSub(docOrPath) {
  const p = typeof docOrPath === 'string' ? docOrPath : (docOrPath?.path || '');
  const lower = p.toLowerCase();
  if (lower.includes('2024')) return 'retreat_2024';
  if (lower.includes('2025')) return 'retreat_2025';
  return 'retreat_planning';
}

function categorizePhotoSub(docOrPath) {
  const p = typeof docOrPath === 'string' ? docOrPath : (docOrPath?.path || '');
  const lower = p.toLowerCase();
  if (lower.includes('retreat') || lower.includes('nuuksio')) return 'photo_retreats';
  if (lower.includes('photoshoot')) return 'photo_shoot';
  if (lower.includes('group photo')) return 'photo_group';
  if (lower.includes('grilling') || lower.includes('party')) return 'photo_events';
  return 'photo_misc';
}

function categorizeVisitSub() {
  return 'visit_records';
}

function categorizeOutreachSub() {
  return 'outreach_media';
}

const PARTY_GROUPS = [
  {
    id: 'parties',
    label: 'Lab Parties',
    categories: [
      {
        id: 'party_halloween',
        label: 'Halloween',
        description: 'Halloween party planning and event files.',
      },
      {
        id: 'party_grilling',
        label: 'Grilling & Social Events',
        description: 'Grilling parties and informal gatherings.',
      },
      {
        id: 'party_planning',
        label: 'Party Planning',
        description: 'General party plans and event documents.',
      },
    ],
  },
];

const WINTER_GROUPS = [
  {
    id: 'winter',
    label: 'Winter Day',
    categories: [
      {
        id: 'winter_photos',
        label: 'Event Photos',
        description: 'Pictures from lab winter day and seasonal events.',
      },
      {
        id: 'winter_docs',
        label: 'Documents',
        description: 'Planning notes and non-image files.',
      },
    ],
  },
];

const RETREAT_GROUPS = [
  {
    id: 'retreats',
    label: 'Lab Retreats',
    categories: [
      {
        id: 'retreat_2024',
        label: '2024 Retreat',
        description: 'Nuuksio retreat materials from 2024.',
      },
      {
        id: 'retreat_2025',
        label: '2025 Retreat',
        description: 'Nuuksio retreat materials from 2025.',
      },
      {
        id: 'retreat_planning',
        label: 'Retreat Planning',
        description: 'Retreat schedules, plans, and shared documents.',
      },
    ],
  },
];

const PHOTO_GROUPS = [
  {
    id: 'photos',
    label: 'Lab Photos',
    categories: [
      {
        id: 'photo_retreats',
        label: 'Retreat Albums',
        description: 'Photo albums from lab retreats.',
      },
      {
        id: 'photo_shoot',
        label: 'Lab Photoshoots',
        description: 'Professional and group photoshoot sessions.',
      },
      {
        id: 'photo_group',
        label: 'Group Photos',
        description: 'Official group photos and team portraits.',
      },
      {
        id: 'photo_events',
        label: 'Event Photos',
        description: 'Pictures from parties and lab events.',
      },
      {
        id: 'photo_misc',
        label: 'Other Photos',
        description: 'Additional lab life and miscellaneous images.',
      },
    ],
  },
];

const VISIT_GROUPS = [
  {
    id: 'visits',
    label: 'Researcher Visits',
    categories: [
      {
        id: 'visit_records',
        label: 'Visitor Records',
        description: 'Hosting materials and visitor documentation.',
      },
    ],
  },
];

const OUTREACH_GROUPS = [
  {
    id: 'outreach',
    label: 'Outreach',
    categories: [
      {
        id: 'outreach_media',
        label: 'Outreach & Social Media',
        description: 'Outreach campaigns and social media assets.',
      },
    ],
  },
];

function tabConfig(tabId, categoryGroups, categorizePath, defaultCategory) {
  return {
    sectionIds: ['social_misc'],
    categoryGroups,
    defaultCategory,
    categorizePath,
    documentTitle: socialDocumentTitle,
    documentFilter: (path) =>
      categorizeSocialPrimary(typeof path === 'string' ? path : path?.path || '') === tabId,
  };
}

/** Per navigation sub-tab (mirrors Overview section configs). */
export const SOCIAL_SECTION_CONFIG = {
  lab_parties: tabConfig('lab_parties', PARTY_GROUPS, categorizePartySub, 'party_halloween'),
  winter_events: tabConfig('winter_events', WINTER_GROUPS, categorizeWinterSub, 'winter_photos'),
  lab_retreats: tabConfig('lab_retreats', RETREAT_GROUPS, categorizeRetreatSub, 'retreat_2024'),
  lab_photos: tabConfig('lab_photos', PHOTO_GROUPS, categorizePhotoSub, 'photo_retreats'),
  researcher_visits: tabConfig(
    'researcher_visits',
    VISIT_GROUPS,
    categorizeVisitSub,
    'visit_records'
  ),
  outreach: tabConfig('outreach', OUTREACH_GROUPS, categorizeOutreachSub, 'outreach_media'),
};

export function getSocialConfig(subId) {
  return SOCIAL_SECTION_CONFIG[subId] || null;
}

/** Legacy single-tab export */
export const SOCIAL_CATEGORY_GROUPS = [
  {
    id: 'social_events',
    label: 'Lab Events',
    categories: PARTY_GROUPS[0].categories.concat(
      WINTER_GROUPS[0].categories,
      RETREAT_GROUPS[0].categories
    ),
  },
  {
    id: 'social_media',
    label: 'Photos & Outreach',
    categories: PHOTO_GROUPS[0].categories.concat(
      VISIT_GROUPS[0].categories,
      OUTREACH_GROUPS[0].categories
    ),
  },
];

export const SOCIAL_SECTION_CONFIG_LEGACY = {
  sectionIds: ['social_misc'],
  categoryGroups: SOCIAL_CATEGORY_GROUPS,
  defaultCategory: 'lab_photos',
  categorizePath: categorizeSocialPath,
  documentTitle: socialDocumentTitle,
};
