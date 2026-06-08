import { useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  FolderOpen,
  Loader2,
} from 'lucide-react';
import DocumentViewer from '@/features/documents/components/DocumentViewer.jsx';
import DocumentFileSearch from '@/features/documents/components/DocumentFileSearch.jsx';
import { apiFetch } from '@/services/client.js';
import {
  catalogDocBreadcrumb,
  catalogDocDisplayTitle,
  catalogDocTypeLabel,
  catalogTopFolder,
  filterCatalogDocuments,
  groupCatalogDocuments,
} from '@/lib/catalogDocumentTree.js';

function CatalogFileRow({ doc, active, onSelect }) {
  const title = catalogDocDisplayTitle(doc);
  const breadcrumb = catalogDocBreadcrumb(doc.path);
  const typeLabel = catalogDocTypeLabel(doc);

  return (
    <li className="lab-doc-file-entry">
      <button
        type="button"
        className={`lab-doc-file-btn${active ? ' active' : ''}`}
        onClick={() => onSelect(doc.id)}
        aria-current={active ? 'true' : undefined}
        title={doc.path}
      >
        <FileText size={13} className="lab-doc-file-bullet" aria-hidden />
        <span className="lab-doc-file-text">
          <span className="lab-doc-title">{title}</span>
          <span className="lab-doc-path">
            {typeLabel ? <span className="lab-doc-ext">{typeLabel}</span> : null}
            {breadcrumb || doc.path.split('/').pop()}
          </span>
        </span>
        <ChevronRight size={13} className="lab-doc-file-chevron" aria-hidden />
      </button>
    </li>
  );
}

function CatalogFolderSection({
  folder,
  expanded,
  onToggle,
  activeSubfolderId,
  onSubfolderChange,
  selectedDocId,
  onSelectDoc,
}) {
  const showSubfolderTabs = folder.subfolders.length > 1;
  const activeSubfolder =
    folder.subfolders.find((sub) => sub.id === activeSubfolderId) || folder.subfolders[0];
  const visibleFiles = activeSubfolder?.files || [];

  return (
    <section className="lab-twin-folder-block">
      <button
        type="button"
        className="lab-twin-folder-header"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        {expanded ? <ChevronDown size={15} aria-hidden /> : <ChevronRight size={15} aria-hidden />}
        <FolderOpen size={15} className="lab-twin-folder-icon" aria-hidden />
        <span className="lab-twin-folder-title" title={folder.label}>
          {folder.shortLabel}
        </span>
        <span className="lab-twin-folder-count">{folder.count}</span>
      </button>

      {expanded ? (
        <div className="lab-twin-folder-body">
          {showSubfolderTabs ? (
            <nav className="lab-twin-subfolder-strip" aria-label={`${folder.label} subfolders`}>
              {folder.subfolders.map((sub) => (
                <button
                  key={sub.id}
                  type="button"
                  className={`lab-twin-subfolder-tab${activeSubfolderId === sub.id ? ' active' : ''}`}
                  onClick={() => onSubfolderChange(sub.id)}
                  aria-current={activeSubfolderId === sub.id ? 'true' : undefined}
                >
                  <span className="lab-twin-subfolder-tab-label">{sub.label}</span>
                  <span className="lab-twin-subfolder-tab-count">{sub.files.length}</span>
                </button>
              ))}
            </nav>
          ) : null}

          <ul className="lab-doc-category-files lab-doc-category-files--bulleted lab-twin-file-list">
            {visibleFiles.map((doc) => (
              <CatalogFileRow
                key={doc.id}
                doc={doc}
                active={selectedDocId === doc.id}
                onSelect={onSelectDoc}
              />
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

/**
 * Shows extracted digital-twin data from the local static database catalog.
 */
export default function LabSectionTwinPanel({
  sectionId,
  title,
  description,
  knowledgeSearchHref = '/#data_storage:guidelines',
  compact = false,
  filterFolder = null,
  excludeFolder = null,
}) {
  const [catalog, setCatalog] = useState(null);
  const [docQuery, setDocQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [expandedFolders, setExpandedFolders] = useState({});
  const [activeSubfolders, setActiveSubfolders] = useState({});

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    apiFetch('/api/database/catalog', { timeoutMs: 30_000 })
      .then((data) => {
        if (mounted) {
          setCatalog(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err?.message || 'Failed to load lab catalog.');
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const rawDocuments = useMemo(() => {
    if (!catalog?.sections) return [];

    let searchSections = [];
    if (sectionId?.includes('orders')) searchSections = ['02_Orders'];
    else if (sectionId?.includes('wet_lab') || sectionId === '04_Wet_Lab') searchSections = ['04_Wet_Lab'];
    else if (sectionId?.includes('social')) searchSections = ['03_Social'];
    else searchSections = ['01_Overview', '00_General_Knowledge'];

    let allDocs = [];
    for (const sec of searchSections) {
      if (catalog.sections[sec]) {
        allDocs = allDocs.concat(catalog.sections[sec]);
      }
    }

    if (filterFolder) {
      const qf = filterFolder.toLowerCase();
      allDocs = allDocs.filter((d) => catalogTopFolder(d.path).toLowerCase().includes(qf));
    }

    if (excludeFolder) {
      const qf = excludeFolder.toLowerCase();
      allDocs = allDocs.filter((d) => !catalogTopFolder(d.path).toLowerCase().includes(qf));
    }

    return allDocs;
  }, [catalog, sectionId, filterFolder, excludeFolder]);

  const documents = useMemo(
    () => filterCatalogDocuments(rawDocuments, docQuery),
    [rawDocuments, docQuery]
  );

  const folderGroups = useMemo(() => groupCatalogDocuments(documents), [documents]);

  useEffect(() => {
    if (!folderGroups.length) return;
    setActiveSubfolders((prev) => {
      const next = { ...prev };
      for (const folder of folderGroups) {
        if (!next[folder.id] && folder.subfolders[0]) {
          next[folder.id] = folder.subfolders[0].id;
        }
      }
      return next;
    });
  }, [folderGroups]);

  const selectedDoc = useMemo(
    () => documents.find((doc) => doc.id === selectedDocId) || null,
    [documents, selectedDocId]
  );

  if (!sectionId) {
    return (
      <div className="panel">
        <p className="muted text-footnote">
          Select a subsection to view extracted documents from the lab database.
        </p>
      </div>
    );
  }

  const toggleFolder = (folderId) => {
    setExpandedFolders((prev) => ({ ...prev, [folderId]: !prev[folderId] }));
  };

  return (
    <div className={`stack-md lab-section-twin ${compact ? 'lab-section-twin--compact' : ''}`}>
      <div className="panel">
        <h3 className="panel-title">
          <FileText size={18} /> {title || sectionId}
        </h3>
        <p className="panel-lead prose-block">
          {description || 'Extracted documents from the static lab database.'}
        </p>
        {loading && (
          <p className="text-footnote muted">
            <Loader2 size={14} className="spin-inline" /> Loading digital twin…
          </p>
        )}
        {error && (
          <p className="text-footnote" style={{ color: 'var(--mac-destructive)' }}>
            {error}
          </p>
        )}
        {catalog && !loading && (
          <p className="text-footnote">
            <strong>{documents.length}</strong> documents in this section
            {docQuery.trim() ? ` matching “${docQuery.trim()}”` : ''}.
          </p>
        )}
      </div>

      {catalog && (
        <div className="panel lab-twin-browser">
          <div className="lab-twin-browser-toolbar">
            <div className="lab-twin-browser-toolbar-copy">
              <h4 className="lab-twin-browser-title">Browse documents</h4>
              <p className="text-caption muted lab-twin-browser-hint">
                Grouped by folder — select a file to read its extracted content.
              </p>
            </div>
            <DocumentFileSearch
              value={docQuery}
              onChange={setDocQuery}
              fileCount={documents.length}
              searchPlaceholder="Search files…"
              searchAria="Search section documents"
              filesLabel={`${documents.length} files in section`}
            />
          </div>

          {!documents.length ? (
            <p className="muted text-footnote lab-twin-empty">No documents match your filters.</p>
          ) : (
            <div className={`lab-twin-layout${selectedDocId ? ' lab-twin-layout--open' : ''}`}>
              <div className="lab-twin-sidebar">
                {folderGroups.map((folder) => (
                  <CatalogFolderSection
                    key={folder.id}
                    folder={folder}
                    expanded={Boolean(expandedFolders[folder.id])}
                    onToggle={() => toggleFolder(folder.id)}
                    activeSubfolderId={activeSubfolders[folder.id]}
                    onSubfolderChange={(subId) =>
                      setActiveSubfolders((prev) => ({ ...prev, [folder.id]: subId }))
                    }
                    selectedDocId={selectedDocId}
                    onSelectDoc={setSelectedDocId}
                  />
                ))}
              </div>

              <div className="lab-twin-detail">
                {!selectedDoc ? (
                  <div className="lab-twin-detail-empty">
                    <FileText size={28} aria-hidden />
                    <p>Select a document from the list to preview its content.</p>
                  </div>
                ) : (
                  <>
                    <header className="lab-twin-detail-header">
                      <div>
                        <p className="lab-twin-detail-eyebrow">
                          {catalogDocBreadcrumb(selectedDoc.path) || 'Document'}
                        </p>
                        <h4 className="lab-twin-detail-title">{catalogDocDisplayTitle(selectedDoc)}</h4>
                      </div>
                      <span className="lab-doc-ext">{catalogDocTypeLabel(selectedDoc)}</span>
                    </header>
                    <DocumentViewer documentId={selectedDocId} />
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
