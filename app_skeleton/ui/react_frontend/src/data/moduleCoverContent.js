/** Cover card copy and transparent overlay art per top-level main nav section. */

const OVERLAYS = '/covers/overlays';

/** @typedef {'bottom-right' | 'top-right' | 'bottom-left'} CoverOverlayPosition */

/**
 * Transparent accent art layered on the gradient card (not a full-bleed background).
 * @type {Record<string, { src: string, position?: CoverOverlayPosition }>}
 */
export const MODULE_COVER_OVERLAYS = {
  overview: { src: `${OVERLAYS}/overview.svg`, position: 'bottom-right' },
  orders: { src: `${OVERLAYS}/orders.svg`, position: 'bottom-right' },
  data_storage: { src: `${OVERLAYS}/data-storage.svg`, position: 'bottom-right' },
  projects_data: { src: `${OVERLAYS}/projects.svg`, position: 'bottom-right' },
  wet_lab: { src: `${OVERLAYS}/wetlab.svg`, position: 'bottom-right' },
  cycif: { src: `${OVERLAYS}/cycif.svg`, position: 'top-right' },
  computational: { src: `${OVERLAYS}/computational.svg`, position: 'bottom-right' },
  ai_assistant: { src: `${OVERLAYS}/ai-assistant.svg`, position: 'top-right' },
  profile: { src: `${OVERLAYS}/profile.svg`, position: 'bottom-right' },
  meeting: { src: `${OVERLAYS}/meeting.svg`, position: 'bottom-right' },
  administration: { src: `${OVERLAYS}/administration.svg`, position: 'bottom-right' },
};

export const MODULE_COVER = {
  overview: {
    tone: 'overview',
    accentHue: '#c45c8a',
    overlayArt: MODULE_COVER_OVERLAYS.overview,
    useIntroCopy: true,
    tagline: 'ONCOSYS · ovarian cancer · spatial atlas',
    tags: ['HGSC', 'Spatial biology', 'TME', 'TLS'],
    metaDescription:
      'Lab orientation, onboarding, guidelines, and permits for the Färkkilä Lab ONCOSYS research programme.',
  },
  orders: {
    tone: 'orders',
    accentHue: '#d97706',
    overlayArt: MODULE_COVER_OVERLAYS.orders,
    eyebrow: 'Procurement & billing',
    title: 'Orders & related information',
    tagline: 'Reagents · antibodies · HUS procurement',
    tags: ['Vendor billing', 'Shipments', 'Lab supplies'],
    lead:
      'Vendor billing, HUS ordering instructions, shipment records, and archived procurement — everything needed to place and track lab orders.',
    metaDescription:
      'Procurement, vendor billing, HUS ordering instructions, and shipment records for Färkkilä Lab.',
  },
  data_storage: {
    tone: 'storage',
    accentHue: '#0d9488',
    overlayArt: MODULE_COVER_OVERLAYS.data_storage,
    eyebrow: 'Infrastructure & FAIR data',
    title: 'Data & Storage',
    tagline: 'FAIR principles · multi-tier storage',
    tags: ['L-drive', 'DataCloud', 'CSC Allas', 'FAIR'],
    lead:
      'Where lab data lives: L-drive, P-drive, UH DataCloud & Databank, CSC Allas, local disks, and the workflows that keep ONCOSYS and project data safe.',
    metaDescription:
      'FAIR data storage landscape — L-drive, P-drive, DataCloud, CSC Allas, and transfer workflows.',
  },
  projects_data: {
    tone: 'projects',
    accentHue: '#2563eb',
    overlayArt: MODULE_COVER_OVERLAYS.projects_data,
    eyebrow: 'Research programmes',
    title: 'Project Portfolio',
    tagline: 'SPACE · EyeMT · KRAS · clinical warehouse',
    tags: ['ONCOSYS', 'Decision register', 'Notebooks'],
    lead:
      'SPACE, EyeMT, KRAS, and related programmes — portfolios, living notebooks, decision registers, and clinical feature warehouses.',
    metaDescription:
      'Research project portfolio — SPACE, EyeMT, KRAS notebooks, decisions, and clinical feature warehouse.',
  },
  wet_lab: {
    tone: 'wetlab',
    accentHue: '#16a34a',
    overlayArt: MODULE_COVER_OVERLAYS.wet_lab,
    eyebrow: 'Bench science',
    title: 'Wet-lab',
    tagline: 'Sample prep · staining · QC protocols',
    tags: ['SOPs', 'Reagent panels', 'QC'],
    lead:
      'Protocols, reagent panels, wet-lab tasks, and on-disk SOPs for sample prep, staining, and quality control.',
    metaDescription:
      'Wet-lab protocols, reagent panels, tasks, and SOPs for sample prep and quality control.',
  },
  cycif: {
    tone: 'cycif',
    accentHue: '#06b6d4',
    overlayArt: MODULE_COVER_OVERLAYS.cycif,
    eyebrow: 'Spatial imaging',
    title: 'CyCif / t-CycIF',
    tagline: 'Multiplex tissue · antibody cycles · Napari',
    tags: ['t-CyCIF', 'Visium', 'GeoMx', 'MHC-II'],
    lead:
      'Multiplex tissue imaging pipeline — staining plans, antibody inventory, sectioning orders, Napari viewers, and project run sheets.',
    metaDescription:
      't-CycIF spatial imaging — staining plans, antibody inventory, Napari viewers, and run sheets.',
  },
  computational: {
    tone: 'compute',
    accentHue: '#0891b2',
    overlayArt: MODULE_COVER_OVERLAYS.computational,
    eyebrow: 'HPC & bioinformatics',
    title: 'Computational Hub',
    tagline: 'LUMI · cPouta · single-cell · spatial omics',
    tags: ['LUMI', 'SPACEstat', 'Tribus', 'CEFIIRA'],
    lead:
      'LUMI, cPouta, conda environments, file transfers, troubleshooting, and published lab tools — Tribus, CEFIIRA, SPACEstat.',
    metaDescription:
      'Bioinformatics hub — LUMI HPC, cPouta VMs, conda environments, and lab computational tools.',
  },
  ai_assistant: {
    tone: 'ai',
    accentHue: '#6366f1',
    overlayArt: MODULE_COVER_OVERLAYS.ai_assistant,
    eyebrow: 'Lab intelligence',
    title: 'AI Lab Assistant',
    tagline: 'RAG · hybrid search · grounded answers',
    tags: ['RAG', 'Embeddings', 'Ingestion', 'Copilot'],
    lead:
      'RAG copilot over protocols and project docs, prompt templates, ingestion jobs, and model registry for assisted research.',
    metaDescription:
      'AI lab copilot — RAG Q&A, hybrid search, prompt templates, and document ingestion for grounded answers.',
  },
  profile: {
    tone: 'profile',
    accentHue: '#64748b',
    overlayArt: MODULE_COVER_OVERLAYS.profile,
    eyebrow: 'Lab identity',
    title: 'User Profile',
    tagline: 'Researcher profile · publications · skills',
    tags: ['Publications', 'Skills', 'Contact'],
    lead:
      'Your researcher profile — role, publications, skills, and contact details within the Färkkilä Lab notebook.',
    metaDescription:
      'Researcher profile — role, publications, skills, and lab identity settings.',
  },
  meeting: {
    tone: 'meeting',
    accentHue: '#0284c7',
    overlayArt: MODULE_COVER_OVERLAYS.meeting,
    eyebrow: 'Collaboration',
    title: 'Meeting & Booking',
    tagline: 'Lab meetings · resource booking · coordination',
    tags: ['Calendar', 'Booking', 'Team sync'],
    lead:
      'Schedule lab meetings, book shared resources, and coordinate team sessions across ONCOSYS programmes.',
    metaDescription:
      'Lab meeting calendar and booking for team coordination and shared resources.',
  },
  administration: {
    tone: 'admin',
    accentHue: '#475569',
    overlayArt: MODULE_COVER_OVERLAYS.administration,
    eyebrow: 'Platform operations',
    title: 'Administration',
    tagline: 'Auth · connectors · ingestion · config',
    tags: ['Firebase', 'Connectors', 'Jobs'],
    lead:
      'User allowlist, Firebase auth, connector health, ingestion jobs, and platform configuration for this research notebook.',
    metaDescription:
      'Platform administration — auth, connectors, ingestion jobs, and notebook configuration.',
  },
};

export function getModuleCover(mainId, subId) {
  if (mainId === 'profile' && subId === 'admin') {
    return MODULE_COVER.administration;
  }
  return MODULE_COVER[mainId] || null;
}

export function moduleHasCover(mainId, subId) {
  return Boolean(getModuleCover(mainId, subId));
}

/**
 * Build document title and meta description for the active route.
 * @param {string} sectionTitle — e.g. "Overview · General lab information"
 * @param {string} mainId
 * @param {string} subId
 * @param {string} titleSuffix — i18n document title suffix
 */
export function getModulePageMeta(sectionTitle, mainId, subId, titleSuffix) {
  const cover = getModuleCover(mainId, subId);
  const description = cover?.metaDescription || cover?.lead || PAGE_META_FALLBACK;
  const image = '/assets/hero.png';
  return {
    title: `${sectionTitle} · ${titleSuffix}`,
    description,
    image,
  };
}

const PAGE_META_FALLBACK =
  'OMEIA — the Färkkilä Lab digital research notebook for ONCOSYS projects, wet-lab protocols, spatial imaging, bioinformatics, and AI-assisted knowledge search.';
