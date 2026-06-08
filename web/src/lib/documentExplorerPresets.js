import { findSubNav } from '../config/navigation.js';

/**
 * Maps nav context → Scientific File Explorer domain tab + default filters.
 * Project Portfolio is intentionally excluded — research twins stay on their own screens.
 */

/** Map Document Library sidebar ids → explorer preset main/sub (libraryMain/librarySub). */
export function resolveExplorerNav(mainId, subId) {
  if (mainId === 'library') {
    const sub = findSubNav('library', subId);
    if (sub?.libraryMain) {
      return {
        mainId: sub.libraryMain,
        subId: sub.librarySub || subId,
      };
    }
  }
  return { mainId, subId };
}

const OVERVIEW_SECTION_BY_SUB = {
  onboarding: 'overview_onboarding',
  guidelines: 'overview_guidelines',
  documents_permits: 'overview_documents',
  personnel: 'overview_personnel',
  cleaning: 'overview_cleaning',
  research_materials: 'overview_research_materials',
};

const OVERVIEW_SCOPE_LABELS = {
  onboarding: 'Onboarding & Outboarding',
  guidelines: 'Guidelines',
  documents_permits: 'Documents & Permits',
  personnel: 'Personnel',
  cleaning: 'Lab Cleaning',
  research_materials: 'Research Reference',
  social: 'Social & Events',
  get_started: 'Lab Administration',
};

/** Mirrors document_classification.APP_PAGES path routing for CyCif sub-tabs. */
const CYCIF_APP_PAGE_BY_SUB = {
  cycif_projects: 'cycif.projects',
  cycif_instructions: 'cycif.instructions',
  cycif_sectioning: 'cycif.sectioning',
  cycif_inventory: 'cycif.inventory',
  cycif_protocols: 'cycif.protocols',
};

const CYCIF_SCOPE_LABELS = {
  cycif_projects: 'CyCIF — Individual Projects',
  cycif_instructions: 'CyCIF — Instructions & SOPs',
  cycif_sectioning: 'CyCIF — Sectioning & H&E',
  cycif_inventory: 'CyCIF — Antibody Inventory',
  cycif_protocols: 'CyCIF — Protocols & Resources',
};

/** Wet-lab (Oetlab) twins exclude CyCIF paths — those live under CyCIF nav only. */
const WET_LAB_BASE_FILTERS = { section: 'wet_lab_files', exclude_cycif: true };

/** Top-level library categories (files tab) — flat, no redundant parent chip. */
const WET_LAB_TOP_SCOPE_CHIP_IDS = new Set([
  'protocols_methods',
  'reagents_panels',
  'spatial_platforms',
  'registers_data',
  'chemical_safety',
  'histology_services',
]);

/** Workflow sub-filters nested under top-level wet-lab categories. */
const WET_LAB_WORKFLOW_SCOPE_CHIP_IDS = new Set([
  'patient_samples',
  'sample_preparation',
  'tissue_processing',
  'spatial_assays',
  'staining_flow',
  'reagents_inventory',
]);

/** Scope chips shown per wet-lab sub-tab (ids from smart_taxonomy.json). */
const WET_LAB_SCOPE_CHIP_IDS = {
  files: new Set([
    ...WET_LAB_TOP_SCOPE_CHIP_IDS,
    ...WET_LAB_WORKFLOW_SCOPE_CHIP_IDS,
  ]),
  protocols: new Set([
    'protocols_methods',
    'patient_samples',
    'sample_preparation',
    'tissue_processing',
    'spatial_assays',
    'staining_flow',
  ]),
  inventory: new Set([
    'reagents_panels',
    'reagents_inventory',
  ]),
};

const ORDERS_SCOPE_BY_SUB = {
  billing: { section: 'orders_billing', scopeLabel: 'Billing & Instructions' },
  archive: { section: 'orders_archive', scopeLabel: 'Historical Archive' },
  orders: { section: 'orders_archive', smart_chip: 'yearly_orders', scopeLabel: 'Yearly Order Registers' },
  related: { section: 'orders_billing', scopeLabel: 'Shipping & Related Records' },
};

/** @returns {{ domainTab: string, filters: Record<string, unknown>, systemView?: string, showDomainTabs: boolean, scopeLabel?: string, initialQuery?: string, taxonomyTab?: string, folderTreeRoot?: string|null }} */
export function getExplorerPreset(mainId, subId) {
  const resolved = resolveExplorerNav(mainId, subId);
  mainId = resolved.mainId;
  subId = resolved.subId;

  if (mainId === 'overview') {
    if (subId === 'social') {
      return {
        domainTab: 'overview',
        taxonomyTab: 'overview',
        filters: { domain: 'social_memory', section: 'social_misc' },
        showDomainTabs: false,
        hideScopeFilters: true,
        scopeLabel: OVERVIEW_SCOPE_LABELS.social,
        folderTreeRoot: 'SOCIAL & MISCELLANEOUS',
      };
    }
    const section = OVERVIEW_SECTION_BY_SUB[subId];
    if (section) {
      return {
        domainTab: 'overview',
        taxonomyTab: 'overview',
        filters: { section },
        showDomainTabs: false,
        hideScopeFilters: true,
        scopeLabel: OVERVIEW_SCOPE_LABELS[subId] || 'Lab Administration',
        folderTreeRoot: 'Overview',
      };
    }
    if (subId === 'get_started') {
      return {
        domainTab: 'overview',
        taxonomyTab: 'overview',
        filters: { domain: 'administration' },
        showDomainTabs: false,
        hideScopeFilters: true,
        scopeLabel: OVERVIEW_SCOPE_LABELS.get_started,
        folderTreeRoot: 'Overview',
      };
    }
  }

  if (mainId === 'wet_lab' && subId === 'files') {
    return {
      domainTab: 'wet_lab',
      taxonomyTab: 'wet_lab',
      filters: { ...WET_LAB_BASE_FILTERS },
      showDomainTabs: false,
      hideScopeFilters: true,
      scopeLabel: 'Lab Operations',
      scopeChipIds: WET_LAB_SCOPE_CHIP_IDS.files,
      folderTreeRoot: 'WET_LAB',
    };
  }

  if (mainId === 'wet_lab' && subId === 'protocols') {
    return {
      domainTab: 'wet_lab',
      taxonomyTab: 'wet_lab',
      filters: { ...WET_LAB_BASE_FILTERS, protocol_only: true },
      showDomainTabs: false,
      hideScopeFilters: true,
      scopeLabel: 'Protocols & Methods',
      scopeChipIds: WET_LAB_SCOPE_CHIP_IDS.protocols,
      folderTreeRoot: 'WET_LAB',
    };
  }

  if (mainId === 'wet_lab' && subId === 'inventory') {
    return {
      domainTab: 'wet_lab',
      taxonomyTab: 'wet_lab',
      filters: { ...WET_LAB_BASE_FILTERS, reagents_only: true },
      showDomainTabs: false,
      hideScopeFilters: true,
      scopeLabel: 'Reagents & Panels',
      scopeChipIds: WET_LAB_SCOPE_CHIP_IDS.inventory,
      folderTreeRoot: 'WET_LAB',
    };
  }

  if (mainId === 'cycif') {
    const appPage = CYCIF_APP_PAGE_BY_SUB[subId];
    return {
      domainTab: 'wet_lab',
      taxonomyTab: 'cycif',
      filters: {
        section: 'wet_lab_files',
        cycif_only: true,
        ...(appPage ? { app_page: appPage } : {}),
      },
      initialQuery: '',
      showDomainTabs: false,
      hideScopeFilters: true,
      scopeLabel: CYCIF_SCOPE_LABELS[subId] || 'CyCIF documents',
      folderTreeRoot: 'WET_LAB',
    };
  }

  if (mainId === 'orders') {
    const scope = ORDERS_SCOPE_BY_SUB[subId];
    if (scope) {
      const { scopeLabel, ...filters } = scope;
      return {
        domainTab: 'orders',
        taxonomyTab: 'orders',
        filters,
        showDomainTabs: false,
        hideScopeFilters: true,
        scopeLabel,
        folderTreeRoot: 'ORDERS & RELATED INFORMATION',
      };
    }
  }

  if (mainId === 'data_storage' && (subId === 'documents' || subId === 'all_files')) {
    return {
      domainTab: 'all_files',
      taxonomyTab: 'all_files',
      filters: {},
      showDomainTabs: true,
      scopeLabel: subId === 'all_files' ? 'Full Library' : 'All Lab Documents',
      folderTreeRoot: null,
    };
  }

  if (mainId === 'library' && subId === 'all_files') {
    return {
      domainTab: 'all_files',
      taxonomyTab: 'all_files',
      filters: {},
      showDomainTabs: true,
      scopeLabel: 'Full Library',
      folderTreeRoot: null,
    };
  }

  if (mainId === 'projects') {
    return {
      domainTab: 'projects',
      taxonomyTab: 'projects',
      filters: {},
      showDomainTabs: false,
      scopeLabel: 'Project workspace files',
      folderTreeRoot: 'projects',
    };
  }

  return {
    domainTab: 'all_files',
    taxonomyTab: 'all_files',
    filters: {},
    showDomainTabs: true,
    scopeLabel: 'Full Library',
    folderTreeRoot: null,
  };
}

export function isDocumentExplorerRoute(mainId, subId, screen) {
  if (screen === 'document_library') return true;
  if (mainId === 'library') return true;
  if (mainId === 'data_storage' && (subId === 'documents' || subId === 'all_files')) return true;
  if (screen === 'orders_billing' || screen === 'orders_archive') return true;
  if (screen === 'lab_knowledge') {
    if (mainId === 'overview' && subId !== 'dashboard' && subId !== 'research') {
      return true;
    }
    if (mainId === 'wet_lab' && (subId === 'files' || subId === 'protocols' || subId === 'inventory')) return true;
    if (mainId === 'cycif' && subId !== 'knowledge') return true;
  }
  if (screen === 'wet_protocols' || screen === 'wet_inventory') return true;
  return false;
}

/** Structured scope summary for AI assistant / chat context. */
export function getLibraryScopeContext(mainId, subId) {
  const uiMain = mainId;
  const uiSub = subId;
  const resolved = resolveExplorerNav(mainId, subId);
  const preset = getExplorerPreset(resolved.mainId, resolved.subId);
  if (!preset?.filters || preset.domainTab === 'all_files') return null;
  return {
    main_id: resolved.mainId,
    sub_id: resolved.subId,
    ui_main_id: uiMain,
    ui_sub_id: uiSub,
    domain_tab: preset.domainTab,
    scope_label: preset.scopeLabel,
    filters: preset.filters,
    ...(preset.folderTreeRoot ? { folder_tree_root: preset.folderTreeRoot } : {}),
  };
}
