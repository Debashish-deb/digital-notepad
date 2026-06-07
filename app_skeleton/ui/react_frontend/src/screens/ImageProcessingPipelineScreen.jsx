import { lazy, Suspense, useMemo, useState } from 'react';
import {
  ArrowRight,
  BarChart3,
  Box,
  Cloud,
  FolderOpen,
  Grid3x3,
  LayoutDashboard,
  Scan,
  Server,
  Settings,
  ShieldCheck,
  Terminal,
} from 'lucide-react';
import { HubSectionFrame } from '../components/HubNestedNav.jsx';
import { LazyViewFallback } from '../components/common/LazyViewFallback.jsx';

const Pipeline3DScene = lazy(() =>
  import('../components/Pipeline3DScene.jsx').then((m) => ({ default: m.Pipeline3DScene })),
);
const RunPipelineTab = lazy(() => import('../components/RunPipelineTab.jsx'));
import {
  PIPELINE_ARTIFACTS,
  PIPELINE_3D_METADATA,
  PIPELINE_FLOW_CHAIN,
  PIPELINE_MENU_OPTIONS,
  PIPELINE_PROJAPPL_SCRIPTS,
  PIPELINE_SECTIONS,
  PIPELINE_SETUP_STEPS,
} from '../data/imageProcessingPipelineContent.js';
import './ImageProcessingPipelineScreen.css';

function PipelineMetadataStrip({ items = [] }) {
  if (!items.length) return null;

  return (
    <div className="ipp-runbook__meta-grid" aria-label="Pipeline metadata summary">
      {items.map((item) => (
        <span key={item.label} className="ipp-runbook__meta-tile" style={{ '--ipp-meta-tone': item.tone }}>
          <span className="ipp-runbook__meta-label">{item.label}</span>
          <strong>{item.value}</strong>
        </span>
      ))}
    </div>
  );
}

function PipelineRunbookDiagram({ ariaLabel, compact = false }) {
  const metadata = PIPELINE_3D_METADATA;
  const legend = metadata.zones || [];

  return (
    <section className={`ipp-runbook ipp-glass-3d ipp-runbook--ready${compact ? ' ipp-runbook--compact' : ''}`} aria-label={ariaLabel}>
      {!compact ? (
        <>
          <span className="ipp-runbook__corner ipp-runbook__corner--tl" aria-hidden />
          <span className="ipp-runbook__corner ipp-runbook__corner--tr" aria-hidden />
          <span className="ipp-runbook__corner ipp-runbook__corner--bl" aria-hidden />
          <span className="ipp-runbook__corner ipp-runbook__corner--br" aria-hidden />
          <span className="ipp-runbook__shine" aria-hidden />
        </>
      ) : null}

      <header className="ipp-runbook__chrome">
        {!compact ? (
          <div className="ipp-runbook__title-row">
            <span className="ipp-runbook__live" aria-hidden>
              <span className="ipp-runbook__pulse" />
              SPATIAL PIPELINE MAP
            </span>
            <span className="ipp-runbook__badge">CyCIF · Ovarian cancer · LUMI</span>
          </div>
        ) : null}
        <h3 className="ipp-runbook__headline">{compact ? 'Pipeline map' : metadata.title}</h3>
        {!compact ? <p className="ipp-runbook__subtitle">{metadata.subtitle}</p> : null}
        {!compact ? <PipelineMetadataStrip items={metadata.summary} /> : null}
        {!compact ? (
          <div className="ipp-runbook__tag-row" aria-label="Pipeline tags">
            {(metadata.tags || []).map((tag) => (
              <span key={tag} className="ipp-runbook__tag">{tag}</span>
            ))}
          </div>
        ) : null}
      </header>

      <div className="ipp-diagram-wrap ipp-runbook__canvas ipp-glass-inset ipp-diagram-wrap--3d">
        <div className="ipp-diagram-canvas ipp-diagram-canvas--3d">
          <Suspense fallback={<LazyViewFallback variant="diagram-3d" label="Loading research-grade 3D pipeline map…" />}>
            <Pipeline3DScene ariaLabel={ariaLabel} metadata={metadata} />
          </Suspense>
        </div>
        {!compact ? <div className="ipp-runbook__grid" aria-hidden /> : null}
        {!compact ? <div className="ipp-runbook__glow ipp-runbook__glow--left" aria-hidden /> : null}
        {!compact ? <div className="ipp-runbook__glow ipp-runbook__glow--right" aria-hidden /> : null}
      </div>

      <footer className={`ipp-runbook__legend${compact ? ' ipp-runbook__legend--compact' : ''}`} aria-label="Diagram legend">
        {legend.map((item) => (
          <span key={item.id} className="ipp-runbook__legend-item" title={item.description}>
            <span className="ipp-runbook__legend-swatch" style={{ '--swatch': item.color }} />
            {item.label}
          </span>
        ))}
      </footer>
    </section>
  );
}

function InfoCard({ icon: Icon, title, children }) {
  return (
    <article className="ipp-info-card">
      <div className="ipp-info-card__head">
        {Icon ? <Icon size={16} aria-hidden /> : null}
        <h4>{title}</h4>
      </div>
      {children}
    </article>
  );
}

function FlowChips({ items }) {
  return (
    <div className="ipp-flow-visual" aria-label="Workflow steps">
      {items.map((item, i) => (
        <span key={item} style={{ display: 'contents' }}>
          {i > 0 ? <span className="ipp-flow-arrow" aria-hidden>→</span> : null}
          <span className="ipp-flow-chip">{item}</span>
        </span>
      ))}
    </div>
  );
}

function PipelineRunFeatureCard() {
  return (
    <section className="ipp-run-feature ipp-glass-3d" aria-label="Pipeline run and feature">
      <header className="ipp-run-feature__head">
        <span className="ipp-runbook__live" aria-hidden>
          <span className="ipp-runbook__pulse" />
          PIPELINE RUN &amp; FEATURE
        </span>
        <p className="ipp-run-feature__lead">
          Four setup steps, then an interactive menu when <code>bash run_pipeline.sh</code> starts.
        </p>
      </header>

      <div className="ipp-run-feature__grid">
        <div className="ipp-run-feature__col">
          <h4 className="ipp-run-feature__title">Setup before running</h4>
          <ol className="ipp-run-feature__steps">
            {PIPELINE_SETUP_STEPS.map((item) => (
              <li key={item.step} className="ipp-run-feature__step">
                <span className="ipp-run-feature__step-num">{item.step}</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                  {item.command ? <pre className="ipp-code ipp-code--inline">{item.command}</pre> : null}
                </div>
              </li>
            ))}
          </ol>
        </div>

        <div className="ipp-run-feature__col">
          <h4 className="ipp-run-feature__title">Interactive menu</h4>
          <ol className="ipp-run-feature__menu">
            {PIPELINE_MENU_OPTIONS.map((opt) => (
              <li key={opt.id}>
                <span className="ipp-run-feature__menu-num">{opt.id}</span>
                {opt.label}
              </li>
            ))}
          </ol>
          <p className="text-footnote muted">
            Option 2 pauses at human-review gates (stitching, segmentation). Option 3 runs a single stage.
          </p>
        </div>
      </div>
    </section>
  );
}

function OverviewSection({ compact = false }) {
  return (
    <div className="ipp-guide">
      <div className="ipp-hero">
        <div className="ipp-hero__copy">
          {!compact ? <p className="ipp-hero__eyebrow">{PIPELINE_3D_METADATA.eyebrow}</p> : null}
          <h2 className="ipp-hero__title">
            {compact ? 'Multiplex image pipeline' : 'Research-grade multiplex image-processing ecosystem'}
          </h2>
          <p className="ipp-hero__lead">
            The <strong>LOLA CycIF microscope</strong> produces raw tile data that lands on lab storage —{' '}
            <strong>External HD</strong>, <strong>Allas</strong>, or <strong>P-drive</strong>. Raw data is staged from{' '}
            <strong>Allas</strong> onto <strong>LUMI</strong> Lustre, where the Snakemake pipeline runs: raw data →
            illumination correction → stitching → segmentation (Mesmer whole-cell/nuclear or StarDist) →
            quantification → filter images → result → manual and visual QC. Finished outputs are archived back to
            Allas, P-drive, and External HD.
          </p>
          {!compact ? (
            <p className="text-footnote muted">
              Copy scripts from <code>{PIPELINE_PROJAPPL_SCRIPTS}</code>, then launch <code>bash run_pipeline.sh</code> from the dataset <code>scripts/</code> folder.
            </p>
          ) : null}
          {!compact ? (
            <div className="ipp-flow-chain" aria-label="LUMI pipeline steps">
              {PIPELINE_FLOW_CHAIN.map((step, i) => (
                <span key={step.id} style={{ display: 'contents' }}>
                  {i > 0 ? <span className="ipp-flow-chain__arrow" aria-hidden>→</span> : null}
                  <span
                    className="ipp-flow-chain__pill"
                    style={{ '--ipp-accent': step.color }}
                    title={step.label}
                  >
                    {step.label}
                  </span>
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      <PipelineRunbookDiagram
        compact={compact}
        ariaLabel="Interactive 3D research pipeline: LOLA CyCIF microscope, lab storage, Allas, LUMI orchestration, CPU/GPU processing stages, single-cell analytics, QC gates and archive"
      />

      {!compact ? <PipelineRunFeatureCard /> : null}

      <div className="ipp-content-grid">
        <InfoCard icon={Server} title="Where it runs">
          <p>Interactive launcher on a LUMI login node; compute stages submit to SLURM (<code>small</code> CPU, <code>small-g</code> GPU).</p>
        </InfoCard>
        <InfoCard icon={Cloud} title="Lab storage">
          <p>Raw exports sit on External HD, Allas, or P-drive. Allas is the usual bridge into LUMI scratch; results return to any of the three for long-term storage.</p>
        </InfoCard>
        <InfoCard icon={ShieldCheck} title="QC checkpoints">
          <p>Review stitching and segmentation outputs before continuing. Final QC is a manual and visual checkup on filtered images and quant tables. Flags in <code>pipeline_state/</code> track progress.</p>
        </InfoCard>
        <InfoCard icon={FolderOpen} title="Bundled in this app">
          <p>Full pipeline source lives at <code>app_skeleton/pipelines/lumi_image_processing/</code> — synced from the lab CSC scripts tree.</p>
        </InfoCard>
      </div>
    </div>
  );
}

function LoginSection() {
  return (
    <div className="ipp-guide">
      <p className="ipp-hero__lead">
        The pipeline runs on <strong>LUMI</strong> after SSH login. Use an interactive terminal — Mesmer needs a DeepCell token prompt and review menus require a TTY.
      </p>
      <FlowChips items={['CSC account', 'SSH lumi.csc.fi', 'project allocation', 'module load', 'Snakemake venv', 'run_pipeline.sh']} />

      <div className="ipp-content-grid">
        <InfoCard icon={Terminal} title="1 · Connect to LUMI">
          <pre className="ipp-code">{`ssh <csc_username>@lumi.csc.fi
cd /scratch/project_<PROJECT_ID>/image_processing/<owner>/<dataset>/scripts`}</pre>
        </InfoCard>
        <InfoCard icon={Settings} title="2 · Load Snakemake environment">
          <pre className="ipp-code">{`module load cray-python/3.11.7
source /path/to/envs/snakemake311/bin/activate`}</pre>
          <p>Path is project-specific; check your group&apos;s documented venv on LUMI.</p>
        </InfoCard>
        <InfoCard icon={ShieldCheck} title="3 · Preflight check">
          <pre className="ipp-code">bash run_pipeline.sh --doctor</pre>
          <p>Validates folders, <code>channels_quantification.csv</code>, Apptainer images, and SLURM account.</p>
        </InfoCard>
      </div>

      <div className="ipp-callout">
        <strong>Lustre layout:</strong> project scratch under <code>/scratch/project_*</code>, containers under <code>/projappl/project_*/envs/*.sif</code>. Job scratch uses <code>{'${BASE}'}/tmp/job_scratch</code> — not <code>/tmp</code> on compute nodes.
      </div>
    </div>
  );
}

function AllasSection() {
  return (
    <div className="ipp-guide">
      <p className="ipp-hero__lead">
        Raw data from the LOLA CycIF microscope can land on <strong>External HD</strong>, <strong>Allas</strong>, or{' '}
        <strong>P-drive</strong>. <strong>Allas</strong> is the primary staging path into LUMI — download tiles to
        Lustre, run the pipeline, then archive results back to Allas (and optionally P-drive or External HD).
      </p>
      <FlowChips items={['LOLA CycIF export', 'External HD · Allas · P-drive', 'Allas → LUMI scratch', 'Pipeline run', 'Results → Allas · P-drive · External HD']} />

      <div className="ipp-content-grid">
        <InfoCard icon={Cloud} title="Stage from Allas into LUMI">
          <p>From your workstation (with <code>a-</code> tools configured), pull raw tiles onto LUMI Lustre:</p>
          <pre className="ipp-code">{`# Example: sync a sample folder into the dataset tree
a-put -r local/raw_tiles/ bucket-name/image_processing/dataset/data/raw/SAMPLE1/

# On LUMI — fetch from Allas into data/raw/
a-get -r bucket-name/image_processing/dataset/data/raw/SAMPLE1/ \\
  /scratch/project_XXX/.../data/raw/SAMPLE1/`}</pre>
          <p>Or use <code>rclone</code> / Lumi-O — see Data &amp; Storage → CSC Allas and Transfer tools.</p>
        </InfoCard>
        <InfoCard icon={ArrowRight} title="P-drive & External HD">
          <p>Lab workstations often keep working copies on <strong>P-drive</strong> or an <strong>External HD</strong> before uploading to Allas. You can also copy results back to these locations after QC for local review or sharing.</p>
          <pre className="ipp-code">{`# Direct scp from workstation (bypass Allas)
scp -r local/raw/SAMPLE1/*.rcpnl \\
  user@lumi.csc.fi:/scratch/project_XXX/.../data/raw/SAMPLE1/`}</pre>
        </InfoCard>
        <InfoCard icon={Cloud} title="Archive finished outputs">
          <p>After <code>pipeline_complete.flag</code>, push quant CSVs, masks, and OME-TIFFs to Allas, P-drive, or External HD for long-term storage.</p>
          <pre className="ipp-code">{`# Allas archive
a-put -r /scratch/project_XXX/.../data/quantification/ \\
  bucket-name/results/SAMPLE1/

# Local copy to P-drive or External HD from workstation
a-get -r bucket-name/results/SAMPLE1/ /path/to/P-drive/archive/`}</pre>
        </InfoCard>
      </div>
    </div>
  );
}

function PrepareSection({ compact = false }) {
  return (
    <div className="ipp-guide">
      <p className="ipp-hero__lead">
        Prepare the dataset directory before the first <code>run_pipeline.sh</code> invocation: copy raw microscope
        files into <code>data/</code>, then copy the canonical scripts from projappl.
      </p>

      {!compact ? <PipelineRunFeatureCard /> : null}

      <div className="ipp-content-grid">
        <InfoCard icon={FolderOpen} title="1 · Bootstrap scratch layout">
          <p>Create the dataset tree on LUMI scratch before staging tiles or copying scripts:</p>
          <pre className="ipp-code">{`cd /scratch/project_<PROJECT_ID>/$USER/image_processing/<dataset>/

mkdir -p data/raw data/illumination_correction data/stitching \\
  data/segmentation data/quantification data/filter_images \\
  pipeline_state logs scripts

# Per-sample raw folder (LOLA .rcpnl tiles)
mkdir -p data/raw/SAMPLE1`}</pre>
        </InfoCard>
        <InfoCard icon={FolderOpen} title="2 · Copy raw files into data/">
          <p>Place all LOLA CycIF export tiles under <code>data/raw/&lt;sample&gt;/</code> before copying scripts.</p>
          <pre className="ipp-code">{`# From Allas, P-drive, or External HD — into LUMI scratch
cp -r /path/to/raw_tiles/*.rcpnl data/raw/SAMPLE1/`}</pre>
        </InfoCard>
        <InfoCard icon={Terminal} title="3 · Copy scripts from projappl">
          <p>From the dataset root (parent of <code>data/</code>), copy the lab scripts tree:</p>
          <pre className="ipp-code">{`cd /scratch/project_XXX/image_processing/<dataset>/
cp -r ${PIPELINE_PROJAPPL_SCRIPTS} .
cd scripts/
bash run_pipeline.sh`}</pre>
        </InfoCard>
        <InfoCard icon={FolderOpen} title="Directory tree">
          <pre className="ipp-code">{`image_processing/<dataset>/
├── data/
│   ├── raw/<sample>/*.rcpnl     # INPUT tiles
│   ├── channels_quantification.csv
│   ├── illumination_correction/
│   ├── stitching/
│   ├── segmentation/
│   ├── quantification/
│   └── filter_images/
├── pipeline_state/              # *.flag state machine
├── logs/
└── scripts/                     # run_pipeline.sh, Snakefile`}</pre>
        </InfoCard>
        <InfoCard icon={Grid3x3} title="channels_quantification.csv">
          <p>One marker name per line (excluding DAPI / background / failed channels). Drives quantification and filtering stages.</p>
          <pre className="ipp-code">{`CD3
CD8
PD-L1
...`}</pre>
        </InfoCard>
        <InfoCard icon={Scan} title="Sample discovery">
          <p>Sample IDs are folder names under <code>data/raw/</code>. Each sample needs a consistent set of <code>.rcpnl</code> cycle tiles.</p>
        </InfoCard>
      </div>
    </div>
  );
}

function StitchingSection() {
  return (
    <div className="ipp-guide">
      <p className="ipp-hero__lead">
        After raw tiles are staged, the pipeline applies BaSiC illumination correction per cycle, then Ashlar stitching into <code>sample.ome.tif</code>.
      </p>
      <span className="ipp-gate-badge">Human review required before segmentation</span>

      <div className="ipp-content-grid">
        <InfoCard icon={Grid3x3} title="Illumination (CPU)">
          <p>ImageJ BaSiC in <code>illumination.sif</code> writes FFP/DFP profiles per cycle.</p>
          <p><code>data/illumination_correction/&lt;sample&gt;/&lt;exp&gt;-ffp.tif</code></p>
        </InfoCard>
        <InfoCard icon={Grid3x3} title="Ashlar stitch (CPU)">
          <p>Ashlar in <code>ashlar.sif</code> registers tiles using illumination profiles.</p>
          <p><code>data/stitching/&lt;sample&gt;/&lt;sample&gt;.ome.tif</code></p>
        </InfoCard>
        <InfoCard icon={ShieldCheck} title="Review gate">
          <p>Launcher exits after stitching. Inspect OME-TIFF in Napari or similar, then approve to create <code>stitching_approved.flag</code>.</p>
          <pre className="ipp-code">bash run_pipeline.sh --resume-from stitching_approved</pre>
        </InfoCard>
      </div>
    </div>
  );
}

function SegmentationSection() {
  return (
    <div className="ipp-guide">
      <p className="ipp-hero__lead">
        Segmentation follows stitching. Choose Mesmer (nuclear and/or whole-cell), StarDist (nuclear), or both. Runs on <code>small-g</code> with one MI250 GCD per image job.
      </p>
      <span className="ipp-gate-badge">Human review required before quantification</span>

      <div className="ipp-content-grid">
        <InfoCard icon={Scan} title="Mesmer (GPU)">
          <p>DeepCell Mesmer in <code>mesmer-lumi-rocm63.sif</code>. Requires one-time DeepCell token at <a href="https://users.deepcell.org" target="_blank" rel="noreferrer">users.deepcell.org</a> (session only, never stored).</p>
          <p>See <code>MESMER_INDEX_AUDIT.md</code> for nuclear/membrane channel indices.</p>
        </InfoCard>
        <InfoCard icon={Scan} title="StarDist (GPU)">
          <p>Nuclear masks via <code>stardist.sif</code> — alternative or complement to Mesmer.</p>
        </InfoCard>
        <InfoCard icon={Settings} title="LUMI tuning">
          <p>Control concurrency with <code>MESMER_JOBS</code>, partitions via <code>SLURM_PARTITION_GPU</code>. See <code>SEGMENTATION_LUMI_OPTIMIZATION.md</code> for memory and Lustre striping notes.</p>
        </InfoCard>
      </div>
    </div>
  );
}

function QuantSection() {
  return (
    <div className="ipp-guide">
      <p className="ipp-hero__lead">
        Quantification extracts per-cell marker intensities, then filter images applies white tophat filtering per marker. Finish with manual and visual QC on outputs.
      </p>

      <div className="ipp-content-grid">
        <InfoCard icon={BarChart3} title="Quantification">
          <p>Outputs under <code>data/quantification/&lt;method&gt;/</code>:</p>
          <ul>
            <li><code>&lt;sample&gt;_nuclear.csv</code></li>
            <li><code>&lt;sample&gt;_whole_cell.csv</code> (Mesmer whole-cell)</li>
          </ul>
        </InfoCard>
        <InfoCard icon={BarChart3} title="Filtering">
          <p>Per-marker tophat TIFFs and filtered CSVs:</p>
          <ul>
            <li><code>data/filter_images/tif/...</code></li>
            <li><code>data/filter_images/csv/...</code></li>
          </ul>
        </InfoCard>
        <InfoCard icon={ShieldCheck} title="QC & completion">
          <p>Inspect filtered TIFFs and CSVs in Napari or your viewer. When satisfied, mark QC complete — launcher sets <code>pipeline_complete.flag</code>. Use <code>--status</code> or <code>--sync-state</code> to reconcile flags.</p>
        </InfoCard>
      </div>
    </div>
  );
}

function ContainersSection() {
  return (
    <div className="ipp-guide">
      <p className="ipp-hero__lead">Apptainer images expected under <code>/projappl/project_*/envs/</code>:</p>

      <div className="ipp-content-grid">
        <InfoCard icon={Box} title="Required SIF images">
          <ul>
            <li><code>illumination.sif</code> — BaSiC / Fiji</li>
            <li><code>ashlar.sif</code> — stitching</li>
            <li><code>mesmer-lumi-rocm63.sif</code> — Mesmer on ROCm TF 2.17</li>
            <li><code>stardist.sif</code> — StarDist nuclear</li>
            <li><code>quantification.sif</code> — quant + filter</li>
          </ul>
        </InfoCard>
        <InfoCard icon={Terminal} title="Build Mesmer image">
          <pre className="ipp-code">{`cd scripts/containers
sudo apptainer build mesmer-lumi-rocm63.sif mesmer-lumi-rocm63.def
scp mesmer-lumi-rocm63.sif user@lumi.csc.fi:/projappl/project_XXX/envs/`}</pre>
        </InfoCard>
      </div>
    </div>
  );
}

function OperationsSection({ dbProjects, API_URL, compact = false }) {
  return (
    <div className="ipp-guide">
      <PipelineRunFeatureCard />

      <div className="ipp-content-grid">
        <InfoCard icon={Terminal} title="Interactive menu & CLI flags">
          <p>Without flags, <code>bash run_pipeline.sh</code> shows the four-option menu. CLI flags bypass the menu:</p>
          <pre className="ipp-code">{`bash run_pipeline.sh              # Menu: full / with stops / step / exit
bash run_pipeline.sh --status
bash run_pipeline.sh --plan
bash run_pipeline.sh --only stitching
bash run_pipeline.sh --from segmentation
bash run_pipeline.sh --resume-from stitching_approved
bash run_pipeline.sh --sync-state`}</pre>
        </InfoCard>
        <InfoCard icon={FolderOpen} title="Repository artifacts">
          <div className="ipp-artifact-list">
            {PIPELINE_ARTIFACTS.map((a) => (
              <span key={a.path} className="ipp-artifact-link text-footnote">
                app_skeleton/pipelines/lumi_image_processing/{a.path}
              </span>
            ))}
          </div>
        </InfoCard>
      </div>

      {!compact && dbProjects && API_URL ? (
        <div className="ipp-trigger-panel">
          <h3 className="panel-title" style={{ fontSize: '1rem' }}>Legacy cluster trigger</h3>
          <p className="text-footnote muted">Optional API hook for older Ashlar / Stardist / Cylinter checker jobs.</p>
          <Suspense fallback={<LazyViewFallback variant="panel" label="Loading pipeline trigger…" showBars={false} />}>
            <RunPipelineTab dbProjects={dbProjects} API_URL={API_URL} />
          </Suspense>
        </div>
      ) : null}
    </div>
  );
}

const SECTION_RENDERERS = {
  overview: OverviewSection,
  login: LoginSection,
  allas: AllasSection,
  prepare: PrepareSection,
  stitching: StitchingSection,
  segmentation: SegmentationSection,
  quant: QuantSection,
  containers: ContainersSection,
};

export default function ImageProcessingPipelineScreen({
  dbProjects,
  API_URL,
  initialSection = 'overview',
  embeddedInHub = false,
}) {
  const [section, setSection] = useState(initialSection);

  const sections = useMemo(() => PIPELINE_SECTIONS, []);

  const Active = SECTION_RENDERERS[section] || OverviewSection;
  const sectionProps = embeddedInHub ? { compact: true } : {};

  return (
    <div className={`ipp-pipeline-shell${embeddedInHub ? ' ipp-pipeline-shell--hub-embedded' : ''}`}>
      <HubSectionFrame
        sections={sections}
        active={section}
        onChange={setSection}
        ariaLabel="Image processing pipeline guide"
        layout={embeddedInHub ? 'horizontal' : 'vertical'}
      >
        {section === 'operations' ? (
          <OperationsSection dbProjects={dbProjects} API_URL={API_URL} compact={embeddedInHub} />
        ) : (
          <Active {...sectionProps} />
        )}
      </HubSectionFrame>
    </div>
  );
}
