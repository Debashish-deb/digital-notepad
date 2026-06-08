import { useMemo } from 'react';
import {
  classifyDocument,
  getDocumentType,
  sortByDocumentType,
} from '@/features/documents/documentTypeRegistry.js';
import { DOCUMENT_TYPE_CATEGORY_ORDER } from '@/features/documents/documentTypeGroups.js';
import './documentTypeLayouts.css';
import {
  Database,
  FileCode,
  FileSpreadsheet,
  FileText,
  FileType,
  Film,
  Image,
} from 'lucide-react';
import { formatBytes } from '@/services/documentLibraryClient.js';
import { smartDocumentTitle } from '@/lib/smartDocumentTitle.js';
import DocumentListMetadataRow from './DocumentListMetadataRow.jsx';
import { useResizableGridColumns } from '@/lib/useResizableGridColumns.js';
import {
  ROW_HEIGHT,
  SFE_COLUMN_WIDTHS_KEY,
  SFE_LIST_COLUMNS,
  prettifyCategory,
  resolveFileBulletKind,
} from '@/features/documents/documentLibraryUi.js';

const FILE_BULLET_ICONS = {
  document: FileText,
  pdf: FileType,
  spreadsheet: FileSpreadsheet,
  image: Image,
  video: Film,
  code: FileCode,
  text: FileText,
  data: Database,
};

function StatusBadges({ item }) {
  const badges = [];
  if (item.indexed_in_search) badges.push(['Indexed', 'indexed']);
  else if (item.digitalization_status === 'indexed') badges.push(['Indexed', 'indexed']);
  else if (item.digitalization_status === 'metadata_only') badges.push(['Metadata only', 'metadata_only']);
  else if (item.has_extracted_content) badges.push(['Extracted', 'partial']);
  else if (item.digitalization_status === 'needs_redigitalization') badges.push(['Needs redigitalization', 'needs_redigitalization']);
  else if (item.digitalization_status === 'pending_extraction') badges.push(['Pending extraction', 'not_started']);
  else if (item.digitalization_status === 'failed') badges.push(['Extraction failed', 'warn']);
  else if (item.digitalization_status === 'not_started') badges.push(['Not indexed', 'not_started']);
  else badges.push(['Not indexed', 'not_started']);
  if (item.preview_status === 'missing' && item.digitalization_status !== 'metadata_only') {
    badges.push(['Preview missing', 'warn']);
  }
  if (item.duplicate_status === 'duplicate') badges.push(['Duplicate', 'duplicate']);
  if (item.unknown_type) badges.push(['Unknown type', 'unknown']);
  if (item.needs_review) badges.push(['Needs review', 'review']);
  const visible = badges.slice(0, 3);
  return (
    <span className="sfe-badges">
      {visible.map(([label, cls]) => (
        <span key={label} className={`sfe-badge sfe-badge--${cls}`}>{label}</span>
      ))}
    </span>
  );
}

function FileListBullet({ item, selected = false }) {
  const kind = resolveFileBulletKind(item);
  const Icon = FILE_BULLET_ICONS[kind] || FileText;
  const indexed = Boolean(
    item?.indexed_in_search
    || item?.digitalization_status === 'indexed'
    || item?.has_extracted_content,
  );

  return (
    <span
      className={[
        'sfe-file-marker',
        `sfe-file-marker--${kind}`,
        selected ? 'is-selected' : '',
        indexed ? 'is-indexed' : '',
      ].filter(Boolean).join(' ')}
      aria-hidden
    >
      <span className="sfe-file-marker__stem" />
      <span className="sfe-file-marker__glass">
        <Icon size={12} strokeWidth={2} />
      </span>
    </span>
  );
}

function resolveItemDocumentType(item) {
  const { typeId } = classifyDocument({
    path: item.logical_path,
    filename: item.filename,
    title: item.title,
    category: item.category,
    subcategory: item.subcategory,
    document_type: item.document_type || item.metadata?.classification?.document_type,
    domain: item.domain,
  });
  return getDocumentType(typeId);
}

function groupItemsByDocumentType(items) {
  const buckets = Object.fromEntries(DOCUMENT_TYPE_CATEGORY_ORDER.map((id) => [id, []]));
  for (const item of items) {
    const type = resolveItemDocumentType(item);
    if (!buckets[type.id]) buckets[type.id] = [];
    buckets[type.id].push({ item, type });
  }
  return DOCUMENT_TYPE_CATEGORY_ORDER
    .map((typeId) => ({
      typeId,
      type: getDocumentType(typeId),
      entries: (buckets[typeId] || []).sort((a, b) => sortByDocumentType(
        { display_title: smartDocumentTitle(a.item) },
        { display_title: smartDocumentTitle(b.item) },
      )),
    }))
    .filter((group) => group.entries.length > 0);
}

export default function DocumentResultList({
  items,
  viewMode,
  selectedId,
  onSelect,
  listDetailExpanded = false,
  groupByDocumentType = false,
}) {
  const { gridTemplateColumns, startResize } = useResizableGridColumns(
    SFE_COLUMN_WIDTHS_KEY,
    SFE_LIST_COLUMNS,
  );
  const rowGridStyle = useMemo(
    () => ({ gridTemplateColumns }),
    [gridTemplateColumns],
  );

  if (!items.length) {
    return <div className="sfe-empty">No files match your filters.</div>;
  }

  const typeGroups = useMemo(
    () => (groupByDocumentType ? groupItemsByDocumentType(items) : null),
    [items, groupByDocumentType],
  );

  const renderCard = (item) => {
    const docType = groupByDocumentType ? resolveItemDocumentType(item) : null;
    return (
      <button
        key={item.asset_id}
        type="button"
        className={`sfe-card${selectedId === item.asset_id ? ' is-selected' : ''}`}
        onClick={() => onSelect(item)}
      >
        <div className="sfe-card-name-line">
          <FileListBullet item={item} selected={selectedId === item.asset_id} />
          <div className="sfe-card-name">{smartDocumentTitle(item)}</div>
          {docType ? <span className="lab-doc-type-badge">{docType.shortLabel}</span> : null}
        </div>
        <DocumentListMetadataRow item={item} className="sfe-row-original sfe-card-meta-row" />
        <div className="sfe-row-path sfe-card-footnote">
          {formatBytes(item.size_bytes)}
          {item.modified_at ? ` · ${item.modified_at.slice(0, 10)}` : ''}
        </div>
        <StatusBadges item={item} />
      </button>
    );
  };

  if (viewMode === 'card') {
    if (typeGroups) {
      return (
        <div className="sfe-type-grouped">
          {typeGroups.map((group) => {
            const TypeIcon = group.type.icon;
            return (
              <section key={group.typeId} className="sfe-type-group">
                <header className="sfe-type-group__header">
                  <TypeIcon size={13} aria-hidden />
                  <span>{group.type.label}</span>
                  <span className="sfe-type-group__count">{group.entries.length}</span>
                </header>
                <div className="sfe-card-grid">{group.entries.map(({ item }) => renderCard(item))}</div>
              </section>
            );
          })}
        </div>
      );
    }
    return <div className="sfe-card-grid">{items.map((item) => renderCard(item))}</div>;
  }

  const listWrapClass = [
    'sfe-list-wrap',
    listDetailExpanded ? 'sfe-list-wrap--resizable' : 'sfe-list-wrap--compact',
  ].join(' ');

  return (
    <div className={listWrapClass}>
      {listDetailExpanded ? (
        <div
          className="sfe-row sfe-row--header"
          style={rowGridStyle}
          role="row"
        >
          {SFE_LIST_COLUMNS.map((col, index) => (
            <div key={col.id} className="sfe-col-header" role="columnheader">
              <span className="sfe-col-label">{col.label}</span>
              {index < SFE_LIST_COLUMNS.length - 1 ? (
                <button
                  type="button"
                  className="sfe-col-resize-handle"
                  aria-label={`Resize ${col.label} column`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    startResize(index, e.clientX);
                  }}
                />
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
      <div className="sfe-virtual-scroll">
        {(typeGroups || [{ typeId: '_flat', type: null, entries: items.map((item) => ({ item })) }]).map((group) => {
          const TypeIcon = group.type?.icon;
          let rowIndex = 0;
          return (
            <div key={group.typeId} className={group.type ? 'sfe-type-group' : undefined}>
              {group.type ? (
                <header className="sfe-type-group__header">
                  {TypeIcon ? <TypeIcon size={13} aria-hidden /> : null}
                  <span>{group.type.label}</span>
                  <span className="sfe-type-group__count">{group.entries.length}</span>
                </header>
              ) : null}
              {group.entries.map(({ item }) => {
                const docType = groupByDocumentType ? resolveItemDocumentType(item) : null;
                const alt = rowIndex % 2 === 1;
                rowIndex += 1;
                return (
                  <div
                    key={item.asset_id}
                    className={`sfe-row${selectedId === item.asset_id ? ' is-selected' : ''}${alt ? ' sfe-row--alt' : ''}`}
                    style={listDetailExpanded ? { ...rowGridStyle, height: ROW_HEIGHT } : { height: ROW_HEIGHT }}
                    onClick={() => onSelect(item)}
                    onKeyDown={(e) => e.key === 'Enter' && onSelect(item)}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="sfe-col-cell sfe-col-cell--name">
                      <div className="sfe-row-name-line">
                        <FileListBullet item={item} selected={selectedId === item.asset_id} />
                        <div className="sfe-row-name-copy">
                          <div className="sfe-row-title">{smartDocumentTitle(item)}</div>
                          <DocumentListMetadataRow
                            item={item}
                            showPathFallback={listDetailExpanded}
                            pathFallback={item.logical_path}
                          />
                        </div>
                        {docType && !listDetailExpanded ? (
                          <span className="lab-doc-type-badge">{docType.shortLabel}</span>
                        ) : null}
                      </div>
                    </div>
                    {listDetailExpanded ? (
                      <>
                        <span className="sfe-row-category sfe-col-cell">
                          {docType?.shortLabel
                            || item.professional_role_label
                            || prettifyCategory(item.project_category_original || item.category)
                            || item.domain
                            || '—'}
                        </span>
                        <span className="sfe-col-cell">{formatBytes(item.size_bytes)}</span>
                        <span className="sfe-col-cell">{item.modified_at?.slice(0, 10) || '—'}</span>
                        <span className="sfe-col-cell sfe-col-cell--status">
                          <StatusBadges item={item} />
                        </span>
                      </>
                    ) : null}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
