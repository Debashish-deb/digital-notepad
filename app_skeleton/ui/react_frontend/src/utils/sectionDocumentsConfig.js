/**
 * Maps main nav + sub-tab to LabDocumentsBrowser section configs.
 */

import { getOverviewConfig } from './overviewCategories.js';
import { getCycifConfig } from './cycifCategories.js';
import { getSocialConfig } from './socialCategories.js';
import { WET_LAB_FILES_CONFIG } from './wetLabCategories.js';

const LAB_KNOWLEDGE_CONFIG = {
  overview: {
    onboarding: () => getOverviewConfig('onboarding'),
    guidelines: () => getOverviewConfig('guidelines'),
    documents_permits: () => getOverviewConfig('documents_permits'),
    personnel: () => getOverviewConfig('personnel'),
    cleaning: () => getOverviewConfig('cleaning'),
  },
  social: {
    /** @deprecated legacy stored nav */
    social_browse: () => getSocialConfig('lab_photos'),
    lab_parties: () => getSocialConfig('lab_parties'),
    winter_events: () => getSocialConfig('winter_events'),
    lab_retreats: () => getSocialConfig('lab_retreats'),
    lab_photos: () => getSocialConfig('lab_photos'),
    researcher_visits: () => getSocialConfig('researcher_visits'),
    outreach: () => getSocialConfig('outreach'),
  },
  wet_lab: {
    files: () => WET_LAB_FILES_CONFIG,
  },
  cycif: {
    cycif_projects: () => getCycifConfig('cycif_projects'),
    cycif_instructions: () => getCycifConfig('cycif_instructions'),
    cycif_sectioning: () => getCycifConfig('cycif_sectioning'),
    cycif_inventory: () => getCycifConfig('cycif_inventory'),
    cycif_protocols: () => getCycifConfig('cycif_protocols'),
    /** @deprecated stored nav may still reference knowledge */
    knowledge: () => getCycifConfig('cycif_projects'),
  },
};

/** Returns browser config for document-backed sub-tabs, or null for custom screens. */
export function getSectionDocumentsConfig(mainId, subId) {
  const main = LAB_KNOWLEDGE_CONFIG[mainId];
  if (!main) return null;
  const resolver = main[subId];
  return resolver ? resolver() : null;
}

export function isDocumentBackedSubTab(mainId, subId) {
  return Boolean(getSectionDocumentsConfig(mainId, subId));
}
