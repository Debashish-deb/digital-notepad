import { Calendar, Camera, FolderOpen, Image, Users } from 'lucide-react';
import { useGuiT } from '../i18n/useGuiT.js';

const KIND_ICONS = {
  retreat: Calendar,
  photoshoot: Camera,
  group: Users,
  event: Image,
  folder: FolderOpen,
};

/**
 * Vertical album picker for nested folders — visually distinct from category pill tabs.
 */
export default function DocumentSubfolderAlbums({
  albums,
  activeId,
  onSelect,
  categoryLabel,
  layout = 'vertical',
}) {
  const { t } = useGuiT();
  if (!albums?.length) return null;

  const activeAlbum = albums.find((album) => album.id === activeId) || albums[0];
  const isHorizontal = layout === 'horizontal';

  return (
    <div className={`lab-doc-album-picker${isHorizontal ? ' lab-doc-album-picker--horizontal' : ''}`}>
      {!isHorizontal ? (
        <div className="lab-doc-album-picker-head">
          <p className="lab-doc-album-picker-eyebrow">{t('docs.albumsEyebrow')}</p>
          <p className="lab-doc-album-picker-context">
            <span className="lab-doc-album-picker-parent">{categoryLabel}</span>
            {activeAlbum ? (
              <>
                <span className="lab-doc-album-picker-sep" aria-hidden>
                  ›
                </span>
                <span className="lab-doc-album-picker-active">{activeAlbum.title}</span>
              </>
            ) : null}
          </p>
        </div>
      ) : (
        <p className="lab-doc-album-picker-eyebrow lab-doc-album-picker-eyebrow--inline">
          {t('docs.albumsEyebrow')}
        </p>
      )}

      <ul
        className={`lab-doc-album-grid${isHorizontal ? ' lab-doc-album-grid--horizontal' : ''}`}
        role="listbox"
        aria-label={t('docs.subfolderTabsAria')}
      >
        {albums.map((album) => {
          const Icon = KIND_ICONS[album.kind] || FolderOpen;
          const active = album.id === activeId;
          const fileLabel =
            album.count === 1
              ? t('docs.albumFileOne')
              : t('docs.albumFileMany', '', { count: album.count });

          return (
            <li key={album.id}>
              <button
                type="button"
                role="option"
                aria-selected={active}
                className={`lab-doc-album-card${active ? ' lab-doc-album-card--active' : ''}${isHorizontal ? ' lab-doc-album-card--chip' : ''}`}
                onClick={() => onSelect(album.id)}
              >
                <span className="lab-doc-album-card-icon" aria-hidden>
                  <Icon size={16} />
                </span>
                <span className="lab-doc-album-card-copy">
                  <span className="lab-doc-album-card-title">{album.title}</span>
                  {album.subtitle ? (
                    <span className="lab-doc-album-card-subtitle">{album.subtitle}</span>
                  ) : null}
                </span>
                <span className="lab-doc-album-card-count">{fileLabel}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
