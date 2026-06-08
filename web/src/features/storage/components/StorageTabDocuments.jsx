import { useEffect, useState } from 'react';
import { ArrowRight, FileText, Loader2 } from 'lucide-react';
import LabDocumentExplorer from '@/features/documents/components/LabDocumentExplorer.jsx';
import LabDocumentsBrowser from '@/features/documents/components/LabDocumentsBrowser.jsx';
import { getRepoDocsForTab, getStorageDocumentsConfig } from '@/lib/storageDocumentsConfig.js';

const STORAGE_CATEGORY_ICONS = {
  cleaning_251205: FileText,
  cleaning_20250528: FileText,
  allas_databank: FileText,
  inventory_disks: FileText,
  storage_units: FileText,
  it_roles: FileText,
  general_storage: FileText,
};

/** Where onboarding/guidelines/cleaning docs live after deduping away from storage tabs. */
const OVERVIEW_LINKS_BY_TAB = {
  network_drives: [
    { sub: 'onboarding', label: 'Onboarding — L-drive, P-drive & folder layout' },
  ],
  datacloud: [
    { sub: 'onboarding', label: 'Onboarding — DataCloud & Databank handover' },
  ],
  cloud_archive: [
    { sub: 'onboarding', label: 'Onboarding — CSC accounts & Allas access' },
    { sub: 'cleaning', label: 'Lab cleaning — Allas upload inventories' },
  ],
  google_drive: [
    { sub: 'onboarding', label: 'Onboarding — Google Drive organisation' },
  ],
  local_storage: [
    { sub: 'cleaning', label: 'Lab cleaning — external drive inventories' },
    { sub: 'personnel', label: 'Personnel — IT hardware & workstations' },
  ],
  guidelines: [
    { sub: 'guidelines', label: 'Lab guidelines' },
    { sub: 'cleaning', label: 'Lab cleaning checklists' },
  ],
  tools: [
    { sub: 'personnel', label: 'Personnel — IT roles & actions' },
    { sub: 'onboarding', label: 'Onboarding — transfer & setup procedures' },
  ],
};

async function fetchRepoMarkdown(path) {
  const file = (path || '').replace(/^configs\//, '');
  try {
    const res = await fetch(`/repo-static/${file}`);
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}

function OverviewDocsLinks({ tabId, onNavigate }) {
  const links = OVERVIEW_LINKS_BY_TAB[tabId];
  if (!links?.length || !onNavigate) return null;

  return (
    <div className="storage-overview-doc-links panel-inset">
      <h4 className="storage-category-title">Related lab documents</h4>
      <p className="text-footnote muted storage-overview-doc-links__lead">
        Onboarding, guidelines, and permits are kept on Overview — one canonical copy per file.
      </p>
      <nav className="storage-overview-doc-links__nav">
        {links.map((link) => (
          <button
            key={link.sub}
            type="button"
            className="btn btn-sm btn-secondary storage-overview-doc-links__btn"
            onClick={() => onNavigate('overview', link.sub)}
          >
            {link.label} <ArrowRight size={12} aria-hidden />
          </button>
        ))}
      </nav>
    </div>
  );
}

function StorageRepoDocsInline({ tabId }) {
  const repoDocs = getRepoDocsForTab(tabId);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(Boolean(repoDocs.length));

  useEffect(() => {
    if (!repoDocs.length) return undefined;
    let alive = true;
    setLoading(true);
    Promise.all(
      repoDocs.map(async (doc) => {
        const content = await fetchRepoMarkdown(doc.path);
        return content ? { ...doc, content } : null;
      }),
    ).then((loaded) => {
      if (!alive) return;
      setDocs(loaded.filter(Boolean));
      setLoading(false);
    });
    return () => {
      alive = false;
    };
  }, [tabId]);

  if (!repoDocs.length) return null;

  return (
    <div className="storage-repo-docs-inline">
      <h4 className="storage-category-title">Platform setup guides</h4>
      {loading ? (
        <p className="text-footnote muted">
          <Loader2 size={14} className="spin-inline" aria-hidden /> Loading setup guides…
        </p>
      ) : null}
      <ul className="storage-repo-docs-list">
        {docs.map((doc) => (
          <li key={doc.id} className="storage-repo-docs-item">
            <strong>{doc.label}</strong>
            <p className="text-footnote muted">{doc.summary}</p>
            <pre className="storage-repo-docs-preview">{doc.content?.slice(0, 1200)}{(doc.content?.length || 0) > 1200 ? '…' : ''}</pre>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function StorageTabDocuments({ tabId, title = 'Related lab documents', onNavigate }) {
  if (tabId === 'documents') {
    return (
      <div className="storage-tab-documents-wrap storage-tab-documents-wrap--explorer">
        <LabDocumentExplorer
          mainId="data_storage"
          subId="documents"
          title="Lab document library"
          description="Search, filter, and preview all lab files with audit-backed indexing status."
        />
      </div>
    );
  }

  const config = getStorageDocumentsConfig(tabId);
  const repoDocs = getRepoDocsForTab(tabId);
  const overviewLinks = OVERVIEW_LINKS_BY_TAB[tabId];

  if (!config) {
    if (!repoDocs.length && !overviewLinks?.length) return null;
    return (
      <div className="storage-tab-documents-wrap">
        <OverviewDocsLinks tabId={tabId} onNavigate={onNavigate} />
        <StorageRepoDocsInline tabId={tabId} />
      </div>
    );
  }

  return (
    <div className="storage-tab-documents-wrap">
      {title ? <h4 className="storage-category-title">{title}</h4> : null}
      <LabDocumentsBrowser
        key={`storage-docs-${tabId}`}
        sectionIds={config.sectionIds}
        categoryGroups={config.categoryGroups}
        defaultCategory={config.defaultCategory}
        categorizePath={(path, sourceSection) => config.categorizePath(path, sourceSection)}
        documentTitle={config.documentTitle}
        documentFilter={config.documentFilter}
        categoryIcons={STORAGE_CATEGORY_ICONS}
        groupByDocumentType
        className="lab-documents-browser storage-documents-browser catalog-space-browser"
      />
    </div>
  );
}
