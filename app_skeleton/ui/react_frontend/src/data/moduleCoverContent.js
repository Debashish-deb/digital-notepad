/** Cover card copy and imagery per top-level main nav section. */

const COVERS = '/covers';

export const MODULE_COVER = {
  overview: {
    tone: 'overview',
    coverImage: `${COVERS}/overview.png`,
    useIntroCopy: true,
    metaDescription:
      'Lab orientation, onboarding, guidelines, and permits for the Färkkilä Lab ONCOSYS research programme.',
  },
  orders: {
    tone: 'orders',
    coverImage: `${COVERS}/orders.png`,
    eyebrow: 'Procurement & billing',
    title: 'Orders & related information',
    lead:
      'Vendor billing, HUS ordering instructions, shipment records, and archived procurement — everything needed to place and track lab orders.',
    metaDescription:
      'Procurement, vendor billing, HUS ordering instructions, and shipment records for Färkkilä Lab.',
  },
  social: {
    tone: 'social',
    coverImage: `${COVERS}/social.png`,
    eyebrow: 'Lab culture & outreach',
    title: 'Social & miscellaneous',
    lead:
      'Retreats, seasonal events, lab photos, visitor hosting, and outreach materials — the human side of the Färkkilä Lab.',
    metaDescription:
      'Lab retreats, events, photos, visitor hosting, and outreach for the Färkkilä research community.',
  },
  data_storage: {
    tone: 'storage',
    coverImage: `${COVERS}/data-storage.png`,
    eyebrow: 'Infrastructure & FAIR data',
    title: 'Data & Storage',
    lead:
      'Where lab data lives: L-drive, P-drive, UH DataCloud & Databank, CSC Allas, local disks, and the workflows that keep ONCOSYS and project data safe.',
    metaDescription:
      'FAIR data storage landscape — L-drive, P-drive, DataCloud, CSC Allas, and transfer workflows.',
  },
  projects_data: {
    tone: 'projects',
    coverImage: `${COVERS}/projects.png`,
    eyebrow: 'Research programmes',
    title: 'Project Portfolio',
    lead:
      'SPACE, EyeMT, KRAS, and related programmes — portfolios, living notebooks, decision registers, and clinical feature warehouses.',
    metaDescription:
      'Research project portfolio — SPACE, EyeMT, KRAS notebooks, decisions, and clinical feature warehouse.',
  },
  wet_lab: {
    tone: 'wetlab',
    coverImage: `${COVERS}/wetlab.png`,
    eyebrow: 'Bench science',
    title: 'Wet-lab',
    lead:
      'Protocols, reagent panels, wet-lab tasks, and on-disk SOPs for sample prep, staining, and quality control.',
    metaDescription:
      'Wet-lab protocols, reagent panels, tasks, and SOPs for sample prep and quality control.',
  },
  cycif: {
    tone: 'cycif',
    coverImage: `${COVERS}/cycif.png`,
    eyebrow: 'Spatial imaging',
    title: 'CyCif / t-CycIF',
    lead:
      'Multiplex tissue imaging pipeline — staining plans, antibody inventory, sectioning orders, Napari viewers, and project run sheets.',
    metaDescription:
      't-CycIF spatial imaging — staining plans, antibody inventory, Napari viewers, and run sheets.',
  },
  computational: {
    tone: 'compute',
    coverImage: `${COVERS}/computational.png`,
    eyebrow: 'HPC & bioinformatics',
    title: 'Computational Hub',
    lead:
      'LUMI, cPouta, conda environments, file transfers, troubleshooting, and published lab tools — Tribus, CEFIIRA, SPACEstat.',
    metaDescription:
      'Bioinformatics hub — LUMI HPC, cPouta VMs, conda environments, and lab computational tools.',
  },
  ai_assistant: {
    tone: 'ai',
    coverImage: `${COVERS}/ai-assistant.png`,
    eyebrow: 'Lab intelligence',
    title: 'AI Lab Assistant',
    lead:
      'RAG copilot over protocols and project docs, prompt templates, ingestion jobs, and model registry for assisted research.',
    metaDescription:
      'AI lab copilot — RAG Q&A, hybrid search, prompt templates, and document ingestion for grounded answers.',
  },
  profile: {
    tone: 'profile',
    coverImage: `${COVERS}/profile.png`,
    eyebrow: 'Lab identity',
    title: 'User Profile',
    lead:
      'Your researcher profile — role, publications, skills, and contact details within the Färkkilä Lab notebook.',
    metaDescription:
      'Researcher profile — role, publications, skills, and lab identity settings.',
  },
  meeting: {
    tone: 'meeting',
    coverImage: `${COVERS}/meeting.png`,
    eyebrow: 'Collaboration',
    title: 'Meeting & Booking',
    lead:
      'Schedule lab meetings, book shared resources, and coordinate team sessions across ONCOSYS programmes.',
    metaDescription:
      'Lab meeting calendar and booking for team coordination and shared resources.',
  },
  administration: {
    tone: 'admin',
    coverImage: `${COVERS}/admin.png`,
    eyebrow: 'Platform operations',
    title: 'Administration',
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
  const image = cover?.coverImage || `${COVERS}/overview.png`;
  return {
    title: `${sectionTitle} · ${titleSuffix}`,
    description,
    image,
  };
}

const PAGE_META_FALLBACK =
  'OMEIA — the Färkkilä Lab digital research notebook for ONCOSYS projects, wet-lab protocols, spatial imaging, bioinformatics, and AI-assisted knowledge search.';
