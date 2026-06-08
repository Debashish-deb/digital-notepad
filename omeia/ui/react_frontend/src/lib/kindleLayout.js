/**
 * Readable layout for extracted lab documents.
 * Join broken lines → sections → grouped info cards (not one card per line).
 */

const MAX_PARAGRAPH_CHARS = 650;

const SENTENCE_END_RE = /[.!?…]["')\]]?\s*$/;

const SECTION_TITLE_RE =
  /^(attention to|billing addresses|billing and delivery|electronic invoicing address|invoice information|delivery information|new|customs invoice|usda import|onboarding|general guidelines|wet lab|safety|keys|key details|background aims?|panel composition|material and methods|results|conclusions|acknowledgements?|references|speaker notes)$/i;

const PAGE_MARKER_RE = /^Page\s+\d+\s+of\s+\d+$/i;

const PROSE_WORD_RE =
  /\b(the|for|that|with|must|should|please|have|will|can|from|your|our|found|information|following|located|either|learn|them|when|after|before|also|into|about)\b/i;

function splitInlineBullets(line) {
  const raw = String(line || '').trim();
  if (!raw.includes('•')) return [raw];

  const parts = raw.split(/\s*•\s*/).map((part) => part.trim()).filter(Boolean);
  if (parts.length <= 1) return [raw];

  return parts.map((part, index) => (index === 0 && !raw.startsWith('•') ? part : `• ${part}`));
}

function normalizeLines(rawText) {
  const lines = [];
  for (const line of String(rawText || '').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || /^\d{1,3}$/.test(trimmed) || PAGE_MARKER_RE.test(trimmed)) continue;
    for (const part of splitInlineBullets(trimmed)) {
      if (part) lines.push(part);
    }
  }
  return lines;
}

function letterRatioDigits(line) {
  const digits = (line.match(/\d/g) || []).length;
  return digits / Math.max(line.length, 1);
}

function isFieldLabelOnly(line) {
  if (line.length > 72 || !/:\s*$/.test(line)) return false;
  const title = line.replace(/:+\s*$/, '').trim();
  if (PROSE_WORD_RE.test(title)) return false;
  if (title.split(/\s+/).length > 6) return false;
  if (!/^[A-ZÄÖÅÜ0-9]/.test(title)) return false;
  return true;
}

function inlineField(line) {
  const m = line.match(/^(.{2,72}?):\s+(.+)$/);
  if (!m) return null;
  const label = m[1].trim();
  let value = m[2].trim();
  let trailing = null;

  const urlTail = value.match(/^(https?:\/\/\S+)(?:\s+(.+))?$/i);
  if (urlTail) {
    value = urlTail[1];
    trailing = urlTail[2]?.trim() || null;
  }

  return { label, value, trailing };
}

/** Split "KEYS https://…" or "Label: URL trailing prose" into separate layout lines. */
function expandCompoundLines(lines) {
  const out = [];
  for (const line of lines) {
    const headingUrl = line.match(/^([A-Z][A-Za-z\s]{1,24}?)\s+(https?:\/\/.+)$/);
    if (headingUrl && headingUrl[1].trim().split(/\s+/).length <= 3 && headingUrl[1].trim().length <= 24) {
      out.push(headingUrl[1].trim());
      const rest = headingUrl[2].trim();
      const urlOnly = rest.match(/^(https?:\/\/\S+)(?:\s+(.+))?$/i);
      if (urlOnly) {
        out.push(urlOnly[1]);
        if (urlOnly[2]?.trim()) out.push(urlOnly[2].trim());
      } else {
        out.push(rest);
      }
      continue;
    }

    const inline = inlineField(line);
    if (inline?.trailing) {
      out.push(`${inline.label}: ${inline.value}`);
      out.push(inline.trailing);
      continue;
    }

    out.push(line);
  }
  return out;
}

function looksLikeUrlContinuation(line) {
  return (
    /^https?:\/\//i.test(line) ||
    /^\/[\w./%-]+/.test(line) ||
    /^[\w.-]+\/[\w./%-]*/.test(line) ||
    /^and-[\w./%-]+/i.test(line)
  );
}

function isSectionTitle(line) {
  const raw = String(line || '').trim();
  if (/^#{1,6}\s+\S/.test(raw)) return true;

  const t = raw.replace(/^#{1,6}\s+/, '').trim();
  if (!t || t.length > 80) return false;
  if (PAGE_MARKER_RE.test(t)) return false;
  if (letterRatioDigits(t) > 0.28) return false;
  if (SECTION_TITLE_RE.test(t.replace(/:+\s*$/, ''))) return true;

  // Standalone colon header: "Safety:", "Affiliation and personnel issues:"
  if (/:\s*$/.test(t)) {
    const title = t.replace(/:+\s*$/, '').trim();
    if (title.length < 3 || title.length > 52) return false;
    if (/[.!?]$/.test(title)) return false;
    if (PROSE_WORD_RE.test(title)) return false;
    if (title.split(/\s+/).length > 7) return false;
    if (!/^[A-ZÄÖÅÜ0-9]/.test(title)) return false;
    return true;
  }

  if (/[.!?]$/.test(t)) return false;
  if (inlineField(line)) return false;
  if (!/^[A-ZÄÖÅÜ#0-9]/.test(t)) return false;

  const letters = t.replace(/[^A-Za-zÄÖÜäöüÅå]/g, '');
  const words = t.split(/\s+/).filter((w) => /[A-Za-zÄÖÜäöüÅå]{2,}/i.test(w));

  // ALL CAPS headings (incl. short ones like "Keys", "WET LAB")
  if (letters.length >= 3 && letters === letters.toUpperCase() && words.length >= 1 && words.length <= 10) {
    return t.length <= 64;
  }

  // Known billing / org section labels
  if (words.length >= 2 && letters.length >= 12 && letters === letters.toUpperCase()) {
    return true;
  }

  // Short title-case headers (e.g. "Biomedicum Address", "Lab credit card orders")
  if (
    words.length >= 2 &&
    words.length <= 5 &&
    t.length <= 48 &&
    /^[A-Z]/.test(t) &&
    !PROSE_WORD_RE.test(t)
  ) {
    const titleWords = t.split(/\s+/);
    const capitalized = titleWords.filter((w) => /^[A-ZÄÖÅÜ]/.test(w)).length;
    if (capitalized >= Math.ceil(titleWords.length * 0.6)) return true;
  }

  return false;
}

/** Org / department headers only — never prose or form field labels. */
function isCardTitle(line) {
  if (isSectionTitle(line) || isFieldLabelOnly(line)) return false;
  if (inlineField(line)) return false;
  if (line.length < 14 || line.length > 58) return false;
  if (/[.!?]$/.test(line)) return false;
  if (/\b(muuttuu|changes|until|please|voisi|tulee|should|have|hello|hei)\b/i.test(line)) {
    return false;
  }

  if (/^Färkkilä Lab$/i.test(line)) return true;
  if (/^International suppliers$/i.test(line)) return true;
  if (/^HUS NaiS$/i.test(line)) return true;
  if (/^University of Helsinki$/i.test(line)) return true;
  if (/^Customs Invoice$/i.test(line)) return true;
  if (/^USDA Statement$/i.test(line)) return true;
  if (/^Laskutusohjeet$/i.test(line)) return true;
  if (/^My billing address/i.test(line)) return true;
  if (/^HUS\b/i.test(line)) return true;
  if (/^HYKS\b/i.test(line)) return true;
  if (/^Joint Authority/i.test(line)) return true;
  if (/Kuntayhtymä/i.test(line)) return true;
  if (/Syöpäkeskus/i.test(line)) return true;
  if (/Department of/i.test(line)) return true;
  return false;
}

function isListLine(line) {
  return /^[-*•]\s?/.test(line) || /^\d+\.\s/.test(line);
}

function isDivider(line) {
  return /^[*_\-=]{3,}$/.test(line);
}

function looksLikeProse(line) {
  if (line.length > 95) return true;
  if (SENTENCE_END_RE.test(line)) return true;
  if (/\b(the|and|for|that|with|must|should|please|jos|että|tulee|voidaan|haluan|klikkaa|make sure|located|opening hours)\b/i.test(line)) {
    return true;
  }
  return false;
}

function shouldJoinLines(prev, next) {
  if (!prev || !next) return false;
  if (prev.includes('•') || next.includes('•')) return false;
  if (isSectionTitle(next) || isSectionTitle(prev)) return false;
  if (isCardTitle(next) || isCardTitle(prev)) return false;
  if (isFieldLabelOnly(next) || isFieldLabelOnly(prev)) return false;
  if (isListLine(next) || isListLine(prev)) return false;
  if (isDivider(next) || isDivider(prev)) return false;

  const inlineNext = inlineField(next);
  const inlinePrev = inlineField(prev);
  if (inlineNext && !/^https?:\/\//i.test(inlineNext.value)) return false;
  if (inlinePrev) return false;

  if (prev.endsWith('-')) return true;
  if (looksLikeUrlContinuation(next)) return true;
  if (/https?:\/\/[^\s]*$/i.test(prev) || /\/[\w-]*$/i.test(prev)) return true;

  if (SENTENCE_END_RE.test(prev)) return false;
  if (/^[a-z(0-9/]/.test(next)) return true;
  if (next.length < 72 && !isCardTitle(next)) return true;
  if (prev.length < 100 && !SENTENCE_END_RE.test(prev)) return true;
  return false;
}

function mergeLines(prev, next) {
  if (prev.endsWith('-')) {
    return `${prev}${next}`.replace(/\s+/g, ' ').trim();
  }
  if (looksLikeUrlContinuation(next) && !/\s$/.test(prev)) {
    const gap = next.startsWith('/') || /^https?:\/\//i.test(next) ? '' : ' ';
    return `${prev}${gap}${next}`.replace(/\s+/g, ' ').trim();
  }
  return `${prev} ${next}`.replace(/\s+/g, ' ').trim();
}

export function joinContinuationLines(lines) {
  if (!lines.length) return [];
  const out = [];
  let buf = lines[0];

  for (let i = 1; i < lines.length; i += 1) {
    const next = lines[i];
    if (shouldJoinLines(buf, next)) {
      buf = mergeLines(buf, next);
    } else {
      out.push(buf);
      buf = next;
    }
  }
  out.push(buf);
  return out;
}

function splitLongParagraph(text) {
  const t = (text || '').replace(/\s+/g, ' ').trim();
  if (!t) return [];
  if (t.length <= MAX_PARAGRAPH_CHARS) return [t];

  // eslint-disable-next-line no-useless-escape -- `[` is literal inside the lookahead character class
  const parts = t.split(/(?<=[.!?…])\s+(?=[A-ZÄÖÅÜ"“(\[])/);
  const chunks = [];
  let buf = '';

  for (const part of parts) {
    const next = buf ? `${buf} ${part}` : part;
    if (next.length > MAX_PARAGRAPH_CHARS && buf) {
      chunks.push(buf.trim());
      buf = part;
    } else {
      buf = next;
    }
  }
  if (buf.trim()) chunks.push(buf.trim());
  return chunks.length ? chunks : [t];
}

/** Break prose around URLs so links wrap on their own line instead of stretching the paragraph. */
function pushProseEntries(card, prose) {
  const parts = String(prose || '')
    .replace(/\s+/g, ' ')
    .trim()
    .split(/(https?:\/\/\S+)/i)
    .map((part) => part.trim())
    .filter(Boolean);

  if (!parts.length) return;

  let textBuf = '';
  const flushText = () => {
    if (!textBuf.trim()) return;
    splitLongParagraph(textBuf.trim()).forEach((p) => {
      card.entries.push({ type: 'paragraph', text: p });
    });
    textBuf = '';
  };

  for (const part of parts) {
    if (/^https?:\/\//i.test(part)) {
      flushText();
      const urlMatch = part.match(/^(https?:\/\/[^\s),.;:]+)([),.;:]+)?$/i);
      const url = urlMatch?.[1] || part;
      const trailing = urlMatch?.[2] || '';
      card.entries.push({ type: 'url', url });
      if (trailing) textBuf = trailing;
      continue;
    }
    textBuf = textBuf ? `${textBuf} ${part}` : part;
  }
  flushText();
}

function createCard(title = null) {
  return { type: 'card', title, entries: [] };
}

function collectFieldValues(lines, startIdx) {
  const values = [];
  let i = startIdx;
  while (i < lines.length) {
    const line = lines[i];
    if (
      isSectionTitle(line) ||
      isCardTitle(line) ||
      isFieldLabelOnly(line) ||
      isListLine(line) ||
      isDivider(line)
    ) {
      break;
    }
    if (looksLikeProse(line) && values.length >= 2) break;
    values.push(line);
    i += 1;
    if (values.length >= 12) break;
  }
  return { values, nextIdx: i };
}

function collectLineGroup(lines, startIdx) {
  const items = [];
  let i = startIdx;
  while (i < lines.length) {
    const line = lines[i];
    if (
      isSectionTitle(line) ||
      isCardTitle(line) ||
      isFieldLabelOnly(line) ||
      isListLine(line) ||
      isDivider(line) ||
      looksLikeProse(line) ||
      inlineField(line)
    ) {
      break;
    }
    items.push(line);
    i += 1;
  }
  return { items, nextIdx: i };
}

function absorbLinesIntoCard(card, lines) {
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    if (isDivider(line)) {
      card.entries.push({ type: 'divider' });
      i += 1;
      continue;
    }

    if (isListLine(line)) {
      const items = [line.replace(/^[-*•]\s*|\d+\.\s*/, '').trim()];
      i += 1;
      while (i < lines.length && isListLine(lines[i])) {
        items.push(lines[i].replace(/^[-*•]\s*|\d+\.\s*/, '').trim());
        i += 1;
      }
      card.entries.push({ type: 'list', items });
      continue;
    }

    const inline = inlineField(line);
    if (inline) {
      const isUrlValue = /^https?:\/\//i.test(inline.value);
      card.entries.push({
        type: isUrlValue ? 'link-field' : 'field',
        label: inline.label,
        values: [inline.value],
        url: isUrlValue ? inline.value : undefined,
      });
      i += 1;
      continue;
    }

    if (isFieldLabelOnly(line)) {
      const label = line.replace(/:+\s*$/, '');
      const { values, nextIdx } = collectFieldValues(lines, i + 1);
      if (!values.length && i + 1 < lines.length && isFieldLabelOnly(lines[i + 1])) {
        card.entries.push({ type: 'label', text: label });
      } else {
        card.entries.push({
          type: 'field',
          label,
          values: values.length ? values : undefined,
        });
      }
      i = nextIdx;
      continue;
    }

    if (/^https?:\/\/\S+$/i.test(line)) {
      card.entries.push({ type: 'url', url: line });
      i += 1;
      continue;
    }

    if (looksLikeProse(line)) {
      let prose = line;
      i += 1;
      while (
        i < lines.length &&
        looksLikeProse(lines[i]) &&
        !isCardTitle(lines[i]) &&
        !isFieldLabelOnly(lines[i]) &&
        !isSectionTitle(lines[i])
      ) {
        prose = mergeLines(prose, lines[i]);
        i += 1;
        if (prose.length > MAX_PARAGRAPH_CHARS) break;
      }
      pushProseEntries(card, prose);
      continue;
    }

    const { items, nextIdx } = collectLineGroup(lines, i);
    if (items.length) {
      card.entries.push({ type: 'lines', items });
      i = nextIdx;
      continue;
    }

    i += 1;
  }
}

function buildSectionBlocks(lines) {
  const card = createCard(null);
  absorbLinesIntoCard(card, lines);
  return card.entries.length ? [card] : [];
}

function wrapInSections(lines) {
  const sections = [];
  let current = { type: 'section', title: null, blocks: [] };
  let buffer = [];

  const flushBuffer = () => {
    if (!buffer.length) return;
    current.blocks.push(...buildSectionBlocks(buffer));
    buffer = [];
  };

  for (const line of lines) {
    if (isSectionTitle(line)) {
      flushBuffer();
      if (current.title || current.blocks.length) sections.push(current);
      current = {
        type: 'section',
        title: line.replace(/^#{1,6}\s+/, '').replace(/:+\s*$/, '').trim(),
        blocks: [],
      };
      continue;
    }
    buffer.push(line);
  }

  flushBuffer();
  if (current.title || current.blocks.length) sections.push(current);
  return sections.length ? sections : [{ type: 'section', title: null, blocks: buildSectionBlocks(lines) }];
}

export function buildKindleBlocks(rawText) {
  const paragraphs = String(rawText || '')
    .replace(/\r\n/g, '\n')
    .replace(/\n(#{1,6}\s)/g, '\n\n$1')
    .split(/\n\s*\n/);

  const joined = [];
  for (const para of paragraphs) {
    const lines = expandCompoundLines(normalizeLines(para));
    if (!lines.length) continue;
    joined.push(...joinContinuationLines(lines));
  }

  return wrapInSections(joined);
}

export function chunkProseParagraphs(text) {
  return splitLongParagraph(text);
}
