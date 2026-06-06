/** Maps navigation sub-tabs to lab database API section ids. */
export const DATABASE_SECTION_BY_SUB = {
  get_started: null,
  onboarding: 'overview_onboarding',
  guidelines: 'overview_guidelines',
  documents_permits: 'overview_documents',
  personnel: 'overview_personnel',
  cleaning: 'overview_cleaning',
  billing: 'orders_billing',
  archive: 'orders_archive',
  social_browse: 'social_misc',
  lab_parties: 'social_misc',
  winter_events: 'social_misc',
  lab_retreats: 'social_misc',
  lab_photos: 'social_misc',
  researcher_visits: 'social_misc',
  outreach: 'social_misc',
  files: 'wet_lab_files',
  knowledge: 'wet_lab_files',
  cycif_projects: 'wet_lab_files',
  cycif_instructions: 'wet_lab_files',
  cycif_sectioning: 'wet_lab_files',
  cycif_inventory: 'wet_lab_files',
  cycif_protocols: 'wet_lab_files',
};

export function databaseSectionIdForSub(subId, navSub) {
  if (navSub?.databaseSub) return navSub.databaseSub;
  return DATABASE_SECTION_BY_SUB[subId] || null;
}
