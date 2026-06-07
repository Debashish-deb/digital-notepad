/**
 * Automatic cleanup for document titles, filenames, and in-document headings.
 * Fixes spacing, casing, separators, and common naming mistakes.
 */

const KNOWN_TYPOS = [
  [/\bBIlling\b/gi, 'Billing'],
  [/\bIlmoitis\b/gi, 'Ilmoitus'],
  [/\bluovotuspyyntö\b/gi, 'luovutuspyyntö'],
  [/\briskiarviounti\b/gi, 'riskiarviointi'],
  [/\bTayttoohje\b/gi, 'Täyttöohje'],
  [/\bRiskinarviointipohja\b/gi, 'Riskinarviointipohja'],
  [/\bONBOARDING\b/g, 'Onboarding'],
  [/\bDATASHEETS\s*&\s*HANDBOOKS\b/gi, 'Datasheets & Handbooks'],
  [/\bCellcycle\b/gi, 'Cell Cycle'],
  [/\bCellcycleproject\b/gi, 'Cell Cycle Project'],
  [/\bGeoMx\b/g, 'GeoMx'],
  [/\bscrna\b/gi, 'scRNA'],
  [/\btcycif\b/gi, 't-CyCIF'],
  [/\bcycif\b/gi, 'CyCIF'],
  [/\bxenium\b/gi, 'Xenium'],
  [/\bfarkkila\b/gi, 'Färkkilä'],
  [/\bfärkkilä\b/gi, 'Färkkilä'],
  [/\bON\s+BOARDING\b/gi, 'Onboarding'],
  [/\buser\s*manual\b/gi, 'User Manual'],
  [/\bhand\s*book\b/gi, 'Handbook'],
  [/\bdata\s*sheet\b/gi, 'Datasheet'],
  [/\bphone\s*numbers?\b/gi, 'Phone Numbers'],
];

const TITLE_STOPWORDS = new Set([
  'a', 'an', 'the', 'and', 'or', 'of', 'for', 'to', 'in', 'on', 'with', 'at', 'by', 'from', 'as',
]);

const PRESERVE_ACRONYMS = new Set([
  'SOP', 'BSL', 'RNA', 'DNA', 'IHC', 'IF', 'QC', 'PI', 'GSK', 'UPS', 'PDF', 'CSV', 'XLSX',
  'HTML', 'API', 'IT', 'LUMI', 'CSC', 'EMEA', 'USDA', 'BSL-2', 'GEO', 'DSP', 'OME', 'XML',
  'RNA-SEQ', 'SCRNA', 'TCYCIF', 'CYCIF', 'XENIUM', 'GEO MX',
]);

const REVISION_PREFIX_RE = /^(?:UPD|UPDATE|REV(?:ISED)?|DRAFT)\s+[\d./-]+(?:\s+[A-Z]{1,3})?\s+/i;
const COPY_OF_RE = /^copy\s+of\s+/i;
const MARKDOWN_NOISE_RE = /\{[^}]*\}/g;
const MARKDOWN_EMPHASIS_RE = /[*_]{1,2}([^*_]+)[*_]{1,2}/g;
const SEPARATOR_RUN_RE = /\s*[_]{2,}\s*/g;
const MULTI_DASH_RE = /\s*[-–—]\s*[-–—]+\s*/g;
const CAMEL_SPLIT_RE = /([a-z0-9])([A-Z])/g;
const SPACE_BEFORE_PUNCT_RE = /\s+([,.;:!?])/g;
const MISSING_SPACE_AFTER_PUNCT_RE = /([,.;:!?])([^\s\d)])/g;
const DUPLICATE_WORD_RE = /\b([A-Za-zÀ-ÿ]{2,})\s+\1\b/gi;
const ALL_CAPS_WORD_RE = /\b[A-Z]{2,}\b/g;

function stripMarkdownNoise(text) {
  return String(text || '')
    .replace(MARKDOWN_NOISE_RE, '')
    .replace(MARKDOWN_EMPHASIS_RE, '$1')
    .replace(/\[(.*?)\]\([^)]*\)/g, '$1')
    .trim();
}

function normalizeUnicodeSpaces(text) {
  return String(text || '')
    .replace(/[\u00a0\u200b\u202f]/g, ' ')
    .replace(/\u00ad/g, '');
}

function applyKnownTypos(text) {
  let out = text;
  for (const [pattern, replacement] of KNOWN_TYPOS) {
    out = out.replace(pattern, replacement);
  }
  return out;
}

function looksMostlyUppercase(text) {
  const letters = (text.match(/[A-Za-zÀ-ÿ]/g) || []);
  if (letters.length < 4) return false;
  const upper = letters.filter((ch) => ch === ch.toUpperCase() && ch !== ch.toLowerCase()).length;
  return upper / letters.length >= 0.82;
}

function preserveTokenCase(word, index) {
  const core = word.replace(/^[^A-Za-z0-9À-ÿ]+|[^A-Za-z0-9À-ÿ]+$/g, '');
  const upperCore = core.toUpperCase();
  if (PRESERVE_ACRONYMS.has(upperCore)) {
    return word.replace(core, upperCore);
  }
  if (core.length <= 6 && core === upperCore && /[A-Z]/.test(core)) {
    return word;
  }
  if (index > 0 && TITLE_STOPWORDS.has(core.toLowerCase())) {
    return word.replace(core, core.toLowerCase());
  }
  const cased = core.charAt(0).toUpperCase() + core.slice(1).toLowerCase();
  return word.replace(core, cased);
}

export function toSmartTitleCase(text) {
  const raw = String(text || '').trim();
  if (!raw) return '';
  return raw
    .split(/\s+/)
    .map((word, index) => preserveTokenCase(word, index))
    .join(' ');
}

function normalizeSeparators(text) {
  return text
    .replace(SEPARATOR_RUN_RE, ' ')
    .replace(MULTI_DASH_RE, ' — ')
    .replace(/\s*[_]\s*/g, ' ')
    .replace(/\s*&\s*/g, ' & ')
    .replace(/\s*\/\s*/g, ' / ')
    .replace(/\s*:\s*/g, ': ')
    .replace(/\s*;\s*/g, '; ')
    .replace(/\s+—\s+/g, ' — ')
    .replace(/\s+–\s+/g, ' – ');
}

function collapseWhitespace(text) {
  return text.replace(/\s+/g, ' ').trim();
}

function removeDuplicateWords(text) {
  let out = text;
  let prev = null;
  for (let i = 0; i < 4; i += 1) {
    out = out.replace(DUPLICATE_WORD_RE, '$1');
    if (out === prev) break;
    prev = out;
  }
  return out;
}

function fixPunctuationSpacing(text) {
  return text
    .replace(SPACE_BEFORE_PUNCT_RE, '$1')
    .replace(MISSING_SPACE_AFTER_PUNCT_RE, '$1 $2')
    .replace(/\s+'/g, "'")
    .replace(/'\s+/g, "'")
    .replace(/\(\s+/g, '(')
    .replace(/\s+\)/g, ')');
}

function looksLikeFilenameStem(text) {
  const s = String(text || '');
  if (!s) return false;
  if (s.includes(' — ')) return false;
  const words = s.split(/\s+/);
  if (words.length >= 5) return false;
  return /[_-]/.test(s) || /^[a-z0-9]+$/i.test(s.replace(/\s/g, '')) || words.some((w) => w.length > 14);
}

function shouldTitleCase(text, mode) {
  if (mode === 'heading') {
    return looksMostlyUppercase(text) || ALL_CAPS_WORD_RE.test(text);
  }
  return looksLikeFilenameStem(text) || (looksMostlyUppercase(text) && text.length <= 80);
}

/**
 * Polish document list / preview titles.
 */
export function polishDisplayTitle(text) {
  return polishDisplayText(text, { mode: 'title' });
}

/**
 * Polish in-document section and card headings.
 */
export function polishDisplayHeading(text) {
  return polishDisplayText(text, { mode: 'heading' });
}

export function polishDisplayText(text, { mode = 'title' } = {}) {
  if (!text) return '';

  let s = normalizeUnicodeSpaces(stripMarkdownNoise(text));
  if (!s) return '';

  s = s.replace(COPY_OF_RE, '');
  if (mode === 'heading') {
    s = s.replace(REVISION_PREFIX_RE, '');
  }

  s = applyKnownTypos(s);
  s = normalizeSeparators(s);
  s = s.replace(CAMEL_SPLIT_RE, '$1 $2');
  s = fixPunctuationSpacing(s);
  s = removeDuplicateWords(s);
  s = collapseWhitespace(s);

  if (shouldTitleCase(s, mode)) {
    s = toSmartTitleCase(s);
  }

  s = applyKnownTypos(s);
  s = fixPunctuationSpacing(s);
  s = collapseWhitespace(s);

  return s || String(text).trim();
}
