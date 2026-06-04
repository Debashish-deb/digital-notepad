import {
  LayoutDashboard,
  ClipboardList,
  FolderOpen,
  FlaskConical,
  Microscope,
  Cpu,
  Bot,
  Users,
  HardDrive,
  Shield,
} from 'lucide-react';

/** Top-level lab areas and their sub-sections (screens map to App.jsx). */
export const MAIN_NAV = [
  {
    id: 'overview',
    label: 'Overview',
    icon: LayoutDashboard,
    defaultSub: 'get_started',
    children: [
      { id: 'get_started', label: 'General lab information', screen: 'lab_knowledge', description: 'All general lab documents: onboarding, guidelines, permits, cleaning, and related folders.' },
      {
        id: 'onboarding',
        label: 'Onboarding & Outboarding',
        screen: 'lab_knowledge',
        databaseSub: 'overview_onboarding',
        description: 'Orientation and onboarding/outboarding checklists.',
      },
      { id: 'guidelines', label: 'Guidelines', screen: 'lab_knowledge', description: 'Research and work-related lab guidelines.' },
      { id: 'documents_permits', label: 'Documents & Permits', screen: 'lab_knowledge', description: 'Permits, forms, datasheets, and handbooks.' },
      { id: 'personnel', label: 'Personnel', screen: 'lab_knowledge', description: 'Personnel records and support documents.' },
      {
        id: 'cleaning',
        label: 'Lab cleaning',
        screen: 'lab_knowledge',
        databaseSub: 'overview_cleaning',
        description: 'Cleaning schedules and lab upkeep documents.',
      },
      { id: 'dashboard', label: 'Lab dashboard', screen: 'dashboard', description: 'Metrics, team, audit trail, platform readiness.' },
      { id: 'research', label: 'Research materials', screen: 'lab_knowledge', databaseSub: 'overview_research_materials', description: 'Conference materials, posters, and publications on disk.' },
    ],
  },
  {
    id: 'orders',
    label: 'Orders & related information',
    icon: ClipboardList,
    defaultSub: 'billing',
    children: [
      { id: 'billing', label: 'Billing & ordering instructions', screen: 'orders_billing', description: 'Billing, vendors, shipments, and HUS ordering.' },
      { id: 'archive', label: 'Archive', screen: 'lab_knowledge', description: 'Historical orders, quotes, and procurement archives.' },
      { id: 'tasks', label: 'Task planner', screen: 'tasks', description: 'Cross-project tasks and assignments.' },
      { id: 'orders', label: 'Orders register', screen: 'orders_register', description: 'Reagents, sequencing, and service orders.' },
      { id: 'related', label: 'Related records', screen: 'orders_related', description: 'Linked samples, shipments, and metadata.' },
    ],
  },
  {
    id: 'social',
    label: 'Social & miscellaneous',
    icon: Users,
    defaultSub: 'social_browse',
    children: [
      { id: 'social_browse', label: 'Browse', screen: 'lab_knowledge', description: 'Parties, retreats, photos, outreach, and visits.' },
    ],
  },
  {
    id: 'data_storage',
    label: 'Data & Storage',
    icon: HardDrive,
    defaultSub: 'vault',
    children: [
      { id: 'vault', label: 'Raw knowledge vault', screen: 'data_storage', dataSection: 'vault', description: 'Asset registry, search, and review queue.' },
      { id: 'roots', label: 'Storage roots', screen: 'data_storage', dataSection: 'roots', description: 'DataCloud WebDAV, P-drive mount, Supabase metadata, and connector status.' },
      { id: 'ingest', label: 'Ingestion & sync', screen: 'data_storage', dataSection: 'ingest', description: 'Digitalization, vault ingest, Supabase sync (dry run), and review.' },
      { id: 'ingestion', label: 'Ingestion dashboard', screen: 'ingestion_dashboard', description: 'Vault summary metrics and digitalization run history.' },
      { id: 'knowledge', label: 'Knowledge search', screen: 'knowledge_search', description: 'Hybrid lab corpus and vault metadata search.' },
      { id: 'lab_corpus', label: 'Lab corpus browser', screen: 'lab_corpus', description: 'All database sections with processed twins and vault counts.' },
    ],
  },
  {
    id: 'projects_data',
    label: 'Projects & Data',
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
    defaultSub: 'pipeline',
    children: [
      { id: 'pipeline', label: 'Imaging pipeline', screen: 'cycif_pipeline', description: 'Stitching, segmentation, and QC triggers.' },
      { id: 'install', label: 'Tool setup', screen: 'cycif_install', description: 'Napari, Cylinter, and viewer installs.' },
      { id: 'structure', label: 'Project structure', screen: 'cycif_structure', description: 't-CycIF folder layout validation.' },
    ],
  },
  {
    id: 'computational',
    label: 'Computational Hub',
    icon: Cpu,
    defaultSub: 'onboarding',
    children: [
      { id: 'onboarding', label: 'Onboarding & credentials', screen: 'bioinformatics', bioSub: 'onboarding' },
      { id: 'conda', label: 'Conda environments', screen: 'bioinformatics', bioSub: 'conda' },
      { id: 'install', label: 'Tool installations', screen: 'bioinformatics', bioSub: 'install' },
      { id: 'file_ops', label: 'File operations', screen: 'bioinformatics', bioSub: 'file_ops' },
      { id: 'lumi', label: 'LUMI HPC', screen: 'bioinformatics', bioSub: 'lumi' },
      { id: 'pouta', label: 'cPouta VMs', screen: 'bioinformatics', bioSub: 'pouta' },
      { id: 'diagnostics', label: 'Diagnostics', screen: 'bioinformatics', bioSub: 'diagnostics' },
      { id: 'troubleshoot', label: 'Log troubleshooting', screen: 'bioinformatics', bioSub: 'troubleshoot' },
      { id: 'tools', label: 'Lab computational tools', screen: 'computational_tools', description: 'Tribus, CEFIIRA, and published pipelines.' },
    ],
  },
  {
    id: 'ai_assistant',
    label: 'AI Lab Assistant',
    icon: Bot,
    defaultSub: 'copilot',
    children: [
      { id: 'copilot', label: 'Chat copilot', screen: 'ai_assistant', aiSub: 'copilot', description: 'RAG Q&A over protocols and project docs.' },
      { id: 'prompts', label: 'Prompt templates', screen: 'ai_assistant', aiSub: 'prompts' },
      { id: 'ingest', label: 'Ingest documents', screen: 'ai_assistant', aiSub: 'ingest' },
      { id: 'models', label: 'Model registry', screen: 'ai_assistant', aiSub: 'models' },
    ],
  },
  {
    id: 'administration',
    label: 'Administration',
    icon: Shield,
    defaultSub: 'admin',
    children: [
      { id: 'admin', label: 'Users & jobs', screen: 'administration', description: 'Health, connectors, allowlist, ingestion jobs, auth.' },
      { id: 'connectors', label: 'Connectors & health', screen: 'administration', description: 'GET /health and /api/platform/connectors readiness.' },
    ],
  },
];

export function findMainNav(mainId) {
  return MAIN_NAV.find((m) => m.id === mainId) || MAIN_NAV[0];
}

export function findSubNav(mainId, subId) {
  const main = findMainNav(mainId);
  return main.children.find((c) => c.id === subId) || main.children[0];
}

export function sectionTitle(mainId, subId) {
  const main = findMainNav(mainId);
  const sub = findSubNav(mainId, subId);
  return `${main.label} · ${sub.label}`;
}

export function parseNavFromStorage(raw) {
  if (!raw || typeof raw !== 'string') return null;
  const [main, sub] = raw.split(':');
  if (!findMainNav(main)) return null;
  return { main, sub: sub || findMainNav(main).defaultSub };
}
