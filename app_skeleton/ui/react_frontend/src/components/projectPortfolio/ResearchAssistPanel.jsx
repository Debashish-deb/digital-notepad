import { useCallback, useMemo, useState } from 'react';
import { Loader2, Sparkles, Wand2 } from 'lucide-react';
import { sendChatMessage } from '../../api/chatClient.js';
import AssistantSearchHits from '../search/AssistantSearchHits.jsx';
import { navigateFromSearchHit } from '../../utils/searchHits.js';
import {
  buildDecisionsAssistPrompt,
  buildNotebookAssistPrompt,
  parseStructuredSections,
  DECISIONS_QUICK_PROMPTS,
  NOTEBOOK_QUICK_PROMPTS,
} from '../../utils/researchAssistPrompts.js';
import './ResearchAssistPanel.css';

function formatPayload(data) {
  const showSources = data?.show_sources === true;
  return {
    content: data?.answer || 'No answer returned.',
    sources: showSources && Array.isArray(data?.sources) ? data.sources : [],
    searchHits: showSources && Array.isArray(data?.search_hits) ? data.search_hits : [],
    limitations: Array.isArray(data?.limitations) ? data.limitations.filter(Boolean) : [],
    intent: data?.intent || 'general_chat',
    showSources,
    synthesisMode: data?.synthesis_mode || 'mock',
  };
}

export default function ResearchAssistPanel({
  mode = 'notebook',
  projectCode,
  entryContext = null,
  decisionDraft = {},
  priorDecisions = [],
  onApplySuggestion,
  onNavigate,
  onSelectProject,
}) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [lastQuery, setLastQuery] = useState('');

  const quickPrompts = useMemo(
    () => (mode === 'decisions' ? DECISIONS_QUICK_PROMPTS(projectCode) : NOTEBOOK_QUICK_PROMPTS(projectCode)),
    [mode, projectCode],
  );

  const projectCodes = useMemo(
    () => (projectCode ? [projectCode] : []),
    [projectCode],
  );

  const runAssist = useCallback(
    async (promptText) => {
      const q = String(promptText || '').trim();
      if (!q || loading) return;
      setLoading(true);
      setError(null);
      setLastQuery(q);

      const message =
        mode === 'decisions'
          ? buildDecisionsAssistPrompt({
              projectCode,
              userQuestion: q,
              draft: decisionDraft,
              priorDecisions,
            })
          : buildNotebookAssistPrompt({
              projectCode,
              userQuestion: q,
              entryContext,
            });

      try {
        const data = await sendChatMessage({
          message,
          project_codes: projectCodes,
        });
        setResult(formatPayload(data));
      } catch (err) {
        setError(err?.message || 'Research assist failed');
        setResult(null);
      } finally {
        setLoading(false);
      }
    },
    [mode, projectCode, decisionDraft, priorDecisions, entryContext, projectCodes, loading],
  );

  const handleOpenSource = useCallback(
    (nav) => {
      if (onNavigate) navigateFromSearchHit(nav, onNavigate, onSelectProject);
    },
    [onNavigate, onSelectProject],
  );

  const handleApply = () => {
    if (!result?.content || !onApplySuggestion) return;
    onApplySuggestion(parseStructuredSections(result.content));
  };

  const title = mode === 'decisions' ? 'AI decision assistant' : 'AI notebook assistant';
  const lead =
    mode === 'decisions'
      ? 'Reads project files, notebook history, prior decisions, and research sources to draft grounded decisions.'
      : 'Reads project documents, data notes, SOPs, and prior logs to suggest notebook content.';

  return (
    <aside className="research-assist-panel panel" aria-label={title}>
      <header className="research-assist-panel__header">
        <Sparkles size={16} aria-hidden />
        <div>
          <h4 className="research-assist-panel__title">{title}</h4>
          <p className="text-footnote muted">{lead}</p>
        </div>
      </header>

      <div className="research-assist-panel__chips">
        {quickPrompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="research-assist-panel__chip"
            disabled={loading}
            onClick={() => {
              setQuestion(prompt);
              runAssist(prompt);
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      <form
        className="research-assist-panel__form"
        onSubmit={(e) => {
          e.preventDefault();
          runAssist(question);
        }}
      >
        <textarea
          className="form-textarea research-assist-panel__input"
          rows={3}
          placeholder={
            mode === 'decisions'
              ? 'e.g. Should we exclude batch 2 samples based on QC docs?'
              : 'e.g. Summarize CyCIF QC findings and suggest next steps'
          }
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={loading || !question.trim()}>
          {loading ? <Loader2 size={14} className="spin-inline" /> : <Wand2 size={14} />}
          Ask with sources
        </button>
      </form>

      {error ? <p className="research-assist-panel__error text-footnote">{error}</p> : null}

      {loading && !result ? (
        <p className="text-footnote muted research-assist-panel__status">
          <Loader2 size={14} className="spin-inline" /> Searching documents & synthesizing…
        </p>
      ) : null}

      {result ? (
        <div className="research-assist-panel__result">
          <div className="research-assist-panel__answer">{result.content}</div>
          {result.limitations?.length ? (
            <p className="research-assist-panel__limitations text-footnote muted">
              {result.limitations.join(' ')}
            </p>
          ) : null}
          {result.synthesisMode === 'mock' ? (
            <p className="text-footnote muted">
              Running in mock mode — configure CHAT_LLM_PROVIDER for live grounded answers.
            </p>
          ) : null}
          {(result.sources?.length > 0 || result.searchHits?.length > 0) ? (
            <AssistantSearchHits
              hits={result.searchHits}
              sources={result.sources}
              query={lastQuery}
              onOpenHit={onNavigate ? handleOpenSource : null}
            />
          ) : null}
          {onApplySuggestion ? (
            <button type="button" className="btn btn-secondary btn-sm" onClick={handleApply}>
              Apply suggestion to form
            </button>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}
