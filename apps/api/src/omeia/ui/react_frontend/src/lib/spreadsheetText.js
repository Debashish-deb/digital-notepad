/**
 * Turn spreadsheet extraction artifacts (R1:, R2:, CSV rows, cell dumps) into readable text.
 */

const SPREADSHEET_ROW_RE = /^R(\d+):\s*(.*)$/i;
const EXTRACTOR_HEADER_RE = /^#{2,3}\s*(?:word\/document\.xml|xl\/|ppt\/)/i;
const SHEET_HEADER_RE = /^##\s*Sheet:\s*/i;
const COLUMN_LETTERS_ROW_RE = /^[a-z](?:,[a-z])+$/i;
const EMPTY_CSV_ROW_RE = /^[,\s"]+$/;

/** xlsx-zip-xml failure: mostly bare integers / floats one per line */
export function isNumericCellDump(text) {
  const lines = String(text || '')
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length < 12) return false;
  const numeric = lines.filter((l) => /^-?\d+(?:\.\d+)?$/.test(l)).length;
  return numeric / lines.length > 0.55;
}

export function stripExtractorHeaders(text) {
  return String(text || '')
    .split('\n')
    .filter((line) => {
      const t = line.trim();
      if (!t) return true;
      if (EXTRACTOR_HEADER_RE.test(t)) return false;
      if (SHEET_HEADER_RE.test(t)) return false;
      return true;
    })
    .join('\n');
}

export function parseSpreadsheetRows(text) {
  const rows = [];
  for (const line of String(text || '').split('\n')) {
    const t = line.trim();
    const m = t.match(SPREADSHEET_ROW_RE);
    if (!m) continue;
    const cells = m[2]
      .split('|')
      .map((c) => c.trim())
      .filter((c, i, arr) => c || (i > 0 && arr.slice(i).some(Boolean)));
    if (cells.length) rows.push(cells);
  }
  return rows;
}

export function hasSpreadsheetRowMarkers(text) {
  const lines = String(text || '').split('\n').filter((l) => l.trim());
  const marked = lines.filter((l) => SPREADSHEET_ROW_RE.test(l.trim())).length;
  return marked >= 2 && marked / Math.max(lines.length, 1) >= 0.4;
}

function looksLikeHeaderRow(cells) {
  if (!cells?.length) return false;
  const textCells = cells.filter((c) => c && Number.isNaN(Number(c.replace(/,/g, ''))));
  return textCells.length >= Math.max(2, Math.ceil(cells.length * 0.4));
}

/** Readable plain-text table from R1:/R2:/… rows. */
export function formatSpreadsheetRowsAsText(rows) {
  if (!rows.length) return '';

  let headerIdx = rows.findIndex((r) => looksLikeHeaderRow(r));
  if (headerIdx < 0) headerIdx = 0;

  const headers = rows[headerIdx].map((h) => h || '');
  const dataRows = rows.slice(headerIdx + 1);
  const out = [];

  if (looksLikeHeaderRow(rows[headerIdx])) {
    out.push(headers.filter(Boolean).join(' · '));
    out.push('');
  }

  for (const row of dataRows) {
    const pairs = [];
    row.forEach((cell, i) => {
      if (!cell) return;
      const label = headers[i] || `Column ${i + 1}`;
      if (!headers[i] && row[0] === '' && i === 1) {
        pairs.push(cell);
      } else if (headers[i]) {
        pairs.push(`${label}: ${cell}`);
      } else {
        pairs.push(cell);
      }
    });
    if (pairs.length) out.push(pairs.join(' | '));
  }

  return out.join('\n').trim();
}

/** in2csv / comma-separated form dumps (e.g. HUSLAB order form). */
export function formatCsvFormText(text) {
  const out = [];
  for (const line of String(text || '').split('\n')) {
    const raw = line.trim();
    if (!raw) continue;
    if (EMPTY_CSV_ROW_RE.test(raw)) continue;
    if (COLUMN_LETTERS_ROW_RE.test(raw)) continue;

    const cells = raw.split(',').map((c) => c.trim().replace(/^"|"$/g, '').replace(/\n/g, ' '));
    const nonEmpty = cells.filter(Boolean);
    if (!nonEmpty.length) continue;

    const label = cells[0];
    const rest = cells.slice(1).filter(Boolean);
    if (label && rest.length) {
      const sep = label.endsWith(':') ? ' ' : ': ';
      out.push(`${label}${sep}${rest.join(' · ')}`);
    } else if (label) {
      out.push(label);
    } else if (rest.length) {
      out.push(rest.join(' · '));
    }
  }
  return out.join('\n').trim();
}

export function hasCsvFormLayout(text) {
  const lines = String(text || '').split('\n').map((l) => l.trim()).filter(Boolean);
  if (lines.length < 3) return false;
  const commaRows = lines.filter((l) => l.includes(',') && !SPREADSHEET_ROW_RE.test(l)).length;
  return commaRows >= 3 && commaRows / lines.length >= 0.5;
}

export function normalizeSpreadsheetBody(text) {
  let t = String(text || '');
  if (!t.trim()) return '';

  t = stripExtractorHeaders(t);
  if (isNumericCellDump(t)) return '';

  if (hasSpreadsheetRowMarkers(t)) {
    const rows = parseSpreadsheetRows(t);
    const formatted = formatSpreadsheetRowsAsText(rows);
    if (formatted) return formatted;
  }

  if (hasCsvFormLayout(t)) {
    const formatted = formatCsvFormText(t);
    if (formatted) return formatted;
  }

  // Strip orphan R#/K# cell prefixes mid-line (not CHK1, 9R20V0, etc.)
  t = t
    .split('\n')
    .map((line) =>
      line
        .replace(/^R(\d+):\s*/i, '')
        .replace(/^K(\d+):\s*/i, '')
        .replace(/^\s*\|\s*/g, '')
        .trimEnd()
    )
    .join('\n');

  return t.trim();
}
