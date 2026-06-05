import './MacPlusVisualStyles.css';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';

import TasksScreen from './TasksScreen';
import LabSectionTwinPanel from '../components/LabSectionTwinPanel.jsx';
import { billingInstructions } from '../data/billingInstructions.js';

/**
 * Orders / Billing / Logistics panels
 * Professional document blueprint hub:
 * - Abort-safe API loading
 * - Robust document normalization
 * - Professional blueprint side navigation
 * - Category-level summaries
 * - Rich document cards with confidence, field/table counts, review status
 * - Search context and sidebar stats
 * - Safer rendering for missing/malformed data
 * - Sensitive values hidden by default
 * - Masked raw source drawer
 * - Preserves existing public exports
 */

const CATEGORY_ORDER = ['billing', 'order_form', 'shipping', 'courier', 'other'];

const CATEGORY_META = {
  billing: {
    id: 'billing',
    label: 'Billing & Invoicing',
    icon: '💳',
    tone: 'blue',
  },
  order_form: {
    id: 'order_form',
    label: 'Order Forms',
    icon: '📋',
    tone: 'violet',
  },
  shipping: {
    id: 'shipping',
    label: 'Customs & Shipping',
    icon: '✈️',
    tone: 'cyan',
  },
  courier: {
    id: 'courier',
    label: 'Courier Accounts',
    icon: '🚚',
    tone: 'green',
  },
  other: {
    id: 'other',
    label: 'Other Documents',
    icon: '📄',
    tone: 'slate',
  },
};

const SENSITIVE_LABEL_PATTERN =
  /\b(password|passcode|secret|secret question|answer|token|api key|apikey|private key|credential|recovery|security question)\b/i;

const SENSITIVE_VALUE_PATTERN =
  /\b(REDACTED|BEGIN PRIVATE KEY|sk-[a-zA-Z0-9]|token=|password=|passwd=)\b/i;

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function toText(value, fallback = '') {
  if (value == null) return fallback;
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);

  if (Array.isArray(value)) {
    return value.map((item) => toText(item)).filter(Boolean).join(', ');
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return fallback;
  }
}

function compactText(value, fallback = '') {
  return toText(value, fallback).replace(/\s+/g, ' ').trim();
}

function titleCaseFromKey(value) {
  return compactText(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function clampNumber(value, min, max, fallback) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function buildApiUrl(baseUrl, path) {
  const cleanBase = compactText(baseUrl).replace(/\/+$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

function getRawDocumentId(doc) {
  return (
    doc?.document_id ||
    doc?.id ||
    doc?.document?.document_id ||
    doc?.document?.id ||
    doc?.metadata?.document_id ||
    doc?.source?.document_id ||
    null
  );
}

function getStableDocId(doc, index) {
  const rawId = getRawDocumentId(doc);
  if (rawId) return String(rawId);

  const fileName =
    doc?.source?.file_name ||
    doc?.document?.source?.file_name ||
    doc?.file_name ||
    'document';

  const title =
    doc?.content?.title ||
    doc?.document?.title ||
    doc?.subject ||
    doc?.name ||
    'untitled';

  return `${compactText(fileName, 'file')}-${compactText(title, 'doc')}-${index}`;
}

function getDocumentType(doc) {
  return compactText(
    doc?.classification?.document_type ||
      doc?.document_type ||
      doc?.document?.classification?.document_type ||
      doc?.document?.document_type ||
      doc?.type ||
      '',
  ).toLowerCase();
}

function getCategoryFromDoc(doc) {
  const docType = getDocumentType(doc);
  const searchable = [
    docType,
    doc?.content?.title,
    doc?.document?.title,
    doc?.subject,
    doc?.source?.file_name,
    doc?.document?.source?.file_name,
    doc?.file_name,
  ]
    .map((item) => compactText(item).toLowerCase())
    .join(' ');

  if (
    docType === 'billing_instruction' ||
    searchable.includes('billing') ||
    searchable.includes('invoice') ||
    searchable.includes('invoicing')
  ) {
    return CATEGORY_META.billing;
  }

  if (
    docType === 'order_form' ||
    searchable.includes('order form') ||
    searchable.includes('purchase order')
  ) {
    return CATEGORY_META.order_form;
  }

  if (
    docType === 'shipping_customs_statement' ||
    searchable.includes('customs') ||
    searchable.includes('shipping') ||
    searchable.includes('shipment') ||
    searchable.includes('usda') ||
    searchable.includes('fedex')
  ) {
    return CATEGORY_META.shipping;
  }

  if (
    docType.startsWith('courier_service') ||
    docType.includes('courier') ||
    searchable.includes('courier') ||
    searchable.includes('fedex') ||
    searchable.includes('dhl') ||
    searchable.includes('ups')
  ) {
    return CATEGORY_META.courier;
  }

  return CATEGORY_META.other;
}

function getDocTitle(doc) {
  return compactText(
    doc?.content?.title ||
      doc?.document?.title ||
      doc?.title ||
      doc?.subject ||
      getRawDocumentId(doc),
    'Untitled document',
  );
}

function getDocSummary(doc) {
  return compactText(
    doc?.content?.short_summary ||
      doc?.document?.short_summary ||
      doc?.summary ||
      doc?.description ||
      doc?.subject,
    '',
  );
}

function getDocFileName(doc) {
  return compactText(
    doc?.source?.file_name ||
      doc?.document?.source?.file_name ||
      doc?.file_name ||
      doc?.source_file ||
      'Unknown file',
  );
}

function getDocLanguage(doc) {
  const language =
    doc?.language?.original ||
    doc?.language?.detected ||
    doc?.document?.language?.original ||
    doc?.document?.language ||
    doc?.language ||
    'en';

  if (isObject(language)) return 'EN';
  return compactText(language, 'en').slice(0, 8).toUpperCase();
}

function getDocConfidence(doc) {
  return clampNumber(
    doc?.classification?.confidence ??
      doc?.document?.classification?.confidence ??
      doc?.confidence,
    0,
    1,
    0.9,
  );
}

function getDocSections(doc) {
  return asArray(
    doc?.gui_display?.sections ||
      doc?.document?.gui_display?.sections ||
      doc?.sections,
  ).filter(Boolean);
}

function getDocTables(doc) {
  return asArray(
    doc?.structured_data?.tables ||
      doc?.document?.structured_data?.tables ||
      doc?.tables,
  ).filter(Boolean);
}

function getRawText(doc) {
  return (
    doc?.content?.original_text ||
    doc?.content?.canonical_text ||
    doc?.document?.content?.original_text ||
    doc?.document?.content?.canonical_text ||
    doc?.original_text ||
    doc?.canonical_text ||
    ''
  );
}

function flattenForSearch(value, depth = 0) {
  if (depth > 5 || value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);

  if (Array.isArray(value)) {
    return value.map((item) => flattenForSearch(item, depth + 1)).join(' ');
  }

  if (isObject(value)) {
    return Object.values(value)
      .map((item) => flattenForSearch(item, depth + 1))
      .join(' ');
  }

  return '';
}

function isSensitiveField(field) {
  const label = compactText(field?.label || field?.name || field?.key);
  const value = compactText(field?.value);

  return (
    SENSITIVE_LABEL_PATTERN.test(label) ||
    SENSITIVE_VALUE_PATTERN.test(value)
  );
}

function maskSensitiveText(rawText) {
  const text = toText(rawText);
  if (!text) return '';

  return text
    .split('\n')
    .map((line) => {
      if (SENSITIVE_LABEL_PATTERN.test(line) || SENSITIVE_VALUE_PATTERN.test(line)) {
        const separatorIndex = line.search(/[:=]/);
        if (separatorIndex >= 0) {
          return `${line.slice(0, separatorIndex + 1)} [hidden]`;
        }
        return '[hidden sensitive line]';
      }

      return line;
    })
    .join('\n');
}

function formatDateTime(value) {
  const text = compactText(value);
  if (!text) return '';

  const date = new Date(text);
  if (Number.isNaN(date.getTime())) return text;

  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  } catch {
    return text;
  }
}

function normalizeDocument(doc, index) {
  const category = getCategoryFromDoc(doc);
  const sections = getDocSections(doc);
  const tables = getDocTables(doc);
  const rawText = getRawText(doc);

  const searchableText = [
    getRawDocumentId(doc),
    getDocTitle(doc),
    getDocSummary(doc),
    getDocFileName(doc),
    getDocumentType(doc),
    category.label,
    getDocLanguage(doc),
    flattenForSearch(sections),
    flattenForSearch(tables),
    rawText,
  ]
    .map((item) => compactText(item).toLowerCase())
    .join(' ');

  return {
    id: getStableDocId(doc, index),
    raw: doc,
    title: getDocTitle(doc),
    summary: getDocSummary(doc),
    fileName: getDocFileName(doc),
    language: getDocLanguage(doc),
    category,
    documentType: getDocumentType(doc),
    confidence: getDocConfidence(doc),
    needsReview:
      Boolean(doc?.quality?.needs_human_review) ||
      Boolean(doc?.document?.quality?.needs_human_review),
    sections,
    tables,
    rawText,
    searchableText,
  };
}

function getDocumentFieldCount(doc) {
  return asArray(doc?.sections).reduce((total, section) => {
    return total + asArray(section?.fields).length;
  }, 0);
}

function getDocumentTableCount(doc) {
  return asArray(doc?.tables).length;
}

function getDocumentTypeLabel(doc) {
  if (doc?.documentType) return titleCaseFromKey(doc.documentType);
  return 'Blueprint';
}

function HighlightedCount({ count, total }) {
  return (
    <span className="obp-count" aria-label={`${count} of ${total} documents visible`}>
      {count === total ? `(${total})` : `(${count}/${total})`}
    </span>
  );
}

function SidebarBlueprintStats({ docs, filteredDocs, searchQuery }) {
  const total = docs.length;
  const visible = filteredDocs.length;
  const reviewCount = docs.filter((doc) => doc.needsReview).length;
  const structuredCount = docs.filter(
    (doc) => doc.sections.length || doc.tables.length,
  ).length;
  const categoryCount = CATEGORY_ORDER.filter((categoryId) =>
    docs.some((doc) => doc.category?.id === categoryId),
  ).length;

  return (
    <div className="obp-sidebar-stats" aria-label="Document blueprint summary">
      <div className="obp-sidebar-stat-card">
        <span className="obp-sidebar-stat-value">{visible}</span>
        <span className="obp-sidebar-stat-label">
          {searchQuery ? 'Visible' : 'Blueprints'}
        </span>
      </div>

      <div className="obp-sidebar-stat-card">
        <span className="obp-sidebar-stat-value">{categoryCount}</span>
        <span className="obp-sidebar-stat-label">Categories</span>
      </div>

      <div className="obp-sidebar-stat-card">
        <span className="obp-sidebar-stat-value">{structuredCount}</span>
        <span className="obp-sidebar-stat-label">Structured</span>
      </div>

      {reviewCount ? (
        <div className="obp-sidebar-stat-card has-warning">
          <span className="obp-sidebar-stat-value">{reviewCount}</span>
          <span className="obp-sidebar-stat-label">Review</span>
        </div>
      ) : null}

      {searchQuery ? (
        <div className="obp-sidebar-stat-card obp-sidebar-stat-card--wide">
          <span className="obp-sidebar-stat-value">{visible}/{total}</span>
          <span className="obp-sidebar-stat-label">Search result</span>
        </div>
      ) : null}
    </div>
  );
}

function SecretValue({ value }) {
  const [revealed, setRevealed] = useState(false);
  const text = compactText(value, '—');

  return (
    <span className="obp-secret-wrap">
      <span className="obp-secret" title={revealed ? undefined : 'Hidden sensitive value'}>
        🔒 {revealed ? text : 'Hidden sensitive value'}
      </span>
      <button
        type="button"
        className="obp-inline-action"
        onClick={() => setRevealed((current) => !current)}
        aria-label={revealed ? 'Hide sensitive value' : 'Reveal sensitive value'}
      >
        {revealed ? 'Hide' : 'Reveal'}
      </button>
    </span>
  );
}

function FieldValue({ field }) {
  const value = field?.value ?? field?.text ?? field?.content ?? '';
  const text = compactText(value, '—');

  if (isSensitiveField(field)) {
    return <SecretValue value={text} />;
  }

  if (/^https?:\/\//i.test(text)) {
    return (
      <a
        href={text}
        className="obp-field-link"
        target="_blank"
        rel="noreferrer"
      >
        {text}
      </a>
    );
  }

  return <>{text}</>;
}


function OrdersArchiveSpotlight({ context = 'default' }) {
  const contextCopy = {
    empty: {
      eyebrow: 'Archive fallback',
      title: 'Orders Archive Still Available',
      body: 'The live billing blueprint API did not return records, but the historical orders archive can still be reviewed from the lab twin.',
    },
    error: {
      eyebrow: 'Archive safety layer',
      title: 'Use the Archive While Live Blueprints Recover',
      body: 'The live endpoint is unavailable. Historical purchase orders and procurement records remain accessible from the processed archive.',
    },
    default: {
      eyebrow: 'Historical procurement intelligence',
      title: 'Orders Archive',
      body: 'Review historical purchase orders, procurement traces, reagent requests, sequencing orders, service records, and lab operational follow-ups.',
    },
  };

  const copy = contextCopy[context] || contextCopy.default;

  return (
    <section className="obp-archive-shell" aria-label="Orders archive">
      <div className="panel obp-archive-hero">
        <div className="obp-archive-hero-copy">
          <p className="text-caption">{copy.eyebrow}</p>
          <h3 className="obp-archive-title">{copy.title}</h3>
          <p className="text-body-secondary obp-archive-lead">
            {copy.body}
          </p>
        </div>

        <div className="obp-archive-scoreboard" aria-label="Archive coverage summary">
          <div className="obp-archive-score-card">
            <span className="obp-archive-score-value">PO</span>
            <span className="obp-archive-score-label">Purchase orders</span>
          </div>
          <div className="obp-archive-score-card">
            <span className="obp-archive-score-value">Vendor</span>
            <span className="obp-archive-score-label">Supplier records</span>
          </div>
          <div className="obp-archive-score-card">
            <span className="obp-archive-score-value">Trace</span>
            <span className="obp-archive-score-label">Audit context</span>
          </div>
        </div>
      </div>

      <div className="obp-archive-layout">
        <aside className="panel obp-archive-sidebar">
          <p className="text-caption">Archive workflow</p>
          <h4 className="text-title-3">Review checklist</h4>

          <ol className="obp-archive-steps">
            <li>
              <span className="obp-archive-step-index">01</span>
              <span>
                <strong>Find the original record</strong>
                <small>Search by vendor, order code, project, reagent, sequencing batch, or service type.</small>
              </span>
            </li>
            <li>
              <span className="obp-archive-step-index">02</span>
              <span>
                <strong>Check operational context</strong>
                <small>Compare archive notes with live billing blueprints, customs files, and courier instructions.</small>
              </span>
            </li>
            <li>
              <span className="obp-archive-step-index">03</span>
              <span>
                <strong>Use traceability carefully</strong>
                <small>Confirm sample, shipment, invoice, and project links before reusing historical details.</small>
              </span>
            </li>
          </ol>

          <div className="obp-archive-note">
            <strong>Best use:</strong> historical lookup, audit support, vendor history, and procurement continuity.
          </div>
        </aside>

        <div className="obp-archive-main">
          <LabSectionTwinPanel
            sectionId="orders_archive"
            title="Orders archive"
            description="Historical purchase orders, procurement records, and archived operational order documents."
            excludeFolder="Billing"
          />
        </div>
      </div>
    </section>
  );
}


function LoadingState() {
  return (
    <div className="obp-shell" aria-busy="true">
      <div className="panel obp-header obp-header--loading">
        <div>
          <p className="text-caption">Orders intelligence</p>
          <h2 className="text-title-1 obp-title">Loading logistics blueprints…</h2>
          <p className="page-lead obp-lead">
            Preparing courier, customs, order, and billing instructions.
          </p>
        </div>
      </div>

      <div className="obp-layout">
        <div className="panel obp-master obp-blueprints-sidebar feed-scroll">
          <div className="obp-skeleton obp-skeleton--title" />
          <div className="obp-skeleton obp-skeleton--card" />
          <div className="obp-skeleton obp-skeleton--card" />
          <div className="obp-skeleton obp-skeleton--card" />
        </div>

        <div className="panel obp-detail">
          <div className="obp-skeleton obp-skeleton--hero" />
          <div className="obp-sections-grid">
            <div className="obp-skeleton obp-skeleton--section" />
            <div className="obp-skeleton obp-skeleton--section" />
            <div className="obp-skeleton obp-skeleton--section" />
            <div className="obp-skeleton obp-skeleton--section" />
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyDocumentsState({ onRetry }) {
  return (
    <div className="stack-md">
      <div className="panel obp-empty-panel">
        <p className="text-caption">No documents found</p>
        <h2 className="text-title-1">No logistics or billing blueprints loaded</h2>
        <p className="text-body-secondary">
          The API responded successfully, but no document records were returned.
        </p>
        <button type="button" className="button button-primary" onClick={onRetry}>
          Reload documents
        </button>
      </div>

      <OrdersArchiveSpotlight context="empty" />
    </div>
  );
}

function ErrorState({ error, endpoint, onRetry }) {
  return (
    <div className="stack-md">
      <div className="panel panel-danger obp-error-panel" role="alert">
        <p className="text-caption">Orders API unavailable</p>
        <h2 className="text-title-2">Could not load billing instructions</h2>
        <p>{error || 'Unknown loading error.'}</p>

        <div className="obp-error-meta">
          <span className="text-caption">Endpoint</span>
          <code>{endpoint}</code>
        </div>

        <button type="button" className="button button-primary" onClick={onRetry}>
          Try again
        </button>
      </div>

      <OrdersArchiveSpotlight context="error" />
    </div>
  );
}

function CategoryGroup({ category, documents, selectedDocId, onSelectDocument }) {
  if (!documents.length) return null;

  const categoryConfidence = documents.length
    ? Math.round(
        (documents.reduce((total, doc) => total + Number(doc.confidence || 0), 0) /
          documents.length) *
          100,
      )
    : 0;

  return (
    <section
      className="obp-cat-group obp-cat-group--premium"
      aria-label={category.label}
      data-category={category.id}
    >
      <div className="obp-cat-header obp-cat-header--premium" data-category={category.id}>
        <div className="obp-cat-heading-left">
          <span className="obp-cat-icon obp-cat-icon--premium" aria-hidden="true">
            {category.icon}
          </span>

          <span className="obp-cat-copy">
            <span className="obp-cat-title">{category.label}</span>
            <span className="obp-cat-subtitle">
              {documents.length} document{documents.length === 1 ? '' : 's'} · {categoryConfidence}% avg confidence
            </span>
          </span>
        </div>

        <span className="obp-cat-count obp-cat-count--premium">
          {documents.length}
        </span>
      </div>

      <div className="obp-cat-doc-stack">
        {documents.map((doc) => {
          const isSelected = doc.id === selectedDocId;
          const fieldCount = getDocumentFieldCount(doc);
          const tableCount = getDocumentTableCount(doc);
          const confidence = Math.round((doc.confidence || 0) * 100);

          return (
            <button
              type="button"
              key={doc.id}
              onClick={() => onSelectDocument(doc.id)}
              className={`obp-doc-item obp-doc-item--premium${isSelected ? ' is-active' : ''}`}
              data-category={category.id}
              aria-current={isSelected ? 'true' : undefined}
              aria-label={`Open ${doc.title}`}
            >
              <span className="obp-doc-active-rail" aria-hidden="true" />

              <span className="obp-doc-card-topline">
                <span className="obp-doc-type-chip">
                  {getDocumentTypeLabel(doc)}
                </span>

                <span className="obp-doc-confidence-mini">
                  {confidence}%
                </span>
              </span>

              <span className="obp-doc-title">{doc.title}</span>

              {doc.summary ? (
                <span className="obp-doc-summary">{doc.summary}</span>
              ) : (
                <span className="obp-doc-summary is-muted">
                  Structured operational document from {doc.fileName}.
                </span>
              )}

              <span className="obp-doc-meta obp-doc-meta--premium">
                <span className="obp-doc-file" title={doc.fileName}>
                  {doc.fileName}
                </span>

                <span className="obp-doc-pill">{doc.language}</span>

                {fieldCount > 0 ? (
                  <span className="obp-doc-pill">{fieldCount} fields</span>
                ) : null}

                {tableCount > 0 ? (
                  <span className="obp-doc-pill">
                    {tableCount} table{tableCount === 1 ? '' : 's'}
                  </span>
                ) : null}

                {doc.needsReview ? (
                  <span className="obp-doc-review">Review</span>
                ) : (
                  <span className="obp-doc-pill is-structured">Structured</span>
                )}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function DocumentSections({ document }) {
  if (!document.sections.length) {
    return (
      <div className="obp-empty-detail-card">
        <h4 className="text-title-3">No structured display sections</h4>
        <p className="text-body-secondary">
          This document does not include GUI display fields yet. Use the masked raw source below
          to inspect extracted text.
        </p>
      </div>
    );
  }

  return (
    <div className="obp-sections-grid">
      {document.sections.map((section, sectionIndex) => {
        const sectionTitle = compactText(
          section?.section_title || section?.title || section?.name,
          `Section ${sectionIndex + 1}`,
        );

        const fields = asArray(section?.fields);
        const isQuality = /quality|review|warning|issue/i.test(sectionTitle);

        return (
          <section
            key={`${sectionTitle}-${sectionIndex}`}
            className={`obp-section${isQuality ? ' obp-section--warning obp-section--full' : ''}`}
          >
            <h4 className="obp-section-title">
              {isQuality ? <span aria-hidden="true">⚠️ </span> : null}
              {sectionTitle}
            </h4>

            {fields.length ? (
              <div className="obp-fields">
                {fields.map((field, fieldIndex) => {
                  const label = compactText(
                    field?.label || field?.name || field?.key,
                    `Field ${fieldIndex + 1}`,
                  );

                  return (
                    <div key={`${label}-${fieldIndex}`} className="obp-field">
                      <span className="obp-field-label">{label}</span>
                      <span className="obp-field-value">
                        <FieldValue field={field} />
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-body-secondary">
                No fields were extracted for this section.
              </p>
            )}
          </section>
        );
      })}
    </div>
  );
}

function DocumentTables({ tables }) {
  if (!tables.length) return null;

  return (
    <>
      {tables.map((table, tableIndex) => {
        const tableName = titleCaseFromKey(table?.name || `Table ${tableIndex + 1}`);
        const columns = asArray(table?.column_names || table?.columns);
        const rows = asArray(table?.rows);

        if (!columns.length && !rows.length) return null;

        const inferredColumns =
          columns.length ||
          !rows.length ||
          !isObject(rows[0])
            ? columns
            : Object.keys(rows[0]);

        return (
          <section key={`${tableName}-${tableIndex}`} className="obp-table-wrap">
            <h4 className="obp-table-title">📋 {tableName}</h4>

            <div className="obp-table-scroll">
              <table className="table obp-table">
                <thead>
                  <tr>
                    {inferredColumns.map((column, columnIndex) => (
                      <th key={`${column}-${columnIndex}`} className="obp-th">
                        {titleCaseFromKey(column)}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {rows.length ? (
                    rows.map((row, rowIndex) => (
                      <tr key={`row-${rowIndex}`}>
                        {inferredColumns.map((column, columnIndex) => (
                          <td key={`${column}-${columnIndex}`} className="obp-td">
                            {isObject(row)
                              ? compactText(row[column], '—')
                              : compactText(row, '—')}
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="obp-td" colSpan={Math.max(inferredColumns.length, 1)}>
                        No table rows extracted.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </>
  );
}

function RawSourceDrawer({ rawText }) {
  const maskedText = maskSensitiveText(rawText);

  if (!maskedText) return null;

  return (
    <details className="obp-raw-drawer">
      <summary className="obp-raw-summary">
        🔍 View masked raw extracted text source
      </summary>

      <p className="text-caption obp-raw-warning">
        Sensitive-looking lines are hidden automatically. Use the structured fields above
        for normal work.
      </p>

      <pre className="code-block obp-raw-pre">{maskedText}</pre>
    </details>
  );
}

function DocumentDetail({ document, searchQuery }) {
  if (!document) {
    return (
      <div className="obp-empty-detail">
        <p className="text-caption">
          {searchQuery ? 'No matching blueprint selected' : 'Nothing selected'}
        </p>
        <h3 className="text-title-2">
          {searchQuery ? 'No document matches this search' : 'Select a document'}
        </h3>
        <p className="text-body-secondary">
          {searchQuery
            ? 'Try a different keyword, filename, field value, courier name, or document ID.'
            : 'Choose a document from the left panel to inspect extracted fields, tables, and source text.'}
        </p>
      </div>
    );
  }

  return (
    <article className="obp-detail-inner" aria-labelledby="orders-document-title">
      <header className="obp-detail-header">
        <div className="obp-detail-badges">
          <span
            className={`obp-badge obp-badge--${document.category.tone || 'blue'}`}
          >
            <span aria-hidden="true">{document.category.icon}</span>&nbsp;
            {document.category.label}
          </span>

          <span className="obp-badge obp-badge--green">
            Confidence: {Math.round(document.confidence * 100)}%
          </span>

          {document.needsReview ? (
            <span className="obp-badge obp-badge--amber">
              ⚠️ Review Required
            </span>
          ) : (
            <span className="obp-badge obp-badge--blue">
              Structured
            </span>
          )}
        </div>

        <h3 id="orders-document-title" className="obp-detail-title">
          {document.title}
        </h3>

        {document.summary ? (
          <p className="page-lead">{document.summary}</p>
        ) : (
          <p className="page-lead">
            Extracted operational document from {document.fileName}.
          </p>
        )}

        <div className="obp-detail-meta">
          <span>
            <strong>File:</strong> {document.fileName}
          </span>
          <span>
            <strong>Language:</strong> {document.language}
          </span>
          {document.documentType ? (
            <span>
              <strong>Type:</strong> {titleCaseFromKey(document.documentType)}
            </span>
          ) : null}
        </div>
      </header>

      <DocumentSections document={document} />
      <DocumentTables tables={document.tables} />
      <RawSourceDrawer rawText={document.rawText} />
    </article>
  );
}

export function OrdersBillingPanel() {
  return (
    <LabSectionTwinPanel
      sectionId="orders_billing"
      title="Billing & Invoicing Blueprints"
      description="Invoices, billing instructions, and financial procurement documents from the billing folder."
      filterFolder="Billing"
    />
  );
}
export function OrdersArchivePanel() {
  return <OrdersArchiveSpotlight />;
}

export function OrdersTasksPanel(props) {
  return <TasksScreen {...props} />;
}

export function OrdersRegisterPanel() {
  return (
    <div className="obp-shell">
      <div className="panel obp-header">
        <div>
          <p className="text-caption">Orders system</p>
          <h2 className="text-title-1 obp-title">Orders Register</h2>
          <p className="page-lead obp-lead">
            Manage your reagent, sequencing, and service orders.
          </p>
        </div>
      </div>
      <div className="panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <p className="muted">Orders register component is currently under maintenance.</p>
      </div>
    </div>
  );
}

export function OrdersRelatedPanel() {
  return (
    <div className="obp-shell">
      <div className="panel obp-header">
        <div>
          <p className="text-caption">Orders intelligence</p>
          <h2 className="text-title-1 obp-title">Related Records</h2>
          <p className="page-lead obp-lead">
            Cross-links between samples, shipments, sequencing batches, project folders,
            and order events.
          </p>
        </div>
      </div>
      <div className="panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <p className="muted">Traceability functionality is currently offline.</p>
      </div>
    </div>
  );
}
