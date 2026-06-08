/**
 * Tab-scoped storage reference — each section maps to a Data & Storage nav tab.
 * Lab-specific facts from corpus + general service documentation (CSC, UH, Nextcloud).
 */

export const LANDSCAPE_CONTENT = {
  intro:
    'Overview of where Färkkilä Lab data lives. Use the tabs above for full detail on each system — this page is the map, not the manual.',
  principles: [
    'Sensitive clinical data → L-drive or HUH-controlled systems only.',
    'Active project files → P-drive, DataCloud, or CSC Allas depending on size and compute needs.',
    'Published or inactive pseudonymized archives → UH Databank.',
    'Never keep the only copy on a laptop, external disk, or HPC scratch.',
    'Every project folder needs a README with dates in filenames (FAIR / cleaning-day rule).',
  ],
  decisionMatrix: [
    {
      question: 'Patient-linked or clinical export?',
      answer: 'L-drive',
      tab: 'network_drives',
      bullets: ['UH network + VPN', 'Not CSC Allas'],
      example: 'Oncosys-OVA cohort CSVs',
    },
    {
      question: 'Large active imaging / omics on UH network?',
      answer: 'P-drive',
      tab: 'network_drives',
      bullets: ['~80 TB combined lab shares', 'CyCIF outputs, WSI trees'],
    },
    {
      question: 'Protocols, posters, shared docs with partners?',
      answer: 'DataCloud',
      tab: 'datacloud',
      bullets: ['WebDAV /farkkila/', '~10 TB lab allocation'],
    },
    {
      question: 'Multi-TB dataset for Puhti/LUMI analysis?',
      answer: 'CSC Allas',
      tab: 'cloud_archive',
      bullets: ['~30 TB object storage', 'Stage before Puhti/LUMI jobs'],
    },
    {
      question: 'Project finished or published — long-term archive?',
      answer: 'UH Databank',
      tab: 'datacloud',
      bullets: ['University frozen store', 'Pseudonymized datasets', 'Especially raw t-CycIF'],
    },
    {
      question: 'Project log, onboarding doc, lightweight collaboration?',
      answer: 'Google Drive',
      tab: 'google_drive',
      bullets: ['Project logs and onboarding docs', 'Archive inactive projects under ARCHIVE/'],
    },
    {
      question: 'Temporary analysis on lab machine or cPouta VM?',
      answer: 'Local / cPouta',
      tab: 'local_storage',
      bullets: ['Scratch only', 'Migrate canonical data upward when done'],
    },
    {
      question: 'Moving data between systems?',
      answer: 'Transfer tools',
      tab: 'tools',
      bullets: ['rclone, rsync, Cyberduck', 'Commands in Computational Hub'],
    },
  ],
  systemMap: [
    { id: 'l_drive', tab: 'network_drives', label: 'L-drive', capacity: 'UH quota', role: 'Sensitive clinical' },
    { id: 'p_drive', tab: 'network_drives', label: 'P-drive', capacity: '~80 TB', role: 'Active project trees' },
    { id: 'datacloud', tab: 'datacloud', label: 'DataCloud', capacity: '~10 TB', role: 'UH WebDAV sharing' },
    { id: 'databank', tab: 'datacloud', label: 'UH Databank', capacity: 'UH quota', role: 'Long-term UH archive' },
    { id: 'allas', tab: 'cloud_archive', label: 'CSC Allas', capacity: '~30 TB', role: 'Active object storage (CSC)' },
    { id: 'google_drive', tab: 'google_drive', label: 'Google Drive', capacity: 'Shared', role: 'Docs & logs' },
    { id: 'cpouta_nfs', tab: 'local_storage', label: 'cPouta /data', capacity: '2 TB', role: 'VM scratch' },
    { id: 'local_workstations', tab: 'local_storage', label: 'Workstations', capacity: 'Per machine', role: 'Staging only' },
  ],
};

export const NETWORK_DRIVES_CONTENT = {
  intro:
    'University of Helsinki network drives mapped as L: and P: on Windows (or equivalent mount on macOS/Linux over VPN). L-drive is for sensitive clinical work; P-drive is bulk active research storage.',
  lDriveSections: [
    {
      title: 'What L-drive is',
      items: [
        'UH-managed network storage for sensitive and clinical research data.',
        'Distinct from CSC Allas (~30 TB) — do not confuse the two systems.',
        'Access is restricted; renewal and quota changes go through UH IT helpdesk.',
        'Used heavily by Oncosys-OVA and SPACE projects for clinical-linked exports.',
      ],
    },
    {
      title: 'Paths & examples',
      items: [
        'Lab root: L:\\ltdk_farkkila\\ and L:\\ltdk_farkkila\\Projects\\',
        'SPACE clinical batch: L:\\ltdk_farkkila\\Projects\\12-SPACE\\SPACE_OncosysOva_ClinicalData_Batch_all.csv',
        'Oncosys-OVA: clinical + imaging metadata alongside DataCloud for controlled sharing.',
      ],
    },
    {
      title: 'Access & VPN',
      items: [
        'Requires UH network or VPN when working off-campus.',
        'Permissions are per-folder; request access via lab admin (Deb/Joonas) or UH IT.',
        'Document admin contacts, access expiry, and expansion process (IT action item).',
        'Julia Casado access renewal — confirm current status with UH IT helpdesk.',
      ],
    },
    {
      title: 'Clinical data pairing',
      items: [
        'Oncosys-OVA stores sensitive material on L-drive and DataCloud under strict access.',
        'Anonymous processing uses HUH Datalake / OVCA-Database — see Local & disks tab.',
        'Never put patient identifiers on P-drive, Google Drive, or unencrypted Allas without review.',
      ],
    },
  ],
  pDriveSections: [
    {
      title: 'What P-drive is',
      items: [
        'UH/Oncosys project shares for active dry-lab data — approximately 80 TB total across all lab trees.',
        'Primary non-sensitive bulk store for large imaging (t-CycIF, WSI) and omics intermediates.',
        'Secondary research storage for CyCIF pipeline outputs (see configs/PDRIVE_SETUP.md).',
        'Individual project folders may have sub-quotas within the overall allocation.',
      ],
    },
    {
      title: 'Folder layout & Oncosys',
      items: [
        'Oncosys consortium P-drive trees mirror consortium project structure.',
        'Per-project folders may sync or mirror to DataCloud /farkkila/Projects/ where applicable.',
        'Inventory every project on cleaning days before Allas/Databank migration.',
        'Planned IT improvement: selective offline sync of one project folder when internet drops.',
      ],
    },
    {
      title: 'Mounting & dev setup',
      items: [
        'Workstation: map P: via UH instructions when on network or VPN.',
        'macOS example mount: /Volumes/pdrive — set PDRIVE_MOUNT_PATH in configs/.env.',
        'PDRIVE_ENABLED=true, PDRIVE_LOGICAL_ROOT=pdrive:// for app connector reads.',
        'Connector is read-only scan/list — no delete or move via API.',
      ],
    },
    {
      title: 'Lab practices',
      items: [
        'Zip and stage before large transfers; prefer rclone for DataCloud ↔ network workflows.',
        'Cleaning day: list P-drive contents in Allas/Databank inventory spreadsheet.',
        'Do not treat P-drive as long-term archive — move inactive data to Databank.',
        'GeoMx and instrument exports may land here temporarily before cloud upload.',
      ],
    },
  ],
  comparisonTable: [
    { aspect: 'Primary role', lDrive: 'Sensitive / clinical UH data', pDrive: 'Active project bulk files' },
    { aspect: 'Capacity', lDrive: 'UH quota (not fixed TB)', pDrive: '~80 TB lab total' },
    { aspect: 'Provider', lDrive: 'University of Helsinki IT', pDrive: 'UH / Oncosys shares' },
    { aspect: 'vs CSC Allas', lDrive: 'Completely different system', pDrive: 'Complementary — network vs object store' },
    { aspect: 'Access', lDrive: 'Restricted, IT helpdesk', pDrive: 'Project-folder permissions' },
    { aspect: 'Typical data', lDrive: 'Clinical CSVs, cohort exports', pDrive: 'WSI, t-CycIF raw, analysis outputs' },
  ],
  externalLinks: [
    { label: 'UH IT — Resources for research', href: 'https://helpdesk.it.helsinki.fi/en/saving-and-sharing/resources-research' },
    { label: 'Lab wiki — IT inventory', href: 'https://wiki.helsinki.fi/xwiki/bin/view/FL/Farkkila%20Lab/IT%20Infrastructure/Inventory/' },
  ],
};

export const DATACLOUD_CONTENT = {
  intro:
    'University of Helsinki provides both DataCloud (active sharing) and Databank (long-term frozen archive). DataCloud is a Nextcloud-based service — the lab uses ~10 TB under /farkkila/ for protocols, project trees, and platform mirrors. Databank is the UH cold-store for published or inactive pseudonymized datasets.',
  sections: [
    {
      title: 'Service overview',
      items: [
        'UH research data storage with Nextcloud UI, mobile apps, and WebDAV access.',
        'Institution-wide Ceph backend — suitable for non-sensitive research data at scale.',
        'Not a scratch disk: files are synced/copied, not edited in place like HPC scratch.',
        'Contact for quota: datacloud@helsinki.fi; lab admin: Deb/Joonas.',
      ],
    },
    {
      title: 'Lab folder structure',
      items: [
        '/farkkila/ — lab group root shared space.',
        '/farkkila/Projects/ — per-project trees (e.g. Virtual_TMAs, SPACE).',
        '/farkkila/LAB-ASSISTANT-PLATFORM — canonical mirror for OMEIA platform assets.',
        'Public share links possible for external collaborators (email-based access).',
      ],
    },
    {
      title: 'WebDAV access',
      items: [
        'WebDAV URL: https://datacloud.helsinki.fi/remote.php/webdav/',
        'Use a Nextcloud app password — not your university login password.',
        'Create app password: DataCloud → Settings → Security → Devices & sessions.',
        'rclone: storage=webdav, vendor=nextcloud, user=<username>, pass=<app password>.',
        'Cyberduck: WebDAV connection with same credentials for GUI browsing.',
      ],
    },
    {
      title: 'rclone workflows',
      items: [
        'Server-to-server: rclone copy allas:bucket-name/ datacloud:farkkila/project/ -P',
        'Use tmux for long uploads to survive SSH disconnects.',
        'Tune --transfers and --tpslimit for DataCloud rate limits on large batches.',
        'Full config snippets: Computational Hub → File operations.',
      ],
    },
    {
      title: 'Platform integration',
      items: [
        'Backend connector: datacloud_webdav (credentials in configs/.env only).',
        'Logical paths exposed to UI — never raw WebDAV URLs in frontend.',
        'Verify: GET /api/storage/datacloud/list and connectors/status endpoint.',
      ],
    },
    {
      title: 'When to use / avoid',
      items: [
        'Use: protocols, presentations, posters, shared docs, moderate-size project trees.',
        'Use: collaboration with UH and external partners via controlled shares.',
        'Avoid: primary store for multi-TB raw WSI — use P-drive or Allas.',
        'Avoid: unrestricted clinical identifiers — pair with L-drive policy.',
        'Avoid: HPC scratch replacement — copy to Allas for compute pipelines.',
      ],
    },
  ],
  databankSections: [
    {
      title: 'What UH Databank is (lab usage)',
      items: [
        'University of Helsinki long-term frozen storage for inactive and published pseudonymized research data.',
        'Workflow rule: Inactive / Published projects → UH Databank (cleaning day 251205).',
        'Priority transfers: raw t-CycIF archives after pseudonymization review.',
        'Coordinated uploads via UH IT — not daily scratch; pair with inventory spreadsheet.',
      ],
    },
    {
      title: 'Preparing data for Databank',
      items: [
        'Pseudonymize and remove direct identifiers before archive transfer.',
        'Include README, file naming with dates, and project metadata.',
        'Compress where sensible; verify checksums after upload.',
        'Document path in Databank inventory spreadsheet alongside DataCloud shares.',
      ],
    },
    {
      title: 'UH Databank vs Fairdata DPS',
      items: [
        'UH Databank (lab workflow): UH frozen store (typically 5–15 years) for UH-produced datasets.',
        'Fairdata Digital Preservation Service: century-scale preservation via partner org agreement.',
        'For lab cleaning days, primary cold target is UH Databank unless archivist directs otherwise.',
        'Active sharing and staging stay on DataCloud — migrate finished datasets to Databank when inactive.',
      ],
    },
  ],
  externalLinks: [
    { label: 'DataCloud portal', href: 'https://datacloud.helsinki.fi' },
    { label: 'UH Think Open — DataCloud intro', href: 'https://blogs.helsinki.fi/thinkopen/high-capacity-research-storage-and-sharing-available-for-research-in-2020/' },
    { label: 'Nextcloud WebDAV manual', href: 'https://docs.nextcloud.com/server/stable/user_manual/en/files/access_webdav.html' },
    { label: 'UH research storage help', href: 'https://helpdesk.it.helsinki.fi/en/saving-and-sharing/resources-research' },
    { label: 'Fairdata digital preservation', href: 'https://www.fairdata.fi/en/dps-for-research-data/' },
  ],
};

export const ALLAS_CONTENT = {
  intro:
    'CSC Allas is object storage for active datasets staged before Puhti/LUMI analysis. Lab allocation ~30 TB, extendable via CSC project billing. Distinct from UH DataCloud and Databank — provided by CSC, not the University.',
  sections: [
    {
      title: 'What Allas is',
      items: [
        'CSC general-purpose object storage — data stored as objects in buckets (S3 or Swift APIs).',
        'Best for write-once, read-many datasets: static or growing archives analyzed on HPC.',
        'Lab project example: project_462001415 — request access via MyCSC portal.',
        'Quota is per CSC project; monitor usage with Deb/Iga during cleaning days.',
      ],
    },
    {
      title: 'Buckets & naming',
      items: [
        'One bucket = top-level container; pseudo-folders via / in object names.',
        'Use consistent bucket names per project; document in cleaning inventory spreadsheet.',
        'LUMI uses Lumi-O (separate S3) — configure with allas-conf --lumi on LUMI.',
        'Bucket names on Lumi-O: lowercase, numbers, and hyphens only.',
      ],
    },
    {
      title: 'S3 vs Swift',
      items: [
        'Swift recommended on Puhti/Mahti shared systems (temporary tokens, better supported).',
        'S3 uses permanent keys — practical for cPouta VMs and personal laptops; security trade-off.',
        'Do not mix protocols for large split objects — upload and download with same protocol.',
        'Endpoint for S3: a3s.fi. Configure via module load allas && allas-conf -m s3.',
      ],
    },
    {
      title: 'Lab workflow',
      items: [
        'Active projects → Allas (cleaning day rule).',
        'Stage P-drive or L-drive exports to Allas before Puhti/LUMI jobs.',
        'Completed WSI → Allas buckets with README metadata, then UH Databank when inactive.',
        'Puhti being phased out — migrate datasets to LUMI/Roihu early.',
      ],
    },
    {
      title: 'Access tools',
      items: [
        'allas-conf — generates rclone, s3cmd, aws config on CSC machines.',
        'a-commands — Swift-based CLI on Puhti/Mahti (module load allas).',
        'rclone — primary cross-service copy (Allas ↔ DataCloud ↔ Lumi-O).',
        'Web UI: allas.csc.fi and Open OnDemand file browsers on LUMI.',
      ],
    },
  ],
  hpcSections: [
    {
      title: 'HPC storage layers (not the same as Allas)',
      items: [
        'LUMI scratch: /scratch/project_462XXXXXX/username/ — temporary, purged, not archived.',
        'LUMI projappl: /projappl/project_462XXXXXX/ — binaries and containers.',
        'Lumi-O: object storage on LUMI — use for durable copies off scratch.',
        'Copy scratch → Allas or Lumi-O before job end; never assume scratch persists.',
      ],
    },
  ],
  externalLinks: [
    { label: 'CSC Allas documentation', href: 'https://docs.csc.fi/data/Allas/' },
    { label: 'CSC Allas service description', href: 'https://research.csc.fi/allas-service-description/' },
    { label: 'allas-conf configuration', href: 'https://docs.csc.fi/data/Allas/using_allas/allas-conf/' },
    { label: 'MyCSC portal', href: 'https://my.csc.fi' },
  ],
};

/** @deprecated Use ALLAS_CONTENT — kept for any stale imports */
export const CLOUD_ARCHIVE_CONTENT = ALLAS_CONTENT;

export const GOOGLE_DRIVE_CONTENT = {
  intro:
    'Google Workspace (farkkilalab@gmail.com) for living documentation, project logs, and onboarding — not for multi-terabyte raw imaging.',
  sections: [
    {
      title: 'Folder structure',
      items: [
        'Projects/ — active project logs and lightweight working documents.',
        'ARCHIVE/ — inactive or completed projects moved during cleaning days.',
        'Onboarding documents — wet-lab instructions, role descriptions, IT inventory links.',
        'Mirror critical paths in network storage; Drive is not the canonical imaging store.',
      ],
    },
    {
      title: 'What belongs on Drive',
      items: [
        'Project logs maintained by lab members (Anniina coordinates project documentation).',
        'Protocols, meeting notes, slide decks, and handover checklists.',
        'Links and pointers to data on P-drive, DataCloud, or Allas.',
        'GitHub-adjacent workflow documentation for code repos (github.com/farkkilab).',
      ],
    },
    {
      title: 'Cleaning & archive policy',
      items: [
        'Cleaning day: revise each project status — active vs inactive vs published.',
        'Move inactive projects under Projects/ → ARCHIVE/ with README noting archive date.',
        'Do not hoard duplicate multi-GB imaging on Drive; migrate to P-drive or Allas.',
        'FAIR organisation guidelines apply across Drive and all network storage.',
      ],
    },
    {
      title: 'Sharing & outboarding',
      items: [
        'Share folders with lab account or named collaborators — avoid public links for sensitive notes.',
        'On leaving the lab: transfer Google Drive folder ownership to farkkilalab@gmail.com.',
        'IT outboarding checklist covers cold storage handover and README requirements.',
        'Sensitive clinical material must not live on Drive — use L-drive.',
      ],
    },
    {
      title: 'General tips',
      items: [
        'Use consistent naming: YYYYMMDD in filenames for snapshots and exports.',
        'Prefer Google Docs/Sheets for living docs; export PDF snapshots for milestones.',
        'Link to wiki inventory for hardware and disk tracking.',
      ],
    },
  ],
  externalLinks: [
    { label: 'Lab wiki — IT inventory', href: 'https://wiki.helsinki.fi/xwiki/bin/view/FL/Farkkila%20Lab/IT%20Infrastructure/Inventory/' },
    { label: 'Färkkilä Lab GitHub', href: 'https://github.com/farkkilab' },
  ],
};

export const LOCAL_STORAGE_CONTENT = {
  intro:
    'Scratch and staging on lab machines, cPouta VMs, and external disks. Canonical data must live on network or CSC storage; HUH clinical systems are separate.',
  workstationSections: [
    {
      title: 'Lab workstations & cpu1-data',
      items: [
        'Biomedicum desktops and linux workstations (cpu1-data/) for temporary analysis.',
        'Not canonical archive — copy finished datasets to P-drive, DataCloud, or Allas.',
        'Cleaning day: remove stale data from computers and cpu1-data shares.',
        'Workstation list and owners: Google Drive IT inventory + onboarding IT_inventory_computers_and_drives.',
        'Heavy compute: prefer CSC LUMI/Puhti or cPouta over personal laptop disks.',
      ],
    },
    {
      title: 'Slack & coordination',
      items: [
        'Channel: #csc-pouta-and-workstations-users for VM access and scratch coordination.',
        'Report full disks to Deb/Iga before jobs fail mid-run.',
      ],
    },
  ],
  cpoutaSections: [
    {
      title: 'VM fleet',
      items: [
        'farkkila-gpu1 — Ubuntu 16.04, CUDA, GPU pipelines & Avivator (128.214.253.252).',
        'farkkila-cpu1 — Ubuntu 18.04, Cyto App port 9999 (195.148.21.14).',
        'farkkila-cpu2 — Ubuntu 18.04, general CPU (195.148.21.26).',
        'Specs and provisioning: Computational Hub → cPouta Cloud VMs.',
      ],
    },
    {
      title: 'NFS /data volume (2 TB)',
      items: [
        'Persistent 2 TB mounted at /data on gpu1; cpu1/cpu2 NFS clients.',
        '/home — configs, git repos, scripts only. Never store large datasets in home.',
        '/data/$USER — personal workspace for raw slides, packages, stitching output.',
        'Symlink: mv ~/dataset /data/$USER/ && ln -s /data/$USER/dataset ~/dataset',
        'Audit: du -sh /data/$USER; df -h; conda clean -a to free root disk.',
      ],
    },
  ],
  externalDiskSections: [
    {
      title: 'External & cold-storage disks',
      items: [
        'Register every disk in wiki IT inventory — label, capacity, location, custodian.',
        'Legacy archives pending Allas/Databank migration; compress where possible on cleaning days.',
        'GeoMx DSP manual: USB 3.0, NTFS or exFAT, ≤10 TB per drive recommended.',
        'Return unused cables and hubs to IT; locate missing disks during inventory.',
      ],
    },
  ],
  clinicalSections: [
    {
      title: 'HUH Datalake & OVCA-Database',
      items: [
        'Hospital-controlled secure clinical identifiers and biobank-linked records.',
        'OVCA-Database on HUH server — anonymous processing pipelines for Oncosys-OVA.',
        'Accessible via Helsinki Biobank Datalake for authorized personnel only.',
        'Requires NDA / study agreements; clinical coordinator and lab manager gate access.',
        'Never export names, social security IDs, or raw diagnosis dates to open storage.',
        'Pairs with L-drive and restricted DataCloud areas for study workflows.',
      ],
    },
  ],
  externalLinks: [
    { label: 'CSC cPouta documentation', href: 'https://docs.csc.fi/cloud/pouta/' },
    { label: 'Lab wiki — IT inventory', href: 'https://wiki.helsinki.fi/xwiki/bin/view/FL/Farkkila%20Lab/IT%20Infrastructure/Inventory/' },
  ],
};

export const GUIDELINES_CONTENT = {
  intro:
    'How the lab decides where data lives, documents it, and moves it through active → archive lifecycle. Applies to cleaning days and everyday work.',
  workflowDetail: [
    {
      status: 'Active',
      destination: 'CSC Allas',
      steps: [
        'Confirm project is ongoing and data is accessed for analysis.',
        'Inventory sources: P-drive, L-drive (if pseudonymized), external disks, workstations.',
        'Upload to Allas bucket with README; document path in inventory spreadsheet.',
        'Use Allas as staging for LUMI/Puhti jobs — not scratch long-term.',
      ],
    },
    {
      status: 'Inactive / Published',
      destination: 'UH Databank',
      steps: [
        'Confirm pseudonymization and publication status with PI.',
        'Prepare raw t-CycIF and large imaging per cleaning-day priority list.',
        'Transfer from P-drive, L-drive, or Allas; verify checksums.',
        'Update inventory; remove redundant copies from scratch locations.',
      ],
    },
  ],
  fairExpanded: [
    'Findable — consistent paths, README in every folder, inventory spreadsheet updated.',
    'Accessible — document who has access (L-drive, DataCloud shares, CSC project membership).',
    'Interoperable — prefer open formats where possible; note proprietary formats in README.',
    'Reusable — metadata, protocol version, and analysis script references in project log.',
    'See onboarding doc: FAIR data and documentation 12022025.',
  ],
  cleaningChecklist: [
    'List all project folders on P-drive, L-drive, Google Drive, and local machines.',
    'Assign status: Active / Inactive / Published for each project.',
    'Move inactive Google Drive projects to ARCHIVE/.',
    'Free workstations and cpu1-data of unnecessary copies.',
    'Locate and label missing external disks; update wiki inventory.',
    'Prepare Databank transfers for published pseudonymized imaging.',
    'Monitor Allas quota; delete obsolete scratch buckets after verification.',
    'Contact Deb/Joonas for L-drive admin and P-drive quota questions.',
  ],
  sensitivityExpanded: [
    {
      level: 'Sensitive / clinical',
      stores: 'L-drive, HUH Datalake/OVCA, restricted DataCloud',
      rules: [
        'Oncosys-OVA confidentiality and ethical approvals required.',
        'No identifiers on P-drive, public Drive links, or unreviewed Allas buckets.',
        'Clinical exports stay on UH-controlled systems.',
      ],
    },
    {
      level: 'Non-sensitive active',
      stores: 'P-drive, DataCloud /farkkila/, Allas, Google Drive docs',
      rules: [
        'General protocols, decks, analysis outputs without direct patient IDs.',
        'Large imaging OK on P-drive and Allas when not clinical-identifiable.',
      ],
    },
    {
      level: 'Published / cold',
      stores: 'UH Databank, tagged external cold disks',
      rules: [
        'Pseudonymized only; README and archive date required.',
        'External disks are interim — target Databank for canonical cold store.',
      ],
    },
  ],
  generalPrinciples: [
    'One canonical location per dataset — avoid “equally authoritative” duplicates.',
    'Scratch is scratch: HPC /scratch, cPouta /data, laptops — all expire or get wiped.',
    'Document before you move: update inventory spreadsheet and project README.',
    'When unsure about sensitivity, ask Deb/Joonas before uploading to shared cloud.',
    'Transfer commands live under Transfer tools tab; full snippets in Computational Hub.',
  ],
};

export const TOOLS_CONTENT = {
  intro:
    'How to move data between lab systems. This tab describes when and why to use each tool; copy-paste commands are in Computational Hub → File operations.',
  toolsExpanded: [
    {
      id: 'rclone',
      when: 'Default for Allas ↔ DataCloud ↔ Lumi-O ↔ local paths',
      steps: [
        'Install rclone locally or use preconfigured CSC environment.',
        'rclone config — create remotes: allas (S3), datacloud (webdav), lumi-o (S3).',
        'Test: rclone lsd remote: then rclone copy source dest --progress.',
        'Long jobs: tmux new -s upload; tune --transfers, --checkers, --retries.',
      ],
      gotchas: [
        'DataCloud needs app password, not university password.',
        'Do not mix S3/Swift for large split objects on Allas.',
        'Rate-limit DataCloud with --tpslimit 2 on huge batches.',
      ],
    },
    {
      id: 'lumi_o',
      when: 'Object storage on LUMI supercomputer',
      steps: [
        'module load allas && allas-conf --lumi (once per session).',
        'Create bucket: rclone mkdir lumi-o:project-name (lowercase, hyphens only).',
        'Upload from scratch: rclone copy /scratch/.../raw/ lumi-o:bucket --progress.',
        'Large WSI: --s3-chunk-size=128M --s3-upload-concurrency=8.',
      ],
      gotchas: ['Scratch on LUMI is temporary — copy to Lumi-O before job ends.', 'Keys from auth.lumidata.eu.'],
    },
    {
      id: 'allas_conf',
      when: 'First-time Allas setup on Puhti, Mahti, LUMI, or Mac/Linux',
      steps: [
        'module load allas',
        'allas-conf (Swift, default on HPC) or allas-conf -m s3 (permanent keys).',
        'Keys land in ~/.s3cfg, ~/.config/rclone/rclone.conf, or ~/.aws/credentials.',
        'Copy config to laptop via scp if needed for local rclone.',
      ],
      gotchas: ['S3 keys do not expire — protect ~/.aws/credentials on shared VMs.'],
    },
    {
      id: 'cyberduck',
      when: 'GUI browsing without CLI',
      steps: [
        'Allas: OpenStack Swift connection to pouta.csc.fi:5001 or S3 to a3s.fi.',
        'DataCloud: WebDAV to datacloud.helsinki.fi with app password.',
        'Use for spot checks — bulk moves still prefer rclone in tmux.',
      ],
      gotchas: ['Not ideal for multi-TB unattended transfers.'],
    },
    {
      id: 'rsync',
      when: 'Direct SSH copy to LUMI scratch or cPouta VMs',
      steps: [
        'rsync -avzP -e "ssh -i ~/.ssh/id_rsa" ./local/ user@lumi.csc.fi:/scratch/project_XXX/',
        'Verify with du -sh on both ends after transfer.',
      ],
      gotchas: ['SSH timeouts — use tmux; prefer rclone for S3 destinations.'],
    },
    {
      id: 'webdav',
      when: 'Mount DataCloud as network drive on desktop',
      steps: [
        'URL: https://datacloud.helsinki.fi/remote.php/webdav/',
        'macOS Finder: Connect to Server; Windows: Map network drive.',
        'Or use Nextcloud desktop sync client for /farkkila/ subtree.',
      ],
      gotchas: ['Sync client not for multi-TB HPC staging — use rclone for bulk.'],
    },
    {
      id: 'git',
      when: 'Code, small derived tables, workflow scripts',
      steps: [
        'github.com/farkkilab — version control for pipelines and analysis code.',
        'Git LFS only for modest binaries — not whole-slide images.',
        'Pair with Allas/Databank for data; cite commit hash in README.',
      ],
      gotchas: ['Never commit secrets, credentials, or clinical identifiers.'],
    },
  ],
  transferPatterns: [
    { from: 'P-drive', to: 'DataCloud', tool: 'rclone copy', note: 'Staging docs and shared trees under /farkkila/Projects/' },
    { from: 'P-drive / workstation', to: 'Allas', tool: 'rclone copy', note: 'Before LUMI analysis; document bucket in inventory' },
    { from: 'Allas', to: 'DataCloud', tool: 'rclone copy', note: 'Server-to-server; tmux + tpslimit' },
    { from: 'LUMI scratch', to: 'Lumi-O / Allas', tool: 'rclone copy', note: 'Before scratch purge' },
    { from: 'Workstation', to: 'cPouta /data', tool: 'rsync / scp', note: 'Short-term VM scratch only' },
    { from: 'Allas / P-drive', to: 'Databank', tool: 'IT-coordinated upload', note: 'Inactive/published pseudonymized archives' },
  ],
  externalLinks: [
    { label: 'CSC rclone with Allas', href: 'https://docs.csc.fi/data/Allas/rclone/' },
    { label: 'Nextcloud WebDAV', href: 'https://docs.nextcloud.com/server/stable/user_manual/en/files/access_webdav.html' },
  ],
};
