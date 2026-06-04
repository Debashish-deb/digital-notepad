/** Maps navigation sub-tabs to lab database API section ids. */
export const DATABASE_SECTION_BY_SUB = {
  get_started: null,
  onboarding: 'overview_onboarding',
  guidelines: 'overview_guidelines',
  documents_permits: 'overview_documents',
  personnel: 'overview_personnel',
  cleaning: 'overview_cleaning',
  research: 'overview_research_materials',
  billing: 'orders_billing',
  archive: 'orders_archive',
  social_browse: 'social_misc',
  files: 'wet_lab_files',
};

export function databaseSectionIdForSub(subId, navSub) {
  if (navSub?.databaseSub) return navSub.databaseSub;
  return DATABASE_SECTION_BY_SUB[subId] || null;
}
