import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import {
  Archive,
  BarChart3,
  BookOpen,
  Calendar,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  FileText,
  FlaskConical,
  FolderOpen,
  FolderTree,
  HardDrive,
  LayoutGrid,
  Loader2,
  Menu,
  Search,
  Users,
} from 'lucide-react';
import MediaViewer from '@/features/documents/components/MediaViewer.jsx';
import { getMediaPreviewKind } from '@/lib/mediaPreviewKind.js';

const ModelViewer3D = lazy(() => import('./ModelViewer3D.jsx'));
import {
  collectFolderEntries,
  filesForFolderEntry,
  filesUnderTreePath,
  formatFileSize,
  formatModifiedAt,
  getChunkTextForProjectFile,
  getDocumentIndexEntry,
  getFilePreviewStatus,
  isAssetPreviewable,
  isExtractPreviewable,
  isTextPreviewable,
  normalizeRelPath,
  sortProjectFiles,
} from '@/lib/folderBrowserUtils.js';
import { inferExtension } from '@/lib/fileTypeMeta.js';
import { projectAssetUrl } from '@/lib/digitalTwinUtils.js';
import PdfDocumentViewer from '@/features/documents/components/PdfDocumentViewer.jsx';
import FileTypeBadge from '@/shared/ui/FileTypeBadge.jsx';
import CopyPathButton from '@/shared/ui/CopyPathButton.jsx';
import SmartLink from '@/shared/ui/SmartLink.jsx';
import LazyDataPadEditor from './LazyDataPadEditor.jsx';
import DocumentFormatter from '@/features/documents/components/DocumentFormatter.jsx';
import { useTaskpad } from '@/contexts/TaskpadContext.jsx';
import { fetchDatapadSectionSummary } from '@/services/datapad.js';
import { folderSectionToWorkspaceTab } from '@/lib/taskpadUtils.js';

const PREVIEW_LIMIT = 12000;

const SECTION_ICONS = {
  management: ClipboardList,
  methods: FlaskConical,
  data_figures: BarChart3,
  writing: BookOpen,
  meetings: Users,
  archive: Archive,
  guidelines: FileText,
  root: FolderOpen,
};

function groupFolders(folders) {
  const library = folders.filter((f) => f.source === 'content_library');
  const tree = folders.filter((f) => f.source === 'folder_tree');
  return [
    { id: 'library', label: 'Content sections', items: library },
    { id: 'tree', label: 'Folder tree', items: tree },
  ].filter((g) => g.items.length > 0);
}

function buildApiUrl(API_URL, path, params) {
  const base = (API_URL || '').replace(/\/$/, '');
  const q = params ? `?${params.toString()}` : '';
  return `${base}${path.startsWith('/') ? path : `/${path}`}${q}`;
}

function folderIcon(folder) {
  const Icon = SECTION_ICONS[folder?.id] || (folder?.source === 'folder_tree' ? FolderTree : FolderOpen);
  return Icon;
}

async function fetchVaultExcerpt(API_URL, filePath, projectCode) {
  if (!API_URL) return null;
  const name = (filePath || '').split('/').pop() || filePath;
  const q = name.replace(/\.[^.]+$/, '').slice(0, 80) || name;
  try {
    const params = new URLSearchParams({ q, limit: '12' });
    const res = await fetch(buildApiUrl(API_URL, '/api/vault/search', params));
    if (!res.ok) return null;
    const data = await res.json();
    const hits = data.results || data.hits || [];
    const norm = normalizeRelPath(filePath);
    const match =
      hits.find((h) => normalizeRelPath(h.relative_path || h.logical_path || h.path || '') === norm) ||
      hits.find(
        (h) =>
          (h.project_hint || h.project_id || h.project_code || '') === projectCode &&
          (h.filename || '').toLowerCase() === name.toLowerCase()
      ) ||
      hits.find((h) => (h.filename || '').toLowerCase() === name.toLowerCase()) ||
      hits[0];
    if (!match) return null;
    const md = match.metadata_preview || {};
    const text = (
      match.excerpt ||
      md.excerpt ||
      match.full_text ||
      match.text ||
      ''
    ).trim();
    if (!text) return null;
    return { content: text, source: 'vault search' };
  } catch {
    return null;
  }
}

export default function ProjectFolderBrowser({ twin, projectCode, API_URL, projectName }) {
  const folders = useMemo(() => collectFolderEntries(twin), [twin]);
  const docIndexByPath = useMemo(() => {
    const map = new Map();
    for (const doc of twin?.document_index || []) {
      if (doc?.path) map.set(normalizeRelPath(doc.path), doc);
    }
    return map;
  }, [twin]);

  const displayName = projectName || twin?.identity?.project_name || projectCode;

  const [selectedId, setSelectedId] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewSource, setPreviewSource] = useState(null);
  const [previewMeta, setPreviewMeta] = useState(null);
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [assetUrl, setAssetUrl] = useState(null);
  const [folderQuery, setFolderQuery] = useState('');
  const [fileQuery, setFileQuery] = useState('');
  const [fileSort, setFileSort] = useState('name');
  const [collapsedGroups, setCollapsedGroups] = useState(() => new Set());
  const [foldersDrawerOpen, setFoldersDrawerOpen] = useState(false);
  const [sectionSummary, setSectionSummary] = useState(null);
  const { openTaskpad } = useTaskpad();

  const contentRoot = twin?.content_root || twin?.folder_path || null;
  const folderGroups = useMemo(() => groupFolders(folders), [folders]);

  const totalFiles = useMemo(
    () => folders.reduce((sum, f) => sum + (f.file_count || 0), 0),
    [folders]
  );

  useEffect(() => {
    if (folders.length && !selectedId) {
      setSelectedId(folders[0].id);
    }
  }, [folders, selectedId]);

  const selectedFolder = folders.find((f) => f.id === selectedId);

  useEffect(() => {
    if (!projectCode || !selectedFolder?.id) {
      setSectionSummary(null);
      return;
    }
    let cancelled = false;
    fetchDatapadSectionSummary(projectCode, selectedFolder.id)
      .then((data) => {
        if (!cancelled) setSectionSummary(data);
      })
      .catch(() => {
        if (!cancelled) setSectionSummary(null);
      });
    return () => {
      cancelled = true;
    };
  }, [projectCode, selectedFolder?.id]);

  const folderFiles = useMemo(() => {
    if (!selectedFolder) return [];
    if (selectedFolder.section) return filesForFolderEntry(selectedFolder);
    if (selectedFolder.source === 'folder_tree') {
      return filesUnderTreePath(twin, selectedFolder.path);
    }
    return [];
  }, [selectedFolder, twin]);

  const sortedFiles = useMemo(() => sortProjectFiles(folderFiles, fileSort), [folderFiles, fileSort]);

  const filteredGroups = useMemo(() => {
    const q = folderQuery.trim().toLowerCase();
    if (!q) return folderGroups;
    return folderGroups
      .map((g) => ({
        ...g,
        items: g.items.filter((f) => f.label.toLowerCase().includes(q) || f.path.toLowerCase().includes(q)),
      }))
      .filter((g) => g.items.length > 0);
  }, [folderGroups, folderQuery]);

  const visibleFiles = useMemo(() => {
    const q = fileQuery.trim().toLowerCase();
    if (!q) return sortedFiles;
    return sortedFiles.filter(
      (f) =>
        (f.name || '').toLowerCase().includes(q) ||
        (f.path || '').toLowerCase().includes(q)
    );
  }, [sortedFiles, fileQuery]);

  const groupedFiles = useMemo(() => {
    const groups = {
      documents: [],
      figures: [],
      data_files: [],
      code_scripts: [],
      other: []
    };
    
    visibleFiles.forEach(file => {
      const ext = inferExtension(file.name, file.extension);
      let cat = 'other';
      
      if (file.asset_type) {
        if (['documents', 'writing', 'presentations'].includes(file.asset_type)) cat = 'documents';
        else if (['figures', 'images', 'videos'].includes(file.asset_type)) cat = 'figures';
        else if (['data_files', 'tables'].includes(file.asset_type)) cat = 'data_files';
        else if (['text_files', 'scripts'].includes(file.asset_type)) cat = 'code_scripts';
        else cat = 'other';
      } else {
         if (['.pdf', '.doc', '.docx', '.rtf', '.txt', '.md'].includes(ext)) cat = 'documents';
         else if (['.png', '.jpg', '.jpeg', '.svg', '.tif', '.tiff', '.gif'].includes(ext)) cat = 'figures';
         else if (['.csv', '.tsv', '.xlsx', '.xls', '.json', '.h5', '.rds'].includes(ext)) cat = 'data_files';
         else if (['.py', '.r', '.sh', '.js', '.ipynb'].includes(ext)) cat = 'code_scripts';
      }
      
      groups[cat].push(file);
    });
    
    return groups;
  }, [visibleFiles]);

  const breadcrumbParts = useMemo(() => {
    const parts = [displayName, 'Data Pad'];
    if (selectedFolder) parts.push(selectedFolder.label);
    if (selectedFile) parts.push(selectedFile.name);
    return parts;
  }, [displayName, selectedFolder, selectedFile]);

  const filePreviewStatus = useMemo(() => {
    if (!selectedFile?.path) return null;
    return getFilePreviewStatus(selectedFile, twin, normalizeRelPath(selectedFile.path));
  }, [selectedFile, twin]);

  useEffect(() => {
    setSelectedFile(null);
    setPreview(null);
    setPreviewSource(null);
    setPreviewMeta(null);
    setPreviewError(null);
    setAssetUrl(null);
    setPreviewExpanded(false);
    setFileQuery('');
  }, [selectedId]);

  const toggleGroup = (groupId) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  };

  const selectFolder = (id) => {
    setSelectedId(id);
    setFoldersDrawerOpen(false);
  };

  const loadFilePreview = async (file) => {
    setSelectedFile(file);
    setPreview(null);
    setPreviewSource(null);
    setPreviewMeta(null);
    setPreviewError(null);
    setAssetUrl(null);
    setPreviewExpanded(false);

    if (!file?.path) return;

    const ext = inferExtension(file.name, file.extension);
    const normPath = normalizeRelPath(file.path);
    const status = getFilePreviewStatus(file, twin, normPath);
    setPreviewMeta(status);

    const fileMediaKind = getMediaPreviewKind(ext);
    if (fileMediaKind && ext !== '.pdf') {
      setAssetUrl(projectAssetUrl(projectCode, normPath, API_URL, contentRoot));
      setPreviewSource('asset');
      return;
    }

    const fromChunks = getChunkTextForProjectFile(twin, normPath);
    if (fromChunks) {
      setPreview(fromChunks);
      setPreviewSource('indexed chunks');
      return;
    }

    const indexed = docIndexByPath.get(normPath) || getDocumentIndexEntry(twin, normPath);
    if (indexed?.excerpt) {
      const title = (indexed.title || '').trim();
      const body =
        title && !indexed.excerpt.startsWith(title.slice(0, 40))
          ? `${title}\n\n${indexed.excerpt}`
          : indexed.excerpt;
      setPreview(body);
      setPreviewSource('document index');
      if (indexed.extractor) setPreviewMeta({ ...status, extractor: indexed.extractor });
      return;
    }

    if (file.excerpt) {
      setPreview(file.excerpt);
      setPreviewSource('digital twin metadata');
      return;
    }

    if (isAssetPreviewable(ext) && !isTextPreviewable(ext)) {
      setAssetUrl(projectAssetUrl(projectCode, normPath, API_URL, contentRoot));
      if (ext !== '.pdf') {
        setPreviewSource('image');
        return;
      }
    }

    setPreviewLoading(true);
    try {
      if (isTextPreviewable(ext) && API_URL) {
        const params = new URLSearchParams({
          project_code: projectCode,
          relative_path: normPath,
        });
        const res = await fetch(buildApiUrl(API_URL, '/api/project-files/read', params));
        if (res.ok) {
          const data = await res.json();
          setPreview(data.content || '');
          setPreviewSource('file on disk');
          return;
        }
        if (res.status === 410) {
          const vault = await fetchVaultExcerpt(API_URL, normPath, projectCode);
          if (vault) {
            setPreview(vault.content);
            setPreviewSource(vault.source);
            return;
          }
        }
      }

      if (API_URL) {
        const params = new URLSearchParams({
          project_code: projectCode,
          relative_path: normPath,
        });
        const res = await fetch(buildApiUrl(API_URL, '/api/project-files/preview-text', params));
        if (res.ok) {
          const data = await res.json();
          setPreview(data.content || '');
          setPreviewSource(data.source || 'extracted');
          if (data.extractor || data.status) {
            setPreviewMeta({
              ...status,
              extractor: data.extractor,
              status: data.status,
            });
          }
          return;
        }
        if (res.status === 410) {
          const vault = await fetchVaultExcerpt(API_URL, normPath, projectCode);
          if (vault) {
            setPreview(vault.content);
            setPreviewSource(vault.source);
            return;
          }
        }
        const err = await res.json().catch(() => ({}));
        if (res.status !== 422) {
          throw new Error(err.detail || res.statusText);
        }
      }

      const vault = await fetchVaultExcerpt(API_URL, normPath, projectCode);
      if (vault) {
        setPreview(vault.content);
        setPreviewSource(vault.source);
        return;
      }

      if (isExtractPreviewable(ext)) {
        setPreviewError(
          'No extracted text yet. Run “Scan project folder” to index this file, or open the original below.'
        );
      } else if (isAssetPreviewable(ext)) {
        if (!assetUrl) {
          setAssetUrl(projectAssetUrl(projectCode, normPath, API_URL, contentRoot));
        }
      } else {
        setPreviewError(
          'No indexed preview for this type. Open the file directly, or re-scan the project folder.'
        );
      }
    } catch (e) {
      setPreviewError(String(e.message || e));
    } finally {
      setPreviewLoading(false);
    }
  };

  if (!twin) {
    return (
      <section className="panel workspace-section data-pad">
        <header className="data-pad-hierarchy">
          <h3 className="panel-title">
            <HardDrive size={18} /> Data Pad
          </h3>
        </header>
        <p className="text-footnote muted workspace-empty-state">
          Load the digital record to browse project folders and preview extracted text from documents.
        </p>
      </section>
    );
  }

  if (!folders.length) {
    return (
      <section className="panel workspace-section data-pad">
        <header className="data-pad-hierarchy">
          <h3 className="panel-title">
            <HardDrive size={18} /> Data Pad
          </h3>
        </header>
        <p className="text-footnote muted workspace-empty-state">
          No indexed folders yet. Click ↻ Scan project folder to scan the project directory.
        </p>
      </section>
    );
  }

  const previewSlice = preview
    ? previewExpanded || preview.length <= PREVIEW_LIMIT
      ? preview
      : `${preview.slice(0, PREVIEW_LIMIT)}\n…`
    : null;

  const selectedExt = selectedFile ? inferExtension(selectedFile.name, selectedFile.extension) : '';
  const sectionEditableCount =
    sectionSummary?.sections?.[0]?.editable_count ??
    (selectedFolder ? visibleFiles.filter((f) => ['.md', '.txt', '.html', '.rtf'].includes(inferExtension(f.name, f.extension))).length : 0);
  const isPdf = selectedExt === '.pdf';
  const mediaKind = getMediaPreviewKind(selectedExt);
  const layoutClass = `pfb-layout${selectedFile ? ' pfb-layout--file-open' : ''}${foldersDrawerOpen ? ' pfb-layout--folders-open' : ''}`;

  return (
    <section className="panel workspace-section data-pad project-folder-browser">
      <header className="data-pad-hierarchy">
        <div className="data-pad-hierarchy-main">
          <h3 className="panel-title">
            <HardDrive size={18} /> Data Pad
          </h3>
          <nav className="data-pad-breadcrumb" aria-label="Location">
            {breadcrumbParts.map((part, i) => (
              <span key={`${part}-${i}`} className="data-pad-crumb">
                {i > 0 && <ChevronRight size={12} className="data-pad-crumb-sep" aria-hidden />}
                <span className={i === breadcrumbParts.length - 1 ? 'data-pad-crumb-current' : ''}>
                  {part}
                </span>
              </span>
            ))}
          </nav>
        </div>
        <div className="data-pad-hierarchy-stats">
          <span className="data-pad-stat">
            <FolderOpen size={14} /> {folders.length} sections
          </span>
          <span className="data-pad-stat">
            <FileText size={14} /> {totalFiles} files
          </span>
          {selectedFolder && (
            <span className="data-pad-stat">
              <LayoutGrid size={14} /> {visibleFiles.length} shown
            </span>
          )}
        </div>
      </header>

      {contentRoot && (
        <div className="data-pad-root">
          <SmartLink href={contentRoot} showCopy maxLabelLen={48} />
        </div>
      )}

      <div className="data-pad-filter-bar">
        <button
          type="button"
          className="btn btn-secondary btn-sm data-pad-drawer-toggle"
          onClick={() => setFoldersDrawerOpen((v) => !v)}
          aria-expanded={foldersDrawerOpen}
        >
          <Menu size={14} /> Sections
        </button>
        <label className="data-pad-filter-field">
          <Search size={14} aria-hidden />
          <input
            type="search"
            className="form-input data-pad-filter-input"
            placeholder="Filter sections…"
            aria-label="Filter sections"
            value={folderQuery}
            onChange={(e) => setFolderQuery(e.target.value)}
          />
        </label>
        <label className="data-pad-filter-field">
          <Search size={14} aria-hidden />
          <input
            type="search"
            className="form-input data-pad-filter-input"
            placeholder="Filter files in section…"
            aria-label="Filter files in section"
            value={fileQuery}
            onChange={(e) => setFileQuery(e.target.value)}
            disabled={!selectedFolder}
          />
        </label>
        <select
          className="form-select data-pad-sort-select"
          value={fileSort}
          onChange={(e) => setFileSort(e.target.value)}
          aria-label="Sort files"
          disabled={!selectedFolder}
        >
          <option value="name">Sort: name</option>
          <option value="type">Sort: type</option>
          <option value="modified">Sort: modified</option>
          <option value="size">Sort: size</option>
        </select>
      </div>

      <div className={layoutClass}>
        <aside
          className="pfb-column pfb-folder-list pfb-column--resizable"
          aria-label="Content sections"
        >
          {filteredGroups.map((group) => {
            const collapsed = collapsedGroups.has(group.id);
            return (
              <div key={group.id} className="pfb-folder-group">
                <button
                  type="button"
                  className="pfb-folder-group-header"
                  onClick={() => toggleGroup(group.id)}
                  aria-expanded={!collapsed}
                >
                  {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
                  <span>{group.label}</span>
                  <span className="pfb-folder-count">{group.items.length}</span>
                </button>
                {!collapsed &&
                  group.items.map((folder) => {
                    const Icon = folderIcon(folder);
                    return (
                      <button
                        key={folder.id}
                        type="button"
                        className={`pfb-folder-item ${selectedId === folder.id ? 'active' : ''}`}
                        onClick={() => selectFolder(folder.id)}
                        title={folder.path}
                      >
                        <Icon size={14} className="pfb-folder-icon" />
                        <span className="pfb-folder-label">{folder.label}</span>
                        <span className="pfb-folder-count">{folder.file_count}</span>
                      </button>
                    );
                  })}
              </div>
            );
          })}
        </aside>

        <div className="pfb-column pfb-files-pane pfb-column--resizable">
          {selectedFolder ? (
            <>
              <div className="pfb-files-header">
                <h4 className="workspace-subpanel-title">{selectedFolder.label}</h4>
                <span className="pfb-files-meta muted text-footnote">
                  {visibleFiles.length} of {folderFiles.length} files
                  {sectionEditableCount > 0 && ` · ${sectionEditableCount} editable`}
                </span>
              </div>
              {visibleFiles.length === 0 ? (
                <p className="muted text-footnote workspace-empty-state">
                  {folderFiles.length === 0
                    ? 'No files indexed in this section.'
                    : 'No files match your filter.'}
                </p>
              ) : (
                <div className="pfb-file-grouped-wrap">
                  {Object.entries(groupedFiles).map(([category, files]) => {
                    if (!files.length) return null;
                    const labels = {
                      documents: 'Documents & Writing',
                      figures: 'Figures & Imaging',
                      data_files: 'Data Assets',
                      code_scripts: 'Scripts & Code',
                      other: 'Other Files'
                    };
                    return (
                      <div key={category} className="pfb-file-category">
                        <h5 className="pfb-category-title">
                          {labels[category]} <span className="muted">({files.length})</span>
                        </h5>
                        <div className="pfb-file-grid">
                          {files.map((file) => {
                            const norm = normalizeRelPath(file.path);
                            const rowStatus = getFilePreviewStatus(file, twin, norm);
                            return (
                              <div
                                key={file.path}
                                className={`pfb-file-card ${selectedFile?.path === file.path ? 'active' : ''}`}
                                onClick={() => loadFilePreview(file)}
                                title={file.path}
                              >
                                <div className="pfb-file-card-header">
                                  <div className="pfb-file-card-icon">
                                    <FileTypeBadge file={file} />
                                  </div>
                                  <div className="pfb-file-card-info">
                                    <span className="pfb-file-name">{file.name}</span>
                                    <span className="pfb-file-meta">
                                      {formatFileSize(file.size_bytes)} • {formatModifiedAt(file.modified_at)}
                                    </span>
                                  </div>
                                </div>
                                <div className="pfb-file-card-footer">
                                  <span className={`pfb-index-badge tone-${rowStatus.tone}`}>
                                    {rowStatus.label}
                                  </span>
                                  <FileText size={14} className="muted" aria-hidden />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <p className="muted text-footnote workspace-empty-state">Select a content section.</p>
          )}
        </div>

        <div className="pfb-column pfb-preview-pane pfb-column--resizable">
          <h4 className="workspace-subpanel-title">Preview</h4>
          {!selectedFile ? (
            <div className="pfb-preview-empty">
              <FileText size={32} className="pfb-preview-empty-icon" aria-hidden />
              <p className="muted text-footnote">
                Select a file from the list to preview extracted text, PDFs, or images.
              </p>
              <p className="text-footnote muted">
                Tip: run <strong>Scan project folder</strong> to refresh the digital twin index.
              </p>
            </div>
          ) : (
            <>
              <div className="pfb-preview-header">
                <div className="pfb-preview-title-row">
                  <b className="pfb-preview-filename">{selectedFile.name}</b>
                  <FileTypeBadge file={selectedFile} />
                </div>
                {filePreviewStatus && (
                  <div className="pfb-preview-status-row">
                    <span className={`pfb-index-badge tone-${filePreviewStatus.tone}`}>
                      {filePreviewStatus.label}
                    </span>
                    {previewSource && (
                      <span className="text-footnote muted">Loaded via {previewSource}</span>
                    )}
                    {previewMeta?.extractor && (
                      <span className="text-footnote muted">· {previewMeta.extractor}</span>
                    )}
                  </div>
                )}
                <div className="pfb-preview-path-row">
                  <SmartLink href={selectedFile.path} showCopy maxLabelLen={80} />
                </div>
                <div className="pfb-preview-actions">
                  <a
                    href={projectAssetUrl(projectCode, selectedFile.path, API_URL)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary btn-sm"
                    download={!isPdf && !mediaKind ? selectedFile.name : undefined}
                  >
                    Open file
                  </a>
                  <CopyPathButton value={selectedFile.path} label="Copy relative path" />
                </div>
              </div>
              {previewLoading && (
                <p className="text-loading pfb-preview-loading">
                  <Loader2 size={14} className="spin" /> Loading preview…
                </p>
              )}
              {previewError && !previewLoading && (
                <p className="text-callout pfb-preview-error">{previewError}</p>
              )}
              {['.md', '.txt', '.html', '.rtf'].includes(selectedExt) && preview != null && !previewLoading && (
                <LazyDataPadEditor
                  projectCode={projectCode}
                  relativePath={normalizeRelPath(selectedFile.path)}
                  fileName={selectedFile.name}
                  sectionLabel={selectedFolder?.label}
                  initialContent={preview}
                  onSaved={(text) => {
                    setPreview(text);
                    setPreviewSource('Data Pad (saved)');
                  }}
                />
              )}
              {previewSlice && !mediaKind && !['.md', '.txt', '.html', '.rtf'].includes(selectedExt) && (
                <>
                  <div className="surface-inset" style={{ padding: '1.5rem' }}>
                    <DocumentFormatter 
                      text={previewSlice} 
                      onCreateTask={(text) =>
                        openTaskpad(text, {
                          section: folderSectionToWorkspaceTab(selectedFolder?.id),
                          filePath: selectedFile.path,
                          fileName: selectedFile.name,
                        })
                      }
                    />
                  </div>
                  {preview.length > PREVIEW_LIMIT && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setPreviewExpanded((v) => !v)}
                    >
                      {previewExpanded ? 'Show less' : `Show full preview (${preview.length.toLocaleString()} chars)`}
                    </button>
                  )}
                </>
              )}
              {assetUrl && isPdf && (
                <PdfDocumentViewer
                  url={assetUrl}
                  title={selectedFile.name}
                  documentKey={selectedFile.path || assetUrl}
                  exportLocal={{
                    filename: selectedFile.name,
                    originalUrl: assetUrl,
                    title: selectedFile.name,
                  }}
                  className="database-pdf-frame pfb-pdf-frame"
                />
              )}
              {assetUrl && mediaKind === 'model3d' && !previewLoading && (
                <Suspense fallback={<p className="text-footnote muted">Loading 3D viewer…</p>}>
                  <ModelViewer3D url={assetUrl} title={selectedFile.name} />
                </Suspense>
              )}
              {assetUrl && mediaKind && mediaKind !== 'model3d' && !previewLoading && (
                <MediaViewer
                  url={assetUrl}
                  title={selectedFile.name}
                  kind={mediaKind}
                  labels={{
                    loading: 'Loading…',
                    failed: 'Could not load image.',
                    videoLoading: 'Loading video…',
                    videoFailed: 'Could not load video.',
                  }}
                />
              )}
              {assetUrl && isPdf && !previewSlice && !previewLoading && !previewError && (
                <p className="text-footnote muted" style={{ marginTop: '0.5rem' }}>
                  PDF shown above. Re-scan the project for searchable extracted text below.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
