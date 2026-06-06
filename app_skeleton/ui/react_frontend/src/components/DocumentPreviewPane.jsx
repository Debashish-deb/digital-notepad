import { lazy, Suspense, useState } from 'react';
import { ArrowLeft, Expand, FileText, Loader2, X } from 'lucide-react';
import DocumentFormatter from './DocumentFormatter.jsx';
import DataPadEditor from './DataPadEditor.jsx';
import FileTypeBadge from './FileTypeBadge.jsx';
import SpreadsheetPreview from './SpreadsheetPreview.jsx';
import CodePreview from './CodePreview.jsx';
import MediaViewer from './MediaViewer.jsx';
import { inferCodeLanguage } from '../utils/filePreviewKind.js';

const ModelViewer3D = lazy(() => import('./ModelViewer3D.jsx'));

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
  onCreateTask,
  onBackToFiles,
}) {
  const [pdfExpanded, setPdfExpanded] = useState(false);

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

  const hasFormattedText =
    Boolean(previewText) &&
    !hasEditor &&
    !editorHint &&
    !showSpreadsheet &&
    !showCode &&
    !showMarkup &&
    !showPlainText &&
    (!sheetFailed || !previewText);
  const showPdfThumb = Boolean(pdfPreviewUrl);

  const resolvedMediaKind = mediaKind || (isImage && (imageUrl || mediaUrl) ? 'image' : null);
  const resolvedMediaUrl = mediaUrl || imageUrl;
  const resolvedMediaAlt = mediaAlt || imageAlt || title;
  const showMedia =
    Boolean(resolvedMediaKind && resolvedMediaUrl) &&
    !hasEditor &&
    !showSpreadsheet &&
    !showCode &&
    !showMarkup &&
    !showPlainText &&
    !hasFormattedText;

  const markupSource = rawContent || previewText;

  return (
    <div className="doc-preview-pane">
      <div className="doc-preview-toolbar">
        <div className="doc-preview-toolbar-title">
          {onBackToFiles ? (
            <button
              type="button"
              className="btn btn-secondary btn-sm doc-preview-back"
              onClick={onBackToFiles}
              title="Back to file list"
            >
              <ArrowLeft size={14} aria-hidden /> Files
            </button>
          ) : null}
          <h4 className="pfb-preview-filename">{title}</h4>
          <FileTypeBadge extension={extension} />
        </div>
        {path ? <p className="text-caption muted pfb-preview-path-row">{path}</p> : null}
        {actions ? <div className="pfb-preview-actions">{actions}</div> : null}
      </div>

      <div className="doc-preview-editor-stage">
        {hasEditor ? (
          <DataPadEditor
            {...editorProps}
            defaultEditMode
            editorHeight="calc(100% - 2.5rem)"
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
        ) : showMarkup ? (
          <div className="doc-preview-editor-scroll kindle-doc-scroll academic-manuscript">
            <DocumentFormatter text={markupSource} onCreateTask={onCreateTask} preferProse={preferProse} />
          </div>
        ) : hasFormattedText ? (
          <div className="doc-preview-editor-scroll kindle-doc-scroll academic-manuscript">
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
        ) : (
          <p className="text-footnote muted doc-preview-placeholder">
            {emptyHint || 'No preview available.'}
          </p>
        )}

        {showPdfThumb ? (
          <button
            type="button"
            className="pdf-corner-thumb"
            onClick={() => setPdfExpanded(true)}
            title="Expand PDF preview"
            aria-label={`Expand ${pdfThumbLabel} preview`}
          >
            <span className="pdf-corner-thumb-label">
              <Expand size={12} aria-hidden /> {pdfThumbLabel}
            </span>
            <object
              data={pdfPreviewUrl}
              type="application/pdf"
              className="pdf-corner-thumb-object"
              aria-hidden
              tabIndex={-1}
            >
              <span className="pdf-corner-thumb-fallback">PDF</span>
            </object>
          </button>
        ) : null}
      </div>

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
  );
}
