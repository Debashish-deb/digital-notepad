/**
 * Clean noisy extracted document text and detect junk display names.
 */

import {
  isNumericCellDump,
  normalizeSpreadsheetBody,
} from './spreadsheetText.js';

const SPREADSHEET_XML_DUMP = /###\s*xl\//i;
const OFFICE_XML_DUMP = /###\s*(?:word|ppt|xl)\//i;

const BROWSER_PRINT_HEADER =
  /^(?:Firefox|Chrome|Safari|Edge)\s+(?:about:blank|https?:\/\/\S+)\s*/i;
const BROWSER_PRINT_PAGE_FI =
  /^\d+\s*\/\s*\d+\s+\d{1,2}\.\d{1,2}\.\d{4}\s+klo\s+\d{1,2}\.\d{2}\s*$/i;

/** Strip browser print chrome without eating the whole document (single-line PDF extracts). */
function stripBrowserChrome(text) {
  let t = text;
  t = t.replace(
    /^(?:(?:Firefox|Chrome|Safari|Edge)\s+)?(?:UPS CampusShip\s*\|\s*UPS\s*-?\s*Finland\s+)?https?:\/\/\S+\s*/i,
    ''
  );
  t = t.replace(/^\d+\s+of\s+\d+\s+\d{1,2}\/\d{1,2}\/\d{4},?\s*\d{1,2}:\d{2}\s*(?:AM|PM)?\s*/i, '');
  t = t.replace(/^(?:Firefox|Chrome|Safari|Edge)\s+https?:\/\/\S+\s*/gim, '');
  t = t.replace(/^UPS CampusShip[^\n]*\n+/gim, '');
  // Firefox/Chrome "Print to PDF" headers (often the only text in scanned form exports)
  t = t.replace(
    /(?:Firefox|Chrome|Safari|Edge)\s+about:blank\s*(?:\n+\s*\d+\s*\/\s*\d+\s+\d{1,2}\.\d{1,2}\.\d{4}\s+klo\s+\d{1,2}\.\d{2}\s*)?/gim,
    ''
  );
  t = t.replace(BROWSER_PRINT_PAGE_FI, '');
  return t;
}

/** True when extracted text is only browser print headers/footers (no real document body). */
export function isBrowserPrintChromeOnly(text) {
  if (!text) return true;
  const lines = String(text)
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .filter((l) => !/^###\s*(?:word|ppt|xl)\//i.test(l));
  if (!lines.length) return true;
  return lines.every(
    (line) =>
      BROWSER_PRINT_HEADER.test(line) ||
      BROWSER_PRINT_PAGE_FI.test(line) ||
      /^(?:Firefox|Chrome|Safari|Edge)\s+about:blank$/i.test(line)
  );
}

const JUNK_NAME_PATTERNS = [
  /^(?:firefox|chrome|safari|edge)\b/i,
  /^ups campusship\b/i,
  /^https?:\/\//i,
  /\bhttps?:\/\/\S+/i,
  /^[\d.,\s]+$/,
  /^[a-z](?:,[a-z])+$/i,
  /^[\w.+-]+@[\w.-]+\.\w{2,}$/i,
  /^hi\s+[\w]+,?\s*$/i,
  /^page\s+\d+/i,
  /^###\s+/,
];

/** Known OCR / PDF line-break artifacts from courier label extracts. */
const OCR_REPLACEMENTS = [
  [/Federal\s+Expr\s+essin/gi, 'Federal Expressin'],
  [/Inter\s+net-/gi, 'Internet-'],
  [/sivuiltamme/gi, 'sivuiltamme'],
  [/var\s+ten\b/gi, 'varten'],
  [/KORVAUSVELVOLLISU\s+UDEN/gi, 'KORVAUSVELVOLLISUUDEN'],
  [/työntekijöi\b/gi, 'työntekijöiden'],
  [/EM\s+EA-maita/gi, 'EMEA-maita'],
  [/university'/g, "university's"],
  [/all kind of advice/gi, 'all kinds of advice'],
  [/The products was/gi, 'The products were'],
  [/laboratory testing onl\b/gi, 'laboratory testing only'],
  [/substances are for laboratory testing only in clinical\b/gi, 'substances are for laboratory testing only in clinical research'],
];

export function isJunkDisplayName(value, fileName = '') {
  const s = (value || '').trim().replace(/\s+/g, ' ');
  if (!s) return true;
  if (s.length <= 3 && (fileName || '').length > 12) return true;
  if (SPREADSHEET_XML_DUMP.test(s)) return true;
  return JUNK_NAME_PATTERNS.some((re) => re.test(s));
}

export function humanizeFilenameLabel(fileName) {
  if (!fileName) return 'Document';
  let stem = String(fileName).replace(/\.[^.]+$/, '');
  stem = stem
    .replace(/^BIlling_/i, 'Billing_')
    .replace(/Ilmoitis/gi, 'Ilmoitus')
    .replace(/luovotuspyyntö/gi, 'luovutuspyyntö')
    .replace(/riskiarviounti/gi, 'riskiarviointi')
    .replace(/Tayttoohje/gi, 'Täyttöohje')
    .replace(/Riskinarviointipohja/gi, 'Riskinarviointipohja')
    .replace(/DATASHEETS&HANDBOOKS/gi, 'Datasheets & Handbooks')
    .replace(/&/g, ' & ')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return stem.slice(0, 160) || 'Document';
}

export function cleanExtractedText(text, { maxChars } = {}) {
  if (!text) return '';
  let cleaned = String(text).replace(/\r\n/g, '\n');

  if (SPREADSHEET_XML_DUMP.test(cleaned) || isNumericCellDump(cleaned)) return '';

  cleaned = normalizeSpreadsheetBody(cleaned);
  if (!cleaned) return '';

  cleaned = cleaned
    .replace(/###\s*(?:word|ppt|xl)\/[^\n]+/gi, '')
    .replace(/^\d{5,}\s+\d{4,}\s*$/gm, '')
    .trim();
  if (!cleaned) return '';

  cleaned = stripBrowserChrome(cleaned);

  for (const [pattern, replacement] of OCR_REPLACEMENTS) {
    cleaned = cleaned.replace(pattern, replacement);
  }

  // Soft breaks at hyphens in paths/URLs: "logging-and-\nconnections" -> "logging-and-connections"
  cleaned = cleaned.replace(/([a-z0-9])-\s*\n\s*([a-z0-9])/gi, '$1-$2');
  // Breaks where the hyphen moves to the next line: "logging-\nand-connections" -> "logging-and-connections"
  cleaned = cleaned.replace(/([a-z0-9])-\s*\n\s*and-/gi, '$1-and-');

  // Merge hyphenation breaks: "labora-\ntory" -> "laboratory"
  cleaned = cleaned.replace(/(\w)-\n(\w)/g, '$1$2');

  // Strip PDF page markers
  cleaned = cleaned.replace(/^Page\s+\d+\s+of\s+\d+\s*$/gim, '');

  // Collapse excessive blank lines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

  if (maxChars && cleaned.length > maxChars) {
    cleaned = `${cleaned.slice(0, maxChars)}…`;
  }

  return cleaned;
}

export function isJunkPreviewText(text) {
  if (isBrowserPrintChromeOnly(text)) return true;
  const cleaned = cleanExtractedText(text);
  if (!cleaned || cleaned.length < 40) return true;
  if (/^https?:\/\/\S+$/i.test(cleaned)) return true;
  if (/^(?:Firefox|UPS CampusShip)\s+https?:\/\//i.test(cleaned)) return true;
  if (/^(?:Firefox|Chrome|Safari|Edge)\s+about:blank/i.test(cleaned)) return true;
  return false;
}
