import React, { memo, useMemo } from 'react';
import {
  ExternalLink,
  PlusSquare,
  Rows3,
  Table2,
} from 'lucide-react';
import CodePreview from './CodePreview.jsx';
import './DocumentFormatter.css';
import { cleanExtractedText } from '../utils/textCleanup.js';
import { buildKindleBlocks } from '../utils/kindleLayout.js';
import {
  hasSpreadsheetRowMarkers,
  parseSpreadsheetRows,
} from '../utils/spreadsheetText.js';

const MAX_PREVIEW_SAMPLE = 5000;
const MAX_CODE_SIGNAL_LINES = 56;

function safeText(value) {
  return String(value ?? '').trim();
}

function isNumericCell(value) {
  const normalized = String(value ?? '')
    .trim()
    .replace(/,/g, '')
    .replace(/%$/, '');

  if (!normalized) return false;
  return !Number.isNaN(Number(normalized));
}

function safeExternalUrl(value) {
  const raw = String(value || '').trim();

  if (!raw) return null;

  try {
    const url = new URL(raw);
    if (!['http:', 'https:', 'mailto:'].includes(url.protocol)) return null;
    return url.href;
  } catch {
    return null;
  }
}

function looksLikeSourceCode(text) {
  const sample = String(text || '').slice(0, MAX_PREVIEW_SAMPLE);
  const lines = sample
    .split('\n')
    .map((line) => line.trimEnd())
    .filter((line) => line.trim())
    .slice(0, MAX_CODE_SIGNAL_LINES);

  if (lines.length < 4) return false;

  const sourceKeywordSignal =
    /^\s*(import |export |from |def |class |function |const |let |var |#include |package |public |private |protected |interface |type |enum |if\s*\(|for\s*\(|while\s*\(|switch\s*\(|return |try\s*\{|catch\s*\(|<\?xml|<!doctype|<html|SELECT |WITH |CREATE |INSERT |UPDATE |DELETE )/im.test(
      sample,
    );

  const syntaxLineCount = lines.filter((line) => {
    const trimmed = line.trim();

    return (
      /[{};]$/.test(trimmed) ||
      trimmed.startsWith('#') ||
      trimmed.startsWith('//') ||
      trimmed.startsWith('/*') ||
      trimmed.startsWith('*') ||
      trimmed.includes('=>') ||
      trimmed.includes(':=') ||
      /^\w+\s*[:=]\s*/.test(trimmed) ||
      /^<\/?[a-z][\s\S]*>/i.test(trimmed)
    );
  }).length;

  const indentationCount = lines.filter((line) => /^\s{2,}\S/.test(line)).length;
  const syntaxRatio = syntaxLineCount / lines.length;
  const indentationRatio = indentationCount / lines.length;

  return sourceKeywordSignal || syntaxRatio >= 0.32 || (syntaxRatio >= 0.22 && indentationRatio >= 0.35);
}

function getStableKey(prefix, index, fallback = '') {
  return `${prefix}-${index}-${String(fallback).slice(0, 32).replace(/\s+/g, '-')}`;
}

function buildFallbackSections(cleaned) {
  const paragraphs = cleaned
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);

  return [
    {
      title: null,
      blocks: [
        {
          type: 'card',
          title: null,
          entries: paragraphs.map((paragraph) => ({
            type: 'paragraph',
            text: paragraph,
          })),
        },
      ],
    },
  ];
}

function buildSafeKindleSections(cleaned) {
  try {
    const sections = buildKindleBlocks(cleaned);

    if (!Array.isArray(sections) || sections.length === 0) {
      return buildFallbackSections(cleaned);
    }

    return sections;
  } catch (error) {
    console.warn('[DocumentFormatter] Kindle layout failed. Falling back to paragraphs.', error);
    return buildFallbackSections(cleaned);
  }
}

function detectSpreadsheetHeaders(rows) {
  if (!rows.length) return { headerIndex: 0, headers: [], body: [], colCount: 1 };

  let headerIndex = 0;

  for (let i = 0; i < Math.min(rows.length, 6); i += 1) {
    const row = rows[i] || [];
    const nonEmpty = row.filter((cell) => safeText(cell));
    const textCells = nonEmpty.filter((cell) => !isNumericCell(cell));

    if (textCells.length >= 2 || (textCells.length >= 1 && nonEmpty.length >= 3)) {
      headerIndex = i;
      break;
    }
  }

  const headers = rows[headerIndex] || [];
  const body = rows.slice(headerIndex + 1);
  const colCount = Math.max(headers.length, ...body.map((row) => row.length), 1);

  return { headerIndex, headers, body, colCount };
}

const SpreadsheetTable = memo(function SpreadsheetTable({ rows }) {
  const { headers, body, colCount } = useMemo(() => detectSpreadsheetHeaders(rows), [rows]);

  if (!rows.length) return null;

  return (
    <section className="kindle-spreadsheet" aria-label="Extracted spreadsheet table">
      <div className="kindle-spreadsheet-header">
        <div className="kindle-spreadsheet-title">
          <Table2 size={16} aria-hidden="true" />
          <span>Extracted table</span>
        </div>

        <div className="kindle-spreadsheet-meta">
          <Rows3 size={14} aria-hidden="true" />
          <span>{body.length.toLocaleString()} rows</span>
        </div>
      </div>

      <div className="kindle-table-wrap">
        <table className="table obp-table kindle-table">
          <thead>
            <tr>
              {Array.from({ length: colCount }, (_, index) => (
                <th key={`th-${index}`} className="obp-th">
                  {safeText(headers[index]) || (index === 0 ? 'Item' : `Col ${index + 1}`)}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {body.map((row, rowIndex) => (
              <tr key={getStableKey('row', rowIndex, row.join('-'))}>
                {Array.from({ length: colCount }, (_, cellIndex) => (
                  <td key={`cell-${rowIndex}-${cellIndex}`} className="obp-td">
                    {safeText(row[cellIndex]) || '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
});

function InlineLink({ href, children, className = 'kindle-link' }) {
  const safeHref = safeExternalUrl(href);

  if (!safeHref) {
    return <span className="kindle-link kindle-link--invalid">{children || href}</span>;
  }

  return (
    <a href={safeHref} target="_blank" rel="noreferrer noopener" className={className}>
      <span>{children || safeHref}</span>
      <ExternalLink size={11} aria-hidden="true" />
    </a>
  );
}

function renderLinks(value) {
  const str = String(value ?? '');
  const parts = str.split(/(\[[^\]]+?\]\([^)]+?\)|https?:\/\/[^\s<>"')]+|mailto:[^\s<>"')]+)/g);

  return parts.map((part, index) => {
    if (!part) return null;

    const markdownMatch = part.match(/^\[([^\]]+?)\]\(([^)]+?)\)$/);

    if (markdownMatch) {
      return (
        <InlineLink key={getStableKey('md-link', index, markdownMatch[2])} href={markdownMatch[2]}>
          {markdownMatch[1]}
        </InlineLink>
      );
    }

    if (/^(https?:\/\/|mailto:)/i.test(part)) {
      return (
        <InlineLink key={getStableKey('raw-link', index, part)} href={part}>
          {part}
        </InlineLink>
      );
    }

    return part;
  });
}

function TaskButton({ text, onCreateTask }) {
  if (!onCreateTask || !text || text.length <= 40) return null;

  return (
    <button
      type="button"
      className="kindle-task-btn btn btn-secondary btn-sm"
      onClick={() => onCreateTask(text)}
      title="Create task from this paragraph"
      aria-label="Create task from this paragraph"
    >
      <PlusSquare size={12} aria-hidden="true" />
      <span>Task</span>
    </button>
  );
}

const CardEntry = memo(function CardEntry({ entry, onCreateTask }) {
  if (!entry || typeof entry !== 'object') return null;

  switch (entry.type) {
    case 'label':
      return <h4 className="doc-inline-label">{safeText(entry.text)}</h4>;

    case 'url':
      return (
        <p className="doc-url-block">
          <InlineLink href={entry.url} className="kindle-link doc-url-link">
            {entry.url}
          </InlineLink>
        </p>
      );

    case 'link-field':
      return (
        <div className="doc-link-field">
          <span className="doc-link-field-label">{safeText(entry.label)}</span>
          <InlineLink href={entry.url} className="kindle-link doc-url-link">
            {entry.url}
          </InlineLink>
        </div>
      );

    case 'field':
      return (
        <dl className="doc-field">
          <dt className="doc-field-label">{safeText(entry.label)}</dt>

          {entry.values?.length ? (
            <dd className="doc-field-body">
              {entry.values.map((value, index) => (
                <p key={getStableKey('field-value', index, value)} className="doc-field-value">
                  {renderLinks(value)}
                </p>
              ))}
            </dd>
          ) : null}
        </dl>
      );

    case 'divider':
      return <hr className="doc-divider" aria-hidden="true" />;

    case 'list':
      return (
        <ul className="doc-list">
          {(entry.items || []).map((item, index) => (
            <li key={getStableKey('list-item', index, item)}>{renderLinks(item)}</li>
          ))}
        </ul>
      );

    case 'lines':
      return (
        <div className="doc-lines">
          {(entry.items || []).map((line, index) => (
            <p key={getStableKey('line', index, line)}>{renderLinks(line)}</p>
          ))}
        </div>
      );

    case 'paragraph':
    default: {
      const paragraphText = safeText(entry.text);

      if (!paragraphText) return null;

      return (
        <div className="doc-paragraph-row">
          <p className="doc-paragraph">{renderLinks(paragraphText)}</p>
          <TaskButton text={paragraphText} onCreateTask={onCreateTask} />
        </div>
      );
    }
  }
});

const DocumentCard = memo(function DocumentCard({ card, onCreateTask }) {
  if (!card || typeof card !== 'object') return null;

  const entries = Array.isArray(card.entries) ? card.entries : [];

  return (
    <article className="doc-card">
      {card.title ? <h3 className="doc-card-title">{safeText(card.title)}</h3> : null}

      <div className="doc-card-body">
        {entries.map((entry, index) => (
          <CardEntry
            key={getStableKey('entry', index, entry?.text || entry?.label || entry?.type)}
            entry={entry}
            onCreateTask={onCreateTask}
          />
        ))}
      </div>
    </article>
  );
});

function DocumentSections({ sections, onCreateTask }) {
  if (!Array.isArray(sections) || sections.length === 0) {
    return (
      <div className="kindle-empty">
        <FileTextIcon />
        <p>No readable document sections were detected.</p>
      </div>
    );
  }

  return (
    <article className="kindle-doc-body">
      {sections.map((section, sectionIndex) => {
        const blocks = Array.isArray(section.blocks) ? section.blocks : [];

        return (
          <section
            key={getStableKey('section', sectionIndex, section.title)}
            className={`kindle-section${sectionIndex % 2 === 1 ? ' kindle-section--alt' : ''}`}
          >
            {section.title ? <h2 className="kindle-heading">{safeText(section.title)}</h2> : null}

            <div className="kindle-section-body">
              {blocks.map((block, blockIndex) => {
                if (block.type === 'card') {
                  return (
                    <DocumentCard
                      key={getStableKey('card', blockIndex, block.title)}
                      card={block}
                      onCreateTask={onCreateTask}
                    />
                  );
                }

                if (block.type === 'divider') {
                  return <hr key={getStableKey('divider', blockIndex)} className="doc-divider" aria-hidden="true" />;
                }

                if (block.type === 'paragraph' && block.text) {
                  return (
                    <div key={getStableKey('paragraph', blockIndex, block.text)} className="doc-paragraph-row">
                      <p className="doc-paragraph">{renderLinks(block.text)}</p>
                      <TaskButton text={block.text} onCreateTask={onCreateTask} />
                    </div>
                  );
                }

                return null;
              })}
            </div>
          </section>
        );
      })}
    </article>
  );
}

function FileTextIcon() {
  return (
    <svg
      className="kindle-empty-icon"
      width="44"
      height="44"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
      <path d="M16 13H8" />
      <path d="M16 17H8" />
      <path d="M10 9H8" />
    </svg>
  );
}

export default function DocumentFormatter({ text, onCreateTask, preferProse = false }) {
  const cleaned = useMemo(() => cleanExtractedText(text || ''), [text]);

  const spreadsheetRows = useMemo(() => {
    if (!text || !hasSpreadsheetRowMarkers(text)) return null;

    const rows = parseSpreadsheetRows(text);
    return rows.length >= 2 ? rows : null;
  }, [text]);

  const isCode = useMemo(() => {
    if (!cleaned || spreadsheetRows || preferProse) return false;
    return looksLikeSourceCode(cleaned);
  }, [cleaned, spreadsheetRows, preferProse]);

  const sections = useMemo(() => {
    if (!cleaned || spreadsheetRows || isCode) return null;
    return buildSafeKindleSections(cleaned);
  }, [cleaned, spreadsheetRows, isCode]);

  if (!cleaned && !spreadsheetRows) return null;

  if (spreadsheetRows) {
    return (
      <div className="kindle-doc kindle-doc--full kindle-doc--spreadsheet">
        <SpreadsheetTable rows={spreadsheetRows} />
      </div>
    );
  }

  if (isCode) {
    return (
      <div className="kindle-doc kindle-doc--full kindle-doc--code">
        <CodePreview content={cleaned} language="plaintext" />
      </div>
    );
  }

  return (
    <div className="kindle-doc kindle-doc--full">
      <DocumentSections sections={sections} onCreateTask={onCreateTask} />
    </div>
  );
}