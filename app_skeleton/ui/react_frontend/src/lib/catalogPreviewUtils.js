/** Fallback previews from static /database/catalog.json when originals are offline. */

import { cleanExtractedText, isBrowserPrintChromeOnly, isJunkPreviewText } from './textCleanup.js';
import { isSpreadsheetPreviewable } from './folderBrowserUtils.js';
import {
  hasSpreadsheetRowMarkers,
  normalizeSpreadsheetBody,
  parseSpreadsheetRows,
} from './spreadsheetText.js';

let indexPromise = null;
/** @type {{ byPath: Map<string, string>, byBasename: Map<string, string> } | null} */
let catalogIndex = null;

function normPath(p) {
  return (p || '').replace(/\\/g, '/').replace(/^\//, '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function basenameOf(p) {
  return normPath(p).split('/').pop() || '';
}

async function loadCatalogIndex() {
  if (catalogIndex) return catalogIndex;
  if (!indexPromise) {
    indexPromise = fetch('/database/catalog.json', { cache: 'no-store' })
      .then((res) => {
        if (!res.ok) throw new Error('Catalog unavailable');
        return res.json();
      })
      .then((data) => {
        const byPath = new Map();
        const byBasename = new Map();
        for (const docs of Object.values(data.sections || {})) {
          for (const doc of docs || []) {
            const key = normPath(doc.path);
            if (key && doc.id) {
              byPath.set(key, doc.id);
              const base = basenameOf(key);
              if (base && !byBasename.has(base)) byBasename.set(base, doc.id);
            }
          }
        }
        catalogIndex = { byPath, byBasename };
        return catalogIndex;
      })
      .catch((err) => {
        indexPromise = null;
        throw err;
      });
  }
  return indexPromise;
}

export async function resolveCatalogDocId(relativePath, fileName = null) {
  const index = await loadCatalogIndex();
  const key = normPath(relativePath);
  if (key && index.byPath.has(key)) return index.byPath.get(key);
  const base = basenameOf(fileName || relativePath);
  if (base && index.byBasename.has(base)) return index.byBasename.get(base);
  return null;
}

/** @returns {Promise<object | null>} */
export async function fetchCatalogDocument(relativePath, fileName = null) {
  const docId = await resolveCatalogDocId(relativePath, fileName);
  if (!docId) return null;
  const res = await fetch(`/database/docs/${docId}.json`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

/** Turn catalog R1:/R2: spreadsheet extraction into SpreadsheetPreview sheet models. */
export function catalogDocToSheetModels(doc) {
  const text = (doc?.full_text || '').trim();
  if (!text || !hasSpreadsheetRowMarkers(text)) return null;

  const rows = parseSpreadsheetRows(text);
  if (!rows.length) return null;

  const sheetNames = doc?.metadata?.extraction_metadata?.sheet_names;
  const name =
    (Array.isArray(sheetNames) && sheetNames.find((n) => n && !String(n).startsWith('._')))
    || 'Extracted';
  const maxCols = rows.reduce((m, row) => Math.max(m, row.length), 0);

  return [
    {
      name: String(name).replace(/^\._/, ''),
      rows: rows.map((row) => {
        const cells = [...row];
        while (cells.length < maxCols) cells.push('');
        return cells.map((cell) => (cell == null ? '' : String(cell)));
      }),
      truncated: false,
      totalRows: rows.length,
      totalCols: maxCols,
    },
  ];
}

/** Readable prose / instructions from catalog (docx, pdf, xlsx without row markers). */
export function catalogDocToDisplayText(doc) {
  const text = (doc?.full_text || '').trim();
  if (!text) return null;

  const fileName = doc?.filename || doc?.metadata?.source?.filename || '';
  const ext = (fileName.match(/\.[^.]+$/)?.[0] || '').toLowerCase();

  if (isSpreadsheetPreviewable(ext)) {
    if (hasSpreadsheetRowMarkers(text)) return null;
    const normalized = normalizeSpreadsheetBody(text);
    return normalized && !isJunkPreviewText(normalized) ? normalized : null;
  }

  const cleaned = cleanExtractedText(text, { maxChars: 50000 });
  if (!cleaned || isBrowserPrintChromeOnly(cleaned)) return null;
  if (isJunkPreviewText(cleaned)) return null;
  return cleaned;
}

/** @returns {Promise<{ doc: object, sheets: object[] | null, displayText: string | null } | null>} */
export async function fetchCatalogPreviewPayload(relativePath, fileName = null) {
  const doc = await fetchCatalogDocument(relativePath, fileName);
  if (!doc) return null;
  return {
    doc,
    sheets: catalogDocToSheetModels(doc),
    displayText: catalogDocToDisplayText(doc),
  };
}

/** @returns {Promise<string | null>} */
export async function fetchCatalogPreviewText(relativePath, fileName = null) {
  const payload = await fetchCatalogPreviewPayload(relativePath, fileName);
  if (!payload) return null;
  return payload.displayText;
}
