import { useMemo } from 'react';
import './DataStorageScreen.css';
import {
  Archive,
  ArrowRight,
  Check,
  Cloud,
  ExternalLink,
  HardDrive,
  Network,
  Server,
  Shield,
  X,
} from 'lucide-react';
import {
  CSC_HPC_STORAGE_NOTES,
  ONBOARDING_STORAGE_RESOURCES,
  PROJECT_STORAGE_WORKFLOW,
  REFERENCE_DOCUMENTS,
  STORAGE_CONTACTS,
  STORAGE_CAPACITY_OVERVIEW,
  CPOUTA_VOLUME_RULES,
  TRANSFER_TOOLS,
  getStorageById,
  getLabAllocatedCapacityTb,
} from '@/data/labStorageCatalog.js';
import {
  LANDSCAPE_CONTENT,
  NETWORK_DRIVES_CONTENT,
  DATACLOUD_CONTENT,
  ALLAS_CONTENT,
  GOOGLE_DRIVE_CONTENT,
  LOCAL_STORAGE_CONTENT,
  GUIDELINES_CONTENT,
  TOOLS_CONTENT,
} from '@/data/labStorageTabContent.js';
import StorageTabDocuments from '@/features/storage/components/StorageTabDocuments.jsx';
import { TAB_RAIL_CAPACITY_IDS } from '@/lib/storageDocumentsConfig.js';

const ICON_BY_KEY = {
  network: Network,
  cloud: Cloud,
  archive: Archive,
  local: HardDrive,
  shield: Shield,
  csc: Server,
};

const QUICK_NAV = [
  { id: 'landscape', label: 'Full landscape' },
  { id: 'network_drives', label: 'L-drive & P-drive' },
  { id: 'datacloud', label: 'DataCloud & Databank' },
  { id: 'cloud_archive', label: 'CSC Allas' },
  { id: 'google_drive', label: 'Google Drive' },
  { id: 'local_storage', label: 'Local & disks' },
  { id: 'guidelines', label: 'Guidelines' },
  { id: 'tools', label: 'Transfer tools' },
  { id: 'documents', label: 'Lab documents' },
  { id: 'all_files', label: 'All Files' },
];

function StorageIcon({ iconKey, size = 20 }) {
  const Icon = ICON_BY_KEY[iconKey] || HardDrive;
  return <Icon size={size} aria-hidden />;
}

function sensitivityLabel(sensitivity) {
  if (sensitivity === 'high') return 'Sensitive';
  if (sensitivity === 'low') return 'Archive';
  return 'Mixed';
}

function TabLead({ children }) {
  return (
    <div className="panel storage-lead-panel">
      <p className="panel-lead prose-block">{children}</p>
    </div>
  );
}

function ContentSection({ title, items, children }) {
  return (
    <div className="panel storage-tab-section">
      <h4 className="storage-tab-section__title">{title}</h4>
      {items?.length > 0 && (
        <ul className="storage-compact-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
      {children}
    </div>
  );
}

function ContentSectionGrid({ sections }) {
  if (!sections?.length) return null;
  const gridClass = [
    'storage-tab-section-grid',
    sections.length === 1 && 'storage-tab-section-grid--single',
    sections.length === 2 && 'storage-tab-section-grid--pair',
  ].filter(Boolean).join(' ');

  return (
    <div className={gridClass}>
      {sections.map((sec) => (
        <ContentSection key={sec.title} title={sec.title} items={sec.items} />
      ))}
    </div>
  );
}

function ExternalLinksPanel({ links, title = 'Official & reference links' }) {
  if (!links?.length) return null;
  return (
    <div className="panel storage-tab-section">
      <h4 className="storage-tab-section__title">{title}</h4>
      <ul className="storage-external-links">
        {links.map((link) => (
          <li key={link.href}>
            <a href={link.href} target="_blank" rel="noopener noreferrer" className="storage-link">
              {link.label} <ExternalLink size={12} />
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StorageCard({ system, layout = 'grid' }) {
  const sensitivityClass =
    system.sensitivity === 'high' ? 'high' : system.sensitivity === 'low' ? 'low' : 'medium';

  return (
    <article className={`storage-card storage-card--${system.category} storage-card--${layout}`}>
      <header className="storage-card__hero">
        <div className="storage-card__hero-main">
          <span className="storage-card__icon-wrap">
            <StorageIcon iconKey={system.icon} />
          </span>
          <div className="storage-card__hero-text">
            <div className="storage-card__title-row">
              <h4 className="storage-card__title">{system.name}</h4>
              {system.capacityLabel && (
                <span
                  className={`storage-capacity-badge ${system.capacityVerified ? 'verified' : 'estimate'}`}
                >
                  {system.capacityLabel}
                  {!system.capacityVerified && <span className="storage-capacity-est">est.</span>}
                </span>
              )}
            </div>
            <p className="storage-card__role">{system.role}</p>
            <p className="storage-card__provider">{system.provider}</p>
          </div>
        </div>
        <div className="storage-card__hero-badges">
          <span className={`storage-sensitivity storage-sensitivity--${sensitivityClass}`}>
            {sensitivityLabel(system.sensitivity)}
          </span>
          {system.extendable && <span className="storage-pill">Expandable</span>}
        </div>
      </header>

      <div className="storage-card__body">
        {system.paths?.length > 0 && (
          <section className="storage-card__section">
            <h5 className="storage-card__label">Paths</h5>
            <div className="storage-path-chips">
              {system.paths.map((p) => (
                <code key={p} className="storage-path-chip">
                  {p}
                </code>
              ))}
            </div>
          </section>
        )}

        <section className="storage-card__section storage-card__section--positive">
          <h5 className="storage-card__label">Use for</h5>
          <ul className="storage-icon-list">
            {system.useFor.map((item) => (
              <li key={item}>
                <Check size={13} className="storage-icon-list__icon storage-icon-list__icon--ok" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>

        {system.notFor?.length > 0 && (
          <section className="storage-card__section storage-card__section--negative">
            <h5 className="storage-card__label">Avoid</h5>
            <ul className="storage-icon-list">
              {system.notFor.map((item) => (
                <li key={item}>
                  <X size={13} className="storage-icon-list__icon storage-icon-list__icon--no" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      {system.notes?.length > 0 && (
        <div className="storage-card__notes">
          {system.notes.map((note) => (
            <span key={note} className="storage-note-chip">
              {note}
            </span>
          ))}
        </div>
      )}

      <dl className="storage-card__facts">
        {system.extendNote && (
          <div className="storage-card__fact">
            <dt>Capacity</dt>
            <dd>{system.extendNote}</dd>
          </div>
        )}
        <div className="storage-card__fact">
          <dt>Access</dt>
          <dd>{system.access}</dd>
        </div>
        <div className="storage-card__fact">
          <dt>Contacts</dt>
          <dd>{system.contacts.join(' · ')}</dd>
        </div>
      </dl>

      {system.urls?.length > 0 && (
        <div className="storage-card__links">
          {system.urls.map((u) => (
            <a key={u.href} href={u.href} target="_blank" rel="noopener noreferrer" className="storage-link">
              {u.label} <ExternalLink size={12} />
            </a>
          ))}
        </div>
      )}
    </article>
  );
}

function StorageQuickRail({ onNavigate, activeSection }) {
  const railIds = TAB_RAIL_CAPACITY_IDS[activeSection];
  const capacityRows =
    railIds === null || railIds === undefined
      ? STORAGE_CAPACITY_OVERVIEW
      : railIds.length
        ? STORAGE_CAPACITY_OVERVIEW.filter((r) => railIds.includes(r.id))
        : [];

  return (
    <aside className="storage-quick-rail">
      {capacityRows.length > 0 && (
        <div className="storage-rail-block">
          <h5 className="storage-rail-title">
            {activeSection === 'landscape' ? 'Capacities' : 'This tab'}
          </h5>
          <ul className="storage-rail-capacity">
            {capacityRows.map((row) => (
              <li key={row.id}>
                <span className="storage-rail-capacity__name">{row.label}</span>
                <span className="storage-rail-capacity__val">{row.capacity}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="storage-rail-block">
        <h5 className="storage-rail-title">Project workflow</h5>
        <ul className="storage-rail-workflow">
          {PROJECT_STORAGE_WORKFLOW.map((row) => (
            <li key={row.status}>
              <span className="storage-rail-workflow__status">{row.status}</span>
              <ArrowRight size={12} aria-hidden />
              <span className="storage-rail-workflow__dest">{row.destination}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="storage-rail-block">
        <h5 className="storage-rail-title">Lab contacts</h5>
        <ul className="storage-rail-contacts">
          {Object.values(STORAGE_CONTACTS).map((c) => (
            <li key={c.label}>
              <span className="storage-rail-contacts__role">{c.label}</span>
              <span>{c.people.join(' · ')}</span>
            </li>
          ))}
        </ul>
      </div>

      {onNavigate && (
        <div className="storage-rail-block">
          <h5 className="storage-rail-title">Jump to</h5>
          <nav className="storage-rail-nav">
            {QUICK_NAV.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`storage-rail-nav__btn ${activeSection === item.id ? 'active' : ''}`}
                onClick={() => onNavigate('data_storage', item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      )}
    </aside>
  );
}

function StoragePageShell({ children, activeSection, onNavigate, fullWidth = false }) {
  return (
    <div className={`storage-page-layout${fullWidth ? ' storage-page-layout--full' : ''}`}>
      <div className="storage-page-main">{children}</div>
      {fullWidth ? null : (
        <StorageQuickRail onNavigate={onNavigate} activeSection={activeSection} />
      )}
    </div>
  );
}

function SystemCards({ systemIds, pair }) {
  const systems = systemIds.map((id) => getStorageById(id)).filter(Boolean);
  if (!systems.length) return null;

  const count = systems.length;
  const isSingle = count === 1;
  const isPair = Boolean(pair) || count === 2;
  const useWideLayout = isSingle || isPair;
  const gridClass = [
    'storage-cards-row',
    isSingle && 'storage-cards-row--single',
    isPair && 'storage-cards-row--pair',
  ].filter(Boolean).join(' ');

  return (
    <div className={gridClass}>
      {systems.map((s) => (
        <StorageCard key={s.id} system={s} layout={useWideLayout ? 'wide' : 'grid'} />
      ))}
    </div>
  );
}

function DecisionMatrix({ rows, onNavigate }) {
  return (
    <div className="panel storage-tab-section">
      <h4 className="storage-tab-section__title">Where does my data go?</h4>
      <div className="storage-decision-grid">
        {rows.map((row) => {
          const bullets = row.bullets?.length
            ? row.bullets
            : row.note
              ? row.note.split(/(?<=[.!?])\s+/).filter(Boolean)
              : [];

          return (
            <div key={row.question} className="storage-decision-card">
              <p className="storage-decision-card__q">{row.question}</p>
              <div className="storage-decision-card__body">
                <div className="storage-decision-card__destination">
                  <span className="storage-decision-card__label">Use</span>
                  <strong className="storage-decision-card__answer">{row.answer}</strong>
                </div>
                {bullets.length ? (
                  <ul className="storage-decision-card__details">
                    {bullets.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
                {row.example ? (
                  <p className="storage-decision-card__example">
                    <span className="storage-decision-card__label">Example</span>
                    <span>{row.example}</span>
                  </p>
                ) : null}
              </div>
              {onNavigate && row.tab ? (
                <div className="storage-decision-card__actions">
                  <button
                    type="button"
                    className="btn btn-sm storage-ref-btn"
                    onClick={() => onNavigate('data_storage', row.tab)}
                  >
                    Open tab <ArrowRight size={12} />
                  </button>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SystemMapGrid({ systems, onNavigate }) {
  return (
    <div className="panel storage-tab-section">
      <h4 className="storage-tab-section__title">Systems at a glance</h4>
      <div className="storage-system-map">
        {systems.map((s) => (
          <button
            key={s.id}
            type="button"
            className="storage-system-map__card"
            onClick={() => onNavigate?.('data_storage', s.tab)}
            disabled={!onNavigate}
          >
            <span className="storage-system-map__cap">{s.capacity}</span>
            <strong>{s.label}</strong>
            <span className="text-caption muted">{s.role}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function ComparisonTable({ rows }) {
  return (
    <div className="panel storage-tab-section">
      <h4 className="storage-tab-section__title">L-drive vs P-drive</h4>
      <div className="storage-comparison-wrap">
        <table className="storage-comparison-table">
          <thead>
            <tr>
              <th>Aspect</th>
              <th>L-drive</th>
              <th>P-drive</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.aspect}>
                <td>{row.aspect}</td>
                <td>{row.lDrive}</td>
                <td>{row.pDrive}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CpoutaVolumePanel() {
  return (
    <ContentSection title="cPouta VM volume rules">
      <dl className="storage-guide-rules">
        {CPOUTA_VOLUME_RULES.map((row) => (
          <div key={row.rule} className="storage-guide-rules__row">
            <dt>{row.rule}</dt>
            <dd>{row.detail}</dd>
          </div>
        ))}
      </dl>
    </ContentSection>
  );
}

function WorkflowPanel({ compact = false, detailed }) {
  const rows = detailed || PROJECT_STORAGE_WORKFLOW;
  return (
    <div className={`panel storage-workflow-panel ${compact ? 'storage-workflow-panel--compact' : ''}`}>
      <h4 className="text-title-3">Project lifecycle → storage</h4>
      {!compact && (
        <p className="text-footnote muted panel-lead">
          Map each project status before moving data (cleaning day inventory).
        </p>
      )}
      <div className="storage-workflow-grid">
        {rows.map((row) => (
          <div key={row.status || row.destination} className="storage-workflow-card">
            <div className="storage-workflow-card__head">
              <span className="storage-workflow-status">{row.status}</span>
              <ArrowRight size={14} className="muted" aria-hidden />
              <strong>{row.destination}</strong>
            </div>
            {row.detail && <p className="text-footnote">{row.detail}</p>}
            {row.steps && (
              <ul className="storage-compact-list">
                {row.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            )}
            {row.sources && (
              <p className="text-caption muted">{row.sources.join(' · ')}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ReferencesPanel({ onNavigate }) {
  return (
    <div className="panel storage-tab-section">
      <h4 className="storage-tab-section__title">Source documents (lab corpus)</h4>
      <div className="storage-ref-grid">
        {REFERENCE_DOCUMENTS.map((doc) => (
          <div key={doc.title} className="storage-ref-tile">
            <strong>{doc.title}</strong>
            <p className="text-caption muted">{doc.context}</p>
            {onNavigate && (
              <button
                type="button"
                className="btn btn-sm storage-ref-btn"
                onClick={() => onNavigate('overview', doc.section)}
              >
                Overview <ArrowRight size={12} />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function HubLinkButton({ onNavigate, sub = 'utilities', label = 'Computational Hub → Utilities' }) {
  if (!onNavigate) return null;
  return (
    <button
      type="button"
      className="btn btn-sm btn-secondary storage-tool-nav"
      onClick={() => onNavigate('computational', sub)}
    >
      {label} <ArrowRight size={12} />
    </button>
  );
}

/* ─── Tab views ─── */

function LandscapeTab({ onNavigate }) {
  const totalTb = getLabAllocatedCapacityTb();
  return (
    <StoragePageShell onNavigate={onNavigate} activeSection="landscape">
      <div className="storage-hero panel">
        <div className="storage-hero__copy">
          <p className="storage-summary-lead">{LANDSCAPE_CONTENT.intro}</p>
          <p className="storage-hero__footnote text-footnote muted">
            Major allocations: P-drive ~80 TB · CSC Allas ~30 TB · DataCloud ~10 TB · UH Databank (UH quota)
            (~{totalTb} TB combined). L-drive uses UH clinical quota separately.
          </p>
        </div>
        <div className="storage-hero__stats" aria-label="Storage capacities">
          {STORAGE_CAPACITY_OVERVIEW.map((row) => (
            <div key={row.id} className="storage-stat">
              <span className="storage-stat__value">{row.capacity}</span>
              <span className="storage-stat__label">{row.label}</span>
            </div>
          ))}
        </div>
      </div>

      <DecisionMatrix rows={LANDSCAPE_CONTENT.decisionMatrix} onNavigate={onNavigate} />
      <SystemMapGrid systems={LANDSCAPE_CONTENT.systemMap} onNavigate={onNavigate} />

      <ContentSection title="General principles (all systems)">
        <ul className="storage-compact-list">
          {LANDSCAPE_CONTENT.principles.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      </ContentSection>
    </StoragePageShell>
  );
}

function NetworkDrivesTab({ onNavigate }) {
  return (
    <StoragePageShell onNavigate={onNavigate} activeSection="network_drives">
      <TabLead>{NETWORK_DRIVES_CONTENT.intro}</TabLead>
      <SystemCards systemIds={['l_drive', 'p_drive']} pair />
      <h4 className="storage-category-title">L-drive reference</h4>
      <ContentSectionGrid sections={NETWORK_DRIVES_CONTENT.lDriveSections} />
      <h4 className="storage-category-title">P-drive reference</h4>
      <ContentSectionGrid sections={NETWORK_DRIVES_CONTENT.pDriveSections} />
      <ComparisonTable rows={NETWORK_DRIVES_CONTENT.comparisonTable} />
      <ExternalLinksPanel links={NETWORK_DRIVES_CONTENT.externalLinks} />
      <StorageTabDocuments tabId="network_drives" title="L-drive & P-drive documents" />
    </StoragePageShell>
  );
}

function DatacloudTab({ onNavigate }) {
  return (
    <StoragePageShell onNavigate={onNavigate} activeSection="datacloud">
      <TabLead>{DATACLOUD_CONTENT.intro}</TabLead>
      <SystemCards systemIds={['datacloud', 'databank']} pair />
      <h4 className="storage-category-title">DataCloud</h4>
      <ContentSectionGrid sections={DATACLOUD_CONTENT.sections} />
      <h4 className="storage-category-title">UH Databank</h4>
      <ContentSectionGrid sections={DATACLOUD_CONTENT.databankSections} />
      <ExternalLinksPanel links={DATACLOUD_CONTENT.externalLinks} />
      <HubLinkButton onNavigate={onNavigate} />
      <StorageTabDocuments tabId="datacloud" title="DataCloud & Databank documents" />
    </StoragePageShell>
  );
}

function AllasTab({ onNavigate }) {
  return (
    <StoragePageShell onNavigate={onNavigate} activeSection="cloud_archive">
      <TabLead>{ALLAS_CONTENT.intro}</TabLead>
      <SystemCards systemIds={['allas']} />
      <ContentSectionGrid sections={ALLAS_CONTENT.sections} />
      <h4 className="storage-category-title">HPC scratch vs object storage</h4>
      <ContentSectionGrid sections={ALLAS_CONTENT.hpcSections} />
      <ContentSection title="CSC HPC quick notes">
        <ul className="storage-compact-list">
          {CSC_HPC_STORAGE_NOTES.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
        <HubLinkButton onNavigate={onNavigate} sub="onboarding" label="Computational Hub → Onboarding" />
      </ContentSection>
      <WorkflowPanel compact />
      <ExternalLinksPanel links={ALLAS_CONTENT.externalLinks} />
      <StorageTabDocuments tabId="cloud_archive" title="CSC Allas documents" />
    </StoragePageShell>
  );
}

function GoogleDriveTab({ onNavigate }) {
  return (
    <StoragePageShell onNavigate={onNavigate} activeSection="google_drive">
      <TabLead>{GOOGLE_DRIVE_CONTENT.intro}</TabLead>
      <SystemCards systemIds={['google_drive']} />
      <ContentSectionGrid sections={GOOGLE_DRIVE_CONTENT.sections} />
      <ExternalLinksPanel links={GOOGLE_DRIVE_CONTENT.externalLinks} />
      <StorageTabDocuments tabId="google_drive" title="Google Drive & organisation documents" />
    </StoragePageShell>
  );
}

function LocalStorageTab({ onNavigate }) {
  return (
    <StoragePageShell onNavigate={onNavigate} activeSection="local_storage">
      <TabLead>{LOCAL_STORAGE_CONTENT.intro}</TabLead>
      <SystemCards systemIds={['cpouta_nfs', 'local_workstations', 'external_disks', 'huh_datalake']} />
      <h4 className="storage-category-title">Workstations</h4>
      <ContentSectionGrid sections={LOCAL_STORAGE_CONTENT.workstationSections} />
      <h4 className="storage-category-title">cPouta VMs</h4>
      <ContentSectionGrid sections={LOCAL_STORAGE_CONTENT.cpoutaSections} />
      <CpoutaVolumePanel />
      <h4 className="storage-category-title">External disks</h4>
      <ContentSectionGrid sections={LOCAL_STORAGE_CONTENT.externalDiskSections} />
      <h4 className="storage-category-title">HUH clinical systems</h4>
      <ContentSectionGrid sections={LOCAL_STORAGE_CONTENT.clinicalSections} />
      <ExternalLinksPanel links={LOCAL_STORAGE_CONTENT.externalLinks} />
      <HubLinkButton onNavigate={onNavigate} sub="pouta" label="Computational Hub → cPouta VMs" />
      <StorageTabDocuments tabId="local_storage" title="Workstations & disk documents" />
    </StoragePageShell>
  );
}

function GuidelinesTab({ onNavigate }) {
  return (
    <StoragePageShell onNavigate={onNavigate} activeSection="guidelines">
      <TabLead>{GUIDELINES_CONTENT.intro}</TabLead>
      <WorkflowPanel detailed={GUIDELINES_CONTENT.workflowDetail} />
      <div className="storage-tab-section-grid">
        <ContentSection title="FAIR responsibilities">
          <ul className="storage-compact-list">
            {GUIDELINES_CONTENT.fairExpanded.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </ContentSection>
        <ContentSection title="Cleaning day checklist">
          <ul className="storage-compact-list">
            {GUIDELINES_CONTENT.cleaningChecklist.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </ContentSection>
      </div>
      <div className="panel storage-tab-section">
        <h4 className="storage-tab-section__title">Sensitivity classes</h4>
        <div className="storage-sensitivity-grid">
          {GUIDELINES_CONTENT.sensitivityExpanded.map((rule) => (
            <div key={rule.level} className="storage-sensitivity-tile">
              <strong>{rule.level}</strong>
              <p className="text-caption muted">{rule.stores}</p>
              <ul className="storage-compact-list">
                {rule.rules.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <ContentSection title="General data management principles">
        <ul className="storage-compact-list">
          {GUIDELINES_CONTENT.generalPrinciples.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </ContentSection>
      <div className="storage-tab-section-grid">
        <ContentSection title="Onboarding documents">
          <div className="storage-ref-grid">
            {ONBOARDING_STORAGE_RESOURCES.map((res) => (
              <div key={res.label} className="storage-ref-tile">
                <strong>{res.label}</strong>
                <p className="text-caption muted">{res.doc}</p>
                {onNavigate && (
                  <button
                    type="button"
                    className="btn btn-sm storage-ref-btn"
                    onClick={() => onNavigate('overview', res.section)}
                  >
                    Open <ArrowRight size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </ContentSection>
        <ReferencesPanel onNavigate={onNavigate} />
      </div>
      <StorageTabDocuments tabId="guidelines" title="Workflow & cleaning documents" />
    </StoragePageShell>
  );
}

function DocumentsTab({ onNavigate }) {
  return (
    <StoragePageShell onNavigate={onNavigate} activeSection="documents" fullWidth>
      <StorageTabDocuments tabId="documents" onNavigate={onNavigate} />
    </StoragePageShell>
  );
}

function ToolsTab({ onNavigate }) {
  return (
    <StoragePageShell onNavigate={onNavigate} activeSection="tools">
      <TabLead>{TOOLS_CONTENT.intro}</TabLead>
      <div className="storage-tools-expanded-grid">
        {TOOLS_CONTENT.toolsExpanded.map((tool) => {
          const catalog = TRANSFER_TOOLS.find((t) => t.id === tool.id);
          return (
            <div key={tool.id} className="panel storage-tool-expanded">
              <h4 className="storage-tab-section__title">{catalog?.name || tool.id}</h4>
              <p className="text-footnote">
                <strong>When:</strong> {tool.when}
              </p>
              <h5 className="storage-card__label">Steps</h5>
              <ul className="storage-compact-list">
                {tool.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
              {tool.gotchas?.length > 0 && (
                <>
                  <h5 className="storage-card__label">Gotchas</h5>
                  <ul className="storage-compact-list storage-compact-list--muted">
                    {tool.gotchas.map((g) => (
                      <li key={g}>{g}</li>
                    ))}
                  </ul>
                </>
              )}
              {catalog?.nav && onNavigate && (
                <HubLinkButton onNavigate={onNavigate} sub={catalog.nav.sub} />
              )}
            </div>
          );
        })}
      </div>
      <div className="panel storage-tab-section">
        <h4 className="storage-tab-section__title">Common transfer patterns</h4>
        <div className="storage-comparison-wrap">
          <table className="storage-comparison-table">
            <thead>
              <tr>
                <th>From</th>
                <th>To</th>
                <th>Tool</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {TOOLS_CONTENT.transferPatterns.map((row) => (
                <tr key={`${row.from}-${row.to}`}>
                  <td>{row.from}</td>
                  <td>{row.to}</td>
                  <td>
                    <code>{row.tool}</code>
                  </td>
                  <td>{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <ExternalLinksPanel links={TOOLS_CONTENT.externalLinks} />
      <HubLinkButton onNavigate={onNavigate} />
      <StorageTabDocuments tabId="tools" title="IT & transfer reference documents" />
    </StoragePageShell>
  );
}

export default function DataStorageScreen({ section = 'landscape', onNavigate }) {
  const content = useMemo(() => {
    switch (section) {
      case 'network_drives':
        return <NetworkDrivesTab onNavigate={onNavigate} />;
      case 'datacloud':
        return <DatacloudTab onNavigate={onNavigate} />;
      case 'cloud_archive':
        return <AllasTab onNavigate={onNavigate} />;
      case 'google_drive':
        return <GoogleDriveTab onNavigate={onNavigate} />;
      case 'local_storage':
        return <LocalStorageTab onNavigate={onNavigate} />;
      case 'guidelines':
        return <GuidelinesTab onNavigate={onNavigate} />;
      case 'tools':
        return <ToolsTab onNavigate={onNavigate} />;
      case 'documents':
        return <DocumentsTab onNavigate={onNavigate} />;
      case 'landscape':
      default:
        return <LandscapeTab onNavigate={onNavigate} />;
    }
  }, [section, onNavigate]);

  return (
    <div
      className={`data-storage-screen${section === 'documents' ? ' data-storage-screen--documents-full' : ''}`}
    >
      {content}
    </div>
  );
}
