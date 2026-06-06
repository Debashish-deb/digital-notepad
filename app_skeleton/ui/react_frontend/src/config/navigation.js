import {
  LayoutDashboard,
  ClipboardList,
  FolderOpen,
  FlaskConical,
  Microscope,
  Cpu,
  Bot,
  HardDrive,
  Shield,
  User,
  Calendar,
} from 'lucide-react';

/** Top-level lab areas and their sub-sections (screens map to App.jsx). */
export const MAIN_NAV = [
  {
    id: 'overview',
    label: 'Overview',
    icon: LayoutDashboard,
    defaultSub: 'get_started',
    children: [
      { id: 'get_started', label: 'General lab information', sidebarLabel: 'General info', screen: 'lab_knowledge', description: 'Introduction to the Färkkilä Lab and ONCOSYS — orientation and onboarding files are under Onboarding & Outboarding.' },
      {
        id: 'onboarding',
        label: 'Onboarding & Outboarding',
        sidebarLabel: 'Onboarding',
        screen: 'lab_knowledge',
        databaseSub: 'overview_onboarding',
        description: 'Orientation and onboarding/outboarding checklists.',
      },
      { id: 'guidelines', label: 'Guidelines', sidebarLabel: 'Guidelines', screen: 'lab_knowledge', description: 'Research and work-related lab guidelines.' },
      { id: 'documents_permits', label: 'Documents & Permits', sidebarLabel: 'Documents', screen: 'lab_knowledge', description: 'Permits, forms, datasheets, and handbooks.' },
      { id: 'personnel', label: 'Personnel', sidebarLabel: 'Personnel', screen: 'lab_knowledge', description: 'Personnel records and support documents.' },
      {
        id: 'cleaning',
        label: 'Lab cleaning',
        sidebarLabel: 'Cleaning',
        screen: 'lab_knowledge',
        databaseSub: 'overview_cleaning',
        description: 'Cleaning schedules and lab upkeep documents.',
      },
      {
        id: 'social',
        label: 'Social & miscellaneous',
        sidebarLabel: 'Social',
        screen: 'lab_knowledge',
        description: 'Retreats, seasonal events, lab photos, visitor hosting, and outreach materials.',
      },
    ],
  },
  {
    id: 'projects_data',
    label: 'Project Portfolio',
    sidebarLabel: 'Project Portfolio',
    icon: FolderOpen,
    defaultSub: 'portfolio',
    keepsProject: true,
    children: [
      { id: 'portfolio', label: 'Project portfolio', screen: 'projects', description: 'Browse projects and open workspace vitals.' },
      { id: 'notebook', label: 'Living notebook', screen: 'notebook', description: 'Lab notebook logs and protocol wiki.' },
      { id: 'decisions', label: 'Research decisions', screen: 'decisions', description: 'Formal decision register across projects.' },
      { id: 'features', label: 'Feature warehouse', screen: 'features', description: 'Clinical feature matrix and similarity search.' },
    ],
  },
  {
    id: 'data_storage',
    label: 'Data & Storage',
    icon: HardDrive,
    defaultSub: 'landscape',
    children: [
      { id: 'landscape', label: 'Storage landscape', screen: 'data_storage', dataSection: 'landscape', description: 'Overview map — where data goes, capacity summary, and links to each storage tab.' },
      { id: 'network_drives', label: 'L-drive & P-drive', screen: 'data_storage', dataSection: 'network_drives', description: 'L-drive: UH sensitive clinical (not Allas). P-drive: ~80 TB active project storage across all shares.' },
      { id: 'datacloud', label: 'DataCloud & Databank', screen: 'data_storage', dataSection: 'datacloud', description: 'University services: DataCloud WebDAV /farkkila/ (~10 TB) and UH Databank for long-term pseudonymized archives.' },
      { id: 'cloud_archive', label: 'CSC Allas', screen: 'data_storage', dataSection: 'cloud_archive', description: 'CSC object storage (~30 TB active) for datasets staged before Puhti/LUMI analysis.' },
      { id: 'google_drive', label: 'Google Drive', screen: 'data_storage', dataSection: 'google_drive', description: 'Project logs, onboarding docs, and collaboration — archive inactive projects regularly.' },
      { id: 'local_storage', label: 'Local & external disks', screen: 'data_storage', dataSection: 'local_storage', description: 'Workstations, cPouta /data NFS, external disks, GeoMx exports, and HUH Datalake / OVCA.' },
      { id: 'guidelines', label: 'Guidelines & workflow', screen: 'data_storage', dataSection: 'guidelines', description: 'Lifecycle workflow, FAIR rules, sensitivity classes, cleaning-day checklist, and lab source docs.' },
      { id: 'tools', label: 'Transfer tools', screen: 'data_storage', dataSection: 'tools', description: 'rclone, Lumi-O, allas-conf, Cyberduck, rsync — when to use each and common transfer patterns.' },
      { id: 'documents', label: 'Lab documents', screen: 'data_storage', dataSection: 'documents', description: 'Interactive map of every document zone in the app — browse and preview lab files with readable content.' },
    ],
  },
  {
    id: 'wet_lab',
    label: 'Wet-lab',
    icon: FlaskConical,
    defaultSub: 'files',
    children: [
      { id: 'files', label: 'Lab database files', screen: 'lab_knowledge', databaseSub: 'wet_lab_files', description: 'Protocols, inventories, and wet-lab documents on disk.' },
      { id: 'protocols', label: 'Wet-lab protocols', screen: 'wet_protocols', description: 'SOPs for sample prep, staining prep, and QC.' },
      { id: 'tasks', label: 'Wet-lab tasks', screen: 'wet_tasks', description: 'Tasks tagged for wet-lab work.' },
      { id: 'inventory', label: 'Reagents & panels', screen: 'wet_inventory', description: 'Antibody panels and reagent references.' },
    ],
  },
  {
    id: 'cycif',
    label: 'CyCif',
    icon: Microscope,
    defaultSub: 'cycif_projects',
    children: [
      { id: 'pipeline', label: 'Imaging pipeline', screen: 'cycif_pipeline', description: 'Stitching, segmentation, and QC triggers.' },
      { id: 'install', label: 'Tool setup', screen: 'cycif_install', description: 'Napari, Cylinter, and viewer installs.' },
      { id: 'structure', label: 'Project structure', screen: 'cycif_structure', description: 't-CycIF folder layout validation.' },
      {
        id: 'cycif_projects',
        label: 'Individual Projects',
        screen: 'lab_knowledge',
        databaseSub: 'wet_lab_files',
        description: 'Per-project staining plans, notes, and run spreadsheets.',
      },
      {
        id: 'cycif_instructions',
        label: 'Instructions & SOPs',
        screen: 'lab_knowledge',
        databaseSub: 'wet_lab_files',
        description: 't-CycIF workflow instructions, templates, and planning files.',
      },
      {
        id: 'cycif_sectioning',
        label: 'Sectioning & H&E',
        screen: 'lab_knowledge',
        databaseSub: 'wet_lab_files',
        description: 'Sectioning orders and H&E staining after t-CycIF.',
      },
      {
        id: 'cycif_inventory',
        label: 'Antibody Inventory',
        screen: 'lab_knowledge',
        databaseSub: 'wet_lab_files',
        description: 'CyCIF antibody panels and inventory spreadsheets.',
      },
      {
        id: 'cycif_protocols',
        label: 'Protocols & Resources',
        screen: 'lab_knowledge',
        databaseSub: 'wet_lab_files',
        description: 'Spatial CycIF protocols and GeoMx / CycIF resources.',
      },
    ],
  },
  {
    id: 'computational',
    label: 'Computational Hub',
    icon: Cpu,
    defaultSub: 'onboarding',
    children: [
      { id: 'onboarding', label: 'Onboarding & credentials', screen: 'bioinformatics', bioSub: 'onboarding' },
      { id: 'lumi', label: 'LUMI HPC', screen: 'bioinformatics', bioSub: 'lumi', description: 'Slurm jobs, spatial tool installs (Ashlar, Stardist, Cylinter), pipelines, and Lumi-O transfers.' },
      { id: 'pouta', label: 'cPouta VMs', screen: 'bioinformatics', bioSub: 'pouta', description: 'Lab cloud VMs, provisioning guides, and VM-side conda setup.' },
      { id: 'roihu', label: 'Roihu', screen: 'bioinformatics', bioSub: 'roihu', description: 'CSC Roihu supercomputer — content coming soon.' },
      { id: 'troubleshoot', label: 'Troubleshooting', screen: 'bioinformatics', bioSub: 'troubleshoot', description: 'Environment diagnostics and log analysis.' },
      {
        id: 'utilities',
        label: 'Utilities',
        screen: 'bioinformatics',
        bioSub: 'utilities',
        description: 'File operations and conda environment management.',
      },
      {
        id: 'tools',
        label: 'Lab computational tools',
        screen: 'bioinformatics',
        bioSub: 'tools',
        description: 'Published lab software — Tribus, CEFIIRA, SPACEstat, and related spatial analysis tools.',
      },
    ],
  },
  {
    id: 'ai_assistant',
    label: 'AI Lab Assistant',
    icon: Bot,
    defaultSub: 'copilot',
    children: [
      { id: 'copilot', label: 'Chat copilot', screen: 'ai_assistant', aiSub: 'copilot', description: 'RAG Q&A over protocols and project docs.' },
      { id: 'knowledge_search', label: 'Advanced search', screen: 'knowledge_search', description: 'Unified hybrid search across lab corpus, vault, and registry.' },
      { id: 'research_kb', label: 'Research knowledge base', screen: 'research_knowledge', description: 'Färkkilä lab publications, datasets, and public research corpus for grounded AI answers.' },
      { id: 'prompts', label: 'Prompt templates', screen: 'ai_assistant', aiSub: 'prompts' },
      { id: 'ingest', label: 'Ingest documents', screen: 'ai_assistant', aiSub: 'ingest' },
      { id: 'models', label: 'Model registry', screen: 'ai_assistant', aiSub: 'models' },
    ],
  },
  {
    id: 'orders',
    label: 'Orders & related information',
    sidebarLabel: 'Orders',
    icon: ClipboardList,
    defaultSub: 'billing',
    children: [
      { id: 'billing', label: 'Billing & ordering instructions', sidebarLabel: 'Billing', screen: 'orders_billing', description: 'Billing, vendors, shipments, and HUS ordering.' },
      { id: 'archive', label: 'Archive', sidebarLabel: 'Archive', screen: 'orders_archive', description: 'Historical orders, quotes, and procurement archives.' },
      { id: 'orders', label: 'Orders register', sidebarLabel: 'Register', screen: 'orders_register', description: 'Reagents, sequencing, and service orders.' },
      { id: 'related', label: 'Related records', sidebarLabel: 'Related', screen: 'orders_related', description: 'Linked samples, shipments, and metadata.' },
    ],
  },
  {
    id: 'profile',
    label: 'Profile',
    icon: User,
    defaultSub: 'user_profile',
    children: [
      { id: 'user_profile', label: 'User Profile', screen: 'user_profile', description: 'Manage your user profile and settings.' },
      { id: 'admin', label: 'Administration', screen: 'administration', description: 'Health, connectors, allowlist, ingestion jobs, auth.' },
    ],
  },
  {
    id: 'meeting',
    label: 'Meeting',
    icon: Calendar,
    defaultSub: 'booking',
    children: [
      { id: 'booking', label: 'Booking calendar', screen: 'meeting_booking', description: 'Schedule and manage meetings.' },
    ],
  },
];

export function findMainNav(mainId) {
  return MAIN_NAV.find((m) => m.id === mainId) || MAIN_NAV[0];
}

const DATA_STORAGE_LEGACY_SUBS = {
  vault: 'landscape',
  roots: 'landscape',
  ingest: 'tools',
  digitalization: 'landscape',
  ingestion: 'landscape',
  knowledge: 'guidelines',
  lab_corpus: 'landscape',
};

/** Old Computational Hub tabs → new top-level tab id. */
export const COMPUTATIONAL_LEGACY_SUBS = {
  conda: 'utilities',
  install: 'lumi',
  file_ops: 'utilities',
  diagnostics: 'troubleshoot',
  tools: 'tools',
};

/** Nested section inside a reorganized hub tab (when opening a legacy sub id). */
export const COMPUTATIONAL_LEGACY_NESTED = {
  conda: { tab: 'utilities', section: 'conda' },
  install: { tab: 'lumi', section: 'install' },
  file_ops: { tab: 'utilities', section: 'file_ops' },
  diagnostics: { tab: 'troubleshoot', section: 'diagnostics' },
};

export function normalizeComputationalSub(subId) {
  return COMPUTATIONAL_LEGACY_SUBS[subId] || subId;
}

export function findSubNav(mainId, subId) {
  const main = findMainNav(mainId);
  let resolvedSub = subId;
  if (mainId === 'data_storage' && DATA_STORAGE_LEGACY_SUBS[subId]) {
    resolvedSub = DATA_STORAGE_LEGACY_SUBS[subId];
  } else if (mainId === 'computational') {
    resolvedSub = normalizeComputationalSub(subId);
  }
  return main.children.find((c) => c.id === resolvedSub) || main.children[0];
}

export function sectionTitle(mainId, subId) {
  const main = findMainNav(mainId);
  const sub = findSubNav(mainId, subId);
  return `${main.label} · ${sub.label}`;
}

/** Inner tabs inside Overview → Social (not sidebar children). */
export const SOCIAL_INNER_TAB_IDS = [
  'lab_parties',
  'winter_events',
  'lab_retreats',
  'lab_photos',
  'researcher_visits',
  'outreach',
];

/** Legacy top-level Social nav → Overview → Social with inner tab. */
export function resolveSocialLegacyNav(main, sub) {
  if (main !== 'social') return null;
  const resolvedSub =
    sub && SOCIAL_INNER_TAB_IDS.includes(sub)
      ? sub
      : sub === 'social_browse'
        ? 'lab_photos'
        : 'lab_photos';
  return { main: 'overview', sub: 'social', socialSub: resolvedSub };
}

export function parseNavFromStorage(raw) {
  if (!raw || typeof raw !== 'string') return null;
  const [main, sub] = raw.split(':');
  const socialResolved = resolveSocialLegacyNav(main, sub);
  if (socialResolved) return socialResolved;
  if (!findMainNav(main)) return null;
  return { main, sub: sub || findMainNav(main).defaultSub };
}
