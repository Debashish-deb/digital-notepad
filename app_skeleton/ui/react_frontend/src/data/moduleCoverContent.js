/** Cover card copy per top-level main nav section. */

export const MODULE_COVER = {
  overview: {
    tone: 'overview',
    useIntroCopy: true,
  },
  orders: {
    tone: 'orders',
    eyebrow: 'Procurement & billing',
    title: 'Orders & related information',
    lead:
      'Vendor billing, HUS ordering instructions, shipment records, and archived procurement — everything needed to place and track lab orders.',
  },
  social: {
    tone: 'social',
    eyebrow: 'Lab culture & outreach',
    title: 'Social & miscellaneous',
    lead:
      'Retreats, seasonal events, lab photos, visitor hosting, and outreach materials — the human side of the Färkkilä Lab.',
  },
  data_storage: {
    tone: 'storage',
    eyebrow: 'Infrastructure & FAIR data',
    title: 'Data & Storage',
    lead:
      'Where lab data lives: L-drive, P-drive, UH DataCloud & Databank, CSC Allas, local disks, and the workflows that keep ONCOSYS and project data safe.',
  },
  projects_data: {
    tone: 'projects',
    eyebrow: 'Research programmes',
    title: 'Project Portfolio',
    lead:
      'SPACE, EyeMT, KRAS, and related programmes — portfolios, living notebooks, decision registers, and clinical feature warehouses.',
  },
  wet_lab: {
    tone: 'wetlab',
    eyebrow: 'Bench science',
    title: 'Wet-lab',
    lead:
      'Protocols, reagent panels, wet-lab tasks, and on-disk SOPs for sample prep, staining, and quality control.',
  },
  cycif: {
    tone: 'cycif',
    eyebrow: 'Spatial imaging',
    title: 'CyCif / t-CycIF',
    lead:
      'Multiplex tissue imaging pipeline — staining plans, antibody inventory, sectioning orders, Napari viewers, and project run sheets.',
  },
  computational: {
    tone: 'compute',
    eyebrow: 'HPC & bioinformatics',
    title: 'Computational Hub',
    lead:
      'LUMI, cPouta, conda environments, file transfers, troubleshooting, and published lab tools — Tribus, CEFIIRA, SPACEstat.',
  },
  ai_assistant: {
    tone: 'ai',
    eyebrow: 'Lab intelligence',
    title: 'AI Lab Assistant',
    lead:
      'RAG copilot over protocols and project docs, prompt templates, ingestion jobs, and model registry for assisted research.',
  },
  administration: {
    tone: 'admin',
    eyebrow: 'Platform operations',
    title: 'Administration',
    lead:
      'User allowlist, Firebase auth, connector health, ingestion jobs, and platform configuration for this research notebook.',
  },
};

export function getModuleCover(mainId) {
  return MODULE_COVER[mainId] || null;
}

export function moduleHasCover(mainId) {
  return Boolean(MODULE_COVER[mainId]);
}
