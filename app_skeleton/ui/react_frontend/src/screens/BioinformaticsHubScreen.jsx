import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import { 
  Wrench, 
  Terminal, 
  Cpu, 
  ShieldCheck, 
  Database, 
  Play, 
  Settings, 
  AlertCircle, 
  ArrowRight, 
  Clipboard, 
  CheckCircle,
  HardDrive,
  UserCheck,
  Key,
  FolderOpen,
  Cloud,
  FileText,
  Activity,
  Video,
  Volume2,
  Lock,
  RefreshCw,
  Search,
  BookOpen
} from 'lucide-react';

export default function BioinformaticsHubScreen({ dbProjects, API_URL, activeSubTab, hideChrome = false }) {
  const [subTab, setSubTab] = useState(activeSubTab || 'onboarding');

  useEffect(() => {
    if (activeSubTab) setSubTab(activeSubTab);
  }, [activeSubTab]);

  const menuItems = [
    { id: 'onboarding', label: '🔑 Onboarding & Credentials' },
    { id: 'conda', label: '🐍 Conda & Environments' },
    { id: 'install', label: '⚙️ Tool Installations' },
    { id: 'file_ops', label: '🔐 File Operations' },
    { id: 'lumi', label: '💻 LUMI Supercomputing' },
    { id: 'pouta', label: '☁️ cPouta Cloud VMs' },
    { id: 'diagnostics', label: '🩺 System Diagnostic' },
    { id: 'troubleshoot', label: '🔍 Troubleshoot Logs' }
  ];

  return (
    <div style={{ display: 'flex', gap: hideChrome ? 0 : '2rem', minHeight: hideChrome ? 'auto' : 'calc(100vh - 8rem)' }}>
      {!hideChrome && (
      <div style={{width: '260px', flexShrink: 0, borderRight: '1px solid var(--border-color)', paddingRight: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
        <div style={{fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem', letterSpacing: '0.05em'}}>
          BIOINFORMATICS SERVICES
        </div>
        {menuItems.map(item => (
          <button
            key={item.id}
            className={`sidebar-item ${subTab === item.id ? 'active' : ''}`}
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
              color: subTab === item.id ? '#ffffff' : 'var(--text-secondary)'
            }}
          >
            <span style={{fontSize: '0.9rem'}}>{item.label}</span>
          </button>
        ))}
      </div>
      )}

      <div style={{ flexGrow: 1, minWidth: 0 }}>
        {subTab === 'onboarding' && <OnboardingTab />}
        {subTab === 'conda' && <CondaEnvironmentTab />}
        {subTab === 'install' && <InstallSoftwareTab API_URL={API_URL} />}
        {subTab === 'file_ops' && <FileOperationsTab />}
        {subTab === 'lumi' && <LumiJobTab dbProjects={dbProjects} API_URL={API_URL} />}
        {subTab === 'pouta' && <CpoutaVmTab API_URL={API_URL} />}
        {subTab === 'diagnostics' && <DiagnosticsTab API_URL={API_URL} />}
        {subTab === 'troubleshoot' && <TroubleshooterTab API_URL={API_URL} />}
      </div>

    </div>
  );
}

/* ========================================================================= */
/* COPY CLIPBOARD UTILITY                                                    */
/* ========================================================================= */
function CopyableCodeBlock({ code, type = 'success' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getAccentColor = () => {
    if (type === 'primary') return 'var(--color-primary)';
    if (type === 'warning') return 'var(--color-warning)';
    if (type === 'danger') return 'var(--color-danger)';
    return 'var(--color-success)';
  };

  return (
    <div style={{position: 'relative', marginTop: '0.5rem', marginBottom: '1rem'}}>
      <pre className="code-block" style={{
        color: getAccentColor(),
        background: 'rgba(0,0,0,0.4)', 
        padding: '1rem', 
        borderRadius: '8px',
        overflowX: 'auto',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.85rem',
        border: '1px solid var(--border-color)',
        whiteSpace: 'pre'
      }}>{code}</pre>
      <button 
        className="btn btn-secondary" 
        onClick={handleCopy}
        style={{
          position: 'absolute', 
          right: '10px', 
          top: '10px', 
          padding: '0.25rem 0.6rem', 
          fontSize: '0.75rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.25rem',
          background: 'var(--bg-surface)',
          borderColor: 'var(--border-color)'
        }}
      >
        {copied ? '✓ Copied' : 'Copy'}
      </button>
    </div>
  );
}

/* ========================================================================= */
/* 1. ONBOARDING & ACCESS                                                    */
/* ========================================================================= */
function OnboardingTab() {
  const [activeSec, setActiveSec] = useState('flowchart');

  const steps = [
    { num: '1', title: 'Get Access', desc: 'Create CSC account & request project membership (project_462001415)' },
    { num: '2', title: 'Local Setup', desc: 'Generate Ed25519 SSH keys & upload to MyCSC portal' },
    { num: '3', title: 'Data Setup', desc: 'Configure Allas / LUMI storage remotes for project files' },
    { num: '4', title: 'Platform Select', desc: 'Determine target host: LUMI (heavy computing) or cPouta (custom VMs)' },
    { num: '5', title: 'Running Jobs', desc: 'Prepare slurm script & submit via sbatch to compute queues' },
    { num: '6', title: 'Review & Store', desc: 'Collect logs, store long‑term dataset backups in Allas storage' },
    { num: '7', title: 'Lab Standard', desc: 'Follow file-naming SOP & log computing node allocations' }
  ];

  return (
    <div>
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary)'}}>Onboarding & Credentials</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Standard Operating Procedures for onboarding new researchers and establishing secure computing access.</p>
      </div>

      {/* Onboarding Interactive Flowchart */}
      <div className="panel" style={{marginBottom: '2rem'}}>
        <h3 className="panel-title" style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
          <Activity size={18} /> Computational Onboarding Workflow Flowchart
        </h3>
        <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem'}}>
          Interactive step-by-step roadmap for new members of the Färkkilä Lab to begin analytical work on CSC HPC platforms. Click any step to read related documentation.
        </p>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          position: 'relative'
        }}>
          <div className="grid-4col" style={{gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem'}}>
            {steps.map((st) => (
              <div 
                key={st.num} 
                style={{
                  background: 'var(--bg-app)', 
                  border: '1px solid var(--border-color)', 
                  borderRadius: '8px', 
                  padding: '1rem', 
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                  transition: 'all 0.3s ease',
                  cursor: 'pointer'
                }}
                onClick={() => {
                  if (st.num === '1') setActiveSec('account');
                  else if (st.num === '2') setActiveSec('ssh_gen');
                  else if (st.num === '3') setActiveSec('data_mgmt');
                  else setActiveSec('flowchart');
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-primary)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                  e.currentTarget.style.transform = 'none';
                }}
              >
                <div style={{
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  borderBottom: '1px solid var(--border-color)',
                  paddingBottom: '0.5rem'
                }}>
                  <span style={{
                    fontSize: '0.8rem', 
                    fontWeight: 800, 
                    background: 'var(--bg-badge)', 
                    color: 'var(--color-primary)', 
                    padding: '0.1rem 0.5rem', 
                    borderRadius: '4px'
                  }}>STEP 0{st.num}</span>
                  <span style={{color: 'var(--text-muted)'}}>→</span>
                </div>
                <h4 style={{fontSize: '0.9rem', color: '#ffffff', margin: 0}}>{st.title}</h4>
                <p style={{fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: 0}}>{st.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Internal Navigation Tabs */}
      <div style={{display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1.5rem'}}>
        <button 
          onClick={() => setActiveSec('flowchart')} 
          className={`btn ${activeSec === 'flowchart' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          📋 Lab Workflow Standard
        </button>
        <button 
          onClick={() => setActiveSec('account')} 
          className={`btn ${activeSec === 'account' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          👤 Account Creation
        </button>
        <button 
          onClick={() => setActiveSec('ssh_gen')} 
          className={`btn ${activeSec === 'ssh_gen' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          🔑 SSH Key Generation
        </button>
        <button 
          onClick={() => setActiveSec('ssh_setup')} 
          className={`btn ${activeSec === 'ssh_setup' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          🛡️ SSH Access (Admins)
        </button>
      </div>

      {/* Sub-tab content panels */}
      {activeSec === 'flowchart' && (
        <div className="panel">
          <h3 className="panel-title"><UserCheck size={18} /> Färkkilä Lab HPC Workflow Standards</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '1rem'}}>
            The following guidelines ensure consistent, secure, and reproducible computational workflows across all cluster projects (SPACE, EyeMT, KRAS) within our research group:
          </p>
          <ul style={{fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, paddingLeft: '1.5rem', marginBottom: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
            <li><b>Directory Conventions:</b> Always store temporary data under <code>/scratch/project_462XXXXXX/username/</code> and applications/binaries in <code>/projappl/project_462XXXXXX/</code>.</li>
            <li><b>Slurm Exclusivity:</b> Execute all processing workloads (Ashlar, Mesmer, Cylinter) via Slurm tasks. Avoid running jobs on the login nodes to prevent system overload blocks.</li>
            <li><b>Containerization Standards:</b> Utilize Apptainer/Singularity containers for standard pipelines to guarantee version and configuration reproducibility.</li>
            <li><b>Cold Storage Backups:</b> Upload completed datasets and raw WSI slides to <b>Allas</b> storage under the appropriate project bucket with descriptive metadata.</li>
            <li><b>Data Cleaning Days:</b> Participate in quarterly group data cleanup runs. Delete temporary intermediate files and verify backups.</li>
          </ul>

          <div style={{background: 'rgba(251,191,36,0.1)', borderLeft: '4px solid var(--color-warning)', padding: '1rem', borderRadius: '4px'}}>
            <h4 style={{color: 'var(--color-warning)', fontSize: '0.9rem', marginBottom: '0.25rem', fontWeight: 600}}>⚠️ Migration Reminder: Puhti → Roihu</h4>
            <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0}}>
              CSC is currently phasing out the Puhti supercomputer. All lab members must transfer project datasets to Lumi/Roihu using the provided rclone commands, update active singularity configuration profiles, and test pipelines early.
            </p>
          </div>
        </div>
      )}

      {activeSec === 'account' && (
        <div className="panel">
          <h3 className="panel-title"><UserCheck size={18} /> Creating and Activating a CSC Account</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.25rem'}}>
            CSC resources are project-based. Follow this sequence to establish and register your login account:
          </p>
          
          <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
            <div style={{background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '6px', border: '1px solid var(--border-color)'}}>
              <h4 style={{fontSize: '0.95rem', color: '#ffffff', marginBottom: '0.5rem'}}>Step 1: Create Account</h4>
              <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0}}>
                Visit the CSC Customer Portal at <a href="https://my.csc.fi" target="_blank" rel="noreferrer" style={{color: 'var(--color-primary)'}}>my.csc.fi</a>, select "Create new account", and authenticate using your University <b>Haka login</b> credentials. Fill out details and confirm your email. Note your generated CSC username.
              </p>
            </div>

            <div style={{background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '6px', border: '1px solid var(--border-color)'}}>
              <h4 style={{fontSize: '0.95rem', color: '#ffffff', marginBottom: '0.5rem'}}>Step 2: Join Project</h4>
              <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0}}>
                Provide your CSC username to the project manager. The manager will add your account to our active projects (e.g., <code>project_462001415</code>) in the MyCSC system. You will receive an automated email confirmation once approved.
              </p>
            </div>

            <div style={{background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '6px', border: '1px solid var(--border-color)'}}>
              <h4 style={{fontSize: '0.95rem', color: '#ffffff', marginBottom: '0.5rem'}}>Step 3: Access Activation</h4>
              <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0}}>
                Upon joining the project, accept the terms of service for the target supercomputing hosts (Puhti, Lumi, or Allas storage). Your account is now provisioned and waiting for your SSH public key injection.
              </p>
            </div>
          </div>
        </div>
      )}

      {activeSec === 'ssh_gen' && (
        <div className="panel">
          <h3 className="panel-title"><Key size={18} /> SSH Key Pair Generation</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.25rem'}}>
            CSC services strictly enforce SSH key-based authentication. Password-based logins are disabled. Use the instructions below to generate your keys.
          </p>

          <div style={{background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
            <h4 style={{fontSize: '1rem', color: '#ffffff', marginBottom: '0.75rem'}}>Option A: macOS & Linux Terminal</h4>
            <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>
              Open the Terminal app, check if keys exist with <code>ls ~/.ssh</code>. If empty, generate a secure Ed25519 pair:
            </p>
            <CopyableCodeBlock code={`ssh-keygen -t ed25519 -C "your_email@example.com"`} type="primary" />
            <p style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>
              Press Enter to accept the default folder location (<code>~/.ssh/id_ed25519</code>) and enter a strong passphrase. Display the public key:
            </p>
            <CopyableCodeBlock code={`cat ~/.ssh/id_ed25519.pub`} type="primary" />
          </div>

          <div style={{background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)', marginTop: '1rem'}}>
            <h4 style={{fontSize: '1rem', color: '#ffffff', marginBottom: '0.75rem'}}>Option B: Windows PowerShell</h4>
            <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>
              Open Windows PowerShell and check directory contents. Generate the key:
            </p>
            <CopyableCodeBlock code={`ssh-keygen -t ed25519 -C "your_email@example.com"`} type="primary" />
            <p style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>
              Accept default location and display the public key to copy:
            </p>
            <CopyableCodeBlock code={`type $env:USERPROFILE\\.ssh\\id_ed25519.pub`} type="primary" />
          </div>

          <div style={{background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)', marginTop: '1rem'}}>
            <h4 style={{fontSize: '1rem', color: '#ffffff', marginBottom: '0.75rem'}}>Option C: MobaXterm GUI (Windows Workstations)</h4>
            <ul style={{fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem'}}>
              <li>Install MobaXterm (use the Portable Edition if you do not have administrator install rights).</li>
              <li>Go to the main menu and select: <b>Tools → SSH-key generator (MobaKeyGen)</b>.</li>
              <li>Select key type: <b>EdDSA (Ed25519)</b> and click <b>Generate</b>. Move your mouse cursor in the empty block to create randomness.</li>
              <li>Save both the Private Key (somewhere safe) and copy the full public key string shown in the text field at the top to send to the admin or upload to MyCSC.</li>
            </ul>
          </div>
        </div>
      )}

      {activeSec === 'ssh_setup' && (
        <div className="panel">
          <h3 className="panel-title"><Lock size={18} /> SSH User Provisioning (Administrator Guide)</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
            Färkkilä Lab virtual machines (cPouta VMs) are isolated, meaning admins must provision users and key bindings manually on each virtual machine.
          </p>

          <h4 style={{fontSize: '0.95rem', color: '#ffffff', marginBottom: '0.5rem'}}>Normal User Creation Script:</h4>
          <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)'}}>
            Login to target server (e.g. <code>farkkila-gpu1</code>) as root. Select next available UID from <code>/etc/passwd</code> and run:
          </p>
          
          <CopyableCodeBlock code={`export USERNAME="debdebas"
export USERID="1105"
export REALNAME="Debashish Deb"

# Create user with primary group farkkilab
sudo useradd --home /home/\${USERNAME} --shell /bin/bash --gid farkkilab --uid \${USERID} -c "\${REALNAME}" \${USERNAME}

# Set up .ssh directory
sudo mkdir -p /home/\${USERNAME}/.ssh
sudo chown -R \${USERNAME}:farkkilab /home/\${USERNAME}

# Insert public key into authorized_keys file
sudo vi /home/\${USERNAME}/.ssh/authorized_keys # Paste key
sudo chown \${USERNAME}:farkkilab /home/\${USERNAME}/.ssh/authorized_keys
sudo chmod 600 /home/\${USERNAME}/.ssh/authorized_keys
sudo chmod 700 /home/\${USERNAME}/.ssh/.ssh`} type="success" />

          <h4 style={{fontSize: '0.95rem', color: '#ffffff', marginTop: '1.5rem', marginBottom: '0.5rem'}}>User Permissions SOP (Umask configuration)</h4>
          <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>
            To ensure files created by an individual user are editable and readable by other members of the group, enforce group-write permissions by default. Append the umask parameters to their <code>.bashrc</code>:
          </p>
          <CopyableCodeBlock code={`echo "umask 0002" | sudo tee -a /home/\${USERNAME}/.bashrc`} type="success" />
        </div>
      )}
    </div>
  );
}

/* ========================================================================= */
/* 2. ANACONDA & CONDA ENVIRONMENTS                                          */
/* ========================================================================= */
function CondaEnvironmentTab() {
  const [activeSec, setActiveSec] = useState('core');

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

  return (
    <div>
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary)'}}>Anaconda & Environment SOP</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Standardized configuration steps to clone and maintain cluster environments.</p>
      </div>

      <div style={{display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1.5rem'}}>
        <button 
          onClick={() => setActiveSec('core')} 
          className={`btn ${activeSec === 'core' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          🐍 Core Environment Setup
        </button>
        <button 
          onClick={() => setActiveSec('pouta_env')} 
          className={`btn ${activeSec === 'pouta_env' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          ☁️ cPouta VM Miniconda Setup
        </button>
        <button 
          onClick={() => setActiveSec('storage')} 
          className={`btn ${activeSec === 'storage' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          💾 Storage Management
        </button>
      </div>

      {activeSec === 'core' && (
        <div>
          <div className="panel">
            <h3 className="panel-title"><Terminal size={18} /> Core Environment Setup</h3>
            <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
              We use isolated environments with **Python 3.10** for spatial deconvolution and image stitching. To install the unified environment on the local cluster or LUMI supercomputing space, run the following:
            </p>
            <CopyableCodeBlock code={condaScript} type="primary" />
          </div>

          <div className="grid-2col" style={{marginTop: '1.5rem'}}>
            <div className="panel">
              <h4 style={{color: '#ffffff', marginBottom: '0.5rem', fontSize: '0.95rem'}}>Exporting Environment Variables</h4>
              <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>To save the active package configurations into an environment file for portability:</p>
              <pre className="code-block" style={{fontSize: '0.8rem'}}>conda env export --no-builds &gt; environment.yml</pre>
            </div>
            <div className="panel">
              <h4 style={{color: '#ffffff', marginBottom: '0.5rem', fontSize: '0.95rem'}}>Recreating Environment from YML</h4>
              <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>To recreate the dependencies from a git repository file:</p>
              <pre className="code-block" style={{fontSize: '0.8rem'}}>conda env create -f environment.yml</pre>
            </div>
          </div>
        </div>
      )}

      {activeSec === 'pouta_env' && (
        <div className="panel">
          <h3 className="panel-title"><Terminal size={18} /> Setting Up Miniconda on CSC Pouta VMs</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
            cPouta instances are vanilla VMs. To configure Python 3.11 with Miniconda for user-specific development pipelines:
          </p>
          <CopyableCodeBlock code={minicondaPouta} type="success" />

          <h4 style={{fontSize: '0.95rem', color: '#ffffff', marginTop: '1.5rem', marginBottom: '0.5rem'}}>Conda Environment Best Practices:</h4>
          <ul style={{fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem'}}>
            <li>Keep environments lightweight and specific. Do not install unrelated tools in the same environment.</li>
            <li>Clear cached directories regularly using <code>conda clean -a</code> to free root disk space.</li>
            <li>Always ensure packages are pulled from <code>conda-forge</code> for linux compatibility.</li>
          </ul>
        </div>
      )}

      {activeSec === 'storage' && (
        <div className="panel">
          <h3 className="panel-title"><Database size={18} /> Pouta VM Data Storage & Workspaces</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
            To keep root drives free and prevent system crash failures, follow these strict volume allocation principles:
          </p>
          
          <ul style={{fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, paddingLeft: '1.5rem', marginBottom: '1.5rem'}}>
            <li><b>Home Directory:</b> Restrict <code>/home/username</code> strictly to config files, git repositories, and lightweight scripts. Do not write data here.</li>
            <li><b>Data Volume:</b> Store all active raw slide files, packages, and stitching output under the persistent 2 TB storage mounted at <code>/data</code>.</li>
            <li><b>Personal Folder:</b> Create a dedicated directory for your account: <code>mkdir -p /data/$USER</code>.</li>
          </ul>

          <h4 style={{fontSize: '0.95rem', color: '#ffffff', marginBottom: '0.5rem'}}>Symlinking large datasets from /data to home:</h4>
          <CopyableCodeBlock code={`# Move folder to /data
mv ~/large_dataset /data/$USER/
# Create a symbolic link in home
ln -s /data/$USER/large_dataset ~/large_dataset`} type="primary" />

          <h4 style={{fontSize: '0.95rem', color: '#ffffff', marginTop: '1.5rem', marginBottom: '0.5rem'}}>Disk Usage Audit Commands:</h4>
          <CopyableCodeBlock code={`# Check personal directory size
du -sh /data/$USER

# Verify overall system disk volume percentages
df -h`} type="primary" />
        </div>
      )}
    </div>
  );
}

/* ========================================================================= */
/* 3. SOFTWARE TOOL INSTALLATIONS                                            */
/* ========================================================================= */
export function InstallSoftwareTab({ API_URL }) {
  const [software, setSoftware] = useState('ashlar');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeSec, setActiveSec] = useState('generator');

  const handleInstall = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/install_guide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ package_name: software })
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

  const folderStructureLumi = `# Move to work scratch directory
cd /scratch/project_462XXXXXX/username/

# Establish structured directories for pipeline consistency
mkdir -p data/raw
mkdir -p data/stitched
mkdir -p data/masks
mkdir -p scripts/0_illumination
mkdir -p scripts/1_stitching
mkdir -p scripts/2_segmentation

# Upload your raw slide files into the data/raw folder
# Upload your execution python/shell scripts into scripts/`;

  const napariLumi = `# 1. Log in to the LUMI web UI: https://www.lumi.csc.fi/
# 2. Select 'Desktop' option from menu tools
# 3. Configure the Launch parameters:
#    - Compression: 0
#    - Image Quality: 9
#    - Partition: small-g (if using GPU visualization) or small
# 4. Once Desktop is ready and launched, open Terminal Emulator.
# 5. Execute the singularity container to run Napari viewer:
cd ~/Desktop
singularity run --nv napari-xtra.sif napari_fast_masking.py

# 6. Inside Napari, load your slide image and features CSV from scratch:
#    File -> Open -> Computer -> select root drive -> search 'scratch'
#    Open: /scratch/project_462001305/ -> choose target datasets.`;

  return (
    <div>
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-success)'}}>Bioinformatics Tool Installation</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Dynamic guide generators to install spatial-biology packages on server environments.</p>
      </div>

      <div style={{display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1.5rem'}}>
        <button 
          onClick={() => setActiveSec('generator')} 
          className={`btn ${activeSec === 'generator' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          ⚙️ Installer Guide Generator
        </button>
        <button 
          onClick={() => setActiveSec('lumi_folders')} 
          className={`btn ${activeSec === 'lumi_folders' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          📂 LUMI Folder Standards
        </button>
        <button 
          onClick={() => setActiveSec('napari_lumi')} 
          className={`btn ${activeSec === 'napari_lumi' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          🎥 running Napari in LUMI
        </button>
      </div>

      {activeSec === 'generator' && (
        <div className="panel" style={{maxWidth: '650px'}}>
          <h3 className="panel-title"><Settings size={18} /> Choose Package to Install</h3>
          <div className="form-group">
            <label className="form-label">Spatial Toolbox Package</label>
            <select className="form-select" value={software} onChange={(e) => setSoftware(e.target.value)}>
              <option value="ashlar">Ashlar (Stitching & Registration)</option>
              <option value="stardist">Stardist (Nuclei Cell Segmentation)</option>
              <option value="cylinter">Cylinter (Gating QC & Normalization)</option>
              <option value="spacestat">SPACEstat (Spatial joint analytics)</option>
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleInstall} disabled={loading}>
            {loading ? "Generating setup guide..." : "⚙️ Fetch Installation Guide"}
          </button>

          {result && (
            <div style={{marginTop: '1.5rem', background: 'rgba(0,0,0,0.3)', padding: '1.5rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
              <h4 style={{color: 'var(--color-primary)', marginBottom: '0.5rem'}}>Installation Command:</h4>
              <code style={{background: '#000', padding: '0.5rem 1rem', borderRadius: '4px', display: 'block', color: 'var(--color-success)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', marginBottom: '1rem'}}>{result.install_command}</code>
              <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.5}}>{result.instructions}</p>
            </div>
          )}
        </div>
      )}

      {activeSec === 'lumi_folders' && (
        <div className="panel">
          <h3 className="panel-title"><FolderOpen size={18} /> LUMI Project Workspace Conventions</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
            To run image processing pipelines (CEFIIRA/UTAG) seamlessly, configure your project scratch folders using the following layout parameters:
          </p>
          <CopyableCodeBlock code={folderStructureLumi} type="success" />
        </div>
      )}

      {activeSec === 'napari_lumi' && (
        <div className="panel">
          <h3 className="panel-title"><Video size={18} /> running Napari GUI in LUMI Desktops</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
            Napari is a graphical multi-dimensional image viewer. Since the slides are massive, run Napari inside the LUMI virtual desktop to inspect segmentation boundaries locally:
          </p>
          <CopyableCodeBlock code={napariLumi} type="success" />
        </div>
      )}
    </div>
  );
}

/* ========================================================================= */
/* 4. FILE OPERATIONS & TRANSFERS                                            */
/* ========================================================================= */
function FileOperationsTab() {
  const [activeSec, setActiveSec] = useState('guides');
  const [activeGuideSub, setActiveGuideSub] = useState('lumi_o');

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

  return (
    <div>
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-accent)'}}>File Operations SOP</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Standard guidelines for transfer, compression, and encryption of large raw image directories.</p>
      </div>

      {/* Main sub-tabs for File Operations */}
      <div style={{display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1.5rem'}}>
        <button 
          onClick={() => setActiveSec('guides')} 
          className={`btn ${activeSec === 'guides' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          📂 File Transfer Guides
        </button>
        <button 
          onClick={() => setActiveSec('cheatsheet')} 
          className={`btn ${activeSec === 'cheatsheet' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          📝 rclone CLI Cheatsheet
        </button>
        <button 
          onClick={() => setActiveSec('crypto')} 
          className={`btn ${activeSec === 'crypto' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          🔐 Compression & Encryption
        </button>
      </div>

      {/* 4.1 FILE TRANSFER GUIDES SUB-TAB */}
      {activeSec === 'guides' && (
        <div style={{display: 'flex', gap: '1.5rem'}}>
          
          {/* Sub navigation side pills */}
          <div style={{width: '220px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '0.25rem'}}>
            <button 
              onClick={() => setActiveGuideSub('lumi_o')} 
              className={`sidebar-item ${activeGuideSub === 'lumi_o' ? 'active' : ''}`}
              style={{border: 'none', background: 'none', textAlign: 'left', padding: '0.5rem 0.75rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem'}}
            >
              💻 LUMI & Lumi-O S3
            </button>
            <button 
              onClick={() => setActiveGuideSub('csc_dc')} 
              className={`sidebar-item ${activeGuideSub === 'csc_dc' ? 'active' : ''}`}
              style={{border: 'none', background: 'none', textAlign: 'left', padding: '0.5rem 0.75rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem'}}
            >
              🏢 CSC to Datacloud
            </button>
            <button 
              onClick={() => setActiveGuideSub('local_allas')} 
              className={`sidebar-item ${activeGuideSub === 'local_allas' ? 'active' : ''}`}
              style={{border: 'none', background: 'none', textAlign: 'left', padding: '0.5rem 0.75rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem'}}
            >
              🏠 Workstation to Allas
            </button>
            <button 
              onClick={() => setActiveGuideSub('cyberduck')} 
              className={`sidebar-item ${activeGuideSub === 'cyberduck' ? 'active' : ''}`}
              style={{border: 'none', background: 'none', textAlign: 'left', padding: '0.5rem 0.75rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem'}}
            >
              🦢 Cyberduck Swift GUI
            </button>
          </div>

          {/* Guide Display Panel */}
          <div style={{flexGrow: 1}}>
            {activeGuideSub === 'lumi_o' && (
              <div className="panel" style={{margin: 0}}>
                <h4 style={{color: '#ffffff', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                  <Cloud size={16} /> File Transfer in LUMI / Lumi-O Connection
                </h4>
                <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
                  LUMI does not utilize standard Allas Swift protocols for object storage. Instead, LUMI uses **Lumi-O** (S3-compatible Object Storage). Connect and transfer using the following commands:
                </p>
                <CopyableCodeBlock code={rcloneLumiO} type="primary" />
              </div>
            )}

            {activeGuideSub === 'csc_dc' && (
              <div className="panel" style={{margin: 0}}>
                <h4 style={{color: '#ffffff', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
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
                <h4 style={{color: '#ffffff', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
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
                <h4 style={{color: '#ffffff', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                  <Cloud size={16} /> Graphical Transfer: Using Allas with Cyberduck
                </h4>
                <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
                  For macOS and Windows users who prefer a graphical user interface instead of rclone shell command lines:
                </p>
                <pre style={{
                  background: 'rgba(0,0,0,0.15)',
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
        </div>
      )}

      {/* 4.2 RCLONE CHEATSHEET SUB-TAB */}
      {activeSec === 'cheatsheet' && (
        <div className="panel">
          <h3 className="panel-title"><FileText size={18} /> rclone CLI Cheatsheet</h3>
          <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem'}}>
            Quick command references for copying files between local paths, cPouta object stores, and Datacloud.
          </p>
          <CopyableCodeBlock code={rcloneCheatsheetCode} type="success" />
        </div>
      )}

      {/* 4.3 CRYPTO & ENCRYPTION SUB-TAB */}
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
    </div>
  );
}

/* ========================================================================= */
/* 5. LUMI SLURM JOBS                                                        */
/* ========================================================================= */
export function LumiJobTab({ dbProjects, API_URL }) {
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

  return (
    <div>
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary)'}}>LUMI HPC Job Script Generator</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Configure cluster scripts to run parallel stitching and segmentations.</p>
      </div>

      <div style={{display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1.5rem'}}>
        <button 
          onClick={() => setActiveSec('generator')} 
          className={`btn ${activeSec === 'generator' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          💻 Script Generator
        </button>
        <button 
          onClick={() => setActiveSec('status')} 
          className={`btn ${activeSec === 'status' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          🩺 Checking Slurm Status
        </button>
      </div>

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
              <h4 style={{color: '#ffffff', marginBottom: '0.5rem'}}>Slurm Script Code:</h4>
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
            <h4 style={{color: '#ffffff', marginBottom: '0.75rem', fontSize: '0.95rem'}}>Common Slurm Job State Codes</h4>
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
    </div>
  );
}

/* ========================================================================= */
/* 6. cPOUTA CLOUD VM MANAGEMENT & MEDIA                                     */
/* ========================================================================= */
function CpoutaVmTab({ API_URL }) {
  const [activeSec, setActiveSec] = useState('specs');

  return (
    <div>
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary)'}}>cPouta Cloud Virtual Machines</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Deploy, configure, and manage custom virtual machine environments on CSC Pouta infrastructure.</p>
      </div>

      <div style={{display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1.5rem'}}>
        <button 
          onClick={() => setActiveSec('specs')} 
          className={`btn ${activeSec === 'specs' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          🖥️ VM Servers & Specs
        </button>
        <button 
          onClick={() => setActiveSec('creation')} 
          className={`btn ${activeSec === 'creation' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          ⚙️ VM Creation Guide
        </button>
        <button 
          onClick={() => setActiveSec('media')} 
          className={`btn ${activeSec === 'media' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          🎥 Training Media Memos
        </button>
      </div>

      {activeSec === 'specs' && (
        <div>
          <div className="panel">
            <h3 className="panel-title"><Cloud size={18} /> Active cPouta VM Instances</h3>
            <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.5rem'}}>
              Our laboratory maintains three virtual machines on CSC cPouta for custom packages and services not supported on the main LUMI nodes:
            </p>

            <div className="grid-3col" style={{gap: '1rem'}}>
              <div style={{background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                <h4 style={{fontSize: '1rem', color: 'var(--color-primary)', margin: '0 0 0.5rem 0'}}>farkkila-gpu1</h4>
                <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 0.75rem 0'}}>
                  <b>OS:</b> Ubuntu 16.04 (CUDA-enabled)<br/>
                  <b>Flavor:</b> gpu.1.2.gpu (RTX VM)<br/>
                  <b>IP:</b> 128.214.253.252<br/>
                  <b>Host:</b> vm2749.kaj.pouta.csc.fi
                </p>
                <span style={{fontSize: '0.75rem', background: 'rgba(45,212,191,0.1)', color: 'var(--color-primary)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontWeight: 'bold'}}>GPU pipelines & Avivator</span>
              </div>

              <div style={{background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                <h4 style={{fontSize: '1rem', color: 'var(--color-primary)', margin: '0 0 0.5rem 0'}}>farkkila-cpu1</h4>
                <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 0.75rem 0'}}>
                  <b>OS:</b> Ubuntu 18.04 LTS<br/>
                  <b>Flavor:</b> hpc-gen2.48core<br/>
                  <b>IP:</b> 195.148.21.14<br/>
                  <b>Host:</b> vm2794.kaj.pouta.csc.fi
                </p>
                <span style={{fontSize: '0.75rem', background: 'rgba(13,148,136,0.1)', color: 'var(--color-primary)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontWeight: 'bold'}}>Cyto App (port 9999)</span>
              </div>

              <div style={{background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
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
            <h4 style={{color: '#ffffff', marginBottom: '0.75rem', fontSize: '1rem'}}>NFS Shared Storage Volumes</h4>
            <p style={{fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5}}>
              A persistent 2 TB storage volume is mounted directly on <code>farkkila-gpu1</code> at <code>/data</code>, acting as an NFS server. <code>farkkila-cpu1</code> and <code>farkkila-cpu2</code> mount this directory client-side. NFS exports settings are in <code>/etc/exports</code>:
            </p>
            <pre className="code-block" style={{fontSize: '0.8rem', color: 'var(--color-warning)'}}>{`/data 192.168.1.7(rw,sync,no_subtree_check,no_root_squash) 192.168.1.12(rw,sync,no_subtree_check,no_root_squash)`}</pre>
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
            <div style={{background: 'rgba(0,0,0,0.2)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
              <h4 style={{color: '#ffffff', marginBottom: '0.75rem', fontSize: '0.95rem'}}>1. cPouta Setup Video Walkthrough</h4>
              <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>Screen recording of SSH key binding and network routers layout.</p>
              <video 
                controls 
                style={{width: '100%', borderRadius: '4px', background: '#000', maxHeight: '360px'}}
                src={`${API_URL}/csc-media/Cpouta%20User%20setup/video1003837229.mp4`}
              />
            </div>

            <div style={{background: 'rgba(0,0,0,0.2)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
              <h4 style={{color: '#ffffff', marginBottom: '0.75rem', fontSize: '0.95rem'}}>2. VM Instance Creation & Shell Run</h4>
              <p style={{fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem'}}>Console run recording detailing useradd actions and ports checking.</p>
              <video 
                controls 
                style={{width: '100%', borderRadius: '4px', background: '#000', maxHeight: '360px'}}
                src={`${API_URL}/csc-media/Cpouta%20User%20setup/video2003837229.mp4`}
              />
            </div>

            <div style={{background: 'rgba(0,0,0,0.2)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
              <h4 style={{color: '#ffffff', marginBottom: '0.75rem', fontSize: '0.95rem'}}>3. cPouta Audio Memo Notes</h4>
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
    </div>
  );
}

/* ========================================================================= */
/* 7. SYSTEM DIAGNOSTICS                                                     */
/* ========================================================================= */
export function DiagnosticsTab({ API_URL }) {
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
      <div className="module-page-header">
        <h2 className="text-title-1">Cluster Diagnostic Suite</h2>
        <p className="page-lead">Assess pipeline environment layers, Python dependencies, and local tooling.</p>
      </div>

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
export function TroubleshooterTab({ API_URL }) {
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
      <div className="page-header" style={{marginBottom: '1.5rem'}}>
        <h2 style={{fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-danger)'}}>AI Stack Trace Analyzer</h2>
        <p style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>Upload standard error streams from job fails to retrieve fast resolutions.</p>
      </div>

      <div style={{display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1.5rem'}}>
        <button 
          onClick={() => setActiveSec('troubleshoot')} 
          className={`btn ${activeSec === 'troubleshoot' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          💡 Analyzer Tools
        </button>
        <button 
          onClick={() => setActiveSec('linux_cli')} 
          className={`btn ${activeSec === 'linux_cli' ? 'btn-primary' : 'btn-secondary'}`}
          style={{padding: '0.5rem 1rem', fontSize: '0.85rem'}}
        >
          🐧 Linux Commands
        </button>
      </div>

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
    </div>
  );
}
