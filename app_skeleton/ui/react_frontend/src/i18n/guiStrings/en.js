/** English — source of truth for GUI strings. */
export default {
  common: {
    appTitle: 'Farkki Digital Research NotePad',
    appLabName: 'Färkkilä Lab',
    appOrg: 'University of Helsinki',
    sectionTabsAria: 'Section pages',
    sectionPages: 'Pages',
    sidebarToolbarAria: 'Sidebar settings',
    searchRegistry: 'Search Registry...',
    mainNavAria: 'Main lab sections',
    user: 'User:',
    api: 'API:',
    apiConnected: 'Connected',
    apiUnreachable: 'Unreachable',
    apiChecking: 'Checking…',
    dbOffline: 'DB offline',
    themeTitle: 'Theme: {theme}. Click to cycle.',
    skipToWorkspace: 'Skip to workspace',
    platformEyebrow: 'Farkki research platform',
    refresh: 'Refresh',
    refreshAria: 'Refresh project, team and audit data',
    syncing: 'Syncing…',
    ready: 'Ready',
    projectsSynced: 'Projects synced',
    syncWarning: 'Using cached project list where the API was unavailable.',
    langLabel: 'Language',
    documentTitleSuffix: 'Farkki Lab Assistant',
  },

  navMain: {
    overview: 'Overview',
    orders: 'Orders & related information',
    social: 'Social & miscellaneous',
    data_storage: 'Data & Storage',
    projects_data: 'Project Portfolio',
    wet_lab: 'Wet-lab',
    cycif: 'CyCif',
    computational: 'Computational Hub',
    ai_assistant: 'AI Lab Assistant',
    administration: 'Administration',
  },

  navMainSidebar: {
    projects_data: 'Project Portfolio',
    orders: 'Orders',
    social: 'Social',
  },

  navSub: {
    overview: {
      get_started: {
        label: 'General lab information',
        sidebarLabel: 'General info',
        description:
          'Introduction to the Färkkilä Lab and ONCOSYS — orientation and onboarding files are under Onboarding & Outboarding.',
      },
      onboarding: {
        label: 'Onboarding & Outboarding',
        sidebarLabel: 'Onboarding',
        description: 'Orientation and onboarding/outboarding checklists.',
      },
      guidelines: {
        label: 'Guidelines',
        sidebarLabel: 'Guidelines',
        description: 'Research and work-related lab guidelines.',
      },
      documents_permits: {
        label: 'Documents & Permits',
        sidebarLabel: 'Documents',
        description: 'Permits, forms, datasheets, and handbooks.',
      },
      personnel: {
        label: 'Personnel',
        sidebarLabel: 'Personnel',
        description: 'Personnel records and support documents.',
      },
      cleaning: {
        label: 'Lab cleaning',
        sidebarLabel: 'Cleaning',
        description: 'Cleaning schedules and lab upkeep documents.',
      },
      social: {
        label: 'Social & miscellaneous',
        sidebarLabel: 'Social',
        description:
          'Retreats, seasonal events, lab photos, visitor hosting, and outreach materials.',
      },
      dashboard: {
        label: 'Lab dashboard',
        description: 'Metrics, team, audit trail, platform readiness.',
      },
      research: {
        label: 'Research materials',
        description: 'Conference materials, posters, and publications on disk.',
      },
    },
    orders: {
      billing: {
        label: 'Billing & ordering instructions',
        sidebarLabel: 'Billing',
        description: 'Billing, vendors, shipments, and HUS ordering.',
      },
      archive: {
        label: 'Archive',
        sidebarLabel: 'Archive',
        description: 'Historical orders, quotes, and procurement archives.',
      },
      orders: {
        label: 'Orders register',
        sidebarLabel: 'Register',
        description: 'Reagents, sequencing, and service orders.',
      },
      related: {
        label: 'Related records',
        sidebarLabel: 'Related',
        description: 'Linked samples, shipments, and metadata.',
      },
    },
    social: {
      lab_parties: {
        label: 'Lab Parties',
        sidebarLabel: 'Parties',
        description: 'Halloween, grilling parties, and event planning documents.',
      },
      winter_events: {
        label: 'Winter Day & Seasonal',
        sidebarLabel: 'Winter events',
        description: 'Lab winter day photos and seasonal gatherings.',
      },
      lab_retreats: {
        label: 'Lab Retreats',
        sidebarLabel: 'Retreats',
        description: 'Retreat planning and Nuuksio retreat materials.',
      },
      lab_photos: {
        label: 'Lab Photos',
        sidebarLabel: 'Photos',
        description: 'Group photos, retreat albums, and lab life pictures.',
      },
      researcher_visits: {
        label: 'Researcher Visits',
        sidebarLabel: 'Visits',
        description: 'Visitor records and hosting materials.',
      },
      outreach: {
        label: 'Outreach & Social Media',
        sidebarLabel: 'Outreach',
        description: 'Outreach campaigns and social media assets.',
      },
    },
    data_storage: {
      landscape: {
        label: 'Storage landscape',
        description:
          'All lab storage systems — L-drive, P-drive, DataCloud, Google Drive, Allas, Databank — with capacities and roles.',
      },
      network_drives: {
        label: 'L-drive & P-drive',
        description: 'UH network drives: sensitive clinical (L) and active project storage (P).',
      },
      datacloud: {
        label: 'DataCloud & Databank',
        description:
          'University services: DataCloud WebDAV /farkkila/ (~10 TB) and UH Databank for long-term archives.',
      },
      cloud_archive: {
        label: 'CSC Allas',
        description: 'CSC object storage (~30 TB active) for datasets staged before HPC analysis.',
      },
      google_drive: {
        label: 'Google Drive',
        description:
          'Project logs, onboarding docs, and collaboration — archive inactive projects regularly.',
      },
      local_storage: {
        label: 'Local & external disks',
        description:
          'Workstations, cpu1-data, cold-storage disks, and HUH clinical database access.',
      },
      guidelines: {
        label: 'Guidelines & workflow',
        description:
          'Active → CSC Allas, inactive/published → UH Databank, sensitivity rules, and source documents.',
      },
      tools: {
        label: 'Transfer tools',
        description:
          'rclone, Lumi-O, allas-conf, Cyberduck, rsync — when to use each and common transfer patterns.',
      },
      documents: {
        label: 'Lab documents',
        description:
          'All storage-related onboarding, cleaning, IT, and inventory documents in one place.',
      },
    },
    projects_data: {
      portfolio: {
        label: 'Project portfolio',
        description: 'Browse projects and open workspace vitals.',
      },
      notebook: {
        label: 'Living notebook',
        description: 'Lab notebook logs and protocol wiki.',
      },
      decisions: {
        label: 'Research decisions',
        description: 'Formal decision register across projects.',
      },
      features: {
        label: 'Feature warehouse',
        description: 'Clinical feature matrix and similarity search.',
      },
    },
    wet_lab: {
      files: {
        label: 'Lab database files',
        description: 'Protocols, inventories, and wet-lab documents on disk.',
      },
      protocols: {
        label: 'Wet-lab protocols',
        description: 'SOPs for sample prep, staining prep, and QC.',
      },
      tasks: {
        label: 'Wet-lab tasks',
        description: 'Tasks tagged for wet-lab work.',
      },
      inventory: {
        label: 'Reagents & panels',
        description: 'Antibody panels and reagent references.',
      },
    },
    cycif: {
      pipeline: {
        label: 'Imaging pipeline',
        description: 'Stitching, segmentation, and QC triggers.',
      },
      install: {
        label: 'Tool setup',
        description: 'Napari, Cylinter, and viewer installs.',
      },
      structure: {
        label: 'Project structure',
        description: 't-CycIF folder layout validation.',
      },
      cycif_projects: {
        label: 'Individual Projects',
        description: 'Per-project staining plans, notes, and run spreadsheets.',
      },
      cycif_instructions: {
        label: 'Instructions & SOPs',
        description: 't-CycIF workflow instructions, templates, and planning files.',
      },
      cycif_sectioning: {
        label: 'Sectioning & H&E',
        description: 'Sectioning orders and H&E staining after t-CycIF.',
      },
      cycif_inventory: {
        label: 'Antibody Inventory',
        description: 'CyCIF antibody panels and inventory spreadsheets.',
      },
      cycif_protocols: {
        label: 'Protocols & Resources',
        description: 'Spatial CycIF protocols and GeoMx / CycIF resources.',
      },
    },
    computational: {
      onboarding: { label: 'Onboarding & credentials' },
      lumi: {
        label: 'LUMI HPC',
        description: 'Slurm jobs, spatial tool installs, pipelines, and Lumi-O transfers.',
      },
      pouta: {
        label: 'cPouta VMs',
        description: 'Lab cloud VMs, provisioning guides, and VM-side conda setup.',
      },
      roihu: {
        label: 'Roihu',
        description: 'CSC Roihu supercomputer — content coming soon.',
      },
      troubleshoot: {
        label: 'Troubleshooting',
        description: 'Environment diagnostics and log analysis.',
      },
      utilities: {
        label: 'Utilities',
        description: 'File operations and conda environment management.',
      },
      tools: {
        label: 'Lab computational tools',
        description: 'Published lab software — Tribus, CEFIIRA, SPACEstat, and related spatial analysis tools.',
      },
    },
    ai_assistant: {
      copilot: {
        label: 'Chat copilot',
        description: 'RAG Q&A over protocols and project docs.',
      },
      prompts: { label: 'Prompt templates' },
      ingest: { label: 'Ingest documents' },
      models: { label: 'Model registry' },
    },
    administration: {
      admin: {
        label: 'Users & jobs',
        description: 'Health, connectors, allowlist, ingestion jobs, auth.',
      },
      connectors: {
        label: 'Connectors & health',
        description: 'GET /health and /api/platform/connectors readiness.',
      },
    },
  },

  catGroup: {
    billing: 'Billing & Finance',
    logistics: 'Logistics & Shipping',
    other: 'Other',
    guidelines: 'Lab Guidelines',
    onboarding: 'Onboarding & Outboarding',
    cleaning: 'Lab Cleaning',
    personnel: 'Personnel',
    research: 'Research Materials',
    permits: 'Permits & Compliance',
    reference: 'Reference & Equipment',
    pharma: 'GSK Papers',
    archive_finance: 'Lab Finance & Accounts',
    archive_procurement: 'Procurement Records',
    archive_it: 'IT & Infrastructure',
    social_events: 'Lab Events',
    social_media: 'Photos & Outreach',
    wet_protocols: 'Protocols & SOPs',
    wet_platforms: 'Spatial & Platform Assays',
    wet_ops: 'Inventory & Operations',
    tcycif_core: 't-CycIF Projects',
    tcycif_support: 'Supporting Materials',
  },

  cat: {
    biobank: {
      label: 'Biobank Requests',
      description: 'Biobank sample and data requests.',
    },
    bsl_forms: {
      label: 'BSL-2 Forms & Templates',
      description: 'GMM forms, risk assessment templates at BSL-2 root.',
    },
    bsl1_2: {
      label: 'BSL-1 & BSL-2 Manuals',
      description: 'Biosafety manuals, emergency plans, insurance, THL templates.',
    },
    bsl_drafts: {
      label: 'BSL Drafts for Modification',
      description: 'Draft biosafety manuals and cell rules.',
    },
    bsl_gmo: {
      label: 'GMO Application Drafts',
      description: 'GMM application and risk assessment forms.',
    },
    ethanol: {
      label: 'Ethanol Permission (Valvira 2019)',
      description: 'Valvira permits, appeals, and inventory records.',
    },
    datasheets: {
      label: 'Datasheets & Handbooks',
      description: 'Product datasheets and lab handbooks.',
    },
    qiagen: {
      label: 'Qiagen Handbooks',
      description: 'Qiagen kit handbooks and protocols.',
    },
    equipment_barcodes: {
      label: 'Equipment Barcodes',
      description: 'Barcode photos for REVCO, incubators, etc.',
    },
    root_docs: {
      label: 'General Reference',
      description: 'FFPE articles, room numbers, and misc. reference PDFs.',
    },
    gsk_nov2021: {
      label: 'GSK Nov 2021 (GSK3859856B)',
      description: 'Proforma invoices, customs, and purpose forms.',
    },
    gsk_filled: {
      label: 'GSK Filled Forms (Drafts)',
      description: 'Completed RFI forms — Ashwini & Anastasiya.',
    },
    gsk_unfilled: {
      label: 'GSK Unfilled Forms',
      description: 'Blank University of Helsinki RFI templates.',
    },
    gsk_root: {
      label: 'GSK Other',
      description: 'MSDS and other GSK reference files.',
    },
    research: {
      label: 'Research-related',
      description: 'Abstracts, presentations, theses, meetings, grants, and affiliations.',
    },
    work: {
      label: 'Work-related',
      description: 'Holidays, sick leave, and day-to-day work guidelines.',
    },
    orientation: {
      label: 'Orientation & Safety',
      description: 'Onboarding decks, orientation PDFs, and lab safety from Kauppi lab.',
    },
    contacts: {
      label: 'Contacts & Procedures',
      description: 'Onboarding/outboarding checklists and important contacts.',
    },
    cleaning_20250528: {
      label: 'Cleaning Day — 28 May 2025',
      description: 'Data cleaning day tasks and storage unit comments.',
    },
    cleaning_251205: {
      label: 'Cleaning Day — 5 Dec 2025',
      description: 'Wet lab, dry lab, and external drive cleaning inventories.',
    },
    roster: {
      label: 'Current Personnel',
      description: 'Active lab member records.',
    },
    hiring: {
      label: 'Hiring & Recruitment',
      description: 'Job ads, interview materials, and scoring matrices.',
    },
    lab_management: {
      label: 'Lab Management',
      description: 'Management structure, role descriptions, and instructions.',
    },
    conference: {
      label: 'Conference Abstracts & Posters',
      description: 'ESGO, AACR, European Ovarian Cancer Symposium, EMBL, etc.',
    },
    phd_apps: {
      label: 'PhD & Doctoral School',
      description: 'Doctoral school applications and related materials.',
    },
    peer_review: {
      label: 'Peer Review',
      description: 'Papers under peer review.',
    },
    presentations: {
      label: 'Presentations & Posters Archive',
      description: 'Archived presentations and poster files.',
    },
    general_reference: {
      label: 'General Reference',
      description: 'Core billing addresses, delivery info, and university invoice forms.',
    },
    hus_finance: {
      label: 'HUS Finance & Billing',
      description: 'HUS billing instructions, EVO budgets, and HUSLAB order forms.',
    },
    credentials: {
      label: 'Credentials & Access',
      description: 'Vendor website logins and account credentials (sensitive).',
    },
    fedex: {
      label: 'FedEx',
      description: 'FedEx account details and archived air waybills.',
    },
    ups: {
      label: 'UPS',
      description: 'UPS courier setup, screenshots, and air waybills.',
    },
    dna_shipments: {
      label: 'DNA Sample Shipments',
      description: 'International DNA shipments (Copenhagen, Myriad, Denmark).',
    },
    us_customs: {
      label: 'US Customs & Proforma',
      description: 'USDA statements, proforma invoices, and customs examples.',
    },
    other_admin: {
      label: 'Admin & Facilities',
      description: 'Room booking and other administrative references.',
    },
    hus_purchases: {
      label: 'HUS Lab Purchases',
      description: 'HUSLAB account purchases and lab procurement spreadsheets.',
    },
    fican_funding: {
      label: 'FiCAN South Funding',
      description: 'FiCAN South programme funding and budget registers.',
    },
    lab_transfers: {
      label: 'Inter-lab Transfers & Debt',
      description: 'Money transfers and debt settlements between lab accounts.',
    },
    equipment_orders: {
      label: 'Equipment Order Confirmations',
      description: 'Vendor order confirmations (Fisher Scientific, ONCOSYS equipment, etc.).',
    },
    collaboration_orders: {
      label: 'Collaboration Orders',
      description: 'Cross-lab and programme collaboration procurement (Kauppi, TERVA).',
    },
    purchase_registers: {
      label: 'Purchase Registers',
      description: 'Historical purchase spreadsheets and uncategorized registers.',
    },
    computer_orders: {
      label: 'Computer & IT Orders',
      description: 'Workstation orders, Dustin invoices, and IT procurement forms.',
    },
    party_halloween: {
      label: 'Halloween',
      description: 'Halloween party planning and event files.',
    },
    party_grilling: {
      label: 'Grilling & Social Events',
      description: 'Grilling parties and informal gatherings.',
    },
    party_planning: {
      label: 'Party Planning',
      description: 'General party plans and event documents.',
    },
    winter_photos: {
      label: 'Event Photos',
      description: 'Pictures from lab winter day and seasonal events.',
    },
    winter_docs: {
      label: 'Documents',
      description: 'Planning notes and non-image files.',
    },
    retreat_2024: {
      label: '2024 Retreat',
      description: 'Nuuksio retreat materials from 2024.',
    },
    retreat_2025: {
      label: '2025 Retreat',
      description: 'Nuuksio retreat materials from 2025.',
    },
    retreat_planning: {
      label: 'Retreat Planning',
      description: 'Retreat schedules, plans, and shared documents.',
    },
    photo_retreats: {
      label: 'Retreat Albums',
      description: 'Photo albums from lab retreats.',
    },
    photo_shoot: {
      label: 'Lab Photoshoots',
      description: 'Professional and group photoshoot sessions.',
    },
    photo_group: {
      label: 'Group Photos',
      description: 'Official group photos and team portraits.',
    },
    photo_events: {
      label: 'Event Photos',
      description: 'Pictures from parties and lab events.',
    },
    photo_misc: {
      label: 'Other Photos',
      description: 'Additional lab life and miscellaneous images.',
    },
    visit_records: {
      label: 'Visitor Records',
      description: 'Hosting materials and visitor documentation.',
    },
    outreach_media: {
      label: 'Outreach & Social Media',
      description: 'Outreach campaigns and social media assets.',
    },
    project_runs: {
      label: 'Experiment Runs',
      description: 'Per-project staining plans and run spreadsheets.',
    },
    project_validation: {
      label: 'Antibody Validation',
      description: 'Validation experiments and antibody screening files.',
    },
    project_templates: {
      label: 'Templates',
      description: 'Project templates and planning spreadsheets.',
    },
    cycif_planning: {
      label: 'Experiment Planning',
      description: 'Protocols, planning templates, and Cyclops auto-plan files.',
    },
    cycif_antibody_scan: {
      label: 'Antibodies & Scanning',
      description: 'Antibody database exports and scanning references.',
    },
    cycif_instruction_other: {
      label: 'Other Instructions',
      description: 'Additional instruction documents.',
    },
    sectioning_orders: {
      label: 'Sectioning Orders',
      description: 't-CycIF sectioning order spreadsheets.',
    },
    he_after_cycif: {
      label: 'H&E After t-CycIF',
      description: 'H&E staining records after CycIF runs.',
    },
    sectioning_other: {
      label: 'Other Sectioning Files',
      description: 'Additional sectioning-related documents.',
    },
    lab_parties: {
      label: 'Lab Parties',
      description: 'Halloween, grilling parties, and event planning documents.',
    },
    winter_events: {
      label: 'Winter Day & Seasonal Events',
      description: 'Lab winter day photos and seasonal gatherings.',
    },
    lab_retreats: {
      label: 'Lab Retreats',
      description: 'Retreat planning and Nuuksio retreat materials.',
    },
    lab_photos: {
      label: 'Lab Photos',
      description: 'Group photos, retreat albums, and lab life pictures.',
    },
    researcher_visits: {
      label: 'Researcher Visits',
      description: 'Visitor records and hosting materials.',
    },
    outreach: {
      label: 'Outreach & Social Media',
      description: 'Outreach campaigns and social media assets.',
    },
    social_misc: {
      label: 'Other',
      description: 'Uncategorized social and miscellaneous files.',
    },
    patient_samples: {
      label: 'Patient Sample Protocols',
      description: 'Collection, handling, and processing protocols for patient samples.',
    },
    patient_omentum: {
      label: 'Patient · Omentum',
      description: 'Per-sample protocols for omentum (pOme / pOva) specimens.',
    },
    patient_adnexa: {
      label: 'Patient · Adnexa',
      description: 'Per-sample protocols for adnexal (pAdn) specimens.',
    },
    patient_other_sites: {
      label: 'Patient · Other Sites',
      description: 'Protocols for bowel, spleen, vaginal, and other non-omentum sites.',
    },
    patient_misc: {
      label: 'Patient · Unsorted',
      description: 'Patient sample protocols without a clear site code in the filename.',
    },
    proto_sample_prep: {
      label: 'Sample Prep & Organoids',
      description: 'Tissue dissociation, organoid culture, iPDCs, and related medium recipes.',
    },
    proto_tissue_processing: {
      label: 'Tissue Fixation & FFPE',
      description: 'Fixation, processing, and FFPE block preparation SOPs.',
    },
    proto_spatial: {
      label: 'Spatial & CycIF',
      description: 'Spatial assays, t-CycIF, GeoMx slide prep, and imaging reports.',
    },
    proto_staining: {
      label: 'Staining & Flow',
      description: 'Immunofluorescence, flow cytometry, and immune profiling protocols.',
    },
    proto_archive: {
      label: 'Protocol Archive',
      description: 'Legacy bench protocols stored under Archive 2.0.',
    },
    proto_imaging: {
      label: 'Imaging & QC References',
      description: 'EVOS scale-bar references, counting chambers, and microscopy QC.',
    },
    proto_lab_ops: {
      label: 'Lab Operations',
      description: 'Sterilization, calibration, precipitation, and troubleshooting SOPs.',
    },
    proto_scrna: {
      label: 'scRNA-seq',
      description: 'Single-cell RNA sequencing protocols and notes.',
    },
    proto_general: {
      label: 'General Protocols',
      description: 'Root-level protocols and instructions not in a subfolder.',
    },
    protocols: {
      label: 'Protocols & Instructions',
      description: 'General wet-lab protocols and bench instructions.',
    },
    slide_orders: {
      label: 'Slides & Sections Orders',
      description: 'Orders for slides, sections, and histology services.',
    },
    geomx: {
      label: 'NanoString GeoMx',
      description: 'GeoMx project notes, protocols, and run documentation.',
    },
    xenium: {
      label: 'Xenium',
      description: 'Xenium experiment plans and spatial transcriptomics files.',
    },
    individual_projects: {
      label: 'Individual Projects',
      description: 'Per-project staining plans, notes, and run folders.',
    },
    instructions: {
      label: 'Instructions & SOPs',
      description: 't-CycIF workflow instructions and lab SOPs.',
    },
    sectioning: {
      label: 'Sectioning & H&E',
      description: 'Sectioning orders and H&E staining after t-CycIF.',
    },
    antibody_inventory: {
      label: 'CyCIF Antibody Inventory',
      description: 'Antibody panels and inventory spreadsheets for CycIF.',
    },
    spatial_protocols: {
      label: 'Spatial CycIF Protocols',
      description: 'Spatial protocol docs and CycIF processing templates.',
    },
    geomx_cycif: {
      label: 'GeoMx & CycIF Resources',
      description: 'Combined GeoMx / CycIF experiment planning resources.',
    },
    cycif_other: {
      label: 'Other CycIF Files',
      description: 'Additional CycIF-related documents.',
    },
    inventories: {
      label: 'Reagents, Samples & Equipment',
      description: 'Inventory spreadsheets, reagent lists, and equipment records.',
    },
    waste_mgmt: {
      label: 'Waste & Chemical Inventory',
      description: 'Waste management, Fortum forms, and chemical inventory SOPs.',
    },
    wet_spreadsheets: {
      label: 'Registers & Spreadsheets',
      description: 'Vacation sample collection, legacy reagent lists, and misc. registers.',
    },
  },

  taskpad: {
    title: 'Taskpad',
    quickCapture: 'Quick Capture',
    projectLog: 'Project Log',
    collapse: 'Collapse',
    close: 'Collapse taskpad',
    targetArea: 'Target area',
    noteLabel: 'Note / task / status',
    notePlaceholder: 'Type here…',
    save: 'Save',
    savedAlert: 'Saved to Taskpad!',
    projectLogHint: 'Project Log',
    labWide: 'Lab-wide',
    globalScope: 'Lab-wide — all modules',
    generalLab: 'General lab task',
    projectWorkspace: 'Project workspace',
    currentProject: 'This project',
    sectionTitle: 'Section taskpad',
    centralTitle: 'Central Taskpad',
    projectsHubTitle: 'Projects hub taskpad',
    managerMode: 'Manager view',
    managerView: 'Manager',
    workerView: 'Notes',
    managerHint: 'Workers under this manager — open one to view or add notes scoped to that area only.',
    managedByCentral: 'Managed by Central Taskpad',
    managedByProjectsHub: 'Managed by Projects hub',
    recentTasks: 'Recent tasks',
    taskCount: 'tasks',
    noWorkers: 'No registered workers yet — visit a section or project workspace to register workers.',
    binaryFileHint:
      'This project log is a {ext} file. Convert it to .md for full Taskpad editing, or open the original from the Log tab file browser.',
    scope: {
      central: 'Central',
      projectsHub: 'Projects hub',
      section: 'Section',
    },
    central: {
      coordination: 'Lab-wide coordination',
      priorities: 'Priorities & blockers',
    },
    projectsHub: {
      portfolio: 'Portfolio & PI notes',
      coordination: 'Cross-project coordination',
      admin: 'Admin & registry',
    },
  },

  taskbar: {
    edit: 'Edit',
    save: 'Save',
    saving: 'Saving…',
    saved: 'Saved',
    saveFailed: 'Save failed',
    cancel: 'Cancel',
    editing: 'Editing',
    editSections: 'Editable sections',
    selectSection: 'Section',
    noEditor: 'No profile editor for this tab — browse files below.',
    scanFirst: 'Scan the project folder to enable editing.',
    rescan: 'Rescan project folder',
    overviewProfile: 'Overview profile',
    registry: 'Registry & status',
    planActivity: 'Plan & activity',
    dataCatalog: 'Data catalog',
    protocols: 'Protocols',
    filesFigures: 'Files & figures',
    writingAbstracts: 'Writing & abstracts',
    logActivity: 'Log & activity',
    registryHint: 'Database registry fields — priority, blockers, and status notes.',
    shortTitle: 'Short title',
    ethicsRef: 'Ethics reference',
    projectType: 'Project type',
    priority: 'Priority',
    researchQuestion: 'Research question',
    projectSummary: 'Project summary',
    blockers: 'Current blockers',
    nextActions: 'Next actions',
    latestUpdate: 'Latest activity update',
  },

  workspace: {
    overview: 'Overview',
    plan: 'Plan',
    data: 'Data',
    methods: 'Methods',
    writing: 'Writing',
    archive: 'Archive',
    log: 'Log',
  },

  docs: {
    files: 'files',
    searchFiles: 'Search files',
    searchPlaceholder: 'Search files…',
    noFilesCategory: 'No files in this category.',
    noFilesSearch: 'No files match your search.',
    groupTabsAria: 'Document groups',
    groupEyebrow: 'Sections',
    sectionCorpusEyebrow: 'Document library',
    categoryTabsAria: 'Document categories',
    subcategoryEyebrow: 'Categories',
    subfolderTabsAria: 'Document subfolders',
    albumsEyebrow: 'Choose an album',
    albumFileOne: '1 file',
    albumFileMany: '{count} files',
    selectFile: 'Select a file to preview extracted content or open the original.',
    protocolPreviewHint: 'Use the category tabs above to switch protocol types — folders are flattened into one list per category.',
    catalogPreviewHint: 'Use the tabs above to switch sections and categories — pick a file on the left to preview.',
    openOriginal: 'Open original',
    revealSensitive: 'Reveal sensitive',
    hideSensitive: 'Hide sensitive',
    sensitiveMasked: 'Sensitive content — preview masked by default.',
    loading: 'Loading documents…',
    loadingPreview: 'Loading extracted preview…',
    offlineExtractPreview:
      'Original file is not on this server — showing text extracted from the lab catalog.',
    loadError: 'Failed to load documents.',
    teamDirectory: 'Team Directory',
    filesInSection: '{count} files',
    loadingProject: 'Loading project files…',
    noProjectFiles:
      'No files in this workspace section yet. Scan the project folder or add files under the matching numbered folder (e.g. 2_Methods & Experiments).',
    selectFileEdit: 'Select a file to preview or edit.',
    sectionFile: 'Section file',
    editInTaskpad: 'Edit in Taskpad',
    taskpadEditorHint:
      'Use Edit in Taskpad for full Monaco editing with save, proofread, and heading tools.',
    spreadsheetOpen: 'Spreadsheet — open the original file to view tables.',
    spreadsheetLoading: 'Loading spreadsheet…',
    spreadsheetRepaired: 'Recovered from a damaged or non-standard file:',
    spreadsheetTruncated: 'Showing a subset of rows and columns for performance.',
    spreadsheetEmpty: 'This spreadsheet has no visible cells.',
    spreadsheetFailed: 'Could not open this spreadsheet in the browser.',
    codeLoading: 'Loading source file…',
    codeFailed: 'Could not load source file.',
    noTextPreview: 'No text preview. Open the original file or expand the PDF thumbnail.',
    mediaLoading: 'Loading image…',
    mediaFailed: 'Could not load image.',
    videoLoading: 'Loading video…',
    videoFailed: 'Could not play this video in the browser.',
    modelLoading: 'Loading 3D viewer…',
    mediaZoomIn: 'Zoom in',
    mediaZoomOut: 'Zoom out',
    mediaFit: 'Fit to view',
    mediaActualSize: 'Actual size',
    mediaRotate: 'Rotate 90°',
    mediaFullscreen: 'Fullscreen',
    mediaPrevious: 'Previous',
    mediaNext: 'Next',
    modelHint: 'Drag to orbit · Scroll to zoom · Right-drag to pan',
    modelPlay: 'Play animation',
    modelPause: 'Pause animation',
    modelAutoRotate: 'Auto-rotate',
    modelReset: 'Reset view',
  },
};
