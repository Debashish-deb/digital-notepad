/**
 * Fetch, repair, and parse spreadsheets for in-browser table preview.
 */

import * as XLSX from 'xlsx';

export const SPREADSHEET_EXTENSIONS = new Set([
  '.xlsx',
  '.xls',
  '.xlsm',
  '.xlsb',
  '.ods',
  '.fods',
  '.csv',
  '.tsv',
]);

const ZIP_SIGNATURE = [0x50, 0x4b, 0x03, 0x04];
const OLE_SIGNATURE = [0xd0, 0xcf, 0x11, 0xe0];

export function isSpreadsheetPreviewable(ext) {
  return SPREADSHEET_EXTENSIONS.has((ext || '').toLowerCase());
}

async function fetchArrayBuffer(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Could not load file (HTTP ${res.status})`);
  return res.arrayBuffer();
}

/** Trim leading garbage before ZIP/OLE container signatures. */
export function repairBinaryPayload(buffer) {
  const bytes = new Uint8Array(buffer);
  const notes = [];

  const findSig = (sig, limit = 8192) => {
    for (let i = 0; i < Math.min(bytes.length - sig.length, limit); i += 1) {
      if (sig.every((b, j) => bytes[i + j] === b)) return i;
    }
    return -1;
  };

  const zipAt = findSig(ZIP_SIGNATURE);
  const oleAt = findSig(OLE_SIGNATURE);

  let start = 0;
  if (zipAt > 0 && (oleAt < 0 || zipAt <= oleAt)) {
    start = zipAt;
    notes.push('Removed leading bytes before ZIP archive.');
  } else if (oleAt > 0) {
    start = oleAt;
    notes.push('Removed leading bytes before Excel OLE container.');
  }

  let trimmed = start > 0 ? bytes.slice(start) : bytes;

  if (trimmed.length >= 22) {
    const tail = trimmed.length;
    const view = new DataView(trimmed.buffer, trimmed.byteOffset, trimmed.byteLength);
    let end = tail;
    for (let i = tail - 22; i >= Math.max(0, tail - 65558); i -= 1) {
      if (trimmed[i] === 0x50 && trimmed[i + 1] === 0x4b && trimmed[i + 2] === 0x05 && trimmed[i + 3] === 0x06) {
        const commentLen = view.getUint16(i + 20, true);
        end = i + 22 + commentLen;
        if (end < tail) {
          trimmed = trimmed.slice(0, end);
          notes.push('Trimmed trailing bytes after ZIP end record.');
        }
        break;
      }
    }
  }

  return { buffer: trimmed.buffer.slice(trimmed.byteOffset, trimmed.byteOffset + trimmed.byteLength), notes };
}

export function fixCsvText(text) {
  let t = String(text || '');
  if (t.charCodeAt(0) === 0xfeff) t = t.slice(1);
  t = t.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  return t;
}

function parseStrategies(extension) {
  const ext = (extension || '').toLowerCase();
  const isTextDelimited = ext === '.csv' || ext === '.tsv';

  if (isTextDelimited) {
    return [
      { name: 'delimited-utf8', opts: { type: 'string', FS: ext === '.tsv' ? '\t' : ',' } },
      { name: 'delimited-latin1', opts: { type: 'binary', FS: ext === '.tsv' ? '\t' : ',', codepage: 1252 } },
    ];
  }

  return [
    { name: 'standard', opts: { type: 'array', cellDates: true, cellNF: false, cellStyles: false } },
    { name: 'dense', opts: { type: 'array', dense: true, cellDates: true, cellNF: false, cellStyles: false } },
    { name: 'raw-cells', opts: { type: 'array', raw: true, cellNF: false, cellStyles: false } },
    { name: 'permissive', opts: { type: 'array', cellDates: true, cellNF: false, cellStyles: false, WTF: true } },
  ];
}

function decodeDelimitedText(buffer, ext) {
  const utf8 = fixCsvText(new TextDecoder('utf-8', { fatal: false }).decode(new Uint8Array(buffer)));
  if (utf8.includes(',') || utf8.includes('\t') || ext === '.tsv') return utf8;
  try {
    return fixCsvText(new TextDecoder('iso-8859-1').decode(new Uint8Array(buffer)));
  } catch {
    return utf8;
  }
}

export function workbookToSheetModels(workbook, { maxRows = 600, maxCols = 64 } = {}) {
  if (!workbook?.SheetNames?.length) return [];

  return workbook.SheetNames.map((name) => {
    const sheet = workbook.Sheets[name];
    if (!sheet) {
      return { name, rows: [], truncated: false, totalRows: 0, totalCols: 0 };
    }

    const rows = XLSX.utils.sheet_to_json(sheet, {
      header: 1,
      defval: '',
      raw: false,
      blankrows: false,
    });

    const totalRows = rows.length;
    const totalCols = rows.reduce((m, r) => Math.max(m, r.length), 0);
    const clipped = rows.slice(0, maxRows).map((row) => {
      const cells = Array.isArray(row) ? row : [row];
      return cells.slice(0, maxCols).map((cell) => (cell == null ? '' : String(cell)));
    });

    return {
      name,
      rows: clipped,
      truncated: totalRows > maxRows || totalCols > maxCols,
      totalRows,
      totalCols,
    };
  });
}

/**
 * Load spreadsheet from a static file URL with repair + multi-strategy parse.
 * @returns {Promise<{ ok: boolean, sheets?: object[], repairNotes?: string[], error?: string }>}
 */
export async function loadSpreadsheetFromUrl(url, extension) {
  if (!url) return { ok: false, error: 'No file URL' };

  const ext = (extension || '').toLowerCase();
  const attempts = [];

  let buffer;
  try {
    buffer = await fetchArrayBuffer(url);
  } catch (err) {
    return { ok: false, error: err.message || 'Fetch failed', attempts };
  }

  if (!buffer.byteLength) {
    return { ok: false, error: 'File is empty', attempts };
  }

  const repaired = repairBinaryPayload(buffer);
  const repairNotes = [...repaired.notes];
  const payload = repaired.buffer;

  if (ext === '.csv' || ext === '.tsv') {
    const text = decodeDelimitedText(payload, ext);
    for (const { name, opts } of parseStrategies(ext)) {
      try {
        const input = opts.type === 'string' ? text : payload;
        const wb = XLSX.read(input, opts);
        if (wb.SheetNames?.length) {
          const sheets = workbookToSheetModels(wb);
          if (sheets.some((s) => s.rows.length)) {
            return { ok: true, sheets, repairNotes, strategy: name };
          }
        }
      } catch (err) {
        attempts.push({ name, error: err.message });
      }
    }
  }

  for (const { name, opts } of parseStrategies(ext)) {
    try {
      const wb = XLSX.read(payload, opts);
      if (wb.SheetNames?.length) {
        const sheets = workbookToSheetModels(wb);
        if (sheets.some((s) => s.rows.length)) {
          if (name !== 'standard') repairNotes.push(`Recovered using ${name} parser.`);
          return { ok: true, sheets, repairNotes, strategy: name };
        }
      }
    } catch (err) {
      attempts.push({ name, error: err.message });
    }
  }

  if (ext !== '.csv' && ext !== '.tsv') {
    try {
      const text = decodeDelimitedText(payload, '.csv');
      if (text.includes(',') || text.includes('\t')) {
        const wb = XLSX.read(text, { type: 'string', FS: ',' });
        const sheets = workbookToSheetModels(wb);
        if (sheets.some((s) => s.rows.length)) {
          repairNotes.push('Interpreted file as delimited text fallback.');
          return { ok: true, sheets, repairNotes, strategy: 'text-fallback' };
        }
      }
    } catch (err) {
      attempts.push({ name: 'text-fallback', error: err.message });
    }
  }

  const detail = attempts.length ? attempts[attempts.length - 1].error : 'Unknown format';
  return { ok: false, error: detail || 'Could not parse spreadsheet', attempts, repairNotes };
}
