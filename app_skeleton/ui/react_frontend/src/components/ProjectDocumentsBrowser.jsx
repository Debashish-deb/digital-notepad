import { useEffect, useMemo, useState } from 'react';
import {
  Archive,
  BarChart3,
  BookOpen,
  Calendar,
  ClipboardList,
  FileText,
  FlaskConical,
  FolderOpen,
  Loader2,
  Users,
} from 'lucide-react';
import DocumentPreviewPane from './DocumentPreviewPane.jsx';
import DocumentFileSearch from './DocumentFileSearch.jsx';
import SmartLink from './SmartLink.jsx';
import {
  documentDisplayExcerpt,
  getChunkTextForFile,
  labDatabaseAssetUrl,
} from '../utils/labDatabaseUtils.js';
import { isJunkPreviewText } from '../utils/textCleanup.js';
import { smartDocumentTitle } from '../utils/smartDocumentTitle.js';
import { inferExtension } from '../utils/fileTypeMeta.js';
import { getChunkTextForProjectFile, normalizeRelPath } from '../utils/folderBrowserUtils.js';
import { getMediaPreviewKind } from '../utils/mediaPreviewKind.js';
import { buildMediaGallery, mergeGalleryItem } from '../utils/mediaGalleryUtils.js';
import { useSpreadsheetPreview } from '../hooks/useSpreadsheetPreview.js';
import { useRawFilePreview } from '../hooks/useRawFilePreview.js';
import { getFilePreviewKind, shouldFetchRawFile } from '../utils/filePreviewKind.js';
import { projectAssetUrl } from '../utils/digitalTwinUtils.js';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import {
  collectProjectDocuments,
  flattenCategoryOrder,
  groupDocumentsByCategory,
} from '../utils/documentBrowserUtils.js';
import {
  buildProjectTabCategoryGroups,
  getProjectTabDocumentConfig,
  projectDocumentTitle,
} from '../utils/projectDocumentCategories.js';
import { findProjectLogFile, isProjectLogFile } from '../utils/projectLogUtils.js';
import {
  getResearchMaterialsForProject,
  loadResearchMaterialsTwin,
} from '../utils/researchMaterialsRouting.js';
import DocumentCategoryFileList, {
  countGroupedFiles,
} from './DocumentCategoryFileList.jsx';
import { useGuiT } from '../i18n/useGuiT.js';
import { consumeSearchNavigation } from '../utils/searchHits.js';
import {
  buildExpandedPreviewMetadata,
  buildProjectPreviewMetadata,
  computePreviewMetadataScore,
  findCategoryLabelInGroups,
  prettifyPreviewLabel,
} from '../utils/previewMetaUtils.js';
import { isProjectReadmePath } from '../utils/projectReadmeUtils.js';
import { canEditDocument, documentViewBadge, isSourceDocument } from '../utils/documentEditPolicy.js';

const CATEGORY_ICONS = {
  root: FolderOpen,
  wet_lab: FlaskConical,
  dry_lab: BarChart3,
  protocols: FileText,
  schedules: Calendar,
  figures: BarChart3,
  abstracts: BookOpen,
  posters: BookOpen,
  manuscripts: BookOpen,
  peer_review: FileText,
  meeting_notes: ClipboardList,
  archive_root: Archive,
};

const EDITABLE_EXTENSIONS = new Set(['.md', '.txt', '.html', '.rtf']);

function resolveDocumentTitle(doc) {
  if (doc?.display_title) {
    return smartDocumentTitle(doc);
  }
  return projectDocumentTitle(doc);
}

export default function ProjectDocumentsBrowser({
  twin,
  projectCode,
  API_URL,
  workspaceTab,
  defaultCategory: defaultCategoryProp,
  className = 'project-documents-browser',
  onReadmeSaved,
}) {
  const [selectedPath, setSelectedPath] = useState(null);
  const [fileQuery, setFileQuery] = useState('');
  const [viewerExpanded, setViewerExpanded] = useState(false);
  const [researchDocs, setResearchDocs] = useState([]);
  const [researchTwin, setResearchTwin] = useState(null);
  const { openTaskpad } = useTaskpad();
  const { t, localizeCategories } = useGuiT();

  useEffect(() => {
    if (!twin) return;
    const pending = consumeSearchNavigation();
    if (!pending?.relative_path) return;
    setSelectedPath(normalizeRelPath(pending.relative_path));
    if (pending.query) setFileQuery(pending.query);
  }, [twin]);

  useEffect(() => {
    if (workspaceTab !== 'writing' || !projectCode) {
      setResearchDocs([]);
      setResearchTwin(null);
      return undefined;
    }

    let alive = true;
    getResearchMaterialsForProject(projectCode)
      .then((docs) => {
        if (!alive) return;
        setResearchDocs(docs);
      })
      .catch(() => {
        if (alive) setResearchDocs([]);
      });

    loadResearchMaterialsTwin().then((twin) => {
      if (alive) setResearchTwin(twin);
    });

    return () => {
      alive = false;
    };
  }, [workspaceTab, projectCode]);

  const projectLogFile = useMemo(() => findProjectLogFile(twin), [twin]);

  const allDocs = useMemo(() => {
    if (!twin) return workspaceTab === 'writing' ? [...researchDocs] : [];
    const config = getProjectTabDocumentConfig(workspaceTab, [], projectCode);
    const projectDocs = collectProjectDocuments(twin, {
      categorizePath: config.categorizePath,
      documentTitle: projectDocumentTitle,
      tabFilter: config.tabFilter,
    });
    if (workspaceTab !== 'writing' || !researchDocs.length) return projectDocs;

    const seen = new Set(projectDocs.map((d) => d.path));
    const merged = [...projectDocs];
    for (const doc of researchDocs) {
      if (!seen.has(doc.path)) merged.push(doc);
    }
    return merged;
  }, [twin, workspaceTab, projectCode, researchDocs]);

  const categoryGroups = useMemo(
    () => buildProjectTabCategoryGroups(workspaceTab, allDocs),
    [workspaceTab, allDocs]
  );

  const localizedCategoryGroups = useMemo(
    () => localizeCategories(categoryGroups),
    [categoryGroups, localizeCategories]
  );

  const categoryOrder = useMemo(
    () => flattenCategoryOrder(localizedCategoryGroups),
    [localizedCategoryGroups]
  );
  const grouped = useMemo(
    () => groupDocumentsByCategory(allDocs, categoryOrder),
    [allDocs, categoryOrder]
  );

  useEffect(() => {
    const logPath = projectLogFile?.path;
    if (workspaceTab === 'log' && logPath && (grouped.project_log || []).some((d) => d.path === logPath)) {
      setSelectedPath(logPath);
    } else {
      setSelectedPath(null);
    }
    setFileQuery('');
  }, [workspaceTab, categoryOrder.join(','), twin?.processed_at, projectLogFile?.path, grouped]);

  const visibleFileCount = useMemo(
    () =>
      countGroupedFiles(localizedCategoryGroups, grouped, fileQuery, resolveDocumentTitle),
    [localizedCategoryGroups, grouped, fileQuery]
  );

  const fileSearchControl = (
    <DocumentFileSearch
      compact
      value={fileQuery}
      onChange={setFileQuery}
      fileCount={visibleFileCount}
      searchPlaceholder={t('docs.searchPlaceholder')}
      searchAria={t('docs.searchFiles')}
      filesLabel={t('docs.filesInSection', '', { count: visibleFileCount })}
    />
  );

  const selectedDoc = useMemo(
    () => allDocs.find((d) => d.path === selectedPath) || null,
    [allDocs, selectedPath]
  );

  const selectedExt = selectedDoc
    ? inferExtension(selectedDoc.name, selectedDoc.extension)
    : '';
  const isPdf = selectedExt === '.pdf';
  const mediaKind = getMediaPreviewKind(selectedExt);
  const previewKind = getFilePreviewKind(selectedExt, selectedDoc?.path);
  const isSpreadsheet = previewKind === 'spreadsheet';
  const isEditable = selectedDoc ? canEditDocument(selectedDoc, selectedExt) : false;

  const previewText = useMemo(() => {
    if (!selectedDoc) return null;
    const fromChunks = selectedDoc.isResearchMaterial
      ? getChunkTextForFile(researchTwin, selectedDoc.researchMaterialOriginalPath)
      : getChunkTextForProjectFile(twin, selectedDoc.path);
    const excerpt = selectedDoc.excerpt || documentDisplayExcerpt(selectedDoc, 12000);
    const raw = (fromChunks || excerpt || '').trim();
    if (!raw || isJunkPreviewText(raw)) return null;
    return raw;
  }, [selectedDoc, twin, researchTwin]);

  const assetUrl = useMemo(() => {
    if (!selectedDoc) return null;
    if (selectedDoc.isResearchMaterial) {
      return labDatabaseAssetUrl(
        selectedDoc.researchMaterialRoot,
        selectedDoc.researchMaterialOriginalPath
      );
    }
    return projectAssetUrl(projectCode, selectedDoc.path, API_URL, twin?.content_root);
  }, [selectedDoc, projectCode, API_URL, twin?.content_root]);

  const spreadsheetPreview = useSpreadsheetPreview(
    isSpreadsheet && assetUrl ? assetUrl : null,
    selectedExt
  );
  const scriptFallbackText = useMemo(() => {
    if (!selectedDoc || !twin || !shouldFetchRawFile(previewKind)) return null;
    const fromChunks = getChunkTextForProjectFile(twin, selectedDoc.path);
    if (fromChunks?.trim()) return fromChunks;
    const excerpt = selectedDoc.excerpt || documentDisplayExcerpt(selectedDoc, 12000);
    const raw = (excerpt || '').trim();
    return raw && !isJunkPreviewText(raw) ? raw : null;
  }, [selectedDoc, twin, previewKind]);

  const rawFilePreview = useRawFilePreview(assetUrl, previewKind, {
    projectCode,
    relativePath: selectedDoc?.path,
    fallbackText: scriptFallbackText,
  });

  const siblingPdf = useMemo(() => {
    if (!selectedDoc || isPdf) return null;
    const stem = selectedDoc.path.replace(/\.[^.]+$/, '');
    const pdfPath = `${stem}.pdf`;
    return allDocs.find((doc) => doc.path === pdfPath) || null;
  }, [selectedDoc, allDocs, isPdf]);

  const pdfPreviewUrl = useMemo(() => {
    if (isPdf && assetUrl) return assetUrl;
    if (siblingPdf) {
      return projectAssetUrl(projectCode, siblingPdf.path, API_URL, twin?.content_root);
    }
    return null;
  }, [isPdf, assetUrl, siblingPdf, projectCode, API_URL, twin?.content_root]);

  const resolveDocAssetUrl = useMemo(
    () => (doc) => {
      if (!doc) return null;
      if (doc.isResearchMaterial) {
        return labDatabaseAssetUrl(doc.researchMaterialRoot, doc.researchMaterialOriginalPath);
      }
      return projectAssetUrl(projectCode, doc.path, API_URL, twin?.content_root);
    },
    [projectCode, API_URL, twin?.content_root]
  );

  const mediaGallery = useMemo(() => {
    if (!selectedDoc || !mediaKind) return [];
    const siblings = buildMediaGallery(
      selectedDoc,
      allDocs,
      resolveDocAssetUrl,
      resolveDocumentTitle
    );
    return mergeGalleryItem(selectedDoc, siblings, resolveDocAssetUrl, resolveDocumentTitle);
  }, [selectedDoc, allDocs, mediaKind, resolveDocAssetUrl, resolveDocumentTitle]);

  const categoryLabel = useMemo(
    () => findCategoryLabelInGroups(localizedCategoryGroups, selectedDoc?.categoryId),
    [localizedCategoryGroups, selectedDoc?.categoryId]
  );

  const previewMetadataItems = useMemo(
    () =>
      buildProjectPreviewMetadata({
        doc: selectedDoc,
        projectCode,
        workspaceTab,
        previewKind,
        extension: selectedExt,
        previewText,
        categoryLabel,
      }),
    [selectedDoc, projectCode, workspaceTab, previewKind, selectedExt, previewText, categoryLabel]
  );

  const expandedPreviewMetadata = useMemo(
    () =>
      buildExpandedPreviewMetadata({
        doc: selectedDoc,
        path: selectedDoc?.path,
        previewKind,
        extension: selectedExt,
        previewText,
        assetUrl,
        extra: {
          project: projectCode,
          tab: workspaceTab,
          category: categoryLabel,
        },
      }),
    [
      selectedDoc,
      previewKind,
      selectedExt,
      previewText,
      assetUrl,
      projectCode,
      workspaceTab,
      categoryLabel,
    ]
  );

  const metadataCompleteness = useMemo(
    () => computePreviewMetadataScore(selectedDoc, previewText || rawFilePreview?.content),
    [selectedDoc, previewText, rawFilePreview?.content]
  );

  const previewBadges = useMemo(() => {
    const items = [];
    if (previewKind) items.push(prettifyPreviewLabel(previewKind));
    if (selectedDoc?.isResearchMaterial) items.push('Research material');
    const sourceBadge = selectedDoc ? documentViewBadge(selectedDoc, selectedExt) : null;
    if (sourceBadge) items.push(sourceBadge);
    return items;
  }, [previewKind, selectedDoc, selectedExt]);

  const contentRoot = twin?.content_root || twin?.folder_path || null;

  if (!twin) {
    return (
      <div className="panel" style={{ padding: '2rem', textAlign: 'center' }}>
        <Loader2 size={20} className="spin-inline" /> {t('docs.loadingProject')}
      </div>
    );
  }

  if (!allDocs.length) {
    return (
      <section className={`panel workspace-section data-pad data-pad--compact ${className}`}>
        <p className="text-footnote muted">{t('docs.noProjectFiles')}</p>
      </section>
    );
  }

  return (
    <section className={`panel workspace-section data-pad data-pad--compact data-pad--embedded ${className}`}>
      {contentRoot ? (
        <div className="data-pad-root data-pad-root--inline">
          <SmartLink href={contentRoot} showCopy maxLabelLen={48} />
        </div>
      ) : null}

      <div className="lab-docs-section-layout lab-docs-section-layout--grouped">
        <div className="lab-docs-section-main">

          <div
            className={`pfb-layout lab-docs-layout lab-docs-layout--compact lab-docs-layout--project${selectedDoc ? ' pfb-layout--editor-focus pfb-layout--doc-full' : ''}${viewerExpanded ? ' pfb-layout--viewer-expanded' : ''}`}
          >
            <div className="pfb-column pfb-files-pane lab-doc-files-panel">
              <DocumentCategoryFileList
                categoryGroups={localizedCategoryGroups}
                grouped={grouped}
                fileQuery={fileQuery}
                documentTitle={resolveDocumentTitle}
                selectedPath={selectedPath}
                onSelectFile={setSelectedPath}
                categoryIcons={CATEGORY_ICONS}
                categoryLayout="horizontal-top"
                toolbarAfterTabs={fileSearchControl}
              />
            </div>

        <div className="pfb-column pfb-preview-pane pfb-preview-pane--editor-focus">
          {!selectedDoc ? (
            <p className="text-footnote muted" style={{ marginTop: '1rem' }}>
              {t('docs.selectFileEdit')}
            </p>
          ) : (
            <DocumentPreviewPane
              onExpandChange={setViewerExpanded}
              onBackToFiles={() => setSelectedPath(null)}
              title={resolveDocumentTitle(selectedDoc)}
              path={selectedDoc.path}
              extension={selectedDoc.extension || inferExtension(selectedDoc.name)}
              previewKind={previewKind}
              rawFilePreview={rawFilePreview}
              previewText={previewText}
              pdfPreviewUrl={pdfPreviewUrl}
              pdfThumbLabel={isPdf ? 'PDF' : 'PDF copy'}
              mediaKind={mediaKind}
              mediaUrl={assetUrl}
              mediaAlt={resolveDocumentTitle(selectedDoc)}
              mediaGallery={mediaGallery}
              onMediaNavigate={setSelectedPath}
              mediaLabels={{
                loading: t('docs.mediaLoading'),
                failed: t('docs.mediaFailed'),
                videoLoading: t('docs.videoLoading'),
                videoFailed: t('docs.videoFailed'),
                modelLoading: t('docs.modelLoading'),
                zoomIn: t('docs.mediaZoomIn'),
                zoomOut: t('docs.mediaZoomOut'),
                fit: t('docs.mediaFit'),
                actualSize: t('docs.mediaActualSize'),
                rotate: t('docs.mediaRotate'),
                fullscreen: t('docs.mediaFullscreen'),
                download: t('docs.openOriginal'),
                previous: t('docs.mediaPrevious'),
                next: t('docs.mediaNext'),
                hint: t('docs.modelHint'),
                play: t('docs.modelPlay'),
                pause: t('docs.modelPause'),
                autoRotate: t('docs.modelAutoRotate'),
                reset: t('docs.modelReset'),
              }}
              isEditable={isEditable && !isProjectLogFile(selectedDoc.path)}
              editorProps={
                isEditable && previewText && !isProjectLogFile(selectedDoc.path)
                  ? {
                      projectCode,
                      relativePath: normalizeRelPath(selectedDoc.path),
                      fileName: selectedDoc.name,
                      sectionLabel: selectedDoc.section_label,
                      initialContent: previewText,
                      onSaved: isProjectReadmePath(selectedDoc.path) ? onReadmeSaved : undefined,
                    }
                  : null
              }
              spreadsheetPreview={isSpreadsheet ? spreadsheetPreview : null}
              spreadsheetFileUrl={isSpreadsheet ? assetUrl : null}
              spreadsheetLabels={{
                loading: t('docs.spreadsheetLoading'),
                repaired: t('docs.spreadsheetRepaired'),
                truncated: t('docs.spreadsheetTruncated'),
                empty: t('docs.spreadsheetEmpty'),
                failed: t('docs.spreadsheetFailed'),
                openOriginal: t('docs.openOriginal'),
              }}
              codeLabels={{
                loading: t('docs.codeLoading'),
                failed: t('docs.codeFailed'),
              }}
              emptyHint={t('docs.noTextPreview')}
              onCreateTask={(text) =>
                openTaskpad(text, {
                  section: workspaceTab,
                  projectCode,
                  filePath: selectedPath || undefined,
                  fileName: selectedDoc?.name || selectedDoc?.title,
                })
              }
              metadataItems={previewMetadataItems}
              expandedMetadataItems={expandedPreviewMetadata}
              metadataCompleteness={metadataCompleteness}
              badges={previewBadges}
              exportLocal={{
                filename: selectedDoc?.name || selectedDoc?.title,
                title: resolveDocumentTitle(selectedDoc),
                text: previewText || rawFilePreview?.content,
                metadata: selectedDoc,
                originalUrl: assetUrl,
              }}
              actions={
                <>
                  {assetUrl ? (
                    <a
                      href={assetUrl}
                      className="btn btn-secondary btn-sm"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {t('docs.openOriginal')}
                    </a>
                  ) : null}
                </>
              }
            />
          )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
