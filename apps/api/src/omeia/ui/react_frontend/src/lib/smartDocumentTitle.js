/**
 * Runtime cleanup for display titles already stored in inventory metadata.
 */

import { polishDisplayTitle } from './polishDisplayText.js';

const LEADING_DATE_RE = /^(?:\d{1,2}[._]\d{1,2}[._]\d{4}|\d{4}-\d{2}-\d{2})\s*/;
const TRAILING_DATE_RE = /\s*(?:—|–|-)\s*(?:\d{4}-\d{2}-\d{2}|\d{1,2}[._]\d{1,2}[._]\d{4})\s*$/;
const DOTTED_DATE_RE = /(?:^|[\s_])(\d{1,2})[._](\d{1,2})[._](\d{4})(?=[\s_.-]|$)/;
const ISO_DATE_RE = /\b(\d{4})-(\d{2})-(\d{2})\b/;
const LEADING_PROJECT_PREFIX_RE = /^(\d+)[_\s]([A-Za-z][A-Za-z0-9]*)/;

function normalizeDateToken(token) {
  const dotted = token.match(DOTTED_DATE_RE);
  if (dotted) {
    const [, d, m, y] = dotted;
    return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
  }
  const iso = token.match(ISO_DATE_RE);
  if (iso) return iso[0];
  return token.trim();
}

export function parseDateLabelFromFilename(filename) {
  if (!filename) return null;
  const dotted = filename.match(DOTTED_DATE_RE);
  if (dotted) {
    const [, d, m, y] = dotted;
    return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
  }
  const iso = filename.match(ISO_DATE_RE);
  if (iso) return iso[0];
  return null;
}

function fixProjectPrefixes(text) {
  return text.replace(LEADING_PROJECT_PREFIX_RE, (_, num, name) => `${num}-${name}`);
}

function stripLeadingDate(text) {
  return text.replace(LEADING_DATE_RE, '').trim();
}

function stripTrailingDate(text) {
  return text.replace(TRAILING_DATE_RE, '').trim();
}

/**
 * Clean a stored display_title for list cards and preview headers.
 */
export function smartDocumentTitle(item) {
  const raw =
    item?.display_title
    || item?.title
    || item?.filename
    || item?.name
    || '';
  if (!raw) return '';

  let title = stripTrailingDate(stripLeadingDate(raw));
  title = fixProjectPrefixes(title);

  // Collapse duplicated date fragments left in the middle segment
  title = title.replace(
    /\s*(?:—|–|-)\s*\d{1,2}[._]\d{1,2}[._]\d{4}\s+/,
    ' ',
  ).replace(/\s+/g, ' ').trim();

  title = polishDisplayTitle(title);

  return title || polishDisplayTitle(raw.trim());
}

/**
 * Second-row metadata: small date + optional filename.
 */
export function documentTitleSubline(item) {
  const filename = (item?.filename || item?.name || '').trim() || null;
  const dateLabel =
    item?.date_label
    || parseDateLabelFromFilename(filename)
    || parseDateLabelFromFilename(item?.display_title)
    || null;

  const showFilename =
    filename
    && smartDocumentTitle(item).toLowerCase() !== filename.toLowerCase();

  return {
    filename: showFilename ? filename : null,
    dateLabel: dateLabel ? normalizeDateToken(dateLabel) : null,
  };
}
