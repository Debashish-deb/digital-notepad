import { useState } from 'react';
import {
  Activity,
  ChevronDown,
  ExternalLink,
  Key,
  Lock,
  Mail,
  Server,
  ShieldCheck,
  Terminal,
  UserCheck,
} from 'lucide-react';
import { CopyableCodeBlock } from '@/shared/ui/common/CopyableCodeBlock.jsx';
import './OnboardingRoadmap.css';

const EXAMPLE_PROJECT_ID = 'project_462001415';
const PM_NAME = 'Debashish Deb';
const PM_EMAIL = 'debashish.deb@helsinki.fi';

const EXTERNAL_LINKS = {
  myCsc: 'https://my.csc.fi',
  cscAccount: 'https://docs.csc.fi/accounts/index.html',
  cscHaka: 'https://docs.csc.fi/accounts/accounts.html#logging-in-with-haka',
  cscProjects: 'https://docs.csc.fi/accounts/accounts.html#joining-a-project',
  cscSsh: 'https://docs.csc.fi/computing/connecting.html',
  cscSshKeys: 'https://docs.csc.fi/computing/connecting.html#setting-up-ssh-keys',
  lumiConnect: 'https://docs.lumi-supercomputer.eu/runjobs/Connecting_to_LUMI/',
  allas: 'https://docs.csc.fi/data/Allas/usage/',
  lumiStorage: 'https://docs.lumi-supercomputer.eu/storage/',
  mobaxterm: 'https://mobaxterm.mobatek.net/download.html',
};

function LinkChips({ links }) {
  return (
    <div className="onb-links">
      {links.map((link) => (
        <span key={link.href} className="onb-link-chip">
          <ExternalLink size={11} aria-hidden />
          <a href={link.href} target="_blank" rel="noreferrer">{link.label}</a>
        </span>
      ))}
    </div>
  );
}

function CollapsibleBlock({ title, children, links, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={`onb-block${isOpen ? ' is-open' : ''}`}>
      <button
        type="button"
        className="onb-block__trigger"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
      >
        <span className="onb-block__title">{title}</span>
        <ChevronDown size={14} className="onb-block__chevron" aria-hidden />
      </button>
      {isOpen ? (
        <div className="onb-block__body">
          {children}
          {links?.length ? <LinkChips links={links} /> : null}
        </div>
      ) : null}
    </div>
  );
}

const STEP_TONES = {
  mail: '#6366f1',
  account: 'var(--color-primary)',
  keys: 'var(--color-accent, #14b8a6)',
  shield: 'var(--color-success)',
  server: '#3b82f6',
  terminal: 'var(--color-citation, #7c3aed)',
  admin: 'var(--color-warning)',
};

const ONBOARDING_STEPS = [
  {
    id: 'contact-pm',
    num: '01',
    icon: Mail,
    tone: STEP_TONES.mail,
    title: 'Contact the project manager',
    summary: `Email ${PM_NAME} to be added to a lab CSC project — memberships are not self-service.`,
    content: (
      <>
        <div className="onb-callout">
          <p>
            The lab runs <strong>several CSC projects</strong> (e.g. <code>{EXAMPLE_PROJECT_ID}</code> and others).
            You cannot join them yourself in MyCSC — email the project manager and they will add you to the right one.
          </p>
        </div>
        <CollapsibleBlock title="Who to contact" defaultOpen>
          <p>
            <strong>{PM_NAME}</strong><br />
            <a href={`mailto:${PM_EMAIL}`}>{PM_EMAIL}</a>
          </p>
        </CollapsibleBlock>
        <CollapsibleBlock title="What to do">
          <ol>
            <li>Create your CSC account first (Step 02).</li>
            <li>Send a short email to {PM_NAME} with your <strong>name</strong> and <strong>CSC username</strong>.</li>
            <li>Mention which project you need access to, or ask which project applies to your work.</li>
          </ol>
        </CollapsibleBlock>
        <CollapsibleBlock title="What happens next">
          <ol>
            <li>{PM_NAME} adds you to the project in MyCSC.</li>
            <li>You receive a CSC invitation email — accept it.</li>
            <li>Continue with SSH keys (Step 03) and accept LUMI/Allas terms (Step 04).</li>
          </ol>
        </CollapsibleBlock>
      </>
    ),
  },
  {
    id: 'csc-account',
    num: '02',
    icon: UserCheck,
    tone: STEP_TONES.account,
    title: 'Create your CSC account (Haka login)',
    summary: 'Register at my.csc.fi with your university credentials and note your CSC username.',
    content: (
      <>
        <CollapsibleBlock
          title="Step-by-step: first-time registration"
          defaultOpen
          links={[
            { href: EXTERNAL_LINKS.myCsc, label: 'MyCSC portal' },
            { href: EXTERNAL_LINKS.cscAccount, label: 'CSC accounts docs' },
            { href: EXTERNAL_LINKS.cscHaka, label: 'Haka login guide' },
          ]}
        >
          <ol>
            <li>Open <a href={EXTERNAL_LINKS.myCsc} target="_blank" rel="noreferrer">my.csc.fi</a>.</li>
            <li>Click <strong>Create new account</strong> (or <strong>Log in with Haka</strong> if you already have an account).</li>
            <li>Select your home organisation — <strong>University of Helsinki</strong>.</li>
            <li>Authenticate with your university username and password (Haka federation).</li>
            <li>Complete profile fields and confirm any verification email from CSC.</li>
            <li>On the MyCSC dashboard, note your <strong>CSC username</strong> — you need it when emailing {PM_NAME}.</li>
          </ol>
        </CollapsibleBlock>
        <div className="onb-callout onb-callout--warn">
          <p>
            <strong>Do not click “Join” on a lab project in MyCSC.</strong>
            {' '}Membership is added by {PM_NAME} only.
          </p>
        </div>
        <CollapsibleBlock title="After your account exists">
          <p>
            Email <a href={`mailto:${PM_EMAIL}`}>{PM_EMAIL}</a> with your CSC username.
            Wait for the project invitation before connecting to LUMI.
          </p>
        </CollapsibleBlock>
      </>
    ),
  },
  {
    id: 'ssh-keys',
    num: '03',
    icon: Key,
    tone: STEP_TONES.keys,
    title: 'Generate SSH keys & register them in MyCSC',
    summary: 'CSC blocks password login — create an Ed25519 key pair and upload the public key to the portal.',
    content: (
      <>
        <CollapsibleBlock
          title="Why SSH keys?"
          defaultOpen
          links={[
            { href: EXTERNAL_LINKS.cscSsh, label: 'CSC: connecting' },
            { href: EXTERNAL_LINKS.cscSshKeys, label: 'CSC: SSH keys' },
          ]}
        >
          <p>
            LUMI, Puhti, Mahti, and Allas tools authenticate with SSH keys only. You keep a <strong>private key</strong> on your laptop
            (never share it) and upload the matching <strong>public key</strong> (.pub file) to MyCSC.
          </p>
        </CollapsibleBlock>

        <CollapsibleBlock title="macOS or Linux — Terminal">
          <p>Check for existing keys:</p>
          <CopyableCodeBlock code="ls -la ~/.ssh" type="primary" />
          <p>If you do not see <code>id_ed25519</code> and <code>id_ed25519.pub</code>, generate a new pair:</p>
          <CopyableCodeBlock code={`ssh-keygen -t ed25519 -C "${PM_EMAIL}"`} type="primary" />
          <ul>
            <li>Press <strong>Enter</strong> to accept the default path (<code>~/.ssh/id_ed25519</code>).</li>
            <li>Enter a passphrase (recommended) — you will type this when connecting.</li>
            <li>Display the public key to copy:</li>
          </ul>
          <CopyableCodeBlock code="cat ~/.ssh/id_ed25519.pub" type="primary" />
        </CollapsibleBlock>

        <CollapsibleBlock title="Windows — PowerShell">
          <p>Open PowerShell and run:</p>
          <CopyableCodeBlock code={`ssh-keygen -t ed25519 -C "${PM_EMAIL}"`} type="primary" />
          <p>Show the public key:</p>
          <CopyableCodeBlock code="type $env:USERPROFILE\\.ssh\\id_ed25519.pub" type="primary" />
          <p>Copy the entire single line starting with <code>ssh-ed25519</code>.</p>
        </CollapsibleBlock>

        <CollapsibleBlock
          title="Windows — MobaXterm (GUI)"
          links={[{ href: EXTERNAL_LINKS.mobaxterm, label: 'MobaXterm download' }]}
        >
          <ol>
            <li>Download the <strong>Portable edition</strong> if you cannot install software.</li>
            <li>Menu: <strong>Tools → MobaKeyGen (SSH key generator)</strong>.</li>
            <li>Key type: <strong>EdDSA (Ed25519)</strong> → click <strong>Generate</strong>.</li>
            <li>Move the mouse in the blank area until the progress bar completes.</li>
            <li>Save the private key locally. Copy the public key text from the top field.</li>
          </ol>
        </CollapsibleBlock>

        <CollapsibleBlock
          title="Upload public key to MyCSC"
          links={[{ href: EXTERNAL_LINKS.myCsc, label: 'MyCSC → SSH keys' }]}
        >
          <ol>
            <li>Log in to <a href={EXTERNAL_LINKS.myCsc} target="_blank" rel="noreferrer">my.csc.fi</a>.</li>
            <li>Open <strong>My Account → SSH Keys</strong>.</li>
            <li>Click <strong>Add new key</strong>, paste the full <code>ssh-ed25519 AAAA… comment</code> line.</li>
            <li>Save. Propagation to LUMI can take a few minutes.</li>
          </ol>
        </CollapsibleBlock>

        <CollapsibleBlock title="Test your connection">
          <CopyableCodeBlock code="ssh <your_csc_username>@lumi.csc.fi" type="primary" />
          <p>
            First login may ask to verify the host fingerprint — type <code>yes</code>.
            If connection is refused, confirm project membership and that your key is uploaded.
          </p>
        </CollapsibleBlock>
      </>
    ),
  },
  {
    id: 'project-activation',
    num: '04',
    icon: ShieldCheck,
    tone: STEP_TONES.shield,
    title: 'Accept project invitation & enable services',
    summary: 'Confirm CSC emails, accept LUMI/Allas terms, and verify your project in MyCSC.',
    content: (
      <>
        <CollapsibleBlock
          title="Accept project membership"
          defaultOpen
          links={[{ href: EXTERNAL_LINKS.cscProjects, label: 'CSC: joining a project' }]}
        >
          <ol>
            <li>After {PM_NAME} adds you, CSC sends an email invitation.</li>
            <li>Follow the link and click <strong>Accept</strong> in MyCSC.</li>
            <li>In MyCSC → <strong>Projects</strong>, confirm your lab project appears under memberships.</li>
          </ol>
        </CollapsibleBlock>
        <CollapsibleBlock title="Enable LUMI and Allas">
          <ol>
            <li>In the project view, open <strong>Services</strong> or <strong>Applications</strong>.</li>
            <li>Accept terms for <strong>LUMI</strong> supercomputer access and <strong>Allas</strong> object storage (required once per user).</li>
            <li>For cPouta VM access, coordinate with {PM_NAME} separately.</li>
          </ol>
        </CollapsibleBlock>
        <div className="onb-callout">
          <p>
            <strong>Still blocked?</strong> Email <a href={`mailto:${PM_EMAIL}`}>{PM_EMAIL}</a> with your CSC username
            and the error message from <code>ssh lumi.csc.fi</code>.
          </p>
        </div>
      </>
    ),
  },
  {
    id: 'lumi-storage',
    num: '05',
    icon: Server,
    tone: STEP_TONES.server,
    title: 'LUMI login, directories & Allas storage',
    summary: 'Use scratch and projappl under your project; back up completed data to Allas.',
    content: (
      <>
        <CollapsibleBlock
          title="Connect to LUMI"
          defaultOpen
          links={[
            { href: EXTERNAL_LINKS.lumiConnect, label: 'LUMI: connecting' },
            { href: EXTERNAL_LINKS.lumiStorage, label: 'LUMI storage' },
          ]}
        >
          <CopyableCodeBlock code="ssh <csc_username>@lumi.csc.fi" type="primary" />
          <p>Never run heavy processing on the login node — use Slurm batch jobs (see Computational Hub → LUMI HPC tab).</p>
        </CollapsibleBlock>
        <CollapsibleBlock title="Directory layout (lab standard)">
          <ul>
            <li>
              <strong>Scratch (temporary, fast):</strong>{' '}
              <code>/scratch/&lt;project_id&gt;/&lt;your_csc_username&gt;/</code>
            </li>
            <li>
              <strong>Project application space:</strong>{' '}
              <code>/projappl/&lt;project_id&gt;/</code> — shared containers, scripts, reference envs
            </li>
            <li>
              <strong>Home:</strong> small quota only — do not store large datasets in <code>$HOME</code>
            </li>
          </ul>
          <CopyableCodeBlock
            code={`# Example: create your scratch workspace
mkdir -p /scratch/${EXAMPLE_PROJECT_ID}/$USER
cd /scratch/${EXAMPLE_PROJECT_ID}/$USER`}
            type="primary"
          />
        </CollapsibleBlock>
        <CollapsibleBlock
          title="Allas cold storage"
          links={[{ href: EXTERNAL_LINKS.allas, label: 'CSC Allas guide' }]}
        >
          <p>
            Upload finished datasets and irreplaceable raw files to Allas buckets under the lab project.
            Use <code>a-</code> commands or rclone — full command recipes live under <strong>Data &amp; Storage</strong> and
            <strong> LUMI HPC</strong> in this hub.
          </p>
        </CollapsibleBlock>
      </>
    ),
  },
  {
    id: 'lab-standards',
    num: '06',
    icon: Terminal,
    tone: STEP_TONES.terminal,
    title: 'Lab computing standards & job workflow',
    summary: 'Slurm for all heavy jobs, Apptainer containers, quarterly cleanup, Puhti→Roihu migration.',
    content: (
      <>
        <CollapsibleBlock title="Workflow rules" defaultOpen>
          <ul>
            <li><strong>Slurm only:</strong> Ashlar, Mesmer, Cylinter, and large Python jobs must run via <code>sbatch</code> — not on login nodes.</li>
            <li><strong>Apptainer/Singularity:</strong> use lab container images for reproducible pipeline versions.</li>
            <li><strong>Naming:</strong> follow the lab file-naming SOP; log compute allocations in the project workbook.</li>
            <li><strong>Backups:</strong> push completed runs to Allas; scratch is purged automatically.</li>
            <li><strong>Cleanup:</strong> join quarterly data-cleaning days — delete intermediate tiles and duplicate exports.</li>
          </ul>
        </CollapsibleBlock>
        <div className="onb-callout onb-callout--warn">
          <p>
            <strong>Puhti → Roihu / LUMI migration:</strong> CSC is retiring Puhti. Move active datasets and update
            Singularity/Apptainer profiles to LUMI early. Test pipelines before publication deadlines.
          </p>
        </div>
        <CollapsibleBlock title="Where to go next in this app">
          <ul>
            <li><strong>LUMI HPC</strong> — Slurm jobs and imaging pipeline instructions</li>
            <li><strong>Utilities</strong> — LUMI modules, Lumi-O transfers, file operations</li>
            <li><strong>cPouta VMs</strong> — GPU workstations and volume setup</li>
            <li><strong>Troubleshooting</strong> — common SSH, quota, and job errors</li>
            <li><strong>Data &amp; Storage</strong> — L/P-drive layout, rclone, Allas buckets</li>
          </ul>
        </CollapsibleBlock>
      </>
    ),
  },
  {
    id: 'admin-ssh',
    num: '07',
    icon: Lock,
    tone: STEP_TONES.admin,
    title: 'Administrator: SSH provisioning on cPouta VMs',
    summary: 'For project manager / admins — create Linux users and install SSH keys on lab VMs.',
    adminOnly: true,
    content: (
      <>
        <CollapsibleBlock title="When this applies" defaultOpen>
          <p>
            CSC cPouta VMs (e.g. <code>farkkila-gpu1</code>) are lab-managed. After a user sends their public key to {PM_NAME},
            an admin logs in as root and runs the provisioning script below.
          </p>
        </CollapsibleBlock>
        <CollapsibleBlock title="Create user & install key">
          <CopyableCodeBlock
            code={`export USERNAME="new_username"
export USERID="1105"          # pick unused UID from /etc/passwd
export REALNAME="Full Name"

sudo useradd --home /home/\${USERNAME} --shell /bin/bash --gid farkkilab --uid \${USERID} -c "\${REALNAME}" \${USERNAME}

sudo mkdir -p /home/\${USERNAME}/.ssh
sudo chown -R \${USERNAME}:farkkilab /home/\${USERNAME}

# Paste user's public key (single line ssh-ed25519 …)
sudo nano /home/\${USERNAME}/.ssh/authorized_keys

sudo chown \${USERNAME}:farkkilab /home/\${USERNAME}/.ssh/authorized_keys
sudo chmod 700 /home/\${USERNAME}/.ssh
sudo chmod 600 /home/\${USERNAME}/.ssh/authorized_keys`}
            type="success"
          />
        </CollapsibleBlock>
        <CollapsibleBlock title="Group-writable umask (shared lab folders)">
          <CopyableCodeBlock code={`echo "umask 0002" | sudo tee -a /home/\${USERNAME}/.bashrc`} type="success" />
          <p>Ensures new files are group-readable/writable for the <code>farkkilab</code> group.</p>
        </CollapsibleBlock>
      </>
    ),
  },
];

function OnboardingStep({ step, isOpen, onToggle }) {
  return (
    <article
      className={`onb-step onb-glass${isOpen ? ' is-open' : ''}${step.adminOnly ? ' is-admin' : ''}`}
      style={{ '--onb-step-tone': step.tone }}
    >
      <button
        type="button"
        className="onb-step__trigger"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span className="onb-step__num">{step.num}</span>
        <div className="onb-step__head-copy">
          <h3 className="onb-step__title">
            {step.title}
            {step.adminOnly ? <span className="onb-tag">Admin</span> : null}
          </h3>
          <p className="onb-step__summary">{step.summary}</p>
        </div>
        <ChevronDown size={18} className="onb-step__chevron" aria-hidden />
      </button>
      {isOpen ? (
        <div className="onb-step__body">
          <div className="onb-step__body-inner">
            {step.content}
          </div>
        </div>
      ) : null}
    </article>
  );
}

export default function OnboardingRoadmap() {
  const [openSteps, setOpenSteps] = useState(() => new Set());

  const toggleStep = (id) => {
    setOpenSteps((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="onb-roadmap">
      <header className="onb-roadmap__hero onb-glass">
        <h2 className="onb-roadmap__hero-title">
          <Activity size={18} aria-hidden />
          Färkkilä Lab — CSC &amp; LUMI onboarding
        </h2>
        <p className="onb-roadmap__hero-lead">
          Expand each step for full instructions. Create a CSC account, then email {PM_NAME} to be added to a lab project.
        </p>
        <div className="onb-roadmap__hero-meta">
          <span className="onb-roadmap__pill">
            PM: <a href={`mailto:${PM_EMAIL}`}>{PM_NAME}</a>
          </span>
          <span className="onb-roadmap__pill">
            e.g. <code>{EXAMPLE_PROJECT_ID}</code>
          </span>
          <span className="onb-roadmap__pill">
            <a href={EXTERNAL_LINKS.myCsc} target="_blank" rel="noreferrer">my.csc.fi</a>
          </span>
        </div>
      </header>

      <div className="onb-roadmap__steps">
        {ONBOARDING_STEPS.map((step) => (
          <OnboardingStep
            key={step.id}
            step={step}
            isOpen={openSteps.has(step.id)}
            onToggle={() => toggleStep(step.id)}
          />
        ))}
      </div>
    </div>
  );
}
