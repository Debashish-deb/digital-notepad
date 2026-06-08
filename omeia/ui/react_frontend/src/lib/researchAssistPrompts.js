/**
 * Grounded copilot prompts for project notebook & decisions workflows.
 */

export function buildNotebookAssistPrompt({ projectCode, userQuestion, entryContext = null }) {
  const entryBlock = entryContext
    ? `\nCurrent notebook entry:\n- Title: ${entryContext.title || '—'}\n- Project: ${entryContext.project_code || projectCode}\n- Content excerpt: ${String(entryContext.content || '').slice(0, 1200)}\n- Conclusions: ${entryContext.conclusions || '—'}\n- Issues: ${entryContext.issues_found || '—'}\n- Next steps: ${entryContext.next_steps || '—'}\n`
    : '';

  return [
    `Help me update the living notebook for research project ${projectCode}.`,
    'Search and ground your answer in: project workspace files, lab documents, notebook/wiki/decision registers, datasets, and the public research knowledge base when relevant.',
    entryBlock,
    `Task: ${userQuestion}`,
    '',
    'Respond in this structure:',
    '**Observations** — factual notes from sources (cite as [1], [2], …)',
    '**Conclusions** — short synthesis',
    '**Issues found** — blockers, QC gaps, or risks',
    '**Next steps** — concrete actions',
    '**Limitations** — what evidence was missing',
    '',
    'Do not invent sample counts or clinical facts. If evidence is thin, say so.',
  ].join('\n');
}

export function buildDecisionsAssistPrompt({
  projectCode,
  userQuestion,
  draft = {},
  priorDecisions = [],
}) {
  const prior = priorDecisions.slice(0, 5).map((d) => `- ${d.title} (${d.decision_date || 'undated'})`).join('\n');
  return [
    `Help me register a formal research decision for project ${projectCode}.`,
    'Ground recommendations in project documents, methods, data notes, notebook entries, prior decisions, and research publications in the corpus.',
    '',
    'Current draft:',
    `- Title: ${draft.title || '(empty)'}`,
    `- Details: ${draft.details || '(empty)'}`,
    `- Rationale: ${draft.rationale || '(empty)'}`,
    prior ? `\nRecent decisions for this project:\n${prior}` : '',
    '',
    `Task: ${userQuestion}`,
    '',
    'Respond in this structure:',
    '**Recommended title** — one line',
    '**Decision details** — what was decided (cite sources as [1], [2])',
    '**Rationale** — why, with evidence',
    '**Alternatives considered** — brief',
    '**Limitations** — uncertainty or missing data',
    '**Suggested next actions** — for the lab notebook or workspace',
  ].join('\n');
}

/** Best-effort parse of structured assistant reply for form autofill. */
export function parseStructuredSections(text) {
  const raw = String(text || '');
  const pick = (labels) => {
    for (const label of labels) {
      const re = new RegExp(
        `(?:\\*\\*|__)?${label}(?:\\*\\*|__)?\\s*[:\\-–]?\\s*([\\s\\S]*?)(?=\\n\\s*(?:\\*\\*|__)?[A-Za-z][^:\\n]{2,40}(?:\\*\\*|__)?\\s*[:\\-–]|$)`,
        'i',
      );
      const m = raw.match(re);
      if (m?.[1]?.trim()) return m[1].trim();
    }
    return '';
  };

  return {
    title: pick(['Recommended title', 'Title']),
    details: pick(['Decision details', 'Details', 'Observations']),
    rationale: pick(['Rationale']),
    conclusions: pick(['Conclusions']),
    issues: pick(['Issues found', 'Issues']),
    nextSteps: pick(['Next steps', 'Suggested next actions']),
    content: pick(['Observations', 'Decision details', 'Details']),
    limitations: pick(['Limitations']),
    raw,
  };
}

export const NOTEBOOK_QUICK_PROMPTS = (projectCode) => [
  `Summarize the latest evidence and open questions for ${projectCode}`,
  `What methods or QC steps are documented for ${projectCode}?`,
  'Draft conclusions and next steps from project files and notebook history',
  'Flag inconsistencies between protocols and project data notes',
];

export const DECISIONS_QUICK_PROMPTS = (projectCode) => [
  `What decisions are already recorded for ${projectCode}?`,
  `Suggest a decision title and rationale for a scope change on ${projectCode}`,
  'Compare antibody panel or assay choices documented in project files',
  'List evidence gaps that should be resolved before locking a decision',
];
