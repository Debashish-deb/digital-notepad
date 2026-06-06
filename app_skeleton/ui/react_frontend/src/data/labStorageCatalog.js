/**
 * Curated Färkkilä Lab storage landscape — lab corpus + IT allocations.
 * Lab-reported capacities (Jun 2026): Allas ~30 TB, Databank ~30 TB, DataCloud ~10 TB,
 * P-drive ~80 TB (all shares combined). L-drive is separate UH clinical storage (no fixed TB here).
 */

/** Quick reference — lab-reported total allocations */
export const STORAGE_CAPACITY_OVERVIEW = [
  { id: 'p_drive', label: 'P-drive (all shares)', capacity: '~80 TB', extendable: true, note: 'Combined Oncosys / lab P-drive trees' },
  { id: 'allas', label: 'CSC Allas', capacity: '~30 TB', extendable: true, note: 'Active project object storage' },
  { id: 'databank', label: 'UH Databank', capacity: 'UH quota', extendable: true, note: 'Long-term UH frozen archive' },
  { id: 'datacloud', label: 'DataCloud', capacity: '~10 TB', extendable: true, note: 'UH WebDAV /farkkila/' },
  { id: 'cpouta_nfs', label: 'cPouta /data NFS', capacity: '2 TB', extendable: false, note: 'GPU/CPU VM scratch only' },
  { id: 'l_drive', label: 'L-drive', capacity: 'UH quota', extendable: true, note: 'Sensitive clinical — confirm usage with IT' },
];

/** P-drive structure and practices (from IT docs + Computational Hub context) */
export const P_DRIVE_GUIDE = {
  totalCapacityTb: 80,
  summary:
    'University P-drive shares for active project data. Lab total across all Oncosys / farkkila P-drive trees is approximately 80 TB. Individual project folders may have their own sub-quotas.',
  shares: [
    'Oncosys consortium P-drive project trees (imaging, omics, collaboration)',
    'Per-project folders mirrored or synced with DataCloud where applicable',
    'Large imaging projects (e.g. t-CycIF, WSI) — primary non-sensitive bulk store',
  ],
  mountNotes: [
    'Access via UH network or VPN; mount path depends on your workstation setup.',
    'Dev mirror: set PDRIVE_MOUNT_PATH to local mount (see configs/PDRIVE_SETUP.md).',
    'Planned: selective offline sync of a project folder when internet drops (IT backlog).',
  ],
  practices: [
    'Inventory on cleaning days before moving data to Allas or Databank.',
    'Do not store uncontrolled clinical identifiers — use L-drive for sensitive cohort exports.',
    'Zip and stage large transfers; use rclone for DataCloud ↔ P-drive workflows (Computational Hub → File operations).',
  ],
};

/** L-drive — distinct from Allas; sensitive UH network storage */
export const L_DRIVE_GUIDE = {
  summary:
    'L-drive is UH network storage for sensitive and clinical research data. It is not the same as CSC Allas (~30 TB). Access renewal and expansion go through UH IT helpdesk.',
  paths: ['L:\\ltdk_farkkila\\', 'L:\\ltdk_farkkila\\Projects\\'],
  examples: [
    'L:\\ltdk_farkkila\\Projects\\12-SPACE\\ — clinical exports (Oncosys-OVA)',
    'Oncosys-OVA sensitive cohort files alongside DataCloud for restricted sharing',
  ],
  adminNotes: [
    'IT action: document L-drive admin, expiry, and expansion (IT important actions).',
    'Julia Casado historically requested access — contact UH IT helpdesk for renewal details.',
  ],
};

/** cPouta VM volume rules — moved from Computational Hub → Conda → Storage Management */
export const CPOUTA_VOLUME_RULES = [
  { rule: 'Home directory', detail: '/home/username — configs, git repos, lightweight scripts only. No large data.' },
  { rule: 'Data volume', detail: '/data — all active raw slides, packages, stitching output (2 TB NFS on farkkila-gpu1).' },
  { rule: 'Personal workspace', detail: 'mkdir -p /data/$USER — create your own folder on the shared volume.' },
  { rule: 'Symlink pattern', detail: 'mv ~/large_dataset /data/$USER/ then ln -s /data/$USER/large_dataset ~/large_dataset' },
  { rule: 'Disk audit', detail: 'du -sh /data/$USER and df -h to monitor usage; conda clean -a to free root disk.' },
];

export const STORAGE_CONTACTS = {
  it_specialist: { label: 'IT Specialist (storage)', people: ['Deb', 'Joonas'] },
  csc_compute: { label: 'CSC compute & Allas', people: ['Deb', 'Iga'] },
  uh_it: { label: 'UH IT helpdesk', people: ['UH IT helpdesk'] },
};

export const PROJECT_STORAGE_WORKFLOW = [
  {
    status: 'Active',
    destination: 'CSC Allas',
    detail: 'Working datasets for ongoing analysis — large imaging, omics intermediates.',
    sources: ['P-drive', 'L-drive', 'external disks', 'local workstations'],
  },
  {
    status: 'Inactive / Published',
    destination: 'UH Databank',
    detail: 'Long-term pseudonymized archive — especially raw t-CycIF and published project outputs.',
    sources: ['P-drive', 'L-drive', 'Allas', 'external disks'],
  },
];

export const FAIR_RESPONSIBILITIES = [
  'Keep data Findable, Accessible, Interoperable, Reusable (FAIR) — see onboarding doc FAIR data and documentation.',
  'Store sensitive clinical data only on approved systems (L-drive, HUH pipelines).',
  'Do regular backups; participate in lab cleaning days.',
  'Add README files to every project folder with dates in file names.',
  'On outboarding: transfer Google Drive folder ownership to farkkilalab@gmail.com.',
];

export const ONBOARDING_STORAGE_RESOURCES = [
  { label: 'Guidelines about data organisation', doc: 'Google Drive / onboarding', section: 'overview_onboarding' },
  { label: 'Network_drives_and_datacloud', doc: 'Folder layout for P-drive, L-drive, DataCloud', section: 'overview_onboarding' },
  { label: 'IT_inventory_computers_and_drives', doc: 'Laptops, workstations, external disks', section: 'overview_onboarding' },
  { label: 'CSC_resources', doc: 'CSC account, Allas, Puhti/Mahti/LUMI access', section: 'overview_onboarding' },
  { label: 'FAIR data and documentation 12022025', doc: 'FAIR principles for lab outputs', section: 'overview_onboarding' },
];

export const SENSITIVITY_RULES = [
  {
    level: 'Sensitive / clinical',
    stores: ['L-drive', 'DataCloud (restricted areas)', 'HUH Datalake / OVCA database'],
    guidance: 'Patient-identifiable or clinical exports. Oncosys-OVA confidentiality required.',
  },
  {
    level: 'Non-sensitive active',
    stores: ['P-drive', 'DataCloud /farkkila/', 'CSC Allas', 'Google Drive (project docs)'],
    guidance: 'General project files, presentations, protocols, analysis without direct identifiers.',
  },
  {
    level: 'Published / cold archive',
    stores: ['UH Databank', 'cold-storage external disks'],
    guidance: 'Pseudonymized data kept after publication or project closure.',
  },
];

export const LAB_STORAGE_SYSTEMS = [
  {
    id: 'l_drive',
    name: 'L-drive',
    shortName: 'L-drive',
    category: 'network',
    provider: 'University of Helsinki',
    role: 'Sensitive & clinical research storage (separate from CSC Allas)',
    capacityTb: null,
    capacityLabel: 'UH clinical quota',
    capacityVerified: false,
    extendable: true,
    extendNote: 'Not the same as Allas (~30 TB). Expansion via UH IT helpdesk (Deb/Joonas).',
    sensitivity: 'high',
    paths: ['L:\\ltdk_farkkila\\', 'L:\\ltdk_farkkila\\Projects\\'],
    access: 'UH network or VPN; restricted to approved users',
    contacts: ['Deb', 'Joonas', 'UH IT helpdesk'],
    useFor: [
      'Oncosys-OVA and clinical cohort data',
      'Patient-linked exports and sensitive imaging',
      'Data that must stay on UH-controlled storage',
    ],
    notFor: ['Casual sharing; non-clinical scratch data without access review'],
    notes: [
      'Distinct from CSC Allas (~30 TB) — L-drive is UH network clinical storage.',
      'Example: L:\\ltdk_farkkila\\Projects\\12-SPACE\\ clinical CSV exports.',
      'IT action: document admin, expiry, and expansion with UH IT helpdesk.',
    ],
    sources: ['IT important actions.docx', 'Role description IT Specialist', 'Dry lab cleaning day 251205'],
    urls: [],
    icon: 'network',
  },
  {
    id: 'p_drive',
    name: 'P-drive',
    shortName: 'P-drive',
    category: 'network',
    provider: 'University of Helsinki (Oncosys / lab shares)',
    role: 'Active project file storage — all lab P-drive shares combined',
    capacityTb: 80,
    capacityLabel: '~80 TB total',
    capacityVerified: false,
    extendable: true,
    extendNote: '~80 TB across all Oncosys / lab P-drive trees; per-project sub-quotas may apply.',
    sensitivity: 'medium',
    paths: ['P:\\… (Oncosys / farkkila shares)', 'Project trees synced with DataCloud where applicable'],
    access: 'UH network or VPN; project-folder permissions',
    contacts: ['Deb', 'Joonas'],
    useFor: [
      'Active dry-lab project folders and large imaging outputs',
      'Day-to-day analysis files when clinical sensitivity is not required',
      'Sync target when working offline (planned Dropbox-like sync — IT backlog)',
    ],
    notFor: ['Uncontrolled clinical identifiers without L-drive policy'],
    notes: [
      'Lab total ~80 TB across all P-drive shares (Oncosys + project trees).',
      'Secondary research storage for CyCIF outputs and large imaging (PDRIVE_SETUP.md).',
      'Cleaning workflow inventories P-drive before Allas/Databank transfer.',
      'Planned: offline project-folder sync when internet drops (IT backlog).',
    ],
    sources: ['IT important actions.docx', 'Lab data cleaning day', 'Allas and Databank inventory'],
    urls: [],
    icon: 'network',
  },
  {
    id: 'datacloud',
    name: 'DataCloud',
    shortName: 'DataCloud',
    category: 'cloud',
    provider: 'University of Helsinki',
    role: 'Primary lab cloud file sharing (WebDAV)',
    capacityTb: 10,
    capacityLabel: '~10 TB lab allocation',
    capacityVerified: false,
    extendable: true,
    extendNote: 'UH DataCloud quota can be increased — contact IT / lab admin.',
    sensitivity: 'mixed',
    paths: ['/farkkila/', '/farkkila/Projects/', '/farkkila/LAB-ASSISTANT-PLATFORM'],
    access: 'Web UI, WebDAV (Cyberduck, rclone); UH credentials',
    contacts: ['Deb', 'Joonas'],
    useFor: [
      'Protocols, presentations, posters, shared project trees',
      'Canonical path for lab assistant platform mirror',
      'Collaboration with UH and external partners via shared links',
    ],
    notFor: ['Replacing CSC Allas for huge HPC datasets; unrestricted clinical exports'],
    notes: [
      'WebDAV URL for rclone: https://datacloud.helsinki.fi/remote.php/webdav/',
      'Use DataCloud app password (not university password) for WebDAV clients.',
      'Server-to-server copy example: rclone copy allas:bucket/ datacloud:farkkila/project/',
    ],
    sources: ['docs/15_STORAGE_MASTER_PLAN.md', 'configs/DATACLOUD_WEBDAV_SETUP.md', 'IT Specialist role'],
    urls: [
      { label: 'DataCloud portal', href: 'https://datacloud.helsinki.fi' },
      { label: 'Lab wiki — IT inventory', href: 'https://wiki.helsinki.fi/xwiki/bin/view/FL/Farkkila%20Lab/IT%20Infrastructure/Inventory/' },
    ],
    icon: 'cloud',
  },
  {
    id: 'google_drive',
    name: 'Google Drive',
    shortName: 'Google Drive',
    category: 'cloud',
    provider: 'Google Workspace (farkkilalab@gmail.com)',
    role: 'Project documentation, logs, onboarding, collaboration',
    capacityTb: null,
    capacityLabel: 'Workspace quota (shared lab account)',
    capacityVerified: false,
    extendable: true,
    extendNote: 'Archive inactive projects under Projects → ARCHIVE during cleaning days.',
    sensitivity: 'medium',
    paths: ['Projects/', 'ARCHIVE/', 'Onboarding documents'],
    access: 'Google account; shared drives/folders per project',
    contacts: ['Deb', 'Joonas', 'Anniina (project logs)'],
    useFor: [
      'Living project logs and lightweight documentation',
      'Onboarding / wet-lab instruction folders',
      'GitHub-adjacent workflow docs and handover material',
    ],
    notFor: ['Primary store for multi-TB raw imaging — use P-drive, Allas, or Databank'],
    notes: [
      'Cleaning day: revise project status and archive inactive projects.',
      'FAIR project organisation guidelines apply across Drive and network storage.',
    ],
    sources: ['Dry lab cleaning day 251205', 'Role description IT Specialist', 'Lab manager onboarding'],
    urls: [],
    icon: 'cloud',
  },
  {
    id: 'allas',
    name: 'CSC Allas',
    shortName: 'Allas',
    category: 'csc',
    provider: 'CSC — Färkkilä lab project',
    role: 'Active project object storage (S3-compatible)',
    capacityTb: 30,
    capacityLabel: '~30 TB',
    capacityVerified: false,
    extendable: true,
    extendNote: 'Lab allocation ~30 TB, extendable via CSC project billing. Monitor and clean with Deb/Iga.',
    sensitivity: 'medium',
    paths: ['allas://project-buckets/…'],
    access: 'CSC account + project membership; rclone / a-commands',
    contacts: ['Deb', 'Iga', 'Joonas'],
    useFor: [
      'Active large datasets staged for Puhti/Mahti/LUMI analysis',
      'Intermediate imaging and omics between network drives and HPC',
    ],
    notFor: ['Long-term published archive — use UH Databank'],
    notes: [
      'Workflow rule: Active projects → Allas (see cleaning inventory spreadsheet).',
      'CSC project example: project_462001415 — request access via MyCSC.',
      'LUMI uses Lumi-O (S3) for object storage; configure via allas-conf --lumi.',
      'Puhti is being phased out — migrate datasets to LUMI/Roihu (Computational Hub).',
      'Transfer guides in Computational Hub → File operations.',
    ],
    sources: ['Allas and Databank data upload inventory.xlsx', 'Dry lab cleaning day', 'IT important actions'],
    urls: [
      { label: 'CSC Allas docs', href: 'https://docs.csc.fi/data/Allas/' },
    ],
    icon: 'archive',
  },
  {
    id: 'databank',
    name: 'UH Databank',
    shortName: 'Databank',
    category: 'cloud',
    provider: 'University of Helsinki',
    role: 'Long-term pseudonymized research archive (UH frozen store)',
    capacityTb: null,
    capacityLabel: 'UH quota',
    capacityVerified: false,
    extendable: true,
    extendNote: 'University frozen storage (typically 5–15 years); confirm quota with UH IT.',
    sensitivity: 'low',
    paths: ['UH Databank archive paths (IT-coordinated)'],
    access: 'UH Databank service; coordinated upload via UH IT',
    contacts: ['Deb', 'Joonas'],
    useFor: [
      'Inactive and published project data',
      'Large t-CycIF raw archives (pseudonymized)',
      'Cold storage after cleaning-day preparation',
    ],
    notFor: ['Active daily scratch — use DataCloud, P-drive, or CSC Allas'],
    notes: [
      'Workflow rule: Inactive / Published → UH Databank.',
      'Pair with DataCloud for active sharing; migrate finished datasets when projects close.',
      'Priority on cleaning days: prepare raw t-CycIF for transfer.',
    ],
    sources: ['Dry lab cleaning day 251205', 'Allas and Databank inventory'],
    urls: [
      { label: 'UH research storage help', href: 'https://helpdesk.it.helsinki.fi/en/saving-and-sharing/resources-research' },
    ],
    icon: 'archive',
  },
  {
    id: 'cpouta_nfs',
    name: 'cPouta shared NFS (/data)',
    shortName: 'cPouta /data',
    category: 'local',
    provider: 'CSC cPouta VMs (farkkila-gpu1 / cpu1 / cpu2)',
    role: 'Shared 2 TB active scratch on lab cloud VMs',
    capacityTb: 2,
    capacityLabel: '2 TB NFS',
    capacityVerified: true,
    extendable: false,
    sensitivity: 'medium',
    paths: ['/data on farkkila-gpu1 (NFS server)', 'Mounted on farkkila-cpu1 and farkkila-cpu2'],
    access: 'SSH to cPouta VMs; coordinate in Slack #csc-pouta-and-workstations-users',
    contacts: ['Deb', 'Iga'],
    useFor: [
      'Active raw slide files, stitching output, and packages on GPU/CPU VMs',
      'Short-term shared scratch between farkkila-gpu1, cpu1, and cpu2',
    ],
    notFor: ['Long-term archive — copy finished datasets to Allas or Databank'],
    notes: [
      'Home /home — configs only; all data under /data/$USER on the 2 TB NFS volume.',
      'NFS exported from farkkila-gpu1; cpu1/cpu2 mount as clients (/etc/exports).',
      'Symlink large folders from /data to home; run du -sh and df -h regularly.',
    ],
    sources: ['Bioinformatics Hub — cPouta VM specs', 'Onboarding — workstation guidelines'],
    urls: [{ label: 'CSC cPouta', href: 'https://docs.csc.fi/cloud/pouta/' }],
    icon: 'local',
  },
  {
    id: 'local_workstations',
    name: 'Lab workstations & cpu1-data',
    shortName: 'Local storage',
    category: 'local',
    provider: 'In-lab Linux/macOS workstations + Biomedicum desktops',
    role: 'Scratch and analysis staging — not canonical archive',
    capacityTb: null,
    capacityLabel: 'Per machine',
    capacityVerified: true,
    extendable: false,
    sensitivity: 'mixed',
    paths: ['cpu1-data/', 'local ~/project folders', 'Biomedicum lab desktops'],
    access: 'Physical lab machines; SSH where configured; Slack #csc-pouta-and-workstations-users',
    contacts: ['Deb', 'Iga'],
    useFor: ['Temporary analysis', 'Staging before upload to network/cloud storage'],
    notFor: ['Only copy of irreplaceable data'],
    notes: [
      'Cleaning day: remove unnecessary data from computers and cpu1-data.',
      'Workstation list and responsible people: Google Drive IT inventory + onboarding doc.',
      'Heavy compute: prefer CSC Puhti/Mahti/LUMI or cPouta VMs over personal laptop storage.',
    ],
    sources: ['Lab data cleaning day', 'Färkkilä Lab ONBOARDING', 'Bioinformatics Hub'],
    urls: [
      { label: 'IT inventory (wiki)', href: 'https://wiki.helsinki.fi/xwiki/bin/view/FL/Farkkila%20Lab/IT%20Infrastructure/Inventory/' },
    ],
    icon: 'local',
  },
  {
    id: 'external_disks',
    name: 'External & cold-storage disks',
    shortName: 'External disks',
    category: 'local',
    provider: 'Lab-owned USB / HDD arrays',
    role: 'Cold storage, GeoMx export, legacy project copies',
    capacityTb: null,
    capacityLabel: 'Per disk (track in wiki inventory)',
    capacityVerified: false,
    extendable: true,
    extendNote: 'Register every disk in wiki inventory; return unused cables/hubs to IT.',
    sensitivity: 'mixed',
    paths: ['Tagged cold-storage disks', 'GeoMx USB exports (≤10 TB per device)'],
    access: 'Physical custody; label and log location',
    contacts: ['Deb'],
    useFor: [
      'Legacy archives pending Allas/Databank migration',
      'Instrument exports (GeoMx recommends ≤10 TB external drives)',
    ],
    notFor: ['Untracked long-term storage — must be inventoried'],
    notes: [
      'Cleaning day: locate missing disks; compress cold-storage raw/intermediate data.',
      'GeoMx manual: external drives NTFS/exFAT, USB 3.0, max ~10 TB.',
    ],
    sources: ['Lab data cleaning day', 'GeoMx DSP manual (processed TLS.json)'],
    urls: [],
    icon: 'local',
  },
  {
    id: 'huh_datalake',
    name: 'HUH Datalake / OVCA database',
    shortName: 'HUH clinical DB',
    category: 'clinical',
    provider: 'Helsinki University Hospital',
    role: 'Secure clinical identifiers & biobank-linked records',
    capacityTb: null,
    capacityLabel: 'Hospital-controlled',
    capacityVerified: true,
    sensitivity: 'high',
    paths: ['OVCA-Database on HUH server', 'Helsinki Biobank Datalake'],
    access: 'Authorized personnel only; NDA / study agreements',
    contacts: ['Clinical Research Coordinator', 'Anniina', 'Lab manager'],
    useFor: ['Anonymous clinical processing pipelines', 'Linking approved study IDs'],
    notFor: ['Names, SSIDs, or diagnosis dates in exports'],
    notes: ['Clinical data also stored on L-drive and DataCloud under strict access rules.'],
    sources: ['ONCOSYS onboarding materials', 'Research materials overview'],
    urls: [],
    icon: 'shield',
  },
];

export const TRANSFER_TOOLS = [
  {
    id: 'rclone',
    name: 'rclone',
    use: 'Primary tool: workstation ↔ Allas, Allas ↔ DataCloud, LUMI scratch ↔ Lumi-O buckets',
    where: 'Full config snippets in Computational Hub → Utilities → File operations',
    nav: { main: 'computational', sub: 'utilities' },
    tips: ['Use tmux for long uploads to avoid SSH timeout', 'Datacloud remote: webdav + nextcloud vendor'],
  },
  {
    id: 'lumi_o',
    name: 'Lumi-O (S3 on LUMI)',
    use: 'Object storage on LUMI supercomputer — allas-conf --lumi, rclone lumi-o:',
    where: 'Computational Hub → LUMI HPC → Lumi-O transfers',
    nav: { main: 'computational', sub: 'lumi' },
    tips: ['Bucket names: lowercase, numbers, hyphens only', 'Use --s3-chunk-size=128M for large WSIs'],
  },
  {
    id: 'allas_conf',
    name: 'allas-conf / a-commands',
    use: 'Configure Allas S3 keys on Puhti/Mahti; list and copy buckets',
    where: 'module load allas && allas-conf -m s3',
    nav: { main: 'computational', sub: 'onboarding' },
  },
  {
    id: 'cyberduck',
    name: 'Cyberduck',
    use: 'GUI for Allas (OpenStack Swift on pouta.csc.fi:5001) and DataCloud WebDAV',
    where: 'Computational Hub → Utilities → File operations → Cyberduck',
    nav: { main: 'computational', sub: 'utilities' },
  },
  {
    id: 'rsync',
    name: 'rsync / scp',
    use: 'Direct transfer to LUMI scratch or cPouta VMs over SSH',
    where: 'Computational Hub → Utilities → File operations; target /scratch/project_462…/',
    nav: { main: 'computational', sub: 'utilities' },
  },
  {
    id: 'webdav',
    name: 'DataCloud WebDAV',
    use: 'Mount or sync /farkkila/ with app password',
    where: 'https://datacloud.helsinki.fi/remote.php/webdav/',
  },
  {
    id: 'git',
    name: 'Git / GitHub',
    use: 'Code and small derived artifacts — github.com/farkkilab',
    where: 'Not for multi-TB raw imaging; pair with Allas/Databank for data',
  },
];

export const CSC_HPC_STORAGE_NOTES = [
  'Scratch on LUMI: /scratch/project_462XXXXXX/username/ — temporary, not archived.',
  'Applications: /projappl/project_462XXXXXX/ — binaries and containers.',
  'Completed WSI datasets → Allas project buckets with metadata.',
  'Puhti → LUMI/Roihu migration in progress — move data early.',
];

export const REFERENCE_DOCUMENTS = [
  {
    title: 'IT important actions',
    context: 'L-drive admin, P-drive sync goals, Allas monitoring',
    section: 'overview_personnel',
  },
  {
    title: 'Dry lab cleaning day 251205',
    context: 'Allas vs Databank rules, Google Drive archive, disk inventory',
    section: 'overview_cleaning',
  },
  {
    title: 'Allas and Databank data upload inventory',
    context: 'Per-project storage location spreadsheet',
    section: 'overview_cleaning',
  },
  {
    title: 'Role description — IT Specialist',
    context: 'Ownership of all storage services',
    section: 'overview_personnel',
  },
  {
    title: 'Färkkilä Lab ONBOARDING — Storage section',
    context: 'FAIR principles, IT inventory, Network_drives_and_datacloud, CSC_resources',
    section: 'overview_onboarding',
  },
  {
    title: 'FAIR data and documentation',
    context: 'How lab results should be documented and stored',
    section: 'overview_onboarding',
  },
  {
    title: 'IT outboarding — data handover',
    context: 'Cold storage, READMEs, Google Drive ownership transfer on leaving',
    section: 'overview_onboarding',
  },
];

export function getSystemsByCategory(category) {
  return LAB_STORAGE_SYSTEMS.filter((s) => s.category === category);
}

export function getStorageById(id) {
  return LAB_STORAGE_SYSTEMS.find((s) => s.id === id);
}

/** Sum of lab-reported major allocations (P-drive + CSC + DataCloud). Excludes L-drive quota and VM scratch. */
export function getLabAllocatedCapacityTb() {
  return ['p_drive', 'allas', 'databank', 'datacloud'].reduce(
    (sum, id) => sum + (getStorageById(id)?.capacityTb ?? 0),
    0,
  );
}

export function getTotalVerifiedCapacityTb() {
  return getLabAllocatedCapacityTb();
}
