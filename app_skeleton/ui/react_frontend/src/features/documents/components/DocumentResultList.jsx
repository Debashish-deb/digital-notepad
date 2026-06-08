import { useMemo } from 'react';
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
import { smartDocumentTitle, documentTitleSubline } from '@/lib/smartDocumentTitle.js';
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

function DocumentTitleSubline({ item, className = 'sfe-row-original', pathFallback = null }) {
  const subline = documentTitleSubline(item);
  if (!subline.dateLabel && !subline.filename) {
    return pathFallback ? <div className="sfe-row-path">{pathFallback}</div> : null;
  }
  return (
    <div className={className}>
      {subline.dateLabel ? (
        <span className="sfe-preview-date">{subline.dateLabel}</span>
      ) : null}
      {subline.filename ? <span>{subline.filename}</span> : null}
    </div>
  );
}

export default function DocumentResultList({
  items,
  viewMode,
  selectedId,
  onSelect,
  listDetailExpanded = false,
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

  if (viewMode === 'card') {
    return (
      <div className="sfe-card-grid">
        {items.map((item) => (
          <button
            key={item.asset_id}
            type="button"
            className={`sfe-card${selectedId === item.asset_id ? ' is-selected' : ''}`}
            onClick={() => onSelect(item)}
          >
            <div className="sfe-card-name-line">
              <FileListBullet item={item} selected={selectedId === item.asset_id} />
              <div className="sfe-card-name">{smartDocumentTitle(item)}</div>
            </div>
            <DocumentTitleSubline item={item} />
            <div className="sfe-row-path">{item.project_category_original || item.category || item.domain} · {formatBytes(item.size_bytes)}</div>
            <StatusBadges item={item} />
          </button>
        ))}
      </div>
    );
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
        {items.map((item, rowIndex) => (
          <div
            key={item.asset_id}
            className={`sfe-row${selectedId === item.asset_id ? ' is-selected' : ''}${rowIndex % 2 === 1 ? ' sfe-row--alt' : ''}`}
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
                  {listDetailExpanded ? (
                    <DocumentTitleSubline item={item} pathFallback={item.logical_path} />
                  ) : null}
                </div>
              </div>
            </div>
            {listDetailExpanded ? (
              <>
                <span className="sfe-row-category sfe-col-cell">
                  {item.professional_role_label || prettifyCategory(item.project_category_original || item.category) || item.domain || '—'}
                </span>
                <span className="sfe-col-cell">{formatBytes(item.size_bytes)}</span>
                <span className="sfe-col-cell">{item.modified_at?.slice(0, 10) || '—'}</span>
                <span className="sfe-col-cell sfe-col-cell--status">
                  <StatusBadges item={item} />
                </span>
              </>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
