const LOG_SECTION_RE =
  /(?:^|\n)\s*(?:#{1,3}\s*)?\*{0,2}(?:Project\s+Log|Logbook|Changelog|Updates?|Meeting\s+(?:notes?|log))\*{0,2}\s*:?/i;

const PERSONNEL_LINE_RE =
  /^\s*(?:\*{0,2})?(?:Project\s+(?:lead|members?|leader)|Principal\s+investigator|PI|Members\s+of\s+the\s+project|External\s+collaborators?)\b/i;

const DESCRIPTION_SPLIT_RE = /\s*\*{0,2}Description\s*:\s*\*{0,2}\s*/i;

function stripMarkdownInline(text) {
  return String(text || '')
    .replace(/\[\[([^\]]+)\]\][{(](.*?)[})]/g, '$1')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
    .replace(/\*{1,2}([^*]+)\*{1,2}/g, '$1')
    .trim();
}

function formatIntroParagraphs(text) {
  const paragraphs = [];
  let current = [];
  for (const raw of String(text || '').split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('![')) {
      if (current.length) {
        paragraphs.push(current.join(' '));
        current = [];
      }
      continue;
    }
    if (PERSONNEL_LINE_RE.test(line)) {
      if (current.length) {
        paragraphs.push(current.join(' '));
        current = [];
      }
      continue;
    }
    current.push(stripMarkdownInline(line));
  }
  if (current.length) paragraphs.push(current.join(' '));
  const cleaned = paragraphs.filter(Boolean);
  if (
    cleaned.length > 2
    && cleaned.reduce((sum, p) => sum + p.length, 0) / cleaned.length < 110
  ) {
    return [cleaned.join(' ')];
  }
  return cleaned;
}

function dedupeDescription(text) {
  const parts = text.split(DESCRIPTION_SPLIT_RE);
  if (parts.length <= 1) return text.trim();
  const head = parts[0].trim();
  for (let i = 1; i < parts.length; i += 1) {
    const tail = parts[i].trim();
    if (!tail) continue;
    if (head && tail.toLowerCase().startsWith(head.slice(0, Math.min(head.length, 120)).toLowerCase())) {
      continue;
    }
    if (tail.length > head.length + 40) return head;
  }
  return head;
}

/** Cover-board narrative only — no logs, team lists, or duplicate description tails. */
export function sanitizeCoverSummary(summary) {
  if (!summary) return '';
  let text = String(summary);
  const logCut = text.search(LOG_SECTION_RE);
  if (logCut >= 0) text = text.slice(0, logCut).trim();

  for (const marker of [
    /\n\s*(?:\*{0,2})?Project\s+(?:lead|members?|leader)\b/i,
    /\n\s*(?:\*{0,2})?Members\s+of\s+the\s+project\b/i,
    /\n\s*(?:\*{0,2})?External\s+collaborators?\b/i,
    /\n#{1,3}\s/,
  ]) {
    const hit = text.search(marker);
    if (hit >= 0) text = text.slice(0, hit).trim();
  }

  text = dedupeDescription(text);
  return formatIntroParagraphs(text);
}
