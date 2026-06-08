import { useMemo } from 'react';
import DocumentFormatter from './DocumentFormatter.jsx';
import {
  classifyDocument,
  getDocumentType,
} from '@/features/documents/documentTypeRegistry.js';
import { smartDocumentTitle } from '@/lib/smartDocumentTitle.js';
import DocumentListMetadataRow from './DocumentListMetadataRow.jsx';
import './documentTypeLayouts.css';

function formatCorrespondenceDate(doc) {
  const raw = doc?.modified_at || doc?.metadata?.source?.modified || doc?.date;
  if (!raw) return null;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return String(raw);
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'long' }).format(date);
}

/**
 * Type-aware wrapper — picks layout variant and styling from document classification.
 */
export default function DocumentTypeShell({
  doc = null,
  text,
  title,
  onCreateTask,
  preferProse = false,
  typeId: typeIdProp = null,
  showHeader = true,
  className = '',
}) {
  const classification = useMemo(() => {
    if (typeIdProp) {
      return { typeId: typeIdProp, confidence: 100, signals: [] };
    }
    if (doc) return classifyDocument(doc);
    return classifyDocument({ title, excerpt: text?.slice?.(0, 800) });
  }, [doc, typeIdProp, title, text]);

  const type = useMemo(
    () => getDocumentType(classification.typeId),
    [classification.typeId],
  );

  const TypeIcon = type.icon;
  const layoutClass = `doc-type-shell--${type.layoutVariant}`;
  const displayTitle = title || (doc ? smartDocumentTitle(doc) : 'Document');
  const corrDate = type.layoutVariant === 'correspondence' ? formatCorrespondenceDate(doc) : null;

  return (
    <article
      className={['doc-type-shell', layoutClass, className].filter(Boolean).join(' ')}
      data-document-type={type.id}
      data-layout-variant={type.layoutVariant}
    >
      {showHeader ? (
        <header className="doc-type-shell__header">
          <span className="doc-type-shell__icon" aria-hidden>
            <TypeIcon size={18} strokeWidth={2} />
          </span>
          <div className="doc-type-shell__titles">
            <p className="doc-type-shell__eyebrow">{type.label}</p>
            <h3 className="doc-type-shell__title">{displayTitle}</h3>
            {doc ? (
              <DocumentListMetadataRow
                item={doc}
                className="doc-type-shell__meta sfe-preview-top__subline"
              />
            ) : null}
            {!doc && corrDate ? (
              <p className="doc-type-shell__meta">{corrDate}</p>
            ) : null}
          </div>
        </header>
      ) : null}

      <div className="doc-type-shell__body">
        <DocumentFormatter text={text} onCreateTask={onCreateTask} preferProse={preferProse} />
      </div>
    </article>
  );
}
