import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FileText, LayoutGrid, List, Loader2, Lock } from 'lucide-react';
import DocumentPreviewPane from '@/features/documents/components/DocumentPreviewPane.jsx';
import DocumentFileSearch from '@/features/documents/components/DocumentFileSearch.jsx';
import SmartLink from '@/shared/ui/SmartLink.jsx';
import {
  documentDisplayExcerpt,
  fetchLabSectionProcessed,
  getChunkTextForFile,
  labDatabaseAssetUrl,
} from '@/lib/labDatabaseUtils.js';
import { isJunkPreviewText } from '@/lib/textCleanup.js';
import { inferExtension } from '@/lib/fileTypeMeta.js';
import { getMediaPreviewKind } from '@/lib/mediaPreviewKind.js';
import { buildMediaGallery, mergeGalleryItem } from '@/lib/mediaGalleryUtils.js';
import { useSpreadsheetPreview } from '@/shared/hooks/useSpreadsheetPreview.js';
import { useRawFilePreview } from '@/shared/hooks/useRawFilePreview.js';
import { useCatalogDocumentPreview } from '@/shared/hooks/useCatalogDocumentPreview.js';
import { getFilePreviewKind } from '@/lib/filePreviewKind.js';
import { useTaskpad } from '@/contexts/TaskpadContext.jsx';
import {
  collectProjectDocuments,
  deduplicateDocumentsByPath,
  flattenCategoryOrder,
  groupDocumentsByCategory,
} from '@/lib/documentBrowserUtils.js';
import { normalizeDocPath } from '@/lib/folderBrowserUtils.js';
import DocumentCategoryFileList, {
  countGroupedFiles,
} from '@/features/documents/components/DocumentCategoryFileList.jsx';
import DocumentMediaGallery from './DocumentMediaGallery.jsx';
import {
  deriveBrowserLayoutMode,
  isGalleryLayoutMode,
} from '@/lib/documentBrowserLayoutMode.js';
import { useGuiT } from '@/i18n/useGuiT.js';
import { useModuleShellHeaderSlot } from '@/contexts/ModuleShellHeaderSlotContext.jsx';
import { consumeSearchNavigation } from '@/lib/searchHits.js';
import {
  buildExpandedPreviewMetadata,
  buildLabPreviewMetadata,
  computePreviewMetadataScore,
  prettifyPreviewLabel,
} from '@/lib/previewMetaUtils.js';

export default function LabDocumentsBrowser({
  sectionId,
  sectionIds,
  title,
  description,
  icon: Icon = FileText,
  categoryGroups,
  defaultCategory,
  categorizePath,
  documentTitle,
  categoryIcons = {},
  className = 'lab-documents-browser',
  topPanel = null,
  sensitiveCategories = [],
  documentFilter = null,
  syntheticDocs = [],
  syntheticPreviewField = 'inlineContent',
  folderHintResolver = null,
  layoutVariant = 'catalog',
}) {
  const [twins, setTwins] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPath, setSelectedPath] = useState(null);
  const [fileQuery, setFileQuery] = useState('');
  const [viewerExpanded, setViewerExpanded] = useState(false);
  const [revealSensitive, setRevealSensitive] = useState(false);
  const [visibleFiles, setVisibleFiles] = useState([]);
  const [layoutModeOverride, setLayoutModeOverride] = useState(null);
  const [debouncedVisibleFiles, setDebouncedVisibleFiles] = useState([]);
  const layoutDebounceRef = useRef(null);
  const { openTaskpad } = useTaskpad();
  const { t, localizeCategories } = useGuiT();

  const ids = sectionIds?.length ? sectionIds : [sectionId];

  useEffect(() => {
    setSelectedPath(null);
    setVisibleFiles([]);
    setLayoutModeOverride(null);
  }, [ids.join(',')]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    Promise.all(ids.map((id) => fetchLabSectionProcessed(id).then((data) => [id, data])))
      .then((pairs) => {
        if (!mounted) return;
        const loaded = pairs.filter(([, data]) => data);
        const map = Object.fromEntries(loaded);
        if (!Object.keys(map).length) {
          throw new Error('No document sections could be loaded.');
        }
        setTwins(map);
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || 'Failed to load documents.');
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [ids.join(',')]);

  useEffect(() => {
    if (loading || !Object.keys(twins).length) return;
    const pending = consumeSearchNavigation();
    if (!pending?.relative_path) return;
    const target = normalizeDocPath(pending.relative_path);
    if (pending.query) setFileQuery(pending.query);
    setSelectedPath(target);
  }, [loading, twins]);

  const primaryTwin = twins[ids[0]];

  const allDocs = useMemo(() => {
    const docs = [];
    for (const id of ids) {
      const twin = twins[id];
      if (!twin) continue;
      const sectionDocs = collectProjectDocuments(twin, {
        categorizePath: (path) => categorizePath(path, id),
        documentTitle,
      });
      for (const doc of sectionDocs) {
        if (documentFilter && !documentFilter(doc.path)) continue;
        docs.push({
          ...doc,
          sourceSection: id,
          folderHint:
            folderHintResolver?.(id)
            || (ids.length > 1 ? id.replace('overview_', '').replace(/_/g, ' ') : null),
        });
      }
    }
    for (const doc of syntheticDocs) {
      if (documentFilter && !documentFilter(doc.path)) continue;
      docs.push(doc);
    }
    return deduplicateDocumentsByPath(docs);
  }, [twins, ids, categorizePath, documentTitle, documentFilter, syntheticDocs, folderHintResolver]);

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

  const visibleFileCount = useMemo(
    () =>
      countGroupedFiles(localizedCategoryGroups, grouped, fileQuery, documentTitle),
    [localizedCategoryGroups, grouped, fileQuery, documentTitle]
  );

  const setHeaderSlot = useModuleShellHeaderSlot();

  useEffect(() => {
    if (!setHeaderSlot) return undefined;
    setHeaderSlot(
      <DocumentFileSearch
        value={fileQuery}
        onChange={setFileQuery}
        fileCount={visibleFileCount}
        searchPlaceholder={t('docs.searchPlaceholder')}
        searchAria={t('docs.searchFiles')}
        filesLabel={t('docs.filesInSection', '', { count: visibleFileCount })}
      />
    );
    return () => setHeaderSlot(null);
  }, [setHeaderSlot, fileQuery, visibleFileCount, t]);

  const selectedDoc = useMemo(() => {
    if (!selectedPath) return null;
    const key = normalizeDocPath(selectedPath);
    return allDocs.find((d) => normalizeDocPath(d.path) === key) || null;
  }, [allDocs, selectedPath]);

  const selectedCategoryId = selectedDoc?.categoryId;
  const isSensitive = sensitiveCategories.includes(selectedCategoryId);

  const selectedTwin = selectedDoc?.sourceSection
    ? twins[selectedDoc.sourceSection]
    : primaryTwin;

  const maskSensitiveText = (text) => {
    if (!text) return '';
    return text
      .split('\n')
      .map((line) => {
        if (/\b(password|passcode|secret|username|credential|token|api key)\b/i.test(line)) {
          const sep = line.search(/[:=]/);
          if (sep >= 0) return `${line.slice(0, sep + 1)} [hidden]`;
          return '[hidden sensitive line]';
        }
        return line;
      })
      .join('\n');
  };

  const selectedExt = selectedDoc
    ? inferExtension(selectedDoc.name, selectedDoc.extension)
    : '';
  const isPdf = selectedExt === '.pdf';
  const mediaKind = getMediaPreviewKind(selectedExt);
  const previewKind = getFilePreviewKind(selectedExt, selectedDoc?.path);
  const isSpreadsheet = previewKind === 'spreadsheet';

  const relativeRoot = selectedTwin?.relative_root || primaryTwin?.relative_root;
  const assetUrl = useMemo(
    () =>
      selectedDoc && relativeRoot
        ? labDatabaseAssetUrl(relativeRoot, selectedDoc.path)
        : null,
    [selectedDoc, relativeRoot]
  );

  const twinPreviewText = useMemo(() => {
    if (!selectedDoc) return null;
    if (selectedDoc.isSynthetic && selectedDoc[syntheticPreviewField]) {
      const raw = String(selectedDoc[syntheticPreviewField]).trim();
      return isSensitive && !revealSensitive ? maskSensitiveText(raw) : raw;
    }
    if (!selectedTwin) return null;
    const fromChunks = getChunkTextForFile(selectedTwin, selectedDoc.path);
    const excerpt = selectedDoc.excerpt || documentDisplayExcerpt(selectedDoc, 12000);
    const raw = (fromChunks || excerpt || '').trim();
    if (!raw || isJunkPreviewText(raw)) return null;
    return isSensitive && !revealSensitive ? maskSensitiveText(raw) : raw;
  }, [selectedDoc, selectedTwin, isSensitive, revealSensitive, syntheticPreviewField]);

  const catalogPreview = useCatalogDocumentPreview(
    selectedDoc?.path,
    selectedDoc?.name,
    Boolean(selectedDoc?.path)
  );

  const spreadsheetPreview = useSpreadsheetPreview(
    isSpreadsheet && assetUrl ? assetUrl : null,
    selectedExt
  );
  const rawFilePreview = useRawFilePreview(assetUrl, previewKind, {
    fallbackText: twinPreviewText,
  });

  const mergedSpreadsheetPreview = useMemo(() => {
    if (!isSpreadsheet) return null;
    const fileSheets = spreadsheetPreview.sheets;
    const catalogSheets = catalogPreview.sheets;
    const sheets = fileSheets?.length ? fileSheets : catalogSheets;
    const fromCatalog = Boolean(!fileSheets?.length && catalogSheets?.length);
    const loading =
      !sheets?.length && (spreadsheetPreview.loading || catalogPreview.loading);
    const error =
      !sheets?.length &&
      !loading &&
      !catalogPreview.displayText &&
      spreadsheetPreview.error
        ? spreadsheetPreview.error
        : null;
    return {
      loading,
      sheets,
      repairNotes: [
        ...(spreadsheetPreview.repairNotes || []),
        ...(fromCatalog ? ['Rendered from lab catalog extraction.'] : []),
      ],
      error,
      strategy: fileSheets?.length ? spreadsheetPreview.strategy : fromCatalog ? 'catalog' : null,
    };
  }, [isSpreadsheet, spreadsheetPreview, catalogPreview]);

  const spreadsheetReady = Boolean(mergedSpreadsheetPreview?.sheets?.length);

  const previewText = twinPreviewText || catalogPreview.displayText || null;
  const previewFromCatalog = Boolean(
    !twinPreviewText && (catalogPreview.displayText || catalogPreview.sheets?.length)
  );
  const hasImmediatePreview = Boolean(
    (mediaKind && assetUrl) ||
    (isPdf && assetUrl) ||
    previewKind === 'code' ||
    previewKind === 'json' ||
    previewKind === 'text' ||
    previewKind === 'markup' ||
    isSpreadsheet
  );
  const previewLoading =
    !hasImmediatePreview &&
    !previewText &&
    !spreadsheetReady &&
    (catalogPreview.loading || (isSpreadsheet && spreadsheetPreview.loading));

  const siblingPdf = useMemo(() => {
    if (!selectedDoc || isPdf) return null;
    const stem = selectedDoc.path.replace(/\.[^.]+$/, '');
    const pdfPath = `${stem}.pdf`;
    return allDocs.find((doc) => doc.path === pdfPath) || null;
  }, [selectedDoc, allDocs, isPdf]);

  const pdfPreviewUrl = useMemo(() => {
    if (!relativeRoot) return null;
    if (isPdf && assetUrl) return assetUrl;
    if (siblingPdf) return labDatabaseAssetUrl(relativeRoot, siblingPdf.path);
    return null;
  }, [isPdf, assetUrl, siblingPdf, relativeRoot]);

  const mediaGallery = useMemo(() => {
    if (!selectedDoc || !relativeRoot || !mediaKind) return [];
    const resolveUrl = (doc) => labDatabaseAssetUrl(relativeRoot, doc.path);
    const siblings = buildMediaGallery(selectedDoc, allDocs, resolveUrl, documentTitle);
    return mergeGalleryItem(selectedDoc, siblings, resolveUrl, documentTitle);
  }, [selectedDoc, allDocs, relativeRoot, mediaKind, documentTitle]);

  const contentRoot = primaryTwin?.content_root;

  const previewMetadataItems = useMemo(
    () =>
      buildLabPreviewMetadata({
        doc: selectedDoc,
        sectionId,
        previewKind,
        extension: selectedExt,
        previewText,
      }),
    [selectedDoc, sectionId, previewKind, selectedExt, previewText]
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
          section: sectionId,
          sensitivity: selectedDoc?.sensitivity_level,
          source: previewFromCatalog ? 'catalog' : 'twin',
        },
      }),
    [
      selectedDoc,
      previewKind,
      selectedExt,
      previewText,
      assetUrl,
      sectionId,
      previewFromCatalog,
    ]
  );

  const metadataCompleteness = useMemo(
    () => computePreviewMetadataScore(selectedDoc, previewText || rawFilePreview?.content),
    [selectedDoc, previewText, rawFilePreview?.content]
  );

  const previewBadges = useMemo(() => {
    const items = [];
    if (previewKind) items.push(prettifyPreviewLabel(previewKind));
    if (previewFromCatalog) items.push('Catalog extract');
    if (selectedDoc?.sensitivity_level) items.push(prettifyPreviewLabel(selectedDoc.sensitivity_level));
    return items;
  }, [previewKind, previewFromCatalog, selectedDoc?.sensitivity_level]);

  const handleVisibleFilesChange = useCallback((files) => {
    setVisibleFiles((prev) => {
      if (
        prev.length === files.length &&
        prev.every((doc, index) => doc.path === files[index]?.path)
      ) {
        return prev;
      }
      return files;
    });
  }, []);

  useEffect(() => {
    if (layoutDebounceRef.current) clearTimeout(layoutDebounceRef.current);
    layoutDebounceRef.current = setTimeout(() => {
      setDebouncedVisibleFiles(visibleFiles);
    }, 120);
    return () => {
      if (layoutDebounceRef.current) clearTimeout(layoutDebounceRef.current);
    };
  }, [visibleFiles]);

  const layoutInfo = useMemo(
    () => deriveBrowserLayoutMode(debouncedVisibleFiles, { userOverride: layoutModeOverride }),
    [debouncedVisibleFiles, layoutModeOverride]
  );

  useEffect(() => {
    if (layoutInfo.mode !== 'mixed') {
      setLayoutModeOverride(null);
    }
  }, [layoutInfo.mode]);

  const effectiveLayoutMode = useMemo(() => {
    if (layoutModeOverride === 'gallery' || layoutModeOverride === 'split') {
      return layoutModeOverride;
    }
    if (layoutInfo.mode === 'mixed') {
      return layoutInfo.dominantKind === 'image' || layoutInfo.dominantKind === 'video'
        ? 'gallery'
        : 'split';
    }
    if (layoutInfo.mode === 'media') return 'gallery';
    return layoutInfo.mode;
  }, [layoutInfo, layoutModeOverride]);

  const useGalleryLayout = isGalleryLayoutMode(effectiveLayoutMode);

  const resolveDocAssetUrl = useCallback(
    (doc) => {
      const twin = doc?.sourceSection ? twins[doc.sourceSection] : primaryTwin;
      const root = twin?.relative_root || relativeRoot;
      return root && doc?.path ? labDatabaseAssetUrl(root, doc.path) : null;
    },
    [twins, primaryTwin, relativeRoot]
  );

  const galleryLabels = useMemo(
    () => ({
      loading: t('docs.mediaLoading'),
      failed: t('docs.mediaFailed'),
      videoLoading: t('docs.videoLoading'),
      videoFailed: t('docs.videoFailed'),
      zoomIn: t('docs.mediaZoomIn'),
      zoomOut: t('docs.mediaZoomOut'),
      fit: t('docs.mediaFit'),
      actualSize: t('docs.mediaActualSize'),
      rotate: t('docs.mediaRotate'),
      fullscreen: t('docs.mediaFullscreen'),
      download: t('docs.openOriginal'),
      previous: t('docs.mediaPrevious'),
      next: t('docs.mediaNext'),
      gridView: t('docs.galleryGrid', 'Grid'),
      heroView: t('docs.galleryPreview', 'Preview'),
      itemOne: t('docs.galleryItemOne', 'item'),
      itemMany: t('docs.galleryItemMany', 'items'),
      filmstrip: t('docs.galleryFilmstrip', 'Thumbnails'),
    }),
    [t]
  );

  const galleryActions = useMemo(() => {
    if (!selectedDoc || !assetUrl) return null;
    return (
      <>
        <a
          href={assetUrl}
          className="btn btn-secondary btn-sm"
          target="_blank"
          rel="noreferrer"
        >
          {t('docs.openOriginal')}
        </a>
        {isSensitive ? (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setRevealSensitive((v) => !v)}
          >
            {revealSensitive ? t('docs.hideSensitive') : t('docs.revealSensitive')}
          </button>
        ) : null}
      </>
    );
  }, [selectedDoc, assetUrl, isSensitive, revealSensitive, t]);

  const mediaGalleryPane = useMemo(
    () => (
      <DocumentMediaGallery
        files={visibleFiles}
        selectedPath={selectedPath}
        onSelectFile={setSelectedPath}
        resolveUrl={resolveDocAssetUrl}
        documentTitle={documentTitle}
        mediaScope={layoutInfo.mediaScope || 'image'}
        labels={galleryLabels}
        actions={galleryActions}
        emptyHint={t('docs.galleryEmpty', 'No images or videos in this category.')}
      />
    ),
    [
      visibleFiles,
      selectedPath,
      resolveDocAssetUrl,
      documentTitle,
      layoutInfo.mediaScope,
      galleryLabels,
      galleryActions,
      t,
    ]
  );
  const layoutToggle = layoutInfo.mode === 'mixed' ? (
    <div className="lab-doc-layout-toggle" role="group" aria-label={t('docs.layoutToggleAria', 'Browse layout')}>
      <button
        type="button"
        className={`lab-doc-layout-toggle-btn${effectiveLayoutMode === 'split' ? ' active' : ''}`}
        onClick={() => setLayoutModeOverride('split')}
        title={t('docs.layoutList', 'List and preview')}
      >
        <List size={13} aria-hidden />
        <span>{t('docs.layoutList', 'List')}</span>
      </button>
      <button
        type="button"
        className={`lab-doc-layout-toggle-btn${effectiveLayoutMode === 'gallery' ? ' active' : ''}`}
        onClick={() => setLayoutModeOverride('gallery')}
        title={t('docs.layoutGallery', 'Gallery view')}
      >
        <LayoutGrid size={13} aria-hidden />
        <span>{t('docs.layoutGallery', 'Gallery')}</span>
      </button>
    </div>
  ) : null;

  if (loading) {
    return (
      <div className="panel" style={{ padding: '2rem', textAlign: 'center' }}>
        <Loader2 size={20} className="spin-inline" /> {t('docs.loading')}
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel" style={{ padding: '2rem', color: 'var(--mac-destructive)' }}>
        {error}
      </div>
    );
  }

  const resolvedLayoutVariant = layoutVariant === 'default' ? 'catalog' : layoutVariant;
  const isSplitCatalogLayout =
    resolvedLayoutVariant === 'protocols' || resolvedLayoutVariant === 'catalog';
  const sectionHeader = title
    ? {
        eyebrow: t('docs.sectionCorpusEyebrow', 'Document library'),
        title,
        description: description || null,
        icon: Icon,
        contentRoot: contentRoot || null,
      }
    : null;

  const browserClassName = [
    className,
    isSplitCatalogLayout ? 'catalog-space-browser lab-documents-browser--catalog' : '',
    isSplitCatalogLayout && sectionHeader ? 'lab-documents-browser--section-header' : '',
    useGalleryLayout ? 'lab-documents-browser--gallery' : 'lab-documents-browser--split',
  ]
    .filter(Boolean)
    .join(' ');

  const previewPane = (
    <div className="pfb-column pfb-preview-pane pfb-preview-pane--editor-focus">
      {!selectedDoc ? (
        <div className="lab-doc-preview-placeholder">
          <p className="text-footnote muted">{t('docs.selectFile')}</p>
          {isSplitCatalogLayout ? (
            <p className="text-footnote muted lab-doc-preview-placeholder-hint">
              {t('docs.catalogPreviewHint')}
            </p>
          ) : null}
        </div>
      ) : previewLoading ? (
        <div className="panel" style={{ padding: '2rem', textAlign: 'center' }}>
          <Loader2 size={20} className="spin-inline" /> {t('docs.loadingPreview')}
        </div>
      ) : (
        <DocumentPreviewPane
                  onExpandChange={setViewerExpanded}
                  onBackToFiles={() => setSelectedPath(null)}
                  title={documentTitle(selectedDoc)}
                  path={selectedDoc.path}
                  extension={selectedDoc.extension || inferExtension(selectedDoc.name)}
                  previewKind={previewKind}
                  rawFilePreview={rawFilePreview}
                  previewText={previewText}
                  previewFallbackNote={
                    previewFromCatalog &&
                    (mergedSpreadsheetPreview?.strategy === 'catalog' ||
                      rawFilePreview?.error ||
                      spreadsheetPreview.error)
                      ? t('docs.offlineExtractPreview')
                      : null
                  }
                  pdfPreviewUrl={pdfPreviewUrl}
                  pdfThumbLabel={isPdf ? 'PDF' : 'PDF copy'}
                  mediaKind={mediaKind}
                  mediaUrl={assetUrl}
                  mediaAlt={documentTitle(selectedDoc)}
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
                  spreadsheetPreview={isSpreadsheet ? mergedSpreadsheetPreview : null}
                  spreadsheetFileUrl={
                    isSpreadsheet && spreadsheetPreview.sheets?.length ? assetUrl : null
                  }
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
                  emptyHint="No text preview available. Expand the PDF thumbnail or open the original file."
                  onCreateTask={(text) =>
                    openTaskpad(text, {
                      section: sectionId,
                      filePath: selectedPath || undefined,
                      fileName: selectedDoc?.name || selectedDoc?.title,
                    })
                  }
                  exportLocal={{
                    filename: selectedDoc?.name || selectedDoc?.title,
                    title: documentTitle(selectedDoc),
                    text: previewText || rawFilePreview?.content,
                    metadata: selectedDoc,
                    originalUrl: assetUrl,
                  }}
                  metadataItems={previewMetadataItems}
                  expandedMetadataItems={expandedPreviewMetadata}
                  metadataCompleteness={metadataCompleteness}
                  badges={previewBadges}
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
                      {isSensitive ? (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => setRevealSensitive((v) => !v)}
                        >
                          {revealSensitive ? t('docs.hideSensitive') : t('docs.revealSensitive')}
                        </button>
                      ) : null}
                    </>
                  }
                />
      )}
    </div>
  );

  const sensitiveNote = isSensitive ? (
    <p className="lab-doc-sensitive-note">
      <Lock size={14} /> {t('docs.sensitiveMasked')}
    </p>
  ) : null;

  const renderCatalogBody = (fileBody) => {
    if (useGalleryLayout) {
      return (
        <div className="lab-docs-gallery-shell">
          {sensitiveNote}
          {mediaGalleryPane}
        </div>
      );
    }

    return (
      <div
        className={`lab-docs-catalog-split pfb-layout lab-docs-layout lab-docs-layout--compact lab-docs-layout--catalog${selectedDoc ? ' pfb-layout--editor-focus pfb-layout--doc-full' : ''}${viewerExpanded ? ' pfb-layout--viewer-expanded' : ''}`}
      >
        <div className="pfb-column pfb-files-pane lab-doc-files-panel lab-doc-files-panel--catalog">
          {sensitiveNote}
          {fileBody}
        </div>
        {previewPane}
      </div>
    );
  };

  const useTopTabsLayout = isSplitCatalogLayout || useGalleryLayout;

  const fileList = (
    <DocumentCategoryFileList
      categoryGroups={localizedCategoryGroups}
      grouped={grouped}
      fileQuery={fileQuery}
      documentTitle={documentTitle}
      selectedPath={selectedPath}
      onSelectFile={setSelectedPath}
      categoryIcons={categoryIcons}
      sensitiveCategories={sensitiveCategories}
      categoryLayout={useTopTabsLayout ? 'horizontal-top' : 'inline'}
      sectionHeader={isSplitCatalogLayout ? sectionHeader : null}
      toolbarAfterTabs={layoutToggle}
      onVisibleFilesChange={handleVisibleFilesChange}
      renderPreview={useTopTabsLayout ? renderCatalogBody : null}
    />
  );

  return (
    <section className={`panel workspace-section data-pad data-pad--compact data-pad--embedded ${browserClassName}`}>
      {topPanel}

      {!sectionHeader && contentRoot ? (
        <div className="data-pad-root data-pad-root--inline">
          <SmartLink href={contentRoot} showCopy maxLabelLen={48} />
        </div>
      ) : null}

      <div className={`lab-docs-section-layout lab-docs-section-layout--grouped${isSplitCatalogLayout ? ' lab-docs-section-layout--catalog' : ''}`}>
        <div className="lab-docs-section-main">
          {useTopTabsLayout ? (
            <div className="lab-docs-catalog-shell">
              {fileList}
            </div>
          ) : (
            <div
              className={`pfb-layout lab-docs-layout lab-docs-layout--compact${selectedDoc ? ' pfb-layout--editor-focus pfb-layout--doc-full' : ''}${viewerExpanded ? ' pfb-layout--viewer-expanded' : ''}`}
            >
              <div className="pfb-column pfb-files-pane lab-doc-files-panel">
                {sensitiveNote}
                {fileList}
              </div>
              {previewPane}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
