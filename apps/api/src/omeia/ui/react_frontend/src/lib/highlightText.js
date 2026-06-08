/**
 * Highlight query tokens in snippet text for unified search UI.
 */

const TOKEN_RE = /[a-z0-9\u00c0-\uffff]{2,}/gi;

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function extractHighlightTokens(query) {
  const raw = String(query || '').trim();
  if (!raw) return [];
  const seen = new Set();
  const tokens = [];
  for (const match of raw.matchAll(TOKEN_RE)) {
    const tok = match[0].toLowerCase();
    if (tok.length < 2 || seen.has(tok)) continue;
    seen.add(tok);
    tokens.push(tok);
  }
  return tokens.sort((a, b) => b.length - a.length);
}

/**
 * Split text into segments with highlight flags.
 * @returns {{ text: string, highlight: boolean }[]}
 */
export function splitHighlightedText(text, query) {
  const source = String(text || '');
  if (!source) return [];

  const tokens = extractHighlightTokens(query);
  if (!tokens.length) return [{ text: source, highlight: false }];

  const pattern = new RegExp(`(${tokens.map(escapeRegExp).join('|')})`, 'gi');
  const parts = source.split(pattern).filter((part) => part.length > 0);
  const tokenSet = new Set(tokens);

  return parts.map((part) => ({
    text: part,
    highlight: tokenSet.has(part.toLowerCase()),
  }));
}
