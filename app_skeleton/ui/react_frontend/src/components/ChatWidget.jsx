import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Layers,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
} from 'lucide-react';
import { apiFetch } from '../api/client.js';
import { navigateFromSearchHit, readStashedSearchQuery, stashOmniboxPrefill } from '../utils/searchHits.js';
import AssistantSearchHits from './search/AssistantSearchHits.jsx';
import './search/UnifiedSearch.css';
import AiAssistant3DScene from './AiAssistant3DScene.jsx';
import TaskpadSheet from './TaskpadSheet.jsx';
import { useModuleShellCover } from '../contexts/ModuleShellCoverContext.jsx';
import { useGuiT } from '../i18n/useGuiT.js';

const WELCOME_MESSAGE = {
  id: 'assistant-welcome',
  role: 'assistant',
  content:
    'Hello! I am OMEIA Research Copilot. Ask me about staining methodology, spatial deconvolution parameters, ROI selection, Gate normalization, SPACEStat, Ashlar stitching, Stardist segmentation masks, or indexed lab documents.',
};

function makeMessage(role, content, extra = {}) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
    createdAt: new Date().toISOString(),
    ...extra,
  };
}

function normalizeProjectCode(project) {
  if (typeof project === 'string') return project;
  return project?.project_code || project?.code || project?.id || '';
}

function getDefaultProjects(dbProjects = []) {
  const codes = dbProjects.map(normalizeProjectCode).filter(Boolean);
  if (codes.includes('EyeMT')) return ['EyeMT'];
  if (codes.includes('SPACE')) return ['SPACE'];
  return codes.length ? [codes[0]] : ['EyeMT'];
}

function formatAssistantPayload(data) {
  const answer = data?.answer || 'No answer was returned by the copilot.';
  const sources = Array.isArray(data?.sources) ? data.sources : [];
  const searchHits = Array.isArray(data?.search_hits) ? data.search_hits : [];
  const limitations = Array.isArray(data?.limitations) ? data.limitations.filter(Boolean) : [];

  return {
    content: answer,
    sources,
    searchHits,
    limitations,
    databaseCounts: data?.database_counts || {},
    isSafe: data?.is_safe !== false,
  };
}

function MarkdownLite({ text }) {
  const content = String(text || '');
  const lines = content.split('\n');

  return (
    <div className="chat-rich-text">
      {lines.map((line, index) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return <div key={`space-${index}`} className="chat-rich-spacer" aria-hidden="true" />;
        }

        if (trimmed.startsWith('### ')) {
          return <h3 key={index}>{trimmed.replace(/^###\s+/, '')}</h3>;
        }

        if (trimmed.startsWith('## ')) {
          return <h2 key={index}>{trimmed.replace(/^##\s+/, '')}</h2>;
        }

        if (trimmed.startsWith('- ')) {
          return <p key={index} className="chat-rich-bullet">• {trimmed.slice(2)}</p>;
        }

        return <p key={index}>{line}</p>;
      })}
    </div>
  );
}

function ProjectScopePicker({ projects, selected, onToggle }) {
  const options = projects.length
    ? projects
    : [{ project_code: 'EyeMT' }, { project_code: 'SPACE' }, { project_code: 'KRAS' }];

  return (
    <section className="assistant-scope-panel" aria-label="RAG scope project selection">
      <div className="assistant-scope-panel__header">
        <div>
          <span className="assistant-eyebrow">RAG scope</span>
          <h3>Project memory</h3>
        </div>
        <div className="assistant-scope-count">
          <Layers size={14} aria-hidden="true" />
          {selected.length || 0} active
        </div>
      </div>

      <div className="assistant-project-chip-grid">
        {options.map((project) => {
          const code = normalizeProjectCode(project);
          if (!code) return null;

          const checked = selected.includes(code);

          return (
            <label
              key={code}
              className={`assistant-project-chip${checked ? ' is-active' : ''}`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => onToggle(code)}
              />
              <span>{code}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}

export default function ChatWidget({
  dbProjects = [],
  API_URL,
  onNavigate,
  onSelectProject,
  onOpenSearch,
}) {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selProjs, setSelProjs] = useState(() => getDefaultProjects(dbProjects));

  const projectCodes = useMemo(
    () => dbProjects.map(normalizeProjectCode).filter(Boolean),
    [dbProjects],
  );

  const handleOpenSource = useCallback(
    (nav) => {
      if (onNavigate) navigateFromSearchHit(nav, onNavigate, onSelectProject);
    },
    [onNavigate, onSelectProject],
  );

  const handleAskFollowUp = useCallback((text) => {
    setInput(String(text || '').trim());
  }, []);

  const handleSearchOmnibox = useCallback(
    (term) => {
      const q = String(term || '').trim();
      if (!q) return;
      stashOmniboxPrefill(q);
      onOpenSearch?.(q);
    },
    [onOpenSearch],
  );

  useEffect(() => {
    if (!selProjs.length) {
      setSelProjs(getDefaultProjects(dbProjects));
      return;
    }

    if (!projectCodes.length) return;

    setSelProjs((current) => {
      const stillValid = current.filter((code) => projectCodes.includes(code));
      return stillValid.length ? stillValid : getDefaultProjects(dbProjects);
    });
  }, [dbProjects, projectCodes, selProjs.length]);

  const toggleProject = useCallback((code) => {
    setSelProjs((current) => {
      if (current.includes(code)) {
        const next = current.filter((item) => item !== code);
        return next.length ? next : current;
      }

      return [...current, code];
    });
  }, []);

  const sendQuestion = useCallback(
    async (question, { appendUserMessage = true } = {}) => {
      const textToSend = String(question || '').trim();
      if (!textToSend || loading) return;

      if (appendUserMessage) {
        setMessages((prev) => [...prev, makeMessage('user', textToSend)]);
        setInput('');
      }

      setLoading(true);

      try {
        const data = await apiFetch('/ask', {
          method: 'POST',
          body: {
            question: textToSend,
            project_codes: selProjs,
            mode: 'documentation_only',
          },
        });

        const formatted = formatAssistantPayload(data);

        setMessages((prev) => [
          ...prev,
          makeMessage('assistant', formatted.content, {
            sources: formatted.sources,
            searchHits: formatted.searchHits,
            queryContext: textToSend,
            limitations: formatted.limitations,
            databaseCounts: formatted.databaseCounts,
            isSafe: formatted.isSafe,
          }),
        ]);
      } catch (error) {
        const isAuthError = error?.status === 401;
        const isRoleBlocked = error?.status === 403;

        if (isRoleBlocked) {
          try {
            const searchData = await apiFetch('/ask', {
              method: 'POST',
              body: {
                question: textToSend,
                project_codes: selProjs,
                mode: 'search_only',
              },
            });
            const formatted = formatAssistantPayload(searchData);
            setMessages((prev) => [
              ...prev,
              makeMessage('assistant', formatted.content || 'Search results (no LLM synthesis — editor role required for full copilot).', {
                sources: formatted.sources,
                searchHits: formatted.searchHits,
                queryContext: textToSend,
                limitations: formatted.limitations,
                isSafe: true,
              }),
            ]);
            return;
          } catch {
            /* fall through */
          }
        }

        setMessages((prev) => [
          ...prev,
          makeMessage(
            'assistant',
            isAuthError
              ? 'Your session expired. Please sign in again.'
              : isRoleBlocked
                ? 'Search-only mode unavailable. Ask an editor/admin or use ⌘K platform search.'
                : 'Connection timed out or API offline. You can retry this message without retyping it.',
            {
              isError: true,
              originalQuestion: textToSend,
              errorStatus: error?.status,
            },
          ),
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loading, selProjs],
  );

  useEffect(() => {
    const pending = readStashedSearchQuery();
    if (!pending || pending.length < 2) return;
    try {
      sessionStorage.removeItem('farkki_search_last_query');
    } catch {
      /* ignore */
    }
    sendQuestion(pending, { appendUserMessage: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- omnibox handoff once on mount
  }, []);

  const handleSend = useCallback(
    (event) => {
      event?.preventDefault();
      sendQuestion(input);
    },
    [input, sendQuestion],
  );

  const retryMessage = useCallback(
    (question) => {
      sendQuestion(question, { appendUserMessage: false });
    },
    [sendQuestion],
  );

  const shellCover = useModuleShellCover();
  const { nav, t: guiT } = useGuiT();
  const mainNav = nav.findMain(shellCover?.mainId || 'ai_assistant');
  const MainIcon = mainNav?.icon;

  const heroStats = useMemo(
    () => [
      { label: 'Mode', value: 'RAG' },
      { label: 'Scope', value: `${selProjs.length || 0}` },
      { label: 'Status', value: loading ? 'Thinking' : 'Ready' },
    ],
    [loading, selProjs.length],
  );

  const coverToolbar = shellCover ? (
    <>
      <div className="ai3d-hero__toolbar-meta">
        <p className="ai3d-hero__toolbar-eyebrow">
          {MainIcon ? <MainIcon size={14} aria-hidden /> : <Sparkles size={14} aria-hidden="true" />}
          Lab intelligence
        </p>
      </div>
      <div className="ai3d-hero__toolbar-actions">
        <div className="ai3d-hero__taskpad">
          <TaskpadSheet mainId={shellCover.mainId} subId={shellCover.subId} />
        </div>
        {shellCover.onRefresh ? (
          <button
            type="button"
            className="ai3d-hero__icon-btn"
            onClick={shellCover.onRefresh}
            disabled={shellCover.isRefreshing}
            aria-label={shellCover.isRefreshing ? guiT('common.syncing') : guiT('common.refreshAria')}
            title={shellCover.isRefreshing ? guiT('common.syncing') : guiT('common.refresh')}
          >
            <RefreshCw size={15} className={shellCover.isRefreshing ? 'spin' : undefined} aria-hidden />
          </button>
        ) : null}
      </div>
    </>
  ) : null;

  return (
    <section className="assistant-chat-shell" aria-label="OMEIA AI Lab Assistant">
      <AiAssistant3DScene
        merged
        toolbar={coverToolbar}
        title="OMEIA AI Lab Assistant"
        subtitle="RAG copilot and spatial-biology research interface — indexed protocols, lab knowledge, vector search, project docs, prompt templates, and model registry."
        stats={heroStats}
        compact
        className="ai3d-hero--module-ai"
      />

      <ProjectScopePicker
        projects={dbProjects}
        selected={selProjs}
        onToggle={toggleProject}
      />

      <div className="chat-container assistant-chat-container">
        <div className="chat-messages assistant-chat-messages">
          {messages.map((message) => (
            <article
              key={message.id}
              className={`chat-bubble ${message.role} ${message.isError ? 'error-state' : ''}`}
            >
              <div className="chat-bubble__meta">
                <span>
                  {message.role === 'assistant' ? (
                    <>
                      <Sparkles size={13} aria-hidden="true" />
                      OMEIA
                    </>
                  ) : (
                    'You'
                  )}
                </span>
              </div>

              <MarkdownLite text={message.content} />

              {message.limitations?.length ? (
                <div className="chat-limitations">
                  <AlertTriangle size={13} aria-hidden="true" />
                  <span>{message.limitations.join(' ')}</span>
                </div>
              ) : null}

              <AssistantSearchHits
                hits={message.searchHits}
                sources={message.sources}
                query={message.queryContext || ''}
                onOpenHit={onNavigate ? handleOpenSource : null}
                onAskFollowUp={handleAskFollowUp}
                onSearchOmnibox={onOpenSearch ? handleSearchOmnibox : null}
              />

              {message.isError && message.originalQuestion ? (
                <button
                  type="button"
                  onClick={() => retryMessage(message.originalQuestion)}
                  className="btn btn-sm btn-secondary chat-retry-btn"
                  disabled={loading}
                >
                  <RefreshCw size={13} aria-hidden="true" />
                  Retry message
                </button>
              ) : null}
            </article>
          ))}

          {loading && (
            <article className="chat-bubble assistant assistant-thinking-bubble" aria-live="polite">
              <Loader2 size={15} className="spin" aria-hidden="true" />
              <span>Scanning vector collections, ranking sources, and composing answer…</span>
            </article>
          )}
        </div>

        <form onSubmit={handleSend} className="chat-input-area assistant-chat-input-area">
          <input
            type="text"
            placeholder="Ask about CycIF gating, SPACEStat, Ashlar, StarDist, GeoMx, protocols..."
            className="form-input assistant-chat-input"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={loading}
            aria-label="Ask OMEIA Research Copilot"
          />

          <button
            type="submit"
            className="btn btn-primary assistant-send-btn"
            disabled={loading || !input.trim()}
          >
            {loading ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
            Send
          </button>
        </form>
      </div>
    </section>
  );
}
