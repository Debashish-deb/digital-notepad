import { useEffect, useMemo, useState } from 'react';
import { ChevronRight, FileText, Lock } from 'lucide-react';
import { inferExtension } from '../utils/fileTypeMeta.js';
import { normalizeDocPath } from '../utils/folderBrowserUtils.js';
import {
  buildDocumentCategoryBlocks,
  deriveSubfolderAlbums,
  filterFilesBySubfolder,
  shouldShowCategoryTabs,
  shouldShowGroupTabs,
} from '../utils/documentBrowserUtils.js';
import {
  isWetLabProtocolCategory,
  wetLabProtocolPathHint,
} from '../utils/wetLabProtocolCategories.js';
import DocumentSubfolderAlbums from './DocumentSubfolderAlbums.jsx';
import { useGuiT } from '../i18n/useGuiT.js';

function FileList({
  files,
  documentTitle,
  selectedPath,
  onSelectFile,
  compact = false,
  catalogLayout = false,
  pathHintResolver = null,
}) {
  return (
    <ul className="lab-doc-category-files lab-doc-category-files--bulleted">
      {files.map((doc) => {
        const docTitle = documentTitle(doc);
        const fileName = doc.path.split('/').pop();
        const ext = inferExtension(doc.name, doc.extension);
        const pathHint = pathHintResolver?.(doc.path) || null;
        const active = normalizeDocPath(selectedPath) === normalizeDocPath(doc.path);
        return (
          <li key={`${doc.sourceSection || ''}:${doc.path}`} className="lab-doc-file-entry">
            <button
              type="button"
              className={`lab-doc-file-btn${active ? ' active' : ''}${compact ? ' lab-doc-file-btn--compact' : ''}${catalogLayout ? ' lab-doc-file-btn--catalog' : ''}`}
              onClick={() => onSelectFile(doc.path)}
              aria-current={active ? 'true' : undefined}
            >
              <FileText size={13} className="lab-doc-file-bullet" aria-hidden />
              {compact ? (
                <span
                  className={`lab-doc-file-text lab-doc-file-text--compact${catalogLayout ? ' lab-doc-file-text--catalog' : ''}`}
                  title={[docTitle, ext ? ext.replace('.', '') : null, pathHint].filter(Boolean).join(' · ')}
                >
                  <span className={`lab-doc-title lab-doc-title--row${catalogLayout ? ' lab-doc-title--catalog' : ''}`}>
                    {docTitle}
                  </span>
                  {ext ? (
                    <span className={`lab-doc-ext lab-doc-ext--inline${catalogLayout ? ' lab-doc-ext--catalog' : ''}`}>
                      {ext.replace('.', '')}
                    </span>
                  ) : null}
                </span>
              ) : catalogLayout ? (
                <span className="lab-doc-file-text lab-doc-file-text--catalog" title={docTitle}>
                  <span className="lab-doc-title lab-doc-title--catalog">
                    {docTitle}
                    {ext ? (
                      <span className="lab-doc-ext lab-doc-ext--inline lab-doc-ext--catalog">
                        {ext.replace('.', '')}
                      </span>
                    ) : null}
                  </span>
                </span>
              ) : (
                <span className="lab-doc-file-text">
                  <span className="lab-doc-title">{docTitle}</span>
                  <span className="lab-doc-path">
                    {ext ? <span className="lab-doc-ext">{ext.replace('.', '')}</span> : null}
                    {pathHint ? (
                      <span className="lab-doc-path-hint">{pathHint}</span>
                    ) : null}
                    {!pathHint && doc.folderHint ? `${doc.folderHint} · ` : null}
                    {!pathHint ? fileName : null}
                  </span>
                </span>
              )}
              <ChevronRight size={13} className="lab-doc-file-chevron" aria-hidden />
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function CategorySection({
  cat,
  files,
  documentTitle,
  selectedPath,
  onSelectFile,
  categoryIcons,
  sensitiveCategories,
  hideHeader = false,
  hideDescription = false,
  compactFiles = false,
  catalogLayout = false,
  pathHintResolver = null,
}) {
  const Icon = categoryIcons[cat.id];
  const sensitive = cat.sensitive || sensitiveCategories.includes(cat.id);

  return (
    <section
      className={`lab-doc-category-block${sensitive ? ' lab-doc-category-block--sensitive' : ''}`}
      aria-labelledby={`lab-doc-cat-${cat.id}`}
    >
      {!hideHeader ? (
        <header className="lab-doc-category-header">
          {Icon ? <Icon size={15} className="lab-doc-category-icon" aria-hidden /> : null}
          <h4 id={`lab-doc-cat-${cat.id}`} className="lab-doc-category-title">
            {cat.label}
          </h4>
          <span className="lab-doc-category-count">{files.length}</span>
          {sensitive ? (
            <Lock size={11} className="lab-doc-category-sensitive" aria-label="Sensitive" />
          ) : null}
        </header>
      ) : (
        <h4 id={`lab-doc-cat-${cat.id}`} className="visually-hidden">
          {cat.label}
        </h4>
      )}
      {cat.description && !hideDescription ? (
        <p className="lab-doc-category-desc">{cat.description}</p>
      ) : null}
      <FileList
        files={files}
        documentTitle={documentTitle}
        selectedPath={selectedPath}
        onSelectFile={onSelectFile}
        compact={compactFiles}
        catalogLayout={catalogLayout}
        pathHintResolver={pathHintResolver}
      />
    </section>
  );
}

/**
 * Tabbed document browser when groups/categories are large; stacked list for small sections.
 */
export default function DocumentCategoryFileList({
  categoryGroups,
  grouped,
  fileQuery = '',
  documentTitle,
  selectedPath,
  onSelectFile,
  categoryIcons = {},
  sensitiveCategories = [],
  categoryLayout = 'inline',
  renderPreview = null,
  toolbarAfterTabs = null,
}) {
  const { t } = useGuiT();

  const blocks = useMemo(
    () => buildDocumentCategoryBlocks(categoryGroups, grouped, fileQuery, documentTitle),
    [categoryGroups, grouped, fileQuery, documentTitle]
  );

  const showGroupTabs = shouldShowGroupTabs(blocks);

  const [activeGroupId, setActiveGroupId] = useState(null);
  const [activeCategoryId, setActiveCategoryId] = useState(null);
  const [activeSubfolderId, setActiveSubfolderId] = useState(null);

  useEffect(() => {
    if (!blocks.length) {
      setActiveGroupId(null);
      setActiveCategoryId(null);
      setActiveSubfolderId(null);
      return;
    }

    const groupStillValid = blocks.some((b) => b.groupId === activeGroupId);
    const group = groupStillValid
      ? blocks.find((b) => b.groupId === activeGroupId)
      : blocks[0];

    setActiveGroupId(group.groupId);

    const catStillValid = group.categories.some(({ cat }) => cat.id === activeCategoryId);
    const category = catStillValid
      ? group.categories.find(({ cat }) => cat.id === activeCategoryId)
      : group.categories[0];
    setActiveCategoryId(category.cat.id);
  }, [blocks, activeGroupId, activeCategoryId]);

  const activeBlock = blocks.find((b) => b.groupId === activeGroupId) || blocks[0] || null;
  const activeCategoryEntry = activeBlock?.categories.find(({ cat }) => cat.id === activeCategoryId)
    || activeBlock?.categories[0]
    || null;

  const showCategoryTabs = activeBlock
    ? shouldShowCategoryTabs(activeBlock.categories, activeBlock.fileCount)
    : false;

  const tabbedMode = showGroupTabs || showCategoryTabs;
  const horizontalTop = categoryLayout === 'horizontal-top';
  const catalogSplit = horizontalTop && renderPreview;

  const flatCategories = useMemo(
    () => blocks.flatMap((block) => block.categories),
    [blocks]
  );

  const flattenSubfolders = isWetLabProtocolCategory(activeCategoryId);
  const pathHintResolver = flattenSubfolders ? wetLabProtocolPathHint : null;

  const subfolderSourceEntry = tabbedMode
    ? activeCategoryEntry
    : flatCategories.length === 1
      ? flatCategories[0]
      : null;

  const subfolderAlbums = useMemo(() => {
    if (flattenSubfolders || !subfolderSourceEntry) return [];
    if (!tabbedMode && !catalogSplit) return [];
    return deriveSubfolderAlbums(subfolderSourceEntry.files);
  }, [tabbedMode, catalogSplit, subfolderSourceEntry, flattenSubfolders]);

  useEffect(() => {
    if (!subfolderAlbums.length) {
      setActiveSubfolderId(null);
      return;
    }
    const stillValid = subfolderAlbums.some((album) => album.id === activeSubfolderId);
    if (!stillValid) setActiveSubfolderId(subfolderAlbums[0].id);
  }, [subfolderAlbums, activeSubfolderId]);

  const visibleFiles = useMemo(() => {
    if (tabbedMode) {
      if (!activeCategoryEntry) return [];
      return filterFilesBySubfolder(activeCategoryEntry.files, activeSubfolderId);
    }
    if (subfolderAlbums.length && subfolderSourceEntry) {
      return filterFilesBySubfolder(subfolderSourceEntry.files, activeSubfolderId);
    }
    return flatCategories.flatMap(({ files }) => files);
  }, [tabbedMode, activeCategoryEntry, subfolderAlbums, subfolderSourceEntry, activeSubfolderId, flatCategories]);

  const totalFiles = blocks.reduce((sum, block) => sum + block.fileCount, 0);

  if (!totalFiles) {
    return <p className="text-footnote muted lab-doc-grouped-empty">{t('docs.noFilesSearch')}</p>;
  }

  if (!tabbedMode && !catalogSplit) {
    return (
      <div className="lab-doc-grouped-list">
        {toolbarAfterTabs ? (
          <div className="lab-doc-toolbar-after-tabs">{toolbarAfterTabs}</div>
        ) : null}
        {blocks.map((block) => (
          <div key={block.groupId} className="lab-doc-grouped-section">
            {block.categories.map(({ cat, files }) => (
              <CategorySection
                key={cat.id}
                cat={cat}
                files={files}
                documentTitle={documentTitle}
                selectedPath={selectedPath}
                onSelectFile={onSelectFile}
                categoryIcons={categoryIcons}
                sensitiveCategories={sensitiveCategories}
              />
            ))}
          </div>
        ))}
      </div>
    );
  }

  const activeCat = tabbedMode
    ? activeCategoryEntry?.cat
    : flatCategories.length === 1
      ? flatCategories[0].cat
      : null;

  const categoryTabsNav = showCategoryTabs && activeBlock ? (
    <div
      className={`lab-doc-category-strip${horizontalTop ? ' lab-doc-category-strip--horizontal-top lab-doc-tab-tier--child' : flattenSubfolders ? ' lab-doc-category-strip--chips' : ''}`}
    >
      {horizontalTop ? (
        <span className="lab-doc-tab-tier-eyebrow lab-doc-tab-tier-eyebrow--child">
          {t('docs.subcategoryEyebrow')}
        </span>
      ) : null}
      <nav
        className={`lab-doc-nav-tabs lab-doc-category-tabs${horizontalTop ? ' lab-doc-category-tabs--horizontal-top' : flattenSubfolders ? ' lab-doc-category-tabs--chips' : ''}`}
        aria-label={t('docs.categoryTabsAria')}
      >
        {activeBlock.categories.map(({ cat, files }) => {
          const Icon = categoryIcons[cat.id];
          return (
            <button
              key={cat.id}
              type="button"
              className={`lab-doc-nav-tab lab-doc-subcategory-tab${activeCategoryId === cat.id ? ' active' : ''}`}
              onClick={() => {
                setActiveCategoryId(cat.id);
                setActiveSubfolderId(null);
              }}
              aria-current={activeCategoryId === cat.id ? 'true' : undefined}
              title={cat.description || cat.label}
            >
              {Icon ? <Icon size={12} className="lab-doc-nav-tab-icon" aria-hidden /> : null}
              <span className="lab-doc-nav-tab-label">{cat.label}</span>
              <span className="lab-doc-nav-tab-count">{files.length}</span>
            </button>
          );
        })}
      </nav>
    </div>
  ) : null;

  const albumLayout = horizontalTop || renderPreview ? 'horizontal' : 'vertical';

  const albumsNav = subfolderAlbums.length ? (
    <DocumentSubfolderAlbums
      albums={subfolderAlbums}
      activeId={activeSubfolderId}
      onSelect={setActiveSubfolderId}
      categoryLabel={activeCat?.label}
      layout={albumLayout}
    />
  ) : null;

  const filesSection = tabbedMode ? (
    visibleFiles.length ? (
      <CategorySection
        cat={activeCat}
        files={visibleFiles}
        documentTitle={documentTitle}
        selectedPath={selectedPath}
        onSelectFile={onSelectFile}
        categoryIcons={categoryIcons}
        sensitiveCategories={sensitiveCategories}
        hideHeader={showCategoryTabs || subfolderAlbums.length > 0}
        hideDescription={horizontalTop}
        compactFiles={horizontalTop ? false : tabbedMode}
        catalogLayout={horizontalTop}
        pathHintResolver={pathHintResolver}
      />
    ) : (
      <p className="text-footnote muted lab-doc-grouped-empty">{t('docs.noFilesCategory')}</p>
    )
  ) : (
    flatCategories.map(({ cat, files }) => {
      const sectionFiles =
        subfolderAlbums.length && flatCategories.length === 1
          ? filterFilesBySubfolder(files, activeSubfolderId)
          : files;
      if (!sectionFiles.length) return null;
      return (
        <CategorySection
          key={cat.id}
          cat={cat}
          files={sectionFiles}
          documentTitle={documentTitle}
          selectedPath={selectedPath}
          onSelectFile={onSelectFile}
          categoryIcons={categoryIcons}
          sensitiveCategories={sensitiveCategories}
          hideHeader={flatCategories.length === 1 && (subfolderAlbums.length > 0 || horizontalTop)}
          hideDescription={horizontalTop}
          compactFiles={false}
          catalogLayout={horizontalTop}
          pathHintResolver={pathHintResolver}
        />
      );
    })
  );

  const hasFileContent = tabbedMode
    ? Boolean(activeCat && (subfolderAlbums.length || visibleFiles.length))
    : flatCategories.some(({ files }) => files.length);

  const fileBody = hasFileContent ? (
    <>
      {horizontalTop && albumsNav ? (
        <div className="lab-doc-album-top-bar lab-doc-album-top-bar--catalog">{albumsNav}</div>
      ) : null}
      <div
        className={`lab-doc-category-body${!horizontalTop && subfolderAlbums.length ? ' lab-doc-category-body--with-albums' : ''}${horizontalTop ? ' lab-doc-category-body--horizontal-files lab-doc-category-body--catalog-files' : ''}`}
      >
        {!horizontalTop && albumsNav}
        {filesSection}
      </div>
    </>
  ) : (
    <p className="text-footnote muted lab-doc-grouped-empty">{t('docs.noFilesCategory')}</p>
  );

  const topChrome = (
    <>
      {showGroupTabs ? (
        <div
          className={`lab-doc-group-strip${horizontalTop ? ' lab-doc-group-strip--horizontal-top lab-doc-tab-tier--parent' : ''}`}
        >
          {horizontalTop ? (
            <span className="lab-doc-tab-tier-eyebrow lab-doc-tab-tier-eyebrow--parent">
              {t('docs.groupEyebrow')}
            </span>
          ) : null}
          <nav
            className={`lab-doc-nav-tabs lab-doc-group-tabs${horizontalTop ? ' lab-doc-group-tabs--horizontal-top' : ''}`}
            aria-label={t('docs.groupTabsAria')}
          >
            {blocks.map((block) => (
              <button
                key={block.groupId}
                type="button"
                className={`lab-doc-nav-tab lab-doc-group-tab module-top-tab${activeGroupId === block.groupId ? ' active' : ''}`}
                onClick={() => {
                  setActiveGroupId(block.groupId);
                  setActiveCategoryId(null);
                  setActiveSubfolderId(null);
                }}
                aria-current={activeGroupId === block.groupId ? 'true' : undefined}
              >
                <span className="lab-doc-nav-tab-label">{block.groupLabel}</span>
                <span className="lab-doc-nav-tab-count">{block.fileCount}</span>
              </button>
            ))}
          </nav>
        </div>
      ) : null}
      {categoryTabsNav}
      {horizontalTop && (activeCat?.description || flatCategories[0]?.cat?.description) ? (
        <p className="lab-doc-category-desc lab-doc-category-desc--catalog-top">
          {(activeCat || flatCategories[0]?.cat)?.description}
        </p>
      ) : null}
      {horizontalTop && toolbarAfterTabs ? (
        <div className="lab-doc-toolbar-after-tabs">{toolbarAfterTabs}</div>
      ) : null}
    </>
  );

  if (horizontalTop && renderPreview) {
    return (
      <div className="lab-doc-grouped-list lab-doc-grouped-list--tabbed lab-doc-grouped-list--horizontal-top">
        <div className="lab-doc-category-top-bar">{topChrome}</div>
        {renderPreview(fileBody)}
      </div>
    );
  }

  return (
    <div className={`lab-doc-grouped-list lab-doc-grouped-list--tabbed${horizontalTop ? ' lab-doc-grouped-list--horizontal-top' : ''}`}>
      {horizontalTop ? <div className="lab-doc-category-top-bar">{topChrome}</div> : topChrome}
      {fileBody}
    </div>
  );
}

export function countGroupedFiles(categoryGroups, grouped, fileQuery, documentTitle) {
  const blocks = buildDocumentCategoryBlocks(categoryGroups, grouped, fileQuery, documentTitle);
  return blocks.reduce((sum, block) => sum + block.fileCount, 0);
}
