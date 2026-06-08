/**
 * Display titles and list metadata for research documents.
 * Strips embedded dates from titles; shows date, place, and type on a second row.
 */

import { polishDisplayTitle } from './polishDisplayText.js';
import { classifyDocument, getDocumentType } from '@/features/documents/documentTypeRegistry.js';

const LEADING_DATE_RE = /^(?:\d{1,2}[._/-]\d{1,2}[._/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{8})\s*[_\s.-]*/;
const TRAILING_DATE_RE = /\s*(?:—|–|-)\s*(?:\d{4}-\d{2}-\d{2}|\d{1,2}[._/-]\d{1,2}[._/-]\d{2,4}|\d{8})\s*$/;
const ISO_DATE_RE = /\b(\d{4})-(\d{2})-(\d{2})\b/g;
const DOTTED_DATE_RE = /\b(\d{1,2})[._/-](\d{1,2})[._/-](\d{4})\b/g;
const DOTTED_SHORT_YEAR_RE = /\b(\d{1,2})[._/-](\d{1,2})[._/-](\d{2})\b/g;
const COMPACT_DATE_RE = /\b(20\d{2})(\d{2})(\d{2})\b/g;
const LEADING_PROJECT_PREFIX_RE = /^(\d+)[_\s]([A-Za-z][A-Za-z0-9]*)/;

const NOISE_TOKENS_RE = /\b(?:copy\s+of|draft|final|scan|scanned|tmp|temp|old|new|version|v\d+|rev\d+|updated?|non[- ]?thoroughly)\b/gi;
const EXT_RE = /\.[a-z0-9]{1,8}$/i;

const KNOWN_PLACES = [
  'HUS', 'TYKS', 'FHCRC', 'ONCOSYS', 'CSC', 'LUMI', 'UH', 'Virologia', 'Virology',
  'Pathology', 'Oncology', 'Biobank', 'FIMM', 'EMBL', 'Broad', 'MSK', 'DFCI',
  'Helsinki', 'Turku', 'Tampere', 'Oulu', 'Kuopio',
];

const TYPE_PHRASE_RULES = [
  { pattern: /non[- ]?thoroughly\s+received\s+form/i, label: 'Received Form', typeId: 'received' },
  { pattern: /received\s+form|recieved\s+form/i, label: 'Received Form', typeId: 'received' },
  { pattern: /received\s+(?:letter|memo|mail|correspondence)/i, label: 'Received Correspondence', typeId: 'received' },
  { pattern: /tayttoohje|täyttöohje|fill[- ]?in\s+form|application\s+form/i, label: 'Application Form', typeId: 'application' },
  { pattern: /\bilmoitus\b/i, label: 'Notification', typeId: 'application' },
  { pattern: /luovutuspyyntö|transfer\s+request/i, label: 'Transfer Request', typeId: 'application' },
  { pattern: /riskinarviointi|risk\s+assessment/i, label: 'Risk Assessment', typeId: 'report' },
  { pattern: /billing\s+instruction|invoice\s+instruction/i, label: 'Billing Instruction', typeId: 'billing' },
  { pattern: /purchase\s+order|order\s+form|\bpo\b/i, label: 'Purchase Order', typeId: 'order' },
  { pattern: /standard\s+operating|\bsop\b/i, label: 'SOP', typeId: 'instruction_external' },
  { pattern: /protocol|protokolla|method/i, label: 'Protocol', typeId: 'protocol' },
  { pattern: /meeting\s+(?:notes|minutes)|lab\s+meeting/i, label: 'Meeting Notes', typeId: 'note' },
  { pattern: /instruction|ohje|guide/i, label: 'Instruction', typeId: 'instruction' },
  { pattern: /datasheet|msds|sds/i, label: 'Datasheet', typeId: 'report' },
  { pattern: /onboarding|orientation/i, label: 'Onboarding', typeId: 'instruction' },
];

const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function pad2(n) {
  return String(n).padStart(2, '0');
}

function toIsoDate(year, month, day) {
  const y = Number(year);
  const m = Number(month);
  const d = Number(day);
  if (!y || !m || !d || m < 1 || m > 12 || d < 1 || d > 31) return null;
  return `${y}-${pad2(m)}-${pad2(d)}`;
}

function normalizeDateToken(token) {
  if (!token) return null;
  const iso = token.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (iso) return token;
  const dotted = token.match(/^(\d{1,2})[._/-](\d{1,2})[._/-](\d{4})$/);
  if (dotted) return toIsoDate(dotted[3], dotted[2], dotted[1]);
  return token.trim();
}

function formatDisplayDate(iso) {
  if (!iso) return null;
  const match = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return iso;
  const [, y, m, d] = match;
  const month = MONTHS_SHORT[Number(m) - 1];
  if (!month) return iso;
  return `${Number(d)} ${month} ${y}`;
}

function extractAllDates(text) {
  if (!text) return [];
  const found = new Set();
  const source = String(text);

  for (const match of source.matchAll(ISO_DATE_RE)) {
    const iso = toIsoDate(match[1], match[2], match[3]);
    if (iso) found.add(iso);
  }

  for (const match of source.matchAll(DOTTED_DATE_RE)) {
    const iso = toIsoDate(match[3], match[2], match[1]);
    if (iso) found.add(iso);
  }

  for (const match of source.matchAll(DOTTED_SHORT_YEAR_RE)) {
    const year = Number(match[3]) < 50 ? `20${match[3]}` : `19${match[3]}`;
    const iso = toIsoDate(year, match[2], match[1]);
    if (iso) found.add(iso);
  }

  for (const match of source.matchAll(COMPACT_DATE_RE)) {
    const iso = toIsoDate(match[1], match[2], match[3]);
    if (iso) found.add(iso);
  }

  return Array.from(found).sort();
}

function stripAllDates(text) {
  if (!text) return '';
  return String(text)
    .replace(ISO_DATE_RE, ' ')
    .replace(DOTTED_DATE_RE, ' ')
    .replace(DOTTED_SHORT_YEAR_RE, ' ')
    .replace(COMPACT_DATE_RE, ' ')
    .replace(LEADING_DATE_RE, '')
    .replace(TRAILING_DATE_RE, '')
    .replace(/\s*(?:—|–|-)\s*(?=\s|$)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function stemFilename(filename) {
  return String(filename || '').replace(EXT_RE, '').trim();
}

function fixProjectPrefixes(text) {
  return text.replace(LEADING_PROJECT_PREFIX_RE, (_, num, name) => `${num}-${name}`);
}

function detectTypePhrase(text) {
  for (const rule of TYPE_PHRASE_RULES) {
    if (rule.pattern.test(text)) {
      return { ...rule, match: text.match(rule.pattern)?.[0] || '' };
    }
  }
  return null;
}

function detectPlace(text) {
  const haystack = ` ${text} `;
  for (const place of KNOWN_PLACES) {
    const re = new RegExp(`\\b${place.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
    if (re.test(haystack)) return place;
  }

  const beforeReceived = text.match(/([A-Za-zÀ-ÿ][\wÀ-ÿ.-]{1,24})\s+(?:received|recieved)\b/i);
  if (beforeReceived) {
    const candidate = beforeReceived[1].trim();
    if (!/^(non|the|a|an)$/i.test(candidate)) return polishDisplayTitle(candidate);
  }

  const leadingToken = text.match(/^([A-Z]{2,}(?:\s+[A-Z][a-z]+)?)\b/);
  if (leadingToken && leadingToken[1].length <= 24) return leadingToken[1];

  return null;
}

function buildProfessionalTitle({ placeLabel, typeLabel, remainder }) {
  const cleanRemainder = polishDisplayTitle(
    String(remainder || '')
      .replace(NOISE_TOKENS_RE, ' ')
      .replace(/[_]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim(),
  );

  if (placeLabel && typeLabel) return `${placeLabel} ${typeLabel}`;
  if (typeLabel && cleanRemainder && cleanRemainder.toLowerCase() !== typeLabel.toLowerCase()) {
    return polishDisplayTitle(`${typeLabel} — ${cleanRemainder}`);
  }
  if (typeLabel) return typeLabel;
  if (placeLabel && cleanRemainder) return `${placeLabel} ${cleanRemainder}`;
  return cleanRemainder;
}

/**
 * Parse filename/title into display title + metadata fields.
 */
export function parseDocumentDisplayMetadata(item) {
  const filename = (item?.filename || item?.name || '').trim();
  const rawStored =
    item?.display_title
    || item?.title
    || filename
    || '';
  const rawStem = stemFilename(rawStored) || stemFilename(filename);
  const dates = extractAllDates(rawStem);
  const dateLabel = item?.date_label
    ? normalizeDateToken(item.date_label)
    : (dates[dates.length - 1] || null);

  let working = stripAllDates(rawStem);
  working = fixProjectPrefixes(working);
  working = working.replace(NOISE_TOKENS_RE, ' ').replace(/[_]+/g, ' ').replace(/\s+/g, ' ').trim();

  const typePhrase = detectTypePhrase(working);
  let typeLabel = typePhrase?.label || null;
  let typeId = typePhrase?.typeId || null;

  if (typePhrase?.match) {
    working = working.replace(typePhrase.pattern, ' ').replace(/\s+/g, ' ').trim();
  }

  const placeLabel = item?.place_label || item?.metadata?.place || detectPlace(working) || null;
  if (placeLabel) {
    const placeRe = new RegExp(`\\b${placeLabel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
    working = working.replace(placeRe, ' ').replace(/\s+/g, ' ').trim();
  }

  if (!typeLabel || !typeId) {
    const classified = classifyDocument({
      path: item?.logical_path || item?.path,
      filename,
      title: rawStored,
      category: item?.category,
      subcategory: item?.subcategory,
      document_type: item?.document_type || item?.metadata?.classification?.document_type,
      domain: item?.domain,
    });
    typeId = classified.typeId;
    if (!typeLabel) typeLabel = getDocumentType(typeId).shortLabel;
  }

  const title = buildProfessionalTitle({ placeLabel, typeLabel, remainder: working })
    || polishDisplayTitle(rawStem)
    || polishDisplayTitle(filename)
    || 'Untitled document';

  return {
    title,
    dateLabel,
    dateDisplay: dateLabel ? formatDisplayDate(dateLabel) : null,
    placeLabel,
    typeLabel,
    typeId,
    rawFilename: filename || null,
  };
}

export function parseDateLabelFromFilename(filename) {
  const dates = extractAllDates(stemFilename(filename));
  return dates[dates.length - 1] || null;
}

/**
 * Clean professional title for list cards and preview headers.
 */
export function smartDocumentTitle(item) {
  return parseDocumentDisplayMetadata(item).title;
}

/**
 * Rich second-row metadata for list and preview sublines.
 */
export function documentTitleSubline(item) {
  const meta = parseDocumentDisplayMetadata(item);
  const title = meta.title;

  const chips = [];
  if (meta.placeLabel) {
    chips.push({ key: 'place', label: meta.placeLabel, className: 'sfe-meta-chip sfe-meta-chip--place' });
  }
  if (meta.typeLabel) {
    chips.push({ key: 'type', label: meta.typeLabel, className: 'sfe-meta-chip sfe-meta-chip--type' });
  }
  if (meta.dateDisplay) {
    chips.push({ key: 'date', label: meta.dateDisplay, className: 'sfe-meta-chip sfe-meta-chip--date' });
  }

  const showFilename =
    meta.rawFilename
    && stemFilename(meta.rawFilename).toLowerCase() !== title.toLowerCase()
    && !chips.length;

  if (showFilename) {
    chips.push({ key: 'file', label: meta.rawFilename, className: 'sfe-meta-chip sfe-meta-chip--file' });
  }

  return {
    chips,
    dateLabel: meta.dateDisplay || meta.dateLabel,
    placeLabel: meta.placeLabel,
    typeLabel: meta.typeLabel,
    filename: showFilename ? meta.rawFilename : null,
  };
}
