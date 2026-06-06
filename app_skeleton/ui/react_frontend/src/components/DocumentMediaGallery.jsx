import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import { Film, Grid3x3, ImageIcon, Loader2, Play } from 'lucide-react';
import MediaViewer from './MediaViewer.jsx';
import FileTypeBadge from './FileTypeBadge.jsx';
import { inferExtension } from '../utils/fileTypeMeta.js';
import { getMediaPreviewKind } from '../utils/mediaPreviewKind.js';
import { filterMediaFiles } from '../utils/documentBrowserLayoutMode.js';
import { normalizeDocPath } from '../utils/folderBrowserUtils.js';

const FILMSTRIP_WINDOW = 12;

const GalleryGridCard = memo(function GalleryGridCard({
  item,
  active,
  resolveUrl,
  onSelect,
}) {
  const url = useMemo(() => resolveUrl?.(item.doc), [resolveUrl, item.doc]);
  const isVideo = item.kind === 'video';

  if (!url) return null;

  return (
    <button
      type="button"
      role="listitem"
      className={`lab-doc-media-gallery-card${active ? ' lab-doc-media-gallery-card--active' : ''}`}
      onClick={() => onSelect(item.path)}
      aria-current={active ? 'true' : undefined}
    >
      <span className="lab-doc-media-gallery-card-media">
        {isVideo ? (
          <span className="lab-doc-media-gallery-video-thumb">
            <video
              src={url}
              muted
              playsInline
              preload="none"
              className="lab-doc-media-gallery-thumb-video"
            />
            <span className="lab-doc-media-gallery-play-badge" aria-hidden>
              <Play size={18} />
            </span>
          </span>
        ) : (
          <img
            src={url}
            alt={item.title}
            className="lab-doc-media-gallery-thumb"
            loading="lazy"
            decoding="async"
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
});

const FilmstripThumb = memo(function FilmstripThumb({
  item,
  active,
  resolveUrl,
  onSelect,
}) {
  const url = useMemo(() => resolveUrl?.(item.doc), [resolveUrl, item.doc]);
  const isVideo = item.kind === 'video';

  if (!url) return null;

  return (
    <button
      type="button"
      role="listitem"
      className={`lab-doc-media-gallery-strip-thumb${active ? ' lab-doc-media-gallery-strip-thumb--active' : ''}`}
      onClick={() => onSelect(item.path)}
      aria-current={active ? 'true' : undefined}
      title={item.title}
    >
      {isVideo ? (
        <span className="lab-doc-media-gallery-strip-video">
          <video src={url} muted playsInline preload="none" />
          <Play size={10} aria-hidden />
        </span>
      ) : (
        <img src={url} alt="" loading="lazy" decoding="async" />
      )}
    </button>
  );
});

/**
 * Full-width image/video gallery — grid browse + hero preview with filmstrip.
 */
function DocumentMediaGallery({
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
          if (!kind) return null;
          return {
            path: doc.path,
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
    [mediaFiles, documentTitle]
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

  const selectedUrl = useMemo(
    () => (selectedItem ? resolveUrl?.(selectedItem.doc) : null),
    [selectedItem, resolveUrl]
  );

  const viewerGallery = useMemo(() => {
    if (!selectedUrl || !selectedItem) return [];
    return galleryItems.map((item) => ({
      path: item.path,
      url: item.path === selectedItem.path ? selectedUrl : null,
      title: item.title,
      kind: item.kind,
    }));
  }, [galleryItems, selectedItem, selectedUrl]);

  const filmstripItems = useMemo(() => {
    if (galleryItems.length <= FILMSTRIP_WINDOW) return galleryItems;
    const selectedIndex = galleryItems.findIndex(
      (item) => normalizeDocPath(item.path) === normalizeDocPath(selectedPath)
    );
    const center = selectedIndex >= 0 ? selectedIndex : 0;
    const half = Math.floor(FILMSTRIP_WINDOW / 2);
    const start = Math.max(0, center - half);
    const end = Math.min(galleryItems.length, start + FILMSTRIP_WINDOW);
    return galleryItems.slice(Math.max(0, end - FILMSTRIP_WINDOW), end);
  }, [galleryItems, selectedPath]);

  useEffect(() => {
    if (!galleryItems.length) return;
    const key = normalizeDocPath(selectedPath);
    const inGallery = galleryItems.some((item) => normalizeDocPath(item.path) === key);
    if (!inGallery && onSelectFile) {
      onSelectFile(galleryItems[0].path);
    }
  }, [galleryItems, selectedPath, onSelectFile]);

  const handleGridSelect = useCallback(
    (path) => {
      onSelectFile?.(path);
      setViewMode('hero');
    },
    [onSelectFile]
  );

  const handleStripSelect = useCallback(
    (path) => {
      onSelectFile?.(path);
    },
    [onSelectFile]
  );

  if (!galleryItems.length) {
    return (
      <div className="lab-doc-media-gallery lab-doc-media-gallery--empty">
        <p className="text-footnote muted">{emptyHint}</p>
      </div>
    );
  }

  const showHero = viewMode === 'hero' && selectedItem;
  const selectedKey = normalizeDocPath(selectedPath);

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
            url={selectedUrl}
            title={selectedItem.title}
            kind={selectedItem.kind}
            gallery={viewerGallery}
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
          {galleryItems.map((item) => (
            <GalleryGridCard
              key={item.path}
              item={item}
              active={selectedKey === normalizeDocPath(item.path)}
              resolveUrl={resolveUrl}
              onSelect={handleGridSelect}
            />
          ))}
        </div>
      )}

      {showHero && galleryItems.length > 1 ? (
        <div className="lab-doc-media-gallery-filmstrip" role="list" aria-label={labels.filmstrip || 'Thumbnails'}>
          {filmstripItems.map((item) => (
            <FilmstripThumb
              key={`strip-${item.path}`}
              item={item}
              active={selectedKey === normalizeDocPath(item.path)}
              resolveUrl={resolveUrl}
              onSelect={handleStripSelect}
            />
          ))}
        </div>
      ) : null}

      {showHero && !selectedUrl ? (
        <div className="lab-doc-media-gallery-loading">
          <Loader2 size={20} className="spin-inline" aria-hidden />
          <span>{labels.loading || 'Loading…'}</span>
        </div>
      ) : null}
    </div>
  );
}

export default memo(DocumentMediaGallery);
