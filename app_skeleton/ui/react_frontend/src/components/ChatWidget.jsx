import React, { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Bot,
  Layers,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
  User,
} from 'lucide-react';
import { apiFetch } from '../api/client.js';
import { getChatStatus, sendChatMessage, streamChatMessage } from '../api/chatClient.js';
import {
  navigateFromSearchHit,
  readStashedSearchQuery,
  stashOmniboxPrefill,
  formatChatProviderLabel,
} from '../utils/searchNavigation.js';
import AssistantSearchHits from './search/AssistantSearchHits.jsx';
import './search/UnifiedSearch.css';
import './AiAssistantChat.css';
const AiAssistant3DScene = lazy(() => import('./AiAssistant3DScene.jsx'));
import TaskpadSheet from './TaskpadSheet.jsx';
import { useModuleShellCover } from '../contexts/ModuleShellCoverContext.jsx';
import { useGuiT } from '../i18n/useGuiT.js';

const WELCOME_MESSAGE = {
  id: 'assistant-welcome',
  role: 'assistant',
  isWelcome: true,
  content:
    'Hello — I am **OMEIA Research Copilot**. Ask about staining methodology, spatial deconvolution, ROI selection, Gate normalization, SPACEStat, Ashlar stitching, StarDist masks, or any indexed lab document.',
};

const SUGGESTED_PROMPTS = [
  'How do I install Napari on macOS?',
  'What CycIF gating workflow does the lab use?',
  'Summarize SPACEStat spatial statistics steps',
];

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
  const showSources = data?.show_sources === true;
  const intent = data?.intent || 'general_chat';
  const sources = showSources && Array.isArray(data?.sources) ? data.sources : [];
  const searchHits = showSources && Array.isArray(data?.search_hits) ? data.search_hits : [];
  const limitations = Array.isArray(data?.limitations)
    ? data.limitations.filter(Boolean)
    : [];
  const synthesisMode = data?.synthesis_mode || 'mock';
  const effectiveProvider = data?.effective_provider || data?.provider || 'mock';

  return {
    content: answer,
    sources,
    searchHits,
    limitations,
    intent,
    showSources,
    databaseCounts: data?.database_counts || {},
    isSafe: data?.is_safe !== false,
    provider: effectiveProvider,
    synthesisMode,
    model: data?.model || '',
    fallbackUsed: Boolean(data?.fallback_used),
  };
}

function formatTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function MarkdownLite({ text }) {
  const content = String(text || '');
  const lines = content.split('\n');

  const renderInline = (line) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

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
          return (
            <p key={index} className="chat-rich-bullet">
              <span className="chat-rich-bullet__dot" aria-hidden="true" />
              {renderInline(trimmed.slice(2))}
            </p>
          );
        }

        if (trimmed.startsWith('```')) {
          return null;
        }

        return <p key={index}>{renderInline(line)}</p>;
      })}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="chat-typing-dots" aria-hidden="true">
      <span />
      <span />
      <span />
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
  const [chatProvider, setChatProvider] = useState('mock');
  const [chatModel, setChatModel] = useState('');
  const [chatHealthy, setChatHealthy] = useState(null);
  const [streamEnabled, setStreamEnabled] = useState(false);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const messagesContainerRef = useRef(null);

  const projectCodes = useMemo(
    () => dbProjects.map(normalizeProjectCode).filter(Boolean),
    [dbProjects],
  );

  const scrollToBottom = useCallback((behavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior, block: 'end' });
  }, []);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [input, resizeTextarea]);

  useEffect(() => {
    scrollToBottom(messages.length > 2 ? 'smooth' : 'auto');
  }, [messages, loading, scrollToBottom]);

  const handleOpenSource = useCallback(
    (nav) => {
      if (onNavigate) navigateFromSearchHit(nav, onNavigate, onSelectProject);
    },
    [onNavigate, onSelectProject],
  );

  const handleAskFollowUp = useCallback((text) => {
    setInput(String(text || '').trim());
    textareaRef.current?.focus();
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
    let cancelled = false;
    getChatStatus()
      .then((status) => {
        if (cancelled) return;
        const provider = status?.chat_provider || status?.llm?.provider || 'mock';
        setChatProvider(provider);
        setChatModel(status?.chat_model || status?.llm?.model || '');
        setChatHealthy(status?.llm?.healthy ?? null);
        setStreamEnabled(status?.stream_enabled !== false);
      })
      .catch(() => {
        if (!cancelled) {
          setChatProvider('mock');
          setChatHealthy(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

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

      const assistantMessage = makeMessage('assistant', '', { streaming: true });
      let streamedAssistantId = null;

      try {
        if (streamEnabled) {
          streamedAssistantId = assistantMessage.id;
          setMessages((prev) => [...prev, assistantMessage]);

          let streamedContent = '';
          let streamMeta = {};

          await streamChatMessage({
            message: textToSend,
            project_codes: selProjs,
            onMetadata: (meta) => {
              streamMeta = meta;
              if (meta?.provider) setChatProvider(meta.provider);
            },
            onDelta: (delta) => {
              streamedContent += delta || '';
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === streamedAssistantId
                    ? { ...msg, content: streamedContent }
                    : msg,
                ),
              );
            },
          });

          const formatted = formatAssistantPayload({
            answer: streamedContent,
            ...streamMeta,
          });

          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamedAssistantId
                ? {
                    ...msg,
                    content: formatted.content,
                    sources: formatted.sources,
                    searchHits: formatted.searchHits,
                    queryContext: textToSend,
                    limitations: formatted.limitations,
                    intent: formatted.intent,
                    showSources: formatted.showSources,
                    databaseCounts: formatted.databaseCounts,
                    isSafe: formatted.isSafe,
                    provider: formatted.provider || streamMeta.provider || chatProvider,
                    streaming: false,
                  }
                : msg,
            ),
          );
          return;
        }

        const data = await sendChatMessage({
          message: textToSend,
          project_codes: selProjs,
        });

        const formatted = formatAssistantPayload(data);
        if (data?.effective_provider || data?.provider) {
          setChatProvider(data.effective_provider || data.provider);
        }
        if (data?.model) setChatModel(data.model);

        setMessages((prev) => [
          ...prev,
          makeMessage('assistant', formatted.content, {
            sources: formatted.sources,
            searchHits: formatted.searchHits,
            queryContext: textToSend,
            limitations: formatted.limitations,
            intent: formatted.intent,
            showSources: formatted.showSources,
            databaseCounts: formatted.databaseCounts,
            isSafe: formatted.isSafe,
            provider: formatted.provider || chatProvider,
            synthesisMode: formatted.synthesisMode,
            model: formatted.model,
          }),
        ]);
      } catch (error) {
        if (streamedAssistantId) {
          setMessages((prev) => prev.filter((msg) => msg.id !== streamedAssistantId));
        }
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
              makeMessage('assistant', formatted.content || 'Search results (no LLM synthesis — sign in with an approved account for full copilot).', {
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
                ? 'Chat unavailable for this account. Ask an admin or use ⌘K platform search.'
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
    [loading, selProjs, chatProvider, streamEnabled],
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

  const handleKeyDown = useCallback(
    (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendQuestion(input);
      }
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

  const providerLabel = useMemo(() => formatChatProviderLabel(chatProvider), [chatProvider]);

  const providerBadge = useMemo(() => {
    const mode = chatProvider === 'mock' ? 'mock' : 'live';
    const label = formatChatProviderLabel(chatProvider);
    if (chatModel && chatProvider !== 'mock') {
      const shortModel = chatModel.replace(/^gemini-/, '').replace(/-flash.*/, '');
      return `${label} · ${shortModel} (${mode})`;
    }
    return `${label} (${mode})`;
  }, [chatModel, chatProvider, providerLabel]);

  const heroStats = useMemo(
    () => [
      { label: 'Mode', value: 'RAG' },
      { label: 'LLM', value: providerBadge },
      { label: 'Scope', value: `${selProjs.length || 0}` },
      { label: 'Status', value: loading ? 'Thinking' : chatHealthy === false ? 'Offline' : 'Ready' },
    ],
    [loading, providerBadge, selProjs.length, chatHealthy],
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

  const showSuggestions = messages.length === 1 && messages[0]?.isWelcome && !loading;

  return (
    <section className="assistant-chat-shell" aria-label="OMEIA AI Lab Assistant">
      <Suspense fallback={<div className="ai3d-hero-skeleton" aria-hidden />}>
        <AiAssistant3DScene
          merged
          toolbar={coverToolbar}
          title="OMEIA AI Lab Assistant"
          subtitle="RAG copilot and spatial-biology research interface — indexed protocols, lab knowledge, vector search, project docs, prompt templates, and model registry."
          stats={heroStats}
          compact
          className="ai3d-hero--module-ai"
        />
      </Suspense>

      <ProjectScopePicker
        projects={dbProjects}
        selected={selProjs}
        onToggle={toggleProject}
      />

      <div className="chat-container assistant-chat-container">
        <div
          ref={messagesContainerRef}
          className="chat-messages assistant-chat-messages"
          role="log"
          aria-live="polite"
          aria-relevant="additions"
        >
          {messages.map((message) => (
            <article
              key={message.id}
              className={[
                'chat-message-row',
                message.role,
                message.isError ? 'is-error' : '',
                message.isWelcome ? 'is-welcome' : '',
              ].filter(Boolean).join(' ')}
            >
              <div
                className={`chat-avatar chat-avatar--${message.role}`}
                aria-hidden="true"
              >
                {message.role === 'assistant' ? <Bot size={18} /> : <User size={18} />}
              </div>

              <div
                className={`chat-bubble ${message.role} ${message.isError ? 'error-state' : ''} ${message.isWelcome ? 'welcome-state' : ''}`}
              >
                <div className="chat-bubble__meta">
                  <span className="chat-bubble__sender">
                    {message.role === 'assistant' ? (
                      <>
                        <Sparkles size={12} aria-hidden="true" />
                        OMEIA Copilot
                      </>
                    ) : (
                      'You'
                    )}
                  </span>
                  <span className="chat-bubble__meta-end">
                    {message.role === 'assistant' && !message.isError ? (
                      <span
                        className={`assistant-chat-provider-pill${
                          (message.synthesisMode || message.provider || chatProvider) === 'mock'
                          || message.synthesisMode === 'mock'
                            ? ' is-mock'
                            : ' is-live'
                        }`}
                        title={`Synthesis: ${message.synthesisMode || 'unknown'} · Provider: ${formatChatProviderLabel(message.provider || chatProvider)}`}
                      >
                        {formatChatProviderLabel(message.provider || chatProvider)}
                        {message.synthesisMode === 'mock' ? ' · mock' : message.synthesisMode === 'live' ? ' · live' : ''}
                      </span>
                    ) : null}
                    {message.createdAt && !message.isWelcome ? (
                      <time className="chat-bubble__time" dateTime={message.createdAt}>
                        {formatTime(message.createdAt)}
                      </time>
                    ) : null}
                  </span>
                </div>

                <MarkdownLite text={message.content} />

                {message.limitations?.length ? (
                  <div className="chat-limitations">
                    <AlertTriangle size={13} aria-hidden="true" />
                    <span>{message.limitations.join(' ')}</span>
                  </div>
                ) : null}

                {message.showSources !== false
                  && message.intent !== 'smalltalk'
                  && (message.sources?.length > 0 || message.searchHits?.length > 0) ? (
                  <AssistantSearchHits
                    hits={message.searchHits}
                    sources={message.sources}
                    query={message.queryContext || ''}
                    onOpenHit={onNavigate ? handleOpenSource : null}
                    onAskFollowUp={handleAskFollowUp}
                    onSearchOmnibox={onOpenSearch ? handleSearchOmnibox : null}
                  />
                ) : null}

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
              </div>
            </article>
          ))}

          {showSuggestions ? (
            <div className="chat-suggestions" aria-label="Suggested prompts">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="chat-suggestion-chip"
                  onClick={() => sendQuestion(prompt)}
                  disabled={loading}
                >
                  {prompt}
                </button>
              ))}
            </div>
          ) : null}

          {loading && !messages.some((message) => message.streaming) && (
            <article className="chat-message-row assistant assistant-thinking-row" aria-live="polite">
              <div className="chat-avatar chat-avatar--assistant" aria-hidden="true">
                <Bot size={18} />
              </div>
              <div className="chat-bubble assistant assistant-thinking-bubble">
                <TypingIndicator />
                <span>Composing answer…</span>
              </div>
            </article>
          )}

          <div ref={messagesEndRef} className="chat-scroll-anchor" aria-hidden="true" />
        </div>

        <form onSubmit={handleSend} className="chat-input-area assistant-chat-input-area">
          <div className="assistant-chat-input-wrap">
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder="Ask about CycIF gating, SPACEStat, Ashlar, StarDist, GeoMx, protocols…"
              className="form-input assistant-chat-input"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              aria-label="Ask OMEIA Research Copilot"
            />
            <span className="assistant-chat-input-hint">Enter to send · Shift+Enter for newline</span>
          </div>

          <button
            type="submit"
            className="btn btn-primary assistant-send-btn"
            disabled={loading || !input.trim()}
            aria-label="Send message"
          >
            {loading ? (
              <Loader2 size={18} className="spin" aria-hidden="true" />
            ) : (
              <Send size={18} aria-hidden="true" />
            )}
          </button>
        </form>
      </div>
    </section>
  );
}
