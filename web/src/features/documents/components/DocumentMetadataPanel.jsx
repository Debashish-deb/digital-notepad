import { useEffect, useMemo, useState } from 'react';
import {
  ExternalLink,
  FileText,
  Info,
  Loader2,
  Pin,
} from 'lucide-react';
import { fetchDocumentPreview, formatBytes } from '@/services/documentLibraryClient.js';
import { buildViewerHash, loadThumbnailBlobUrl } from '@/services/imageAssetsClient.js';
import { getFilePreviewKind, inferCodeLanguage } from '@/lib/filePreviewKind.js';
import { useSpreadsheetPreview } from '@/shared/hooks/useSpreadsheetPreview.js';
import { useRawFilePreview } from '@/shared/hooks/useRawFilePreview.js';
import { apiSpreadsheetSheetsToModels } from '@/lib/spreadsheetPreview.js';
import { smartDocumentTitle, documentTitleSubline } from '@/lib/smartDocumentTitle.js';
import DocumentListMetadataRow from './DocumentListMetadataRow.jsx';
import DocumentTypeShell from './DocumentTypeShell.jsx';
import SpreadsheetPreview from './SpreadsheetPreview.jsx';
import CodePreview from './CodePreview.jsx';
import MediaViewer from '@/features/documents/components/MediaViewer.jsx';
import DocumentExportMenu from './DocumentExportMenu.jsx';
import DocumentProofreadPanel from './DocumentProofreadPanel.jsx';
import { DocumentViewerExpandButton, DocumentViewerExpandPortal } from './DocumentViewerExpand.jsx';
import {
  DocumentViewerMetaChip,
  DocumentViewerToolButton,
  DocumentViewerToolbar,
} from './DocumentViewerToolbar.jsx';
import {
  extensionFromPreview,
  prettifyCategory,
  resolvePreviewMedia,
} from '@/features/documents/documentLibraryUi.js';

function MetadataSection({ title, children }) {
  if (!children) return null;
  return (
    <section className="sfe-preview-section">
      <h4 className="sfe-preview-section__title">{title}</h4>
      {children}
    </section>
  );
}

function MetaCell({ label, value }) {
  if (value == null || value === '' || (Array.isArray(value) && !value.length)) return null;
  const display = Array.isArray(value) ? value.join(', ') : String(value);
  return (
    <div className="sfe-meta-cell">
      <span className="sfe-meta-cell__label">{label}</span>
      <span className="sfe-meta-cell__value">{display}</span>
    </div>
  );
}

function ImageMetadataCard({ preview, hideThumb = false }) {
  const [thumbUrl, setThumbUrl] = useState(null);
  const imgMeta = preview.image_metadata || {};

  useEffect(() => {
    if (!preview.is_streamable_image || !preview.asset_id || hideThumb) return undefined;
    let alive = true;
    let objectUrl = null;
    loadThumbnailBlobUrl(preview.asset_id)
      .then((url) => {
        if (alive) {
          objectUrl = url;
          setThumbUrl(url);
        } else {
          URL.revokeObjectURL(url);
        }
      })
      .catch(() => { if (alive) setThumbUrl(null); });
    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [preview.asset_id, preview.is_streamable_image, hideThumb]);

  const openViewer = () => {
    window.location.hash = buildViewerHash(preview.asset_id);
  };

  const dimensions = imgMeta.width && imgMeta.height
    ? `${imgMeta.width} × ${imgMeta.height}`
    : imgMeta.dimensions?.shape?.join(' × ');

  return (
    <div className="sfe-image-meta-row">
      <div className="sfe-preview-meta-inline">
        <MetaCell label="Format" value={imgMeta.format} />
        <MetaCell label="Status" value={imgMeta.streaming_status} />
        <MetaCell label="Dimensions" value={dimensions} />
        <MetaCell label="Channels" value={imgMeta.channels} />
        <MetaCell label="Pyramid" value={imgMeta.pyramid_levels} />
        <MetaCell label="OME-XML" value={imgMeta.ome_xml_present ? 'present' : 'no'} />
      </div>
      {!hideThumb && thumbUrl ? (
        <img src={thumbUrl} alt="" className="sfe-preview-thumb-inline" loading="lazy" />
      ) : null}
      <button type="button" className="sfe-preview-viewer-btn" onClick={openViewer}>
        <ExternalLink size={12} aria-hidden /> Streaming viewer
      </button>
    </div>
  );
}

function PreviewMediaPanel({ preview }) {
  const [streamThumbUrl, setStreamThumbUrl] = useState(null);
  const media = useMemo(() => resolvePreviewMedia(preview), [preview]);

  useEffect(() => {
    if (!preview?.is_streamable_image || !preview.asset_id) {
      setStreamThumbUrl(null);
      return undefined;
    }
    let alive = true;
    let objectUrl = null;
    loadThumbnailBlobUrl(preview.asset_id)
      .then((url) => {
        if (alive) {
          objectUrl = url;
          setStreamThumbUrl(url);
        } else {
          URL.revokeObjectURL(url);
        }
      })
      .catch(() => { if (alive) setStreamThumbUrl(null); });
    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setStreamThumbUrl(null);
    };
  }, [preview?.asset_id, preview?.is_streamable_image]);

  const viewerUrl = preview?.is_streamable_image
    ? (streamThumbUrl || media?.url)
    : media?.url;
  const viewerKind = media?.kind || 'image';

  if (!viewerUrl) {
    if (!preview?.is_streamable_image) return null;
    return (
      <div className="sfe-preview-media">
        <ImageMetadataCard preview={preview} hideThumb />
        <div className="sfe-preview-media-loading">
          <Loader2 size={22} className="spin-inline" aria-hidden />
          <span>Loading image preview…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="sfe-preview-media">
      {preview.is_streamable_image ? (
        <ImageMetadataCard preview={preview} hideThumb />
      ) : null}
      <MediaViewer
        url={viewerUrl}
        title={smartDocumentTitle(preview)}
        kind={viewerKind}
        labels={{
          loading: 'Loading image…',
          failed: 'Could not load image.',
          videoLoading: 'Loading video…',
          videoFailed: 'Could not load video.',
        }}
      />
    </div>
  );
}

export default function DocumentMetadataPanel({
  assetId,
  pinned,
  onTogglePin,
  onExpandChange = null,
  layoutMode = 'split',
}) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [viewerExpanded, setViewerExpanded] = useState(false);
  const [draftNotesOpen, setDraftNotesOpen] = useState(false);
  const [draftNotesByAsset, setDraftNotesByAsset] = useState({});
  const isReading = layoutMode === 'reading';

  const extension = extensionFromPreview(preview);
  const previewKind = preview ? getFilePreviewKind(extension, preview.logical_path) : 'document';
  const isPdf = extension === '.pdf';
  const isSpreadsheet = previewKind === 'spreadsheet';
  const previewUrl = preview?.preview_url || null;

  const spreadsheetPreview = useSpreadsheetPreview(
    isSpreadsheet && previewUrl ? previewUrl : null,
    extension,
  );
  const rawFilePreview = useRawFilePreview(
    previewUrl && !isSpreadsheet && !isPdf ? previewUrl : null,
    previewKind,
    { fallbackText: preview?.excerpt },
  );

  const mergedSpreadsheetPreview = useMemo(() => {
    if (!isSpreadsheet || !preview) return null;
    const apiSheets = apiSpreadsheetSheetsToModels(
      preview.spreadsheet_sheets || preview.metadata?.sheets,
    );
    const fileSheets = spreadsheetPreview.sheets;
    const sheets = fileSheets?.length ? fileSheets : apiSheets;
    const fromApi = Boolean(!fileSheets?.length && apiSheets?.length);
    const sheetLoading = !sheets?.length && spreadsheetPreview.loading;
    const error =
      !sheets?.length && !sheetLoading && spreadsheetPreview.error
        ? spreadsheetPreview.error
        : null;
    return {
      loading: sheetLoading,
      sheets,
      repairNotes: [
        ...(spreadsheetPreview.repairNotes || []),
        ...(fromApi ? ['Rendered from extracted spreadsheet metadata.'] : []),
      ],
      error,
      strategy: fileSheets?.length ? spreadsheetPreview.strategy : fromApi ? 'metadata' : null,
    };
  }, [isSpreadsheet, preview, spreadsheetPreview]);

  const spreadsheetReady = Boolean(mergedSpreadsheetPreview?.sheets?.length);
  const showSpreadsheet = isSpreadsheet && (mergedSpreadsheetPreview?.loading || spreadsheetReady);
  const rawLoading = Boolean(rawFilePreview?.loading);
  const rawContent = rawFilePreview?.content;
  const rawError = rawFilePreview?.error;
  const language = inferCodeLanguage(extension, preview?.logical_path);
  const showCode =
    (previewKind === 'code' || previewKind === 'json') && (rawLoading || rawContent || rawError);
  const showPlainText =
    previewKind === 'text' && (rawLoading || rawContent || rawError) && !showSpreadsheet;
  const showMarkup =
    previewKind === 'markup' && (rawContent || preview?.excerpt) && !showSpreadsheet;

  useEffect(() => {
    if (!assetId) {
      setPreview(null);
      return undefined;
    }
    let alive = true;
    setLoading(true);
    fetchDocumentPreview(assetId)
      .then((data) => { if (alive) setPreview(data); })
      .catch(() => { if (alive) setPreview(null); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [assetId]);

  useEffect(() => {
    setViewerExpanded(false);
    setDraftNotesOpen(false);
  }, [assetId]);

  useEffect(() => {
    onExpandChange?.(viewerExpanded);
  }, [viewerExpanded, onExpandChange]);

  const emptyShellClass = isReading
    ? 'overview-reading-article overview-reading-article--empty'
    : 'sfe-preview-panel';

  if (!assetId) {
    const Wrapper = isReading ? 'article' : 'aside';
    return (
      <Wrapper className={emptyShellClass}>
        <div className="sfe-preview-empty">
          <FileText size={32} strokeWidth={1.25} aria-hidden />
          <p>{isReading ? 'Select a document from the list to read.' : 'Select a file to preview metadata and status.'}</p>
        </div>
      </Wrapper>
    );
  }

  if (loading) {
    const Wrapper = isReading ? 'article' : 'aside';
    return (
      <Wrapper className={emptyShellClass}>
        <div className="sfe-preview-empty"><Loader2 className="spin-inline" size={24} /> Loading preview…</div>
      </Wrapper>
    );
  }

  if (!preview) {
    const Wrapper = isReading ? 'article' : 'aside';
    return (
      <Wrapper className={emptyShellClass}>
        <div className="sfe-preview-empty">Preview unavailable.</div>
      </Wrapper>
    );
  }

  const md = preview.metadata || {};
  const completeness = preview.metadata_completeness ?? 0;
  const previewMedia = resolvePreviewMedia(preview);
  const showMedia = Boolean(previewMedia || preview.is_streamable_image);
  const previewTitle = smartDocumentTitle(preview);
  const previewSubline = documentTitleSubline(preview);
  const previewSubtitle = previewSubline.chips?.map((chip) => chip.label).join(' · ')
    || previewSubline.filename
    || preview.filename;
  const hasFormattedText =
    Boolean(preview.excerpt)
    && !showMedia
    && !showSpreadsheet
    && !showCode
    && !showPlainText
    && !showMarkup
    && !isPdf;
  const proofreadSource = showMarkup
    ? (rawContent || preview.excerpt || '')
    : hasFormattedText
      ? (preview.excerpt || '')
      : showPlainText || showCode
        ? (rawContent || '')
        : '';

  const proseReaderClass = isReading
    ? 'overview-reading-prose'
    : 'sfe-preview-reader kindle-doc-scroll academic-manuscript doc-preview-prose';

  const previewBody = (
    <>
      {showMedia ? <PreviewMediaPanel preview={preview} /> : null}
      {!showMedia && showSpreadsheet ? (
        <SpreadsheetPreview
          sheets={mergedSpreadsheetPreview?.sheets}
          repairNotes={mergedSpreadsheetPreview?.repairNotes}
          loading={mergedSpreadsheetPreview?.loading}
          error={mergedSpreadsheetPreview?.error}
          fileUrl={previewUrl}
        />
      ) : null}
      {!showMedia && !showSpreadsheet && isPdf && previewUrl ? (
        <iframe
          title={preview.filename}
          src={previewUrl}
          className="sfe-pdf-frame"
        />
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && showCode ? (
        <CodePreview
          content={rawContent}
          language={previewKind === 'json' ? 'json' : language}
          loading={rawLoading}
          error={rawError}
        />
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && showPlainText ? (
        <CodePreview
          content={rawContent}
          language="plaintext"
          loading={rawLoading}
          error={rawError}
        />
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && showMarkup ? (
        <div className={proseReaderClass}>
          <DocumentTypeShell
            doc={preview}
            text={rawContent || preview.excerpt}
            title={preview?.title || preview?.filename}
            preferProse
          />
        </div>
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && hasFormattedText ? (
        <div className={proseReaderClass}>
          <DocumentTypeShell
            doc={preview}
            text={preview.excerpt}
            title={preview?.title || preview?.filename}
            preferProse
          />
        </div>
      ) : null}
      {!showMedia && !showSpreadsheet && !isPdf && !hasFormattedText && !showCode && !showPlainText && !showMarkup ? (
        <p className="text-footnote muted sfe-preview-empty-text">
          No extracted text yet. Run digitalization to enrich this file.
        </p>
      ) : null}
      {proofreadSource.trim() && !showMedia && !showSpreadsheet && !isPdf ? (
        <DocumentProofreadPanel content={proofreadSource} className="doc-preview-proofread" />
      ) : null}
    </>
  );

  const showExpandControl = !isReading || isPdf;

  const headerActions = (
    <DocumentViewerToolbar>
      {showExpandControl ? (
        <DocumentViewerExpandButton
          variant="toolbar"
          expanded={viewerExpanded}
          onToggle={() => setViewerExpanded((value) => !value)}
        />
      ) : null}
      <DocumentExportMenu assetId={preview.asset_id} compact toolbar />
      <DocumentViewerToolButton
        active={pinned}
        onClick={onTogglePin}
        title={pinned ? 'Unpin file' : 'Pin file'}
      >
        <Pin size={14} aria-hidden />
      </DocumentViewerToolButton>
      <DocumentViewerToolButton
        active={detailsOpen}
        onClick={() => setDetailsOpen((v) => !v)}
        title={detailsOpen ? 'Hide metadata details' : 'Show metadata details'}
      >
        <Info size={14} aria-hidden />
      </DocumentViewerToolButton>
    </DocumentViewerToolbar>
  );

  const metadataFooter = (
    <footer className={`${isReading ? 'overview-reading-footer' : 'sfe-preview-footer'}${detailsOpen ? ' is-expanded' : ''}`}>
      {!detailsOpen ? (
        <div className="sfe-preview-meta-inline">
          <MetaCell label="Category" value={md.category} />
          <MetaCell label="Role" value={md.document_role} />
          <MetaCell label="Project" value={md.project} />
          <MetaCell label="Platform" value={md.assay_tags || md.inferred_platforms} />
          <MetaCell label="Digitalization" value={md.digitalization_status} />
          <MetaCell label="Metadata grade" value={preview.metadata_grade} />
        </div>
      ) : (
        <div className="sfe-preview-footer-scroll">
          <MetadataSection title="Scientific context">
            <div className="sfe-preview-meta-inline">
              <MetaCell label="Project" value={md.project} />
              <MetaCell label="Inferred projects" value={md.inferred_project_codes} />
              <MetaCell label="Sample IDs" value={md.inferred_sample_ids} />
              <MetaCell label="Platform / assay" value={md.assay_tags || md.inferred_platforms} />
              <MetaCell label="Tissue / site" value={md.tissue_tags} />
              <MetaCell label="Markers / panels" value={md.marker_tags} />
              <MetaCell label="Years" value={md.inferred_years} />
            </div>
          </MetadataSection>
          <MetadataSection title="Organization">
            <div className="sfe-preview-meta-inline">
              <MetaCell label="Domain" value={md.domain} />
              <MetaCell label="Section" value={md.section_label || md.section} />
              <MetaCell label="Category" value={md.category} />
              <MetaCell label="Subcategory" value={md.subcategory} />
              <MetaCell label="Folder root" value={md.domain_folder} />
              <MetaCell label="Owner" value={md.owner || md.inferred_people} />
            </div>
          </MetadataSection>
          <MetadataSection title="File & indexing">
            <div className="sfe-preview-meta-inline">
              <MetaCell label="File type" value={md.file_type} />
              <MetaCell label="Document kind" value={md.document_kind} />
              <MetaCell label="Extension" value={md.extension} />
              <MetaCell label="Size" value={formatBytes(preview.size_bytes)} />
              <MetaCell label="Word count" value={md.word_count} />
              <MetaCell label="Extractor" value={md.extractor} />
              <MetaCell label="Modified" value={preview.modified_at?.slice(0, 10)} />
              <MetaCell label="Indexed" value={preview.indexed_at?.slice(0, 10)} />
              <MetaCell label="Digitalization" value={md.digitalization_status} />
              <MetaCell label="Extraction" value={md.extraction_status} />
              <MetaCell label="Vector status" value={md.vector_status} />
              <MetaCell label="Review" value={md.review_status} />
              <MetaCell label="Sensitivity" value={md.sensitivity_level} />
              <MetaCell label="Redigitalization" value={md.redigitalization_reason} />
              <MetaCell label="Protocol category" value={md.protocol_category} />
              <MetaCell label="Reagent category" value={md.reagent_category} />
              <MetaCell label="Path" value={preview.logical_path} />
            </div>
          </MetadataSection>
          {md.processed_metadata && Object.keys(md.processed_metadata).length > 0 ? (
            <MetadataSection title="Extracted file metadata">
              <div className="sfe-preview-meta-inline">
                {Object.entries(md.processed_metadata).slice(0, 16).map(([key, value]) => (
                  <MetaCell
                    key={key}
                    label={prettifyCategory(key)}
                    value={typeof value === 'object' ? JSON.stringify(value) : value}
                  />
                ))}
              </div>
            </MetadataSection>
          ) : null}
        </div>
      )}
    </footer>
  );

  if (isReading) {
    const draftKey = preview.asset_id;
    const draftValue = draftNotesByAsset[draftKey] || '';

    return (
      <>
        <article className={`overview-reading-article${viewerExpanded ? ' overview-reading-article--hidden' : ''}`}>
          <header className="overview-reading-hero">
            <h1 className="overview-reading-hero__title">{previewTitle}</h1>
            <DocumentListMetadataRow
              item={preview}
              className="overview-reading-hero__subline sfe-preview-top__subline"
            />
            {(preview.badges || []).length ? (
              <div className="overview-reading-hero__badges">
                {(preview.badges || []).map((b) => (
                  <span key={b} className="sfe-badge sfe-badge--partial">{b}</span>
                ))}
              </div>
            ) : null}
          </header>

          {preview.duplicate_warning ? (
            <div className="overview-reading-warn">{preview.duplicate_warning}</div>
          ) : null}

          <div className="overview-reading-toolbar">
            <DocumentViewerMetaChip value={completeness} low={completeness < 40} />
            <div className="overview-reading-toolbar__actions">
              <DocumentViewerToolButton
                labeled
                active={draftNotesOpen}
                onClick={() => setDraftNotesOpen((v) => !v)}
                title={draftNotesOpen ? 'Hide draft notes' : 'Open draft notes'}
              >
                <span>{draftNotesOpen ? 'Hide notes' : 'Draft notes'}</span>
              </DocumentViewerToolButton>
              {headerActions}
            </div>
          </div>

          {draftNotesOpen ? (
            <div className="overview-reading-draft">
              <textarea
                value={draftValue}
                onChange={(e) => {
                  setDraftNotesByAsset((prev) => ({ ...prev, [draftKey]: e.target.value }));
                }}
                placeholder="Session-only notes while reading — not saved to the library."
                aria-label="Draft reading notes"
              />
              <p className="overview-reading-draft__hint">Notes stay in this browser session only.</p>
            </div>
          ) : null}

          <div className="overview-reading-body kindle-doc-scroll academic-manuscript doc-preview-prose">
            {previewBody}
          </div>

          {metadataFooter}
        </article>

        {showExpandControl ? (
          <DocumentViewerExpandPortal
            expanded={viewerExpanded}
            onClose={() => setViewerExpanded(false)}
            title={previewTitle}
            subtitle={previewSubtitle}
            headerActions={headerActions}
          >
            <div className="sfe-preview-content sfe-preview-content--expanded">{previewBody}</div>
          </DocumentViewerExpandPortal>
        ) : null}
      </>
    );
  }

  return (
    <>
    <aside className={`sfe-preview-panel${viewerExpanded ? ' sfe-preview-panel--hidden' : ''}`}>
      <header className="sfe-preview-top">
        <div className="sfe-preview-top__primary">
          <div className="sfe-preview-top__main">
            <h3 className="sfe-preview-title">{previewTitle}</h3>
            <DocumentListMetadataRow item={preview} className="sfe-preview-top__subline" />
            {(preview.badges || []).length ? (
              <div className="sfe-preview-top__badges">
                {(preview.badges || []).map((b) => (
                  <span key={b} className="sfe-badge sfe-badge--partial">{b}</span>
                ))}
              </div>
            ) : null}
          </div>
          <div className="sfe-preview-top__rail">
            <DocumentViewerMetaChip value={completeness} low={completeness < 40} />
            {headerActions}
          </div>
        </div>
      </header>

      {preview.duplicate_warning ? (
        <div className="sfe-preview-warn">{preview.duplicate_warning}</div>
      ) : null}

      <div className="sfe-preview-content">{previewBody}</div>

      {metadataFooter}
    </aside>

    <DocumentViewerExpandPortal
      expanded={viewerExpanded}
      onClose={() => setViewerExpanded(false)}
      title={previewTitle}
      subtitle={previewSubtitle}
      headerActions={headerActions}
    >
      <div className="sfe-preview-content sfe-preview-content--expanded">{previewBody}</div>
    </DocumentViewerExpandPortal>
    </>
  );
}
