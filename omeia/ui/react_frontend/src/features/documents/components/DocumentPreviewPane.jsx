import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Expand, FileText, Info, Loader2, X } from 'lucide-react';
import DocumentFormatter from './DocumentFormatter.jsx';
import LazyDataPadEditor from '@/features/projects/components/LazyDataPadEditor.jsx';
import FileTypeBadge from '@/shared/ui/FileTypeBadge.jsx';
import SpreadsheetPreview from './SpreadsheetPreview.jsx';
import CodePreview from './CodePreview.jsx';
import MediaViewer from '@/features/documents/components/MediaViewer.jsx';
import DocumentProofreadPanel from './DocumentProofreadPanel.jsx';
import { DocumentViewerExpandButton, DocumentViewerExpandPortal } from './DocumentViewerExpand.jsx';
import {
  DocumentViewerMetaChip,
  DocumentViewerToolButton,
  DocumentViewerToolbar,
} from './DocumentViewerToolbar.jsx';
import { inferCodeLanguage } from '@/lib/filePreviewKind.js';
import DocumentExportMenu from './DocumentExportMenu.jsx';
import './DocumentExportMenu.css';
import './DocumentPreviewPane.css';
import './DocumentViewerExpand.css';
import './DocumentViewerToolbar.css';

const ModelViewer3D = lazy(() => import('@/features/computational/components/ModelViewer3D.jsx'));

function MetaCell({ label, value }) {
  return (
    <div className="doc-meta-cell">
      <span className="doc-meta-cell__label">{label}</span>
      <span className="doc-meta-cell__value">{value ?? '—'}</span>
    </div>
  );
}

/**
 * Smart document preview: spreadsheets, code, formatted prose, PDF, images.
 */
export default function DocumentPreviewPane({
  title,
  path,
  extension,
  previewText,
  previewKind = 'document',
  rawFilePreview = null,
  pdfPreviewUrl,
  pdfThumbLabel = 'PDF',
  mediaKind = null,
  mediaUrl = null,
  mediaAlt,
  mediaGallery = [],
  onMediaNavigate = null,
  mediaLabels = {},
  /** @deprecated use mediaKind + mediaUrl */
  isImage,
  /** @deprecated use mediaUrl */
  imageUrl,
  /** @deprecated use mediaAlt */
  imageAlt,
  isEditable,
  editorProps,
  editorHint,
  spreadsheetPreview = null,
  spreadsheetFileUrl = null,
  spreadsheetLabels = {},
  codeLabels = {},
  emptyHint,
  previewFallbackNote = null,
  actions = null,
  exportLocal = null,
  metadataItems = [],
  expandedMetadataItems = null,
  metadataCompleteness = null,
  badges = [],
  onCreateTask,
  onBackToFiles,
  onExpandChange = null,
  expandEnabled = true,
}) {
  const [pdfExpanded, setPdfExpanded] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [viewerExpanded, setViewerExpanded] = useState(false);

  const hasEditor = Boolean(isEditable && editorProps);
  const sheetLoading = Boolean(spreadsheetPreview?.loading);
  const sheetReady = Boolean(spreadsheetPreview?.sheets?.length);
  const sheetFailed =
    spreadsheetPreview &&
    !sheetLoading &&
    !sheetReady &&
    Boolean(spreadsheetPreview.error);
  const showSpreadsheet =
    previewKind === 'spreadsheet' && (sheetLoading || sheetReady);

  const rawLoading = Boolean(rawFilePreview?.loading);
  const rawContent = rawFilePreview?.content;
  const rawError = rawFilePreview?.error;
  const language = inferCodeLanguage(extension, path);
  const preferProse = ['.doc', '.docx', '.rtf', '.odt'].includes((extension || '').toLowerCase());

  const showCode =
    (previewKind === 'code' || previewKind === 'json') &&
    (rawLoading || rawContent || rawError);
  const showMarkup =
    previewKind === 'markup' && (rawContent || previewText) && !hasEditor && !showSpreadsheet;
  const showPlainText =
    previewKind === 'text' && (rawLoading || rawContent || rawError) && !showSpreadsheet;

  const resolvedMediaKind = mediaKind || (isImage && (imageUrl || mediaUrl) ? 'image' : null);
  const resolvedMediaUrl = mediaUrl || imageUrl;
  const resolvedMediaAlt = mediaAlt || imageAlt || title;
  const isMediaPreview = Boolean(resolvedMediaKind && resolvedMediaUrl);

  const hasFormattedText =
    Boolean(previewText) &&
    !isMediaPreview &&
    !hasEditor &&
    !editorHint &&
    !showSpreadsheet &&
    !showCode &&
    !showMarkup &&
    !showPlainText &&
    (!sheetFailed || !previewText);
  const showPdfThumb = Boolean(pdfPreviewUrl);

  const showMedia =
    isMediaPreview &&
    !hasEditor &&
    !showSpreadsheet &&
    !showCode &&
    !showMarkup &&
    !showPlainText;

  const markupSource = rawContent || previewText;
  const completeness = metadataCompleteness ?? 0;
  const footerItems = useMemo(
    () => (metadataItems || []).filter((item) => item?.value != null && item.value !== ''),
    [metadataItems]
  );
  const expandedItems = useMemo(() => {
    const source = expandedMetadataItems || footerItems;
    return (source || []).filter((item) => item?.value != null && item.value !== '');
  }, [expandedMetadataItems, footerItems]);
  const showMetadataFooter = footerItems.length > 0 || expandedItems.length > 0;

  const proofreadSource = useMemo(() => {
    if (hasEditor) return editorProps?.initialContent || previewText || '';
    if (showMarkup || hasFormattedText) return markupSource || previewText || '';
    if (showPlainText || showCode) return rawContent || '';
    return '';
  }, [
    hasEditor,
    editorProps?.initialContent,
    showMarkup,
    hasFormattedText,
    showPlainText,
    showCode,
    markupSource,
    previewText,
    rawContent,
  ]);

  const showProofread = Boolean(proofreadSource.trim()) && !showSpreadsheet && !showMedia && !hasEditor;

  const canExpand =
    expandEnabled &&
    (hasEditor ||
      showSpreadsheet ||
      showCode ||
      showPlainText ||
      showMarkup ||
      hasFormattedText ||
      showPdfThumb ||
      showMedia);

  const toggleViewerExpanded = useCallback(() => {
    setViewerExpanded((value) => !value);
  }, []);

  const closeViewerExpanded = useCallback(() => {
    setViewerExpanded(false);
  }, []);

  useEffect(() => {
    onExpandChange?.(viewerExpanded);
  }, [viewerExpanded, onExpandChange]);

  useEffect(() => {
    setViewerExpanded(false);
  }, [path, title]);

  const editorHeight = viewerExpanded ? 'calc(100vh - 9.5rem)' : 'calc(100% - 2.5rem)';

  const renderEditorStage = (expanded = false) => (
    <div className={`doc-preview-editor-stage${expanded ? ' doc-preview-editor-stage--expanded' : ''}`}>
      {hasEditor ? (
        <LazyDataPadEditor
          {...editorProps}
          defaultEditMode
          editorHeight={editorHeight}
        />
      ) : editorHint ? (
        <p className="text-footnote muted doc-preview-placeholder">{editorHint}</p>
      ) : showSpreadsheet ? (
        <SpreadsheetPreview
          sheets={spreadsheetPreview?.sheets}
          repairNotes={spreadsheetPreview?.repairNotes}
          loading={sheetLoading}
          error={spreadsheetPreview?.error}
          fileUrl={spreadsheetFileUrl}
          labels={spreadsheetLabels}
        />
      ) : showCode ? (
        <CodePreview
          content={rawContent}
          language={previewKind === 'json' ? 'json' : language}
          loading={rawLoading}
          error={rawError}
          labels={codeLabels}
        />
      ) : showPlainText ? (
        <CodePreview
          content={rawContent}
          language="plaintext"
          loading={rawLoading}
          error={rawError}
          labels={codeLabels}
        />
      ) : showMedia && resolvedMediaKind === 'model3d' ? (
        <Suspense
          fallback={
            <div className="media-viewer-loading">
              <Loader2 size={24} className="spin" aria-hidden />
              <span>{mediaLabels.modelLoading || 'Loading 3D viewer…'}</span>
            </div>
          }
        >
          <ModelViewer3D url={resolvedMediaUrl} title={title} labels={mediaLabels} />
        </Suspense>
      ) : showMedia && (resolvedMediaKind === 'image' || resolvedMediaKind === 'video') ? (
        <MediaViewer
          url={resolvedMediaUrl}
          title={resolvedMediaAlt}
          kind={resolvedMediaKind}
          gallery={mediaGallery}
          currentPath={path}
          onNavigate={onMediaNavigate}
          labels={mediaLabels}
        />
      ) : showMarkup ? (
        <div className="doc-preview-editor-scroll kindle-doc-scroll academic-manuscript doc-preview-prose">
          <DocumentFormatter text={markupSource} onCreateTask={onCreateTask} preferProse={preferProse} />
        </div>
      ) : hasFormattedText ? (
        <div className="doc-preview-editor-scroll kindle-doc-scroll academic-manuscript doc-preview-prose">
          {previewFallbackNote ? (
            <p className="doc-preview-fallback-note text-footnote muted" role="status">
              {previewFallbackNote}
            </p>
          ) : null}
          <DocumentFormatter text={previewText} onCreateTask={onCreateTask} preferProse={preferProse} />
        </div>
      ) : showPdfThumb ? (
        <div className="doc-preview-placeholder doc-preview-pdf-only">
          <FileText size={28} aria-hidden />
          <p className="text-footnote muted">
            No extracted text for this file. Use the PDF thumbnail to open the original layout.
          </p>
        </div>
      ) : (
        <p className="text-footnote muted doc-preview-placeholder">
          {emptyHint || 'No preview available.'}
        </p>
      )}

      {showProofread ? (
        <DocumentProofreadPanel content={proofreadSource} className="doc-preview-proofread" />
      ) : null}
    </div>
  );

  const pdfThumbButton =
    showPdfThumb && pdfPreviewUrl ? (
      <button
        type="button"
        className="pdf-header-thumb"
        onClick={() => setPdfExpanded(true)}
        title="Open PDF layout"
        aria-label={`Open ${pdfThumbLabel} layout`}
      >
        <span className="pdf-header-thumb__label">
          <Expand size={10} aria-hidden /> {pdfThumbLabel}
        </span>
        <object
          data={pdfPreviewUrl}
          type="application/pdf"
          className="pdf-header-thumb__object"
          aria-hidden
          tabIndex={-1}
        >
          <span className="pdf-header-thumb__fallback">PDF</span>
        </object>
      </button>
    ) : null;

  const headerActions = (
    <DocumentViewerToolbar>
      {canExpand ? (
        <DocumentViewerExpandButton
          variant="toolbar"
          expanded={viewerExpanded}
          onToggle={toggleViewerExpanded}
        />
      ) : null}
      {exportLocal ? <DocumentExportMenu local={exportLocal} compact toolbar /> : null}
      {actions}
      {showMetadataFooter ? (
        <DocumentViewerToolButton
          active={detailsOpen}
          onClick={() => setDetailsOpen((v) => !v)}
          title={detailsOpen ? 'Hide metadata details' : 'Show metadata details'}
        >
          <Info size={14} aria-hidden />
        </DocumentViewerToolButton>
      ) : null}
    </DocumentViewerToolbar>
  );

  return (
    <>
      <div className={`doc-preview-pane doc-preview-pane--smart${viewerExpanded ? ' doc-preview-pane--hidden' : ''}`}>
        <header className="doc-preview-top">
          <div className="doc-preview-top__primary">
            <div className="doc-preview-top__main">
              {onBackToFiles ? (
                <DocumentViewerToolButton
                  labeled
                  onClick={onBackToFiles}
                  title="Back to file list"
                  className="doc-preview-back"
                >
                  <ArrowLeft size={14} aria-hidden />
                  <span>Files</span>
                </DocumentViewerToolButton>
              ) : null}
              <div className="doc-preview-top__titles">
                <h4 className="doc-preview-title">{title}</h4>
                <div className="doc-preview-top__subline">
                  {path ? <span className="doc-preview-filename">{path}</span> : null}
                  <FileTypeBadge extension={extension} />
                  {(badges || []).map((badge) => (
                    <span key={badge} className="doc-preview-badge">
                      {badge}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <div className="doc-preview-top__rail">
              {metadataCompleteness != null ? (
                <DocumentViewerMetaChip value={completeness} low={completeness < 40} />
              ) : null}
              {pdfThumbButton}
              {headerActions}
            </div>
          </div>
        </header>

        {renderEditorStage(false)}

        {showMetadataFooter ? (
          <footer className={`doc-preview-footer${detailsOpen ? ' is-expanded' : ''}`}>
            {detailsOpen ? (
              <div className="doc-preview-footer-scroll">
                <div className="doc-preview-meta-inline">
                  {expandedItems.map((item) => (
                    <MetaCell key={`${item.label}-${item.value}`} label={item.label} value={item.value} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="doc-preview-meta-inline">
                {footerItems.map((item) => (
                  <MetaCell key={`${item.label}-${item.value}`} label={item.label} value={item.value} />
                ))}
              </div>
            )}
          </footer>
        ) : null}

        {pdfExpanded && pdfPreviewUrl ? (
          <div
            className="pdf-expand-overlay"
            role="dialog"
            aria-modal="true"
            aria-label="PDF full view"
            onClick={() => setPdfExpanded(false)}
          >
            <div className="pdf-expand-dialog" onClick={(e) => e.stopPropagation()}>
              <div className="pdf-expand-header">
                <span className="text-title-3">{title}</span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setPdfExpanded(false)}
                  aria-label="Close PDF view"
                >
                  <X size={14} /> Close
                </button>
              </div>
              <object
                data={pdfPreviewUrl}
                type="application/pdf"
                className="database-pdf-frame pdf-expand-frame"
                aria-label="PDF full preview"
              >
                <p className="text-footnote">
                  <a href={pdfPreviewUrl} target="_blank" rel="noreferrer">
                    Download PDF
                  </a>
                </p>
              </object>
            </div>
          </div>
        ) : null}
      </div>

      <DocumentViewerExpandPortal
        expanded={viewerExpanded}
        onClose={closeViewerExpanded}
        title={title}
        subtitle={path}
        headerActions={headerActions}
      >
        <div className="doc-preview-pane doc-preview-pane--smart doc-preview-pane--expanded">
          {renderEditorStage(true)}
        </div>
      </DocumentViewerExpandPortal>
    </>
  );
}
