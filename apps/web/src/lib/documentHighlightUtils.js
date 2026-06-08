/**
 * Detect lab-note commitments, plans, and sample-profiling decisions for subtle highlight.
 */

const COMMITMENT_PATTERNS = [
  /\bwe\s+will\b/i,
  /\bwill\s+(?:profile|perform|start|use|add|prepare|exclude|stain|run|analyze|analyse|validate|design|create|complete|finish|proceed|collect|submit|deliver|test|image|section)\b/i,
  /\bplan(?:ned)?\s+to\b/i,
  /\bgoing\s+to\b/i,
  /\baim\s+to\b/i,
  /\bmain\s+goal\b/i,
  /\bduration\s+of\b/i,
  /\bresponsible\s*:/i,
  /\bproject\s+manager\b/i,
  /\bwill\s+be\s+started\b/i,
  /\b(?:till|until)\s+(?:early|mid|late)\b/i,
  /\bprofile\s+\d+\s+samples?\b/i,
  /\bS\d{2,4}\b[^.]{0,120}\b(?:gBRCA|BRCA|progression|PFS|wt)\b/i,
  /\b(?:no\s+progression|progression\s+PFS)\b/i,
  /\bnext\s+steps?\b/i,
  /\baction\s+items?\b/i,
  /\btimeline\s*:/i,
  /\bdeadline\b/i,
  /\bby\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\b/i,
  /\bslides?\s+will\s+be\b/i,
  /\bvalidation\s+of\b/i,
  /\bselected\s+S\d{2,4}\b/i,
];

export function isCommitmentOrPlanText(text) {
  const sample = String(text || '').trim();
  if (sample.length < 10) return false;
  return COMMITMENT_PATTERNS.some((pattern) => pattern.test(sample));
}
