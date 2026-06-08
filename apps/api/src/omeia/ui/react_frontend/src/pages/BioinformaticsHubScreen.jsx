
import React, { useState, useEffect } from 'react';
import {
  Wrench,
  Terminal,
  Cpu,
  ShieldCheck,
  Database,
  Settings,
  AlertCircle,
  ArrowRight,
  Clipboard,
  CheckCircle,
  HardDrive,
  FolderOpen,
  Cloud,
  FileText,
  Video,
  Volume2,
  RefreshCw,
  Search,
  BookOpen,
} from 'lucide-react';
import ComputationalToolsScreen from './ComputationalToolsScreen.jsx';
import { HubSectionFrame, HubDetailFrame } from '@/shared/layout/HubNestedNav.jsx';
import { CopyableCodeBlock } from '@/features/documents/components/CopyableCodeBlock.jsx';
import { RunPipelineTab } from '@/features/projects/components/RunPipelineTab.jsx';
import OnboardingRoadmap from '@/features/computational/components/hub/OnboardingRoadmap.jsx';
import ImageProcessingPipelineScreen from './ImageProcessingPipelineScreen.jsx';

export { RunPipelineTab };
import { COMPUTATIONAL_LEGACY_NESTED } from '@/config/navigation.js';

function resolveHubTab(activeSubTab, nestedSection) {
  const legacy = COMPUTATIONAL_LEGACY_NESTED[activeSubTab];
  if (legacy) return { tab: legacy.tab, nested: legacy.section };
  if (activeSubTab === 'utilities' && nestedSection === 'tools') {
    return { tab: 'tools', nested: null };
  }
  if (activeSubTab === 'lumi' && nestedSection === 'install') {
    return { tab: 'utilities', nested: 'lumi_modules' };
  }
  if (activeSubTab === 'lumi' && nestedSection === 'transfers') {
    return { tab: 'utilities', nested: 'lumi_transfer' };
  }
  return { tab: activeSubTab || 'onboarding', nested: nestedSection || null };
}

export default function BioinformaticsHubScreen({
  dbProjects,
  API_URL,
  activeSubTab,
  hubNestedSection = null,
  hideChrome = false,
  onNavigate,
}) {
  const resolved = resolveHubTab(activeSubTab, hubNestedSection);
  const [subTab, setSubTab] = useState(resolved.tab);
  const [nestedSection, setNestedSection] = useState(resolved.nested);

  useEffect(() => {
    const next = resolveHubTab(activeSubTab, hubNestedSection);
    setSubTab(next.tab);
    if (next.nested) setNestedSection(next.nested);
  }, [activeSubTab, hubNestedSection]);

  const menuItems = [
    { id: 'onboarding', label: 'Onboarding & credentials' },
    { id: 'lumi', label: 'LUMI HPC' },
    { id: 'pouta', label: 'cPouta VMs' },
    { id: 'roihu', label: 'Roihu' },
    { id: 'troubleshoot', label: 'Troubleshooting' },
    { id: 'utilities', label: 'Utilities' },
    { id: 'tools', label: 'Lab computational tools' },
  ];

  return (
    <div
      className="bioinformatics-hub-screen"
      style={{ display: 'flex', gap: hideChrome ? 0 : '2rem', minHeight: hideChrome ? 'auto' : 'calc(100vh - 8rem)' }}
    >
      {!hideChrome && (
        <div style={{ width: '260px', flexShrink: 0, borderRight: '1px solid var(--border-color)', paddingRight: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>
            BIOINFORMATICS SERVICES
          </div>
          {menuItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`sidebar-item bio-hub-nav-btn ${subTab === item.id ? 'active' : ''}`}
              onClick={() => setSubTab(item.id)}
              style={{
                width: '100%',
                textAlign: 'left',
                border: 'none',
                background: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                cursor: 'pointer',
                borderRadius: '8px',
                padding: '0.75rem 1rem',
              }}
            >
              <span style={{ fontSize: '0.9rem' }}>{item.label}</span>
            </button>
          ))}
        </div>
      )}

      <div style={{ flexGrow: 1, minWidth: 0 }}>
        {subTab === 'onboarding' && <OnboardingRoadmap />}
        {subTab === 'lumi' && (
          <LumiHubTab
            dbProjects={dbProjects}
            API_URL={API_URL}
            onNavigate={onNavigate}
            initialSection={nestedSection || 'jobs'}
            onSectionChange={setNestedSection}
          />
        )}
        {subTab === 'pouta' && (
          <PoutaHubTab
            API_URL={API_URL}
            onNavigate={onNavigate}
            initialSection={nestedSection || 'vms'}
            onSectionChange={setNestedSection}
          />
        )}
        {subTab === 'roihu' && <RoihuTab />}
        {subTab === 'troubleshoot' && (
          <TroubleshootingHubTab
            API_URL={API_URL}
            initialSection={nestedSection || 'diagnostics'}
            onSectionChange={setNestedSection}
          />
        )}
        {subTab === 'utilities' && (
          <UtilitiesHubTab
            API_URL={API_URL}
            onNavigate={onNavigate}
            initialSection={nestedSection || 'file_ops'}
            onSectionChange={setNestedSection}
          />
        )}
        {subTab === 'tools' && <ComputationalToolsScreen />}
      </div>
    </div>
  );
}

/* ========================================================================= */
/* 2. ANACONDA & CONDA ENVIRONMENTS                                          */
/* ========================================================================= */
function StorageHubLinkBanner({ onNavigate, target = 'landscape', label = 'Open Data & Storage' }) {
  if (!onNavigate) return null;
  return (
    <div
      className="panel"
      style={{
        marginBottom: '1.25rem',
        padding: '0.85rem 1rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
        flexWrap: 'wrap',
      }}
    >
      <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
        <HardDrive size={14} style={{ verticalAlign: 'middle', marginRight: '0.35rem' }} />
        Drive capacities, L/P-drive paths, and cPouta volume rules live in <strong>Data &amp; Storage</strong>.
        Command snippets stay here.
      </p>
      <button
        type="button"
        className="btn btn-sm btn-secondary"
        onClick={() => onNavigate('data_storage', target)}
      >
        {label} <ArrowRight size={12} />
      </button>
    </div>
  );
}

function CondaEnvironmentTab({ onNavigate, variant = 'full', embedded = false }) {
  const [activeSec, setActiveSec] = useState(variant === 'pouta' ? 'pouta_env' : 'core');

  const condaScript = `conda create -n farkki_spatial python=3.10 -y
conda activate farkki_spatial
conda install -c conda-forge openjdk libtiff pywavelets scikit-image -y
pip install ashlar stardist cylinter spacestat`;

  const minicondaPouta = `# Download the installer script
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Execute installer
bash Miniconda3-latest-Linux-x86_64.sh
# Accept License, choose path (default: ~/miniconda3), allow shell initialization

# Activate conda
source ~/miniconda3/bin/activate

# Create Python 3.11 environment
conda create -n py311 python=3.11 -y
conda activate py311

# Verify
python --version
conda info --envs`;

  const condaPanels = (
    <>
      {variant !== 'pouta' && (
        <StorageHubLinkBanner onNavigate={onNavigate} target="local_storage" label="cPouta volume rules" />
      )}

      {(variant === 'core' || variant === 'full') && activeSec === 'core' && (
        <div>
          <div className="panel">
            <h3 className="panel-title"><Terminal size={18} /> Core Environment Setup</h3>
            <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
              We use isolated environments with **Python 3.10** for spatial deconvolution and image stitching. To install the unified environment on the local cluster or LUMI supercomputing space, run the following:
            </p>
            <CopyableCodeBlock code={condaScript} type="primary" />
          </div>

          <div className="grid-2col" style={{marginTop: '0.85rem'}}>
            <div className="panel">
              <h4 style={{color: 'var(--text-primary)', marginBottom: '0.5rem', fontSize: '0.95rem'}}>Exporting Environment Variables</h4>
              <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>To save the active package configurations into an environment file for portability:</p>
              <CopyableCodeBlock code="conda env export --no-builds > environment.yml" type="primary" compact />
            </div>
            <div className="panel">
              <h4 style={{color: 'var(--text-primary)', marginBottom: '0.5rem', fontSize: '0.95rem'}}>Recreating Environment from YML</h4>
              <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>To recreate the dependencies from a git repository file:</p>
              <CopyableCodeBlock code="conda env create -f environment.yml" type="primary" compact />
            </div>
          </div>
        </div>
      )}

      {(variant === 'pouta' || variant === 'full') && activeSec === 'pouta_env' && (
        <div className="panel">
          <h3 className="panel-title"><Terminal size={18} /> Setting Up Miniconda on CSC Pouta VMs</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
            cPouta instances are vanilla VMs. To configure Python 3.11 with Miniconda for user-specific development pipelines:
          </p>
          <CopyableCodeBlock code={minicondaPouta} type="success" />

          <h4 style={{fontSize: '0.95rem', color: 'var(--text-primary)', marginTop: '1.5rem', marginBottom: '0.5rem'}}>Conda Environment Best Practices:</h4>
          <ul style={{fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem'}}>
            <li>Keep environments lightweight and specific. Do not install unrelated tools in the same environment.</li>
            <li>Clear cached directories regularly using <code>conda clean -a</code> to free root disk space.</li>
            <li>Always ensure packages are pulled from <code>conda-forge</code> for linux compatibility.</li>
          </ul>
        </div>
      )}
    </>
  );

  return (
    <div>
      {!embedded && (
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary)'}}>Anaconda & Environment SOP</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Standardized configuration steps to clone and maintain cluster environments.</p>
      </div>
      )}

      {variant === 'full' ? (
        <HubDetailFrame
          sections={[
            { id: 'core', label: 'Core environment' },
            { id: 'pouta_env', label: 'cPouta miniconda' },
          ]}
          active={activeSec}
          onChange={setActiveSec}
          ariaLabel="Conda environment views"
        >
          {condaPanels}
        </HubDetailFrame>
      ) : (
        condaPanels
      )}
    </div>
  );
}

/* ========================================================================= */
/* 3. LUMI MODULES, PYTHON & STORAGE TOOLS                                   */
/* ========================================================================= */
export function LumiModulesTab({ embedded = false }) {
  const [activeSec, setActiveSec] = useState('modules');

  const moduleStack = `# Load every new LUMI login session — modules do not persist
module use /appl/local/csc/modulefiles
module load cray-python/3.11.7

# Search what is available
module avail python
module spider rclone

# Common lab stack
module load allas          # a-* commands + rclone allas remote helpers
module load rclone         # when exposed on your partition

# Snakemake pipeline venv (project-specific path)
source /projappl/project_<ID>/envs/snakemake311/bin/activate

# Verify
python --version
which rclone`;

  const pythonPackages = `# Create an isolated venv on LUMI (recommended over system pip)
module load cray-python/3.11.7
python -m venv $HOME/venvs/spatial-tools
source $HOME/venvs/spatial-tools/bin/activate

# Upgrade pip inside the venv
pip install --upgrade pip wheel

# Common analysis packages (CPU login node / lightweight tests)
pip install numpy pandas scipy scikit-image tifffile

# Install from a requirements file copied to scratch
pip install -r /scratch/project_<ID>/$USER/requirements.txt

# Apptainer is preferred for Ashlar / Mesmer / StarDist on compute nodes —
# use pip only for orchestration scripts and QC utilities.`;

  const storageModules = `# Allas + rclone on LUMI (new terminal each session)
module use /appl/local/csc/modulefiles
module load allas
allas-conf -m s3          # first-time S3 keys into ~/.s3cfg
allas-conf --lumi         # Lumi-O credentials (see Utilities → Lumi-O transfer)

# Quick checks
a-access-key list
rclone lsd lumi-o:

# Pull a bucket prefix into scratch before a pipeline run
a-get -r bucket-name/path/to/raw/ /scratch/project_<ID>/$USER/data/raw/SAMPLE1/`;

  const napariLumi = `# 1. Log in to the LUMI web UI: https://www.lumi.csc.fi/
# 2. Select Desktop from the menu
# 3. Launch parameters: Compression 0, Image quality 9, partition small-g (GPU) or small
# 4. Open Terminal in the desktop session
cd ~/Desktop
singularity run --nv napari-xtra.sif napari_fast_masking.py

# 5. Load OME-TIFF / masks from scratch (not $HOME):
# File → Open → /scratch/project_<ID>/.../data/stitching/<sample>/`;

  const installViews = [
    { id: 'modules', label: 'Module stack' },
    { id: 'python', label: 'Python & pip' },
    { id: 'storage_tools', label: 'Allas & rclone' },
    { id: 'napari_lumi', label: 'Napari desktop' },
  ];

  return (
    <HubDetailFrame sections={installViews} active={activeSec} onChange={setActiveSec} ariaLabel="LUMI modules and packages">
      {activeSec === 'modules' && (
        <div className="panel">
          <h3 className="panel-title"><Terminal size={18} /> Loading LUMI modules</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            LUMI uses Environment Modules — load Python, Allas, and rclone at the start of each SSH session before running scripts or the image pipeline.
          </p>
          <CopyableCodeBlock code={moduleStack} type="primary" />
        </div>
      )}

      {activeSec === 'python' && (
        <div className="panel">
          <h3 className="panel-title"><Settings size={18} /> Python packages in a venv</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Use a personal virtual environment for helper scripts. Heavy pipeline stages (Ashlar, Mesmer, StarDist) run inside Apptainer images documented in LUMI HPC → Imaging pipeline.
          </p>
          <CopyableCodeBlock code={pythonPackages} type="success" />
        </div>
      )}

      {activeSec === 'storage_tools' && (
        <div className="panel">
          <h3 className="panel-title"><Cloud size={18} /> Allas &amp; rclone modules</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Stage raw tiles from Allas or Lumi-O into scratch. Full Lumi-O setup and bucket transfers are under <strong>Utilities → Lumi-O transfer</strong>.
          </p>
          <CopyableCodeBlock code={storageModules} type="primary" />
        </div>
      )}

      {activeSec === 'napari_lumi' && (
        <div className="panel">
          <h3 className="panel-title"><Video size={18} /> Napari on LUMI desktop</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Inspect stitched OME-TIFFs and segmentation masks on a LUMI virtual desktop — required for pipeline QC gates.
          </p>
          <CopyableCodeBlock code={napariLumi} type="success" />
        </div>
      )}
    </HubDetailFrame>
  );
}

/** @deprecated alias — use LumiModulesTab */
export const InstallSoftwareTab = LumiModulesTab;

/* ========================================================================= */
/* 4. FILE OPERATIONS & TRANSFERS                                            */
/* ========================================================================= */
function FileOperationsTab({ onNavigate, variant = 'full', embedded = false }) {
  const [activeSec, setActiveSec] = useState('guides');
  const [activeGuideSub, setActiveGuideSub] = useState('csc_dc');

  const transferScript = `rsync -avzP --compress-level=6 \\
  -e "ssh -i ~/.ssh/id_rsa" \\
  /Users/debashishdeb/Downloads/OMEIA-AI/projects/ \\
  username@lumi.csc.fi:/scratch/project_462000000/`;

  const compressScript = `# Tar compress folder with high-performance pigz (parallel gzip)
tar -I pigz -cf project_archive.tar.gz ./projects/9_EyeMT/

# Encrypt the compressed archive using GPG key
gpg --symmetric --cipher-algo AES256 project_archive.tar.gz

# Decrypting
gpg -d project_archive.tar.gz.gpg > decrypted.tar.gz`;

  const rcloneLumiO = `# Step 1: Load Allas tools module (must run each new terminal session)
module use /appl/local/csc/modulefiles
module load allas

# Step 2: One-time setup of Lumi-O Access credentials
allas-conf --lumi
# Prompts will ask:
#   1. Lumi Project Number: Enter number from CSC portal
#   2. Access key / Secret key: Generate them at https://auth.lumidata.eu/
#   3. Make Lumi-O default storage? Select: y

# Step 3: Test connection
rclone lsd lumi-o:

# Step 4: Create project bucket (STRICT: lowercase, numbers, and hyphens only!)
rclone mkdir lumi-o:project-4-cellcycle

# Step 5: Upload slide dataset preserving directory tree structures
rclone copy /scratch/project_XXXX/raw/ lumi-o:project-4-cellcycle --progress

# Step 6: Optimized options for huge Whole Slide Images (multi-GB slides)
rclone copy \\
  --progress \\
  --transfers=8 \\
  --checkers=8 \\
  --s3-chunk-size=128M \\
  --s3-upload-concurrency=8 \\
  /scratch/project_XXXX/raw/ lumi-o:project-4-cellcycle`;

  const rcloneDatacloudAllas = `# Step 1: Initialize rclone configuration tool
rclone config
# Select 'n' for new remote connection

# ----------------- 3.1 Configure Allas (S3 Compliant) -----------------
# Name: allas
# Storage: s3
# Provider: OpenStack Swift (or generic S3)
# To get S3 Access/Secret keys, open a terminal on Puhti and execute:
#   module load allas && allas-conf -m s3
#   grep access_key $HOME/.s3cfg | cut -d " " -f3 (Copy Access Key)
#   grep secret_key $HOME/.s3cfg | cut -d " " -f3 (Copy Secret Key)
# Endpoint: https://a3s.fi
# Save config profile. Now "allas:" remote is active.

# ----------------- 3.2 Configure Datacloud (WebDAV) -----------------
# Name: datacloud
# Storage: webdav
# URL: https://datacloud.helsinki.fi/remote.php/webdav/
# Vendor: nextcloud
# User: <datacloud app username> (Not CSC username)
# Password: <datacloud generated app password>
# Save config profile. Now "datacloud:" remote is active.

# ----------------- Copy Operations via Tmux session -----------------
# Start Tmux to avoid SSH timeout aborts
tmux new -s datacloud_upload

# Server-to-Server file transfer (Allas to Datacloud)
rclone copy allas:bucket-name/ datacloud:farkkila/project/ -P \\
  --transfers 2 --checkers 4 --retries 10 --low-level-retries 20 --tpslimit 2`;

  const rcloneLocalAllas = `# Step 1: Open Terminal on macOS/Linux or PowerShell on Windows
rclone config
# Select 'n' for new remote connection. Name: s3allas
# Storage: Amazon S3 Compliant Storage Providers
# Provider: Any other S3 compatible provider
# Credentials: Enter AWS credentials manually

# Get keys from an active CSC session:
#   grep access_key $HOME/.s3cfg | cut -d " " -f3 (AWS Access Key)
#   grep secret_key $HOME/.s3cfg | cut -d " " -f3 (AWS Secret Key)
# Region: 1
# Endpoint: a3s.fi
# Location constant: <Leave blank>
# ACL: 1
# Save. Now "s3allas:" is configured on your workstation.

# Step 2: Verification and commands
# List buckets
rclone lsd s3allas:
# Upload folder
rclone copy /local/path s3allas:my-bucket-name/ --progress`;

  const cyberduckAllas = `1. Download and install Cyberduck.
2. Open Cyberduck and select Bookmark -> New Bookmark (Ctrl-Shift-B).
3. From the storage protocol dropdown, choose: OpenStack Swift (Keystone 3).
4. Enter Server: pouta.csc.fi
5. Port: 5001
6. Section Project:Domain:Username -> Enter: project_2003009:default:your_username
   (Replace "your_username" with your CSC username)
7. Enter your CSC account Password.
8. Click X to close the bookmark popup.
9. Click the Bookmark icon in the toolbar, right click the bookmark and click "Connect to server".`;

  const rcloneCheatsheetCode = `# ---------------- Basics ----------------
# Dry run test before transferring
rclone copy /src /dst --dry-run
# Realtime status update
rclone copy /src /dst -P --stats 5s

# ---------------- Copy Operations ----------------
# Upload Local to cPouta
rclone copy /local/path cpouta:bucket-name --progress --transfers=8 --checkers=16

# Download cPouta to Local
rclone copy cpouta:bucket-name /local/path --progress --transfers=8 --checkers=16

# Server-to-Server Copy (cPouta to Datacloud)
rclone copy cpouta:bucket-name datacloud:username/folder --progress --transfers=8 --checkers=16

# ---------------- Optimization configs ----------------
# For many small files (CSV, JSON metrics, metadata)
rclone copy /src /dst --progress --transfers=16 --checkers=32 --cutoff-mode=soft

# For very large files (>10GB slides)
rclone copy /src /dst --progress --transfers=4 --checkers=8 --multi-thread-streams=8 --retries=10 --low-level-retries=20

# For mixed workloads (slides + annotations tables)
rclone copy /src /dst --progress --transfers=8 --checkers=16 --multi-thread-streams=4 --retries=10 --low-level-retries=20 --stats 5s`;

  if (variant === 'lumi_transfer') {
    return (
      <div>
        <div className="panel">
          <h3 className="panel-title"><Cloud size={18} /> Lumi-O object storage</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            LUMI uses <strong>Lumi-O</strong> (S3-compatible) for scratch-to-bucket transfers. Load the Allas module each session, then configure once with <code>allas-conf --lumi</code>.
          </p>
          <CopyableCodeBlock code={rcloneLumiO} type="primary" />
        </div>
        <div className="panel">
          <h3 className="panel-title"><HardDrive size={18} /> rsync workstation → LUMI scratch</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            For large slide directories, push directly to project scratch before running the imaging pipeline.
          </p>
          <CopyableCodeBlock code={transferScript} type="primary" />
        </div>
      </div>
    );
  }

  return (
    <div>
      {!embedded && (
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-accent)'}}>File Operations SOP</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Standard guidelines for transfer, compression, and encryption of large raw image directories.</p>
      </div>
      )}

      <StorageHubLinkBanner onNavigate={onNavigate} target="landscape" label="Storage landscape" />

      {(() => {
        const fileOpViews = [
          { id: 'guides', label: 'Transfer guides' },
          { id: 'cheatsheet', label: 'rclone cheatsheet' },
          { id: 'crypto', label: 'Compression & encryption' },
        ];
        const guideViews = [
          { id: 'csc_dc', label: 'CSC to Datacloud' },
          { id: 'local_allas', label: 'Workstation to Allas' },
          { id: 'cyberduck', label: 'Cyberduck GUI' },
        ];

        const fileOpBody = (
          <>
      {activeSec === 'guides' && (
        <HubDetailFrame
          sections={guideViews}
          active={activeGuideSub}
          onChange={setActiveGuideSub}
          ariaLabel="Transfer guide topics"
        >
          <div>
            {activeGuideSub === 'csc_dc' && (
              <div className="panel" style={{margin: 0}}>
                <h4 style={{color: 'var(--text-primary)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                  <Cloud size={16} /> File Transfer from CSC to Datacloud / Allas
                </h4>
                <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
                  To transfer slides directly between CSC cloud hosts and Datacloud (Helsinki University WebDAV storage), configure S3 and Nextcloud remotes:
                </p>
                <CopyableCodeBlock code={rcloneDatacloudAllas} type="success" />
              </div>
            )}

            {activeGuideSub === 'local_allas' && (
              <div className="panel" style={{margin: 0}}>
                <h4 style={{color: 'var(--text-primary)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                  <Cloud size={16} /> File Transfer from Workstation to Allas (rclone CLI)
                </h4>
                <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
                  To copy raw slides directly from your local terminal or Windows Command Prompt to the Allas active storage project:
                </p>
                <CopyableCodeBlock code={rcloneLocalAllas} type="primary" />
              </div>
            )}

            {activeGuideSub === 'cyberduck' && (
              <div className="panel" style={{margin: 0}}>
                <h4 style={{color: 'var(--text-primary)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                  <Cloud size={16} /> Graphical Transfer: Using Allas with Cyberduck
                </h4>
                <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
                  For macOS and Windows users who prefer a graphical user interface instead of rclone shell command lines:
                </p>
                <pre style={{
                  padding: '1.25rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-secondary)',
                  fontSize: '0.85rem',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap'
                }}>
                  {cyberduckAllas}
                </pre>
              </div>
            )}
          </div>
        </HubDetailFrame>
      )}

      {activeSec === 'cheatsheet' && (
        <div className="panel">
          <h3 className="panel-title"><FileText size={18} /> rclone CLI Cheatsheet</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
            Quick command references for copying files between local paths, cPouta object stores, and Datacloud.
          </p>
          <CopyableCodeBlock code={rcloneCheatsheetCode} type="success" />
        </div>
      )}

      {activeSec === 'crypto' && (
        <div>
          <div className="panel">
            <h3 className="panel-title"><HardDrive size={18} /> High-speed File Transfer</h3>
            <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
              Large slide files (.OME-TIFF) should be transferred to LUMI clusters using parallel `rsync` with compression enabled:
            </p>
            <CopyableCodeBlock code={transferScript} type="primary" />
          </div>

          <div className="panel">
            <h3 className="panel-title"><ShieldCheck size={18} /> Compression & Encryption SOP</h3>
            <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
              Raw slide archives must be compressed and encrypted before offsite sync or node transitions:
            </p>
            <CopyableCodeBlock code={compressScript} type="warning" />
          </div>
        </div>
      )}
          </>
        );

        return (
          <HubDetailFrame
            sections={fileOpViews}
            active={activeSec}
            onChange={setActiveSec}
            ariaLabel="File operation views"
          >
            {fileOpBody}
          </HubDetailFrame>
        );
      })()}
    </div>
  );
}

/* ========================================================================= */
/* 5. LUMI SLURM JOBS                                                        */
/* ========================================================================= */
export function LumiJobTab({ dbProjects, API_URL, embedded = false }) {
  const [proj, setProj] = useState('SPACE');
  const [gpus, setGpus] = useState(1);
  const [walltime, setWalltime] = useState('02:00:00');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeSec, setActiveSec] = useState('generator');

  const handleGenerate = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/lumi_job`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_code: proj,
          gpu_count: gpus,
          walltime_limit: walltime,
          stitching_config_params: {}
        })
      });
      if (res.ok) {
        setResult(await res.json());
      }
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  const checkJobSlurm = `# 1. Check your active & pending jobs
squeue -u $USER

# 2. Recommended output format (readable columns)
squeue -u $USER -o "%.18i %.9P %.20j %.8u %.2t %.10M %.6D %R"

# 3. View job details (CPU, Node limits, memory configurations)
scontrol show job <JOBID>
# Example: scontrol show job 31566886

# 4. View stdout output of running job
cat slurm-<JOBID>.out
# Follow log live: tail -f slurm-<JOBID>.out

# 5. View error trace outputs
cat slurm-<JOBID>.err

# 6. Retrieve job memory and efficiency metrics (post-run)
sacct -j <JOBID> --format=JobID,JobName,State,Elapsed,MaxRSS,AllocCPUS

# 7. Cancel job
scancel <JOBID>
# Cancel all your running jobs
scancel -u $USER`;

  const lumiJobViews = [
    { id: 'generator', label: 'Script generator' },
    { id: 'status', label: 'Slurm status' },
  ];

  return (
    <HubDetailFrame sections={lumiJobViews} active={activeSec} onChange={setActiveSec} ariaLabel="Slurm job views">
      {activeSec === 'generator' && (
        <div className="panel" style={{maxWidth: '650px'}}>
          <h3 className="panel-title"><Cpu size={18} /> Slurm Configuration</h3>
          <div className="form-group">
            <label className="form-label">Project Code</label>
            <select className="form-select" value={proj} onChange={(e) => setProj(e.target.value)}>
              {dbProjects.map(p => (
                <option key={p.project_code} value={p.project_code}>{p.project_code}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">GPUs Required</label>
            <input type="number" className="form-input" min="1" max="8" value={gpus} onChange={(e) => setGpus(Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label className="form-label">Walltime Limit (Max hours)</label>
            <input type="text" className="form-input" value={walltime} onChange={(e) => setWalltime(e.target.value)} />
          </div>
          <button className="btn btn-primary" onClick={handleGenerate} disabled={loading}>
            {loading ? "Generating script..." : "💻 Generate Slurm Script"}
          </button>

          {result && (
            <div style={{marginTop: '1.5rem'}}>
              <h4 style={{color: 'var(--text-primary)', marginBottom: '0.5rem'}}>Slurm Script Code:</h4>
              <CopyableCodeBlock code={result.slurm_script_content} type="success" />
            </div>
          )}
        </div>
      )}

      {activeSec === 'status' && (
        <div>
          <div className="panel">
            <h3 className="panel-title"><Terminal size={18} /> Checking Slurm Job Status</h3>
            <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
              Use Slurm commands to monitor your queued and executing slide processing jobs on LUMI:
            </p>
            <CopyableCodeBlock code={checkJobSlurm} type="primary" />
          </div>

          <div className="panel">
            <h4 style={{color: 'var(--text-primary)', marginBottom: '0.75rem', fontSize: '0.95rem'}}>Common Slurm Job State Codes</h4>
            <table className="table" style={{width: '100%', fontSize: '0.85rem', borderCollapse: 'collapse'}}>
              <thead>
                <tr style={{borderBottom: '1px solid var(--border-color)', textAlign: 'left'}}>
                  <th style={{padding: '0.5rem'}}>Code</th>
                  <th style={{padding: '0.5rem'}}>Meaning</th>
                  <th style={{padding: '0.5rem'}}>Description</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}><td style={{padding: '0.5rem', fontWeight: 'bold', color: 'var(--color-primary)'}}>R</td><td style={{padding: '0.5rem'}}>Running</td><td style={{padding: '0.5rem'}}>Job is actively running on compute nodes.</td></tr>
                <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}><td style={{padding: '0.5rem', fontWeight: 'bold', color: 'var(--color-warning)'}}>PD</td><td style={{padding: '0.5rem'}}>Pending</td><td style={{padding: '0.5rem'}}>Waiting in queue (Resource limits / Priority).</td></tr>
                <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}><td style={{padding: '0.5rem', fontWeight: 'bold'}}>CG</td><td style={{padding: '0.5rem'}}>Completing</td><td style={{padding: '0.5rem'}}>Job files writing and node clearing.</td></tr>
                <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}><td style={{padding: '0.5rem', fontWeight: 'bold', color: 'var(--color-success)'}}>CD</td><td style={{padding: '0.5rem'}}>Completed</td><td style={{padding: '0.5rem'}}>Finished successfully (exit code 0).</td></tr>
                <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}><td style={{padding: '0.5rem', fontWeight: 'bold', color: 'var(--color-danger)'}}>F</td><td style={{padding: '0.5rem'}}>Failed</td><td style={{padding: '0.5rem'}}>Run terminated with errors. Check .err logs.</td></tr>
                <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}><td style={{padding: '0.5rem', fontWeight: 'bold', color: 'var(--color-danger)'}}>TO</td><td style={{padding: '0.5rem'}}>Timeout</td><td style={{padding: '0.5rem'}}>Killed due to exceeding requested walltime limit.</td></tr>
                <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}><td style={{padding: '0.5rem', fontWeight: 'bold', color: 'var(--color-danger)'}}>OOM</td><td style={{padding: '0.5rem'}}>Out Of Memory</td><td style={{padding: '0.5rem'}}>Consumed more memory than requested allocations.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </HubDetailFrame>
  );
}

/* ========================================================================= */
/* 6. cPOUTA CLOUD VM MANAGEMENT & MEDIA                                     */
/* ========================================================================= */
const CPOUTA_VM_VIEWS = [
  { id: 'specs', label: 'VM servers & specs' },
  { id: 'creation', label: 'VM creation guide' },
  { id: 'media', label: 'Training media' },
];

function CpoutaVmTab({ API_URL, onNavigate, embedded = false }) {
  const [activeSec, setActiveSec] = useState('specs');

  return (
    <HubDetailFrame sections={CPOUTA_VM_VIEWS} active={activeSec} onChange={setActiveSec} ariaLabel="cPouta VM views">
      {activeSec === 'specs' && (
        <div>
          <div className="panel">
            <h3 className="panel-title"><Cloud size={18} /> Active cPouta VM Instances</h3>
            <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.5rem'}}>
              Our laboratory maintains three virtual machines on CSC cPouta for custom packages and services not supported on the main LUMI nodes:
            </p>

            <div className="grid-3col" style={{gap: '1rem'}}>
              <div className="surface-inset" style={{background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                <h4 style={{fontSize: '1rem', color: 'var(--color-primary)', margin: '0 0 0.5rem 0'}}>farkkila-gpu1</h4>
                <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 0.75rem 0'}}>
                  <b>OS:</b> Ubuntu 16.04 (CUDA-enabled)<br/>
                  <b>Flavor:</b> gpu.1.2.gpu (RTX VM)<br/>
                  <b>IP:</b> 128.214.253.252<br/>
                  <b>Host:</b> vm2749.kaj.pouta.csc.fi
                </p>
                <span style={{fontSize: '0.75rem', background: 'rgba(45,212,191,0.1)', color: 'var(--color-primary)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontWeight: 'bold'}}>GPU pipelines & Avivator</span>
              </div>

              <div className="surface-inset" style={{background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                <h4 style={{fontSize: '1rem', color: 'var(--color-primary)', margin: '0 0 0.5rem 0'}}>farkkila-cpu1</h4>
                <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 0.75rem 0'}}>
                  <b>OS:</b> Ubuntu 18.04 LTS<br/>
                  <b>Flavor:</b> hpc-gen2.48core<br/>
                  <b>IP:</b> 195.148.21.14<br/>
                  <b>Host:</b> vm2794.kaj.pouta.csc.fi
                </p>
                <span style={{fontSize: '0.75rem', background: 'rgba(13,148,136,0.1)', color: 'var(--color-primary)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontWeight: 'bold'}}>Cyto App (port 9999)</span>
              </div>

              <div className="surface-inset" style={{background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                <h4 style={{fontSize: '1rem', color: 'var(--color-primary)', margin: '0 0 0.5rem 0'}}>farkkila-cpu2</h4>
                <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 0.75rem 0'}}>
                  <b>OS:</b> Ubuntu 18.04 LTS<br/>
                  <b>Flavor:</b> hpc-gen2.48core<br/>
                  <b>IP:</b> 195.148.21.26<br/>
                  <b>Host:</b> vm2806.kaj.pouta.csc.fi
                </p>
                <span style={{fontSize: '0.75rem', background: 'rgba(13,148,136,0.1)', color: 'var(--color-primary)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontWeight: 'bold'}}>General CPU Computing</span>
              </div>
            </div>
          </div>

          <div className="panel">
            <h4 style={{color: 'var(--text-primary)', marginBottom: '0.75rem', fontSize: '1rem'}}>NFS Shared Storage Volumes</h4>
            <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5}}>
              2 TB at <code>/data</code> on <code>farkkila-gpu1</code> (NFS server); cpu1/cpu2 mount as clients.
              Home vs <code>/data/$USER</code> rules, symlinks, and disk audits →{' '}
              {onNavigate ? (
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  style={{ marginTop: '0.35rem' }}
                  onClick={() => onNavigate('data_storage', 'local_storage')}
                >
                  Data &amp; Storage <ArrowRight size={12} />
                </button>
              ) : (
                'Data & Storage → Local & external disks'
              )}
            </p>
            <CopyableCodeBlock
              code="/data 192.168.1.7(rw,sync,no_subtree_check,no_root_squash) 192.168.1.12(rw,sync,no_subtree_check,no_root_squash)"
              type="warning"
              compact
            />
          </div>
        </div>
      )}

      {activeSec === 'creation' && (
        <div className="panel">
          <h3 className="panel-title"><Settings size={18} /> cPouta VM Horizon Provisioning (Steps 1-10)</h3>
          <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem'}}>
            Administrators can spin up new compute nodes using the CSC OpenStack dashboard (<a href="https://pouta.csc.fi" target="_blank" rel="noreferrer" style={{color: 'var(--color-primary)'}}>pouta.csc.fi</a>). Follow these steps:
          </p>

          <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem', lineHeight: 1.5}}>
            <div style={{padding: '0.75rem', borderBottom: '1px solid var(--border-color)'}}>
              <b>Step 1: Details:</b> Name the instance and set count = 1. Leave Availability Zone as <i>nova</i>.
            </div>
            <div style={{padding: '0.75rem', borderBottom: '1px solid var(--border-color)'}}>
              <b>Step 2: Source:</b> Select target OS Image. Set <b>Create New Volume = YES</b> to boot from persistent disk storage (detachable block disk) instead of ephemeral memory.
            </div>
            <div style={{padding: '0.75rem', borderBottom: '1px solid var(--border-color)'}}>
              <b>Step 3: Flavor:</b> Choose flavor based on workloads (e.g. <code>gpu.1.2.gpu</code> or <code>hpc-gen2.48core</code>).
            </div>
            <div style={{padding: '0.75rem', borderBottom: '1px solid var(--border-color)'}}>
              <b>Step 4 & 5: Networks & Network Ports:</b> Bind to the default private project subnet (e.g. <code>proj-net</code> connected via <code>proj-router</code>).
            </div>
            <div style={{padding: '0.75rem', borderBottom: '1px solid var(--border-color)'}}>
              <b>Step 6: Security Groups:</b> Assign <b>default</b>, the custom group <b>SSH-fer</b> (specific for our lab), and rule for ports <code>6000-6020</code> for GUI tool forwarding.
            </div>
            <div style={{padding: '0.75rem', borderBottom: '1px solid var(--border-color)'}}>
              <b>Step 7: Key Pairs:</b> Import or select the SSH public keys matching your authorized lab admins key list.
            </div>
            <div style={{padding: '0.75rem'}}>
              <b>Step 8-10: Config & Metadata:</b> Verify options and click <b>Launch Instance</b>. Attach floating public IP for SSH route access.
            </div>
          </div>
        </div>
      )}

      {activeSec === 'media' && (
        <div className="panel">
          <h3 className="panel-title"><Video size={18} /> cPouta Setup Video & Audio Memos</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.5rem'}}>
            Recorded tutorial walk-throughs covering VM setups and user provisioning on CSC Cloud systems.
          </p>

          <div style={{display: 'flex', flexDirection: 'column', gap: '2rem'}}>
            <div className="surface-inset" style={{padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
              <h4 style={{color: 'var(--text-primary)', marginBottom: '0.75rem', fontSize: '0.95rem'}}>1. cPouta Setup Video Walkthrough</h4>
              <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>Screen recording of SSH key binding and network routers layout.</p>
              <video 
                controls 
                style={{width: '100%', borderRadius: '4px', background: 'var(--bg-inset)', maxHeight: '360px'}}
                src={`${API_URL}/csc-media/Cpouta%20User%20setup/video1003837229.mp4`}
              />
            </div>

            <div className="surface-inset" style={{padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
              <h4 style={{color: 'var(--text-primary)', marginBottom: '0.75rem', fontSize: '0.95rem'}}>2. VM Instance Creation & Shell Run</h4>
              <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>Console run recording detailing useradd actions and ports checking.</p>
              <video 
                controls 
                style={{width: '100%', borderRadius: '4px', background: 'var(--bg-inset)', maxHeight: '360px'}}
                src={`${API_URL}/csc-media/Cpouta%20User%20setup/video2003837229.mp4`}
              />
            </div>

            <div className="surface-inset" style={{padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
              <h4 style={{color: 'var(--text-primary)', marginBottom: '0.75rem', fontSize: '0.95rem'}}>3. cPouta Audio Memo Notes</h4>
              <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>Voice dictation regarding persistent volumes attaching guidelines.</p>
              <audio 
                controls 
                style={{width: '100%', marginTop: '0.5rem'}}
                src={`${API_URL}/csc-media/Cpouta%20User%20setup/audio1003837229.m4a`}
              />
            </div>
          </div>
        </div>
      )}
    </HubDetailFrame>
  );
}

/* ========================================================================= */
/* 7. SYSTEM DIAGNOSTICS                                                     */
/* ========================================================================= */
export function DiagnosticsTab({ API_URL, embedded = false }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [checker, setChecker] = useState('python_env');

  const CHECKERS = [
    { id: 'python_env', label: 'Python environment' },
    { id: 'gpu', label: 'GPU / CUDA' },
    { id: 'napari', label: 'Napari' },
    { id: 'docker', label: 'Docker' },
    { id: 'lumi_modules', label: 'LUMI modules' },
    { id: 'cylinter_inputs', label: 'Cylinter inputs' },
    { id: 'project_structure', label: 'tCyCIF project structure' },
  ];

  const handleCheck = async (suite = false) => {
    setLoading(true);
    setResult(null);
    try {
      const url = suite ? `${API_URL}/run_checker_suite` : `${API_URL}/run_checker`;
      const body = suite ? undefined : JSON.stringify({ checker_name: checker });
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        ...(body ? { body } : {}),
      });
      if (res.ok) {
        setResult(await res.json());
      } else {
        const err = await res.json().catch(() => ({}));
        setResult({ status: 'error', execution_logs: err.detail || res.statusText });
      }
    } catch (e) {
      setResult({ status: 'error', execution_logs: String(e) });
    } finally {
      setLoading(false);
    }
  };

  const logText = result?.execution_logs
    || [result?.stdout, result?.stderr].filter(Boolean).join('\n')
    || result?.details
    || '';

  return (
    <div>
      {!embedded && (
      <div className="module-page-header">
        <h2 className="text-title-1">Cluster Diagnostic Suite</h2>
        <p className="page-lead">Assess pipeline environment layers, Python dependencies, and local tooling.</p>
      </div>
      )}

      <div className="panel" style={{ maxWidth: '750px' }}>
        <h3 className="panel-title"><Terminal size={18} /> Environment checkers</h3>
        <div className="form-group">
          <label className="form-label">Single checker</label>
          <select className="form-select" value={checker} onChange={(e) => setChecker(e.target.value)}>
            {CHECKERS.map((c) => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-primary" onClick={() => handleCheck(false)} disabled={loading}>
            {loading ? 'Running…' : 'Run selected checker'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => handleCheck(true)} disabled={loading}>
            Run full suite
          </button>
        </div>

        {result && (
          <div className="prose-block" style={{ marginTop: '1.5rem' }}>
            <div className="text-subhead" style={{ marginBottom: '0.75rem' }}>
              Status: <strong>{result.status}</strong>
            </div>
            <pre className="text-mono" style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{logText}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

/* ========================================================================= */
/* 8. ERROR TROUBLESHOOTER & LINUX CHEATSHEET                                */
/* ========================================================================= */
export function TroubleshooterTab({ API_URL, embedded = false }) {
  const [errorLogs, setErrorLogs] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeSec, setActiveSec] = useState('troubleshoot');

  const handleTroubleshoot = async (e) => {
    e.preventDefault();
    if (!errorLogs.trim() || loading) return;
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch(`${API_URL}/parse_log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ log_text: errorLogs }),
      });
      if (res.ok) {
        setResult(await res.json());
      } else {
        const err = await res.json().catch(() => ({}));
        setResult({ status: 'error', cause: err.detail || res.statusText });
      }
    } catch (e) {
      setResult({ status: 'error', cause: String(e) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {!embedded && (
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-danger)'}}>AI Stack Trace Analyzer</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Upload standard error streams from job fails to retrieve fast resolutions.</p>
      </div>
      )}

      <HubDetailFrame
        sections={[
          { id: 'troubleshoot', label: 'Log analyzer' },
          { id: 'linux_cli', label: 'Linux commands' },
        ]}
        active={activeSec}
        onChange={setActiveSec}
        ariaLabel="Troubleshooting views"
      >
      {activeSec === 'troubleshoot' && (
        <div className="panel" style={{maxWidth: '750px'}}>
          <h3 className="panel-title"><AlertCircle size={18} /> Troubleshoot Logs</h3>
          <form onSubmit={handleTroubleshoot}>
            <div className="form-group">
              <label className="form-label">Error Logs / Terminal Output</label>
              <textarea 
                className="form-textarea" 
                placeholder="Paste log traces here..." 
                value={errorLogs}
                onChange={(e) => setErrorLogs(e.target.value)}
                style={{fontFamily: 'var(--font-mono)', height: '150px'}}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Analyzing logs..." : "💡 Troubleshoot Error Trace"}
            </button>
          </form>

          {result && (
            <div className="prose-block" style={{ marginTop: '1.5rem' }}>
              <h4 className="text-headline callout-title-danger">Diagnosis</h4>
              <p className="text-body" style={{ marginBottom: '0.75rem' }}>{result.cause}</p>
              {result.recommended_fix && (
                <>
                  <h5 className="text-subhead" style={{ fontWeight: 600, marginBottom: '0.35rem' }}>Recommended fix</h5>
                  <p className="text-body-secondary">{result.recommended_fix}</p>
                </>
              )}
              {result.prevention && (
                <>
                  <h5 className="text-subhead" style={{ fontWeight: 600, marginTop: '0.75rem', marginBottom: '0.35rem' }}>Prevention</h5>
                  <p className="text-footnote">{result.prevention}</p>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {activeSec === 'linux_cli' && (
        <div className="panel">
          <h3 className="panel-title"><BookOpen size={18} /> Basic Linux Command Lines Reference</h3>
          <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
            Essential directory and file management tools for command line terminal environments:
          </p>

          <table className="table" style={{width: '100%', fontSize: '0.85rem', borderCollapse: 'collapse'}}>
            <thead>
              <tr style={{borderBottom: '1px solid var(--border-color)', textAlign: 'left'}}>
                <th style={{padding: '0.5rem', width: '200px'}}>Command</th>
                <th style={{padding: '0.5rem'}}>Usage</th>
                <th style={{padding: '0.5rem'}}>Example</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)'}}>pwd</td>
                <td style={{padding: '0.5rem'}}>Print Working Directory path</td>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)'}}>pwd</td>
              </tr>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)'}}>ls</td>
                <td style={{padding: '0.5rem'}}>List directory contents (add -la for hidden/details)</td>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)'}}>ls -la</td>
              </tr>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)'}}>cp -r &lt;src&gt; &lt;dst&gt;</td>
                <td style={{padding: '0.5rem'}}>Copy files or folders recursively</td>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)'}}>cp -r ./raw /data/backup/</td>
              </tr>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)'}}>mv &lt;src&gt; &lt;dst&gt;</td>
                <td style={{padding: '0.5rem'}}>Move or rename files/folders</td>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)'}}>mv slide1.tif slide1_qc.tif</td>
              </tr>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)'}}>rm &lt;file&gt;</td>
                <td style={{padding: '0.5rem'}}>Remove a single file</td>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)'}}>rm temp.txt</td>
              </tr>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)'}}>rm -rf &lt;dir&gt;</td>
                <td style={{padding: '0.5rem'}}>Delete a directory and all its contents (Use with care!)</td>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)'}}>rm -rf ./old_runs/</td>
              </tr>
              <tr style={{borderBottom: '1px solid rgba(255,255,255,0.02)'}}>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)'}}>tail -f &lt;file&gt;</td>
                <td style={{padding: '0.5rem'}}>Follow the end of a log file in real-time</td>
                <td style={{padding: '0.5rem', fontFamily: 'var(--font-mono)'}}>tail -f slurm-12345.out</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
      </HubDetailFrame>
    </div>
  );
}

/* ========================================================================= */
/* HUB COMPOSITE TABS (reorganized navigation)                                 */
/* ========================================================================= */

const LUMI_SECTIONS = [
  { id: 'jobs', label: 'Slurm jobs' },
  { id: 'pipeline', label: 'Imaging pipeline' },
];

function LumiHubTab({ dbProjects, API_URL, onNavigate, initialSection = 'jobs', onSectionChange }) {
  const [section, setSection] = useState(initialSection);

  useEffect(() => {
    setSection(initialSection);
  }, [initialSection]);

  const select = (id) => {
    setSection(id);
    onSectionChange?.(id);
  };

  return (
    <HubSectionFrame
      sections={LUMI_SECTIONS}
      active={section}
      onChange={select}
      ariaLabel="LUMI HPC sections"
      layout="horizontal"
    >
      {section === 'jobs' && <LumiJobTab dbProjects={dbProjects} API_URL={API_URL} embedded />}
      {section === 'pipeline' && (
        <ImageProcessingPipelineScreen
          dbProjects={dbProjects}
          API_URL={API_URL}
          embeddedInHub
        />
      )}
    </HubSectionFrame>
  );
}

const POUTA_SECTIONS = [
  { id: 'vms', label: 'VMs & specs' },
  { id: 'conda', label: 'VM conda setup' },
];

function PoutaHubTab({ API_URL, onNavigate, initialSection = 'vms', onSectionChange }) {
  const [section, setSection] = useState(initialSection);

  useEffect(() => {
    setSection(initialSection);
  }, [initialSection]);

  const select = (id) => {
    setSection(id);
    onSectionChange?.(id);
  };

  return (
    <HubSectionFrame sections={POUTA_SECTIONS} active={section} onChange={select} ariaLabel="cPouta sections">
      {section === 'vms' && <CpoutaVmTab API_URL={API_URL} onNavigate={onNavigate} embedded />}
      {section === 'conda' && <CondaEnvironmentTab onNavigate={onNavigate} variant="pouta" embedded />}
    </HubSectionFrame>
  );
}

function RoihuTab() {
  return (
    <div>
      <div className="panel">
        <h3 className="panel-title"><Cpu size={18} /> Coming soon</h3>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginBottom: '1rem' }}>
          Puhti is being phased out in favour of LUMI and Roihu. Use the LUMI HPC tab for active Slurm workflows today.
          Roihu-specific onboarding, module stacks, and pipeline templates will be documented in this section.
        </p>
        <div style={{ background: 'rgba(251,191,36,0.1)', borderLeft: '4px solid var(--color-warning)', padding: '1rem', borderRadius: '4px' }}>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
            See also <strong>Onboarding &amp; credentials</strong> for the Puhti → Roihu migration reminder and
            <strong> Utilities → Lumi-O transfer</strong> for scratch-to-bucket workflows.
          </p>
        </div>
      </div>
    </div>
  );
}

const TROUBLESHOOT_SECTIONS = [
  { id: 'diagnostics', label: 'Environment diagnostics' },
  { id: 'logs', label: 'Log analyzer' },
];

function TroubleshootingHubTab({ API_URL, initialSection = 'diagnostics', onSectionChange }) {
  const [section, setSection] = useState(initialSection);

  useEffect(() => {
    setSection(initialSection);
  }, [initialSection]);

  const select = (id) => {
    setSection(id);
    onSectionChange?.(id);
  };

  return (
    <HubSectionFrame sections={TROUBLESHOOT_SECTIONS} active={section} onChange={select} ariaLabel="Troubleshooting sections">
      {section === 'diagnostics' && <DiagnosticsTab API_URL={API_URL} embedded />}
      {section === 'logs' && <TroubleshooterTab API_URL={API_URL} embedded />}
    </HubSectionFrame>
  );
}

const UTILITIES_SECTIONS = [
  { id: 'file_ops', label: 'File operations' },
  { id: 'lumi_transfer', label: 'Lumi-O transfer' },
  { id: 'lumi_modules', label: 'LUMI modules & packages' },
  { id: 'conda', label: 'Conda environments' },
];

function UtilitiesHubTab({ API_URL, onNavigate, initialSection = 'file_ops', onSectionChange }) {
  const [section, setSection] = useState(initialSection);

  useEffect(() => {
    setSection(initialSection);
  }, [initialSection]);

  const select = (id) => {
    setSection(id);
    onSectionChange?.(id);
  };

  return (
    <HubSectionFrame sections={UTILITIES_SECTIONS} active={section} onChange={select} ariaLabel="Utilities sections">
      {section === 'file_ops' && <FileOperationsTab onNavigate={onNavigate} embedded />}
      {section === 'lumi_transfer' && <FileOperationsTab variant="lumi_transfer" embedded />}
      {section === 'lumi_modules' && <LumiModulesTab embedded />}
      {section === 'conda' && <CondaEnvironmentTab onNavigate={onNavigate} variant="core" embedded />}
    </HubSectionFrame>
  );
}

