import { useEffect, useMemo, useState } from 'react';
import { Film, Grid3x3, ImageIcon, Loader2, Play } from 'lucide-react';
import MediaViewer from './MediaViewer.jsx';
import FileTypeBadge from './FileTypeBadge.jsx';
import { inferExtension } from '../utils/fileTypeMeta.js';
import { getMediaPreviewKind } from '../utils/mediaPreviewKind.js';
import { filterMediaFiles } from '../utils/documentBrowserLayoutMode.js';
import { normalizeDocPath } from '../utils/folderBrowserUtils.js';

/**
 * Full-width image/video gallery — grid browse + hero preview with filmstrip.
 */
export default function DocumentMediaGallery({
  files = [],
  selectedPath,
  onSelectFile,
  resolveUrl,
  documentTitle,
  mediaScope = 'image',
  labels = {},
  actions = null,
  emptyHint = 'No media files in this category.',
}) {
  const mediaFiles = useMemo(
    () => filterMediaFiles(files, mediaScope),
    [files, mediaScope]
  );

  const [viewMode, setViewMode] = useState('hero');

  const galleryItems = useMemo(
    () =>
      mediaFiles
        .map((doc) => {
          const ext = inferExtension(doc.name, doc.extension);
          const kind = getMediaPreviewKind(ext);
          const url = resolveUrl?.(doc);
          if (!url || !kind) return null;
          return {
            path: doc.path,
            url,
            title: documentTitle(doc),
            kind,
            extension: ext,
            doc,
          };
        })
        .filter(Boolean)
        .sort((a, b) =>
          a.path.localeCompare(b.path, undefined, { numeric: true, sensitivity: 'base' })
        ),
    [mediaFiles, resolveUrl, documentTitle]
  );

  const selectedItem = useMemo(() => {
    if (!selectedPath) return galleryItems[0] || null;
    const key = normalizeDocPath(selectedPath);
    return (
      galleryItems.find((item) => normalizeDocPath(item.path) === key) ||
      galleryItems[0] ||
      null
    );
  }, [galleryItems, selectedPath]);

  useEffect(() => {
    if (!galleryItems.length) return;
    const key = normalizeDocPath(selectedPath);
    const inGallery = galleryItems.some((item) => normalizeDocPath(item.path) === key);
    if (!inGallery && onSelectFile) {
      onSelectFile(galleryItems[0].path);
    }
  }, [galleryItems, selectedPath, onSelectFile]);

  if (!galleryItems.length) {
    return (
      <div className="lab-doc-media-gallery lab-doc-media-gallery--empty">
        <p className="text-footnote muted">{emptyHint}</p>
      </div>
    );
  }

  const showHero = viewMode === 'hero' && selectedItem;

  return (
    <div className={`lab-doc-media-gallery lab-doc-media-gallery--${mediaScope}`}>
      <div className="lab-doc-media-gallery-toolbar">
        <div className="lab-doc-media-gallery-title">
          <ImageIcon size={15} aria-hidden />
          <span className="lab-doc-media-gallery-count">
            {galleryItems.length}{' '}
            {galleryItems.length === 1 ? labels.itemOne || 'item' : labels.itemMany || 'items'}
          </span>
          {selectedItem ? (
            <>
              <span className="lab-doc-media-gallery-sep" aria-hidden>
                ·
              </span>
              <span className="lab-doc-media-gallery-active-title">{selectedItem.title}</span>
              <FileTypeBadge extension={selectedItem.extension} />
            </>
          ) : null}
        </div>
        <div className="lab-doc-media-gallery-toolbar-actions">
          <div className="lab-doc-media-gallery-view-toggle" role="group" aria-label={labels.viewMode || 'View mode'}>
            <button
              type="button"
              className={`lab-doc-media-gallery-view-btn${viewMode === 'grid' ? ' active' : ''}`}
              onClick={() => setViewMode('grid')}
              title={labels.gridView || 'Grid view'}
            >
              <Grid3x3 size={14} aria-hidden />
              <span>{labels.gridView || 'Grid'}</span>
            </button>
            <button
              type="button"
              className={`lab-doc-media-gallery-view-btn${viewMode === 'hero' ? ' active' : ''}`}
              onClick={() => setViewMode('hero')}
              title={labels.heroView || 'Preview view'}
            >
              <Film size={14} aria-hidden />
              <span>{labels.heroView || 'Preview'}</span>
            </button>
          </div>
          {actions}
        </div>
      </div>

      {showHero ? (
        <div className="lab-doc-media-gallery-stage">
          <MediaViewer
            url={selectedItem.url}
            title={selectedItem.title}
            kind={selectedItem.kind}
            gallery={galleryItems}
            currentPath={selectedItem.path}
            onNavigate={onSelectFile}
            labels={labels}
          />
          {selectedItem.path ? (
            <p className="lab-doc-media-gallery-caption text-caption muted">{selectedItem.path}</p>
          ) : null}
        </div>
      ) : (
        <div className="lab-doc-media-gallery-grid" role="list">
          {galleryItems.map((item) => {
            const active =
              normalizeDocPath(selectedPath) === normalizeDocPath(item.path);
            const isVideo = item.kind === 'video';
            return (
              <button
                key={item.path}
                type="button"
                role="listitem"
                className={`lab-doc-media-gallery-card${active ? ' lab-doc-media-gallery-card--active' : ''}`}
                onClick={() => {
                  onSelectFile?.(item.path);
                  setViewMode('hero');
                }}
                aria-current={active ? 'true' : undefined}
              >
                <span className="lab-doc-media-gallery-card-media">
                  {isVideo ? (
                    <span className="lab-doc-media-gallery-video-thumb">
                      <video
                        src={item.url}
                        muted
                        playsInline
                        preload="metadata"
                        className="lab-doc-media-gallery-thumb-video"
                      />
                      <span className="lab-doc-media-gallery-play-badge" aria-hidden>
                        <Play size={18} />
                      </span>
                    </span>
                  ) : (
                    <img
                      src={item.url}
                      alt={item.title}
                      className="lab-doc-media-gallery-thumb"
                      loading="lazy"
                    />
                  )}
                </span>
                <span className="lab-doc-media-gallery-card-copy">
                  <span className="lab-doc-media-gallery-card-title">{item.title}</span>
                  {item.extension ? (
                    <span className="lab-doc-media-gallery-card-ext">
                      {item.extension.replace('.', '')}
                    </span>
                  ) : null}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {showHero && galleryItems.length > 1 ? (
        <div className="lab-doc-media-gallery-filmstrip" role="list" aria-label={labels.filmstrip || 'Thumbnails'}>
          {galleryItems.map((item) => {
            const active =
              normalizeDocPath(selectedPath) === normalizeDocPath(item.path);
            const isVideo = item.kind === 'video';
            return (
              <button
                key={`strip-${item.path}`}
                type="button"
                role="listitem"
                className={`lab-doc-media-gallery-strip-thumb${active ? ' lab-doc-media-gallery-strip-thumb--active' : ''}`}
                onClick={() => onSelectFile?.(item.path)}
                aria-current={active ? 'true' : undefined}
                title={item.title}
              >
                {isVideo ? (
                  <span className="lab-doc-media-gallery-strip-video">
                    <video src={item.url} muted playsInline preload="metadata" />
                    <Play size={10} aria-hidden />
                  </span>
                ) : (
                  <img src={item.url} alt="" loading="lazy" />
                )}
              </button>
            );
          })}
        </div>
      ) : null}

      {showHero && !selectedItem?.url ? (
        <div className="lab-doc-media-gallery-loading">
          <Loader2 size={20} className="spin-inline" aria-hidden />
          <span>{labels.loading || 'Loading…'}</span>
        </div>
      ) : null}
    </div>
  );
}
