import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Bot,
  ChevronDown,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
  User,
} from 'lucide-react';
import { apiFetch } from '../api/client.js';
import { getChatStatus, sendChatMessage, streamChatMessage } from '../api/chatClient.js';
import {
  fetchAgentCategories,
  readStoredCategory,
  readStoredMode,
  sendCategoryChat,
  setDebugModelsEnabled,
  isDebugModelsEnabled,
  writeStoredCategory,
  writeStoredMode,
} from '../api/agentCategoryClient.js';
import { FALLBACK_AGENT_CATEGORIES } from '../data/agentCategoryFallback.js';
import { getLibraryScopeContext } from '../utils/documentExplorerPresets.js';
import AgentCategorySelector from './AgentCategorySelector.jsx';
import { useChatAutoScroll } from '../hooks/useChatAutoScroll.js';
import { revealTextProgressively } from '../utils/chatMotion.js';
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

const CHAT_MODEL_STORAGE_KEY = 'omeia.chat.modelKey';

function parseModelKey(key) {
  const raw = String(key || '').trim();
  const idx = raw.indexOf(':');
  if (idx <= 0) return { provider: null, model: null };
  return { provider: raw.slice(0, idx), model: raw.slice(idx + 1) };
}

function readStoredModelKey() {
  try {
    return localStorage.getItem(CHAT_MODEL_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

function writeStoredModelKey(key) {
  try {
    if (key) localStorage.setItem(CHAT_MODEL_STORAGE_KEY, key);
  } catch {
    /* ignore */
  }
}

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

function renderInlineMarkdown(text, keyPrefix = 'inline') {
  const raw = String(text || '');
  const tokens = raw.split(/(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|`[^`]+`|https?:\/\/[^\s)]+)/g);
  return tokens.map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <a key={key} href={linkMatch[2]} target="_blank" rel="noopener noreferrer" className="chat-rich-link">
          {linkMatch[1]}
        </a>
      );
    }
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={key} className="chat-rich-code-inline">{part.slice(1, -1)}</code>;
    }
    if (/^https?:\/\//.test(part)) {
      return (
        <a key={key} href={part} target="_blank" rel="noopener noreferrer" className="chat-rich-link">
          {part}
        </a>
      );
    }
    return part;
  });
}

function parseMarkdownBlocks(content) {
  const lines = String(content || '').split('\n');
  const blocks = [];
  let i = 0;
  let listItems = null;
  let listType = null;
  let codeLines = null;
  let codeLang = '';

  const flushList = () => {
    if (listItems?.length) {
      blocks.push({ type: listType, items: listItems });
    }
    listItems = null;
    listType = null;
  };

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith('```')) {
      flushList();
      if (codeLines === null) {
        codeLang = trimmed.slice(3).trim();
        codeLines = [];
        i += 1;
        continue;
      }
      blocks.push({ type: 'code', lang: codeLang, content: codeLines.join('\n') });
      codeLines = null;
      codeLang = '';
      i += 1;
      continue;
    }

    if (codeLines !== null) {
      codeLines.push(line);
      i += 1;
      continue;
    }

    if (!trimmed) {
      flushList();
      blocks.push({ type: 'space' });
      i += 1;
      continue;
    }

    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      flushList();
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i].trim());
        i += 1;
      }
      const rows = tableLines
        .filter((row) => !/^\|[\s\-:|]+\|$/.test(row))
        .map((row) => row.slice(1, -1).split('|').map((cell) => cell.trim()));
      if (rows.length) blocks.push({ type: 'table', rows });
      continue;
    }

    const numbered = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numbered) {
      if (listType !== 'ol') {
        flushList();
        listItems = [];
        listType = 'ol';
      }
      listItems.push(numbered[2]);
      i += 1;
      continue;
    }

    if (trimmed.startsWith('- ')) {
      if (listType !== 'ul') {
        flushList();
        listItems = [];
        listType = 'ul';
      }
      listItems.push(trimmed.slice(2));
      i += 1;
      continue;
    }

    flushList();
    if (trimmed.startsWith('### ')) {
      blocks.push({ type: 'h3', text: trimmed.slice(4) });
    } else if (trimmed.startsWith('## ')) {
      blocks.push({ type: 'h2', text: trimmed.slice(3) });
    } else {
      blocks.push({ type: 'p', text: line });
    }
    i += 1;
  }

  flushList();
  if (codeLines !== null) {
    blocks.push({ type: 'code', lang: codeLang, content: codeLines.join('\n') });
  }
  return blocks;
}

function MarkdownLite({ text }) {
  const blocks = useMemo(() => parseMarkdownBlocks(text), [text]);

  return (
    <div className="chat-rich-text">
      {blocks.map((block, index) => {
        if (block.type === 'space') {
          return <div key={`space-${index}`} className="chat-rich-spacer" aria-hidden="true" />;
        }
        if (block.type === 'h2') {
          return <h2 key={index}>{renderInlineMarkdown(block.text, `h2-${index}`)}</h2>;
        }
        if (block.type === 'h3') {
          return <h3 key={index}>{renderInlineMarkdown(block.text, `h3-${index}`)}</h3>;
        }
        if (block.type === 'p') {
          return <p key={index}>{renderInlineMarkdown(block.text, `p-${index}`)}</p>;
        }
        if (block.type === 'ul') {
          return (
            <ul key={index} className="chat-rich-list">
              {block.items.map((item, j) => (
                <li key={j}>{renderInlineMarkdown(item, `ul-${index}-${j}`)}</li>
              ))}
            </ul>
          );
        }
        if (block.type === 'ol') {
          return (
            <ol key={index} className="chat-rich-list chat-rich-list--numbered">
              {block.items.map((item, j) => (
                <li key={j}>{renderInlineMarkdown(item, `ol-${index}-${j}`)}</li>
              ))}
            </ol>
          );
        }
        if (block.type === 'code') {
          return (
            <pre key={index} className="chat-rich-code-block">
              <code>{block.content}</code>
            </pre>
          );
        }
        if (block.type === 'table') {
          const [head, ...body] = block.rows;
          return (
            <div key={index} className="chat-rich-table-wrap">
              <table className="chat-rich-table">
                {head ? (
                  <thead>
                    <tr>
                      {head.map((cell, j) => <th key={j}>{renderInlineMarkdown(cell, `th-${index}-${j}`)}</th>)}
                    </tr>
                  </thead>
                ) : null}
                <tbody>
                  {(head ? body : block.rows).map((row, r) => (
                    <tr key={r}>
                      {row.map((cell, c) => <td key={c}>{renderInlineMarkdown(cell, `td-${index}-${r}-${c}`)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        return null;
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
  const [modelCatalog, setModelCatalog] = useState({ groups: [], options: [], default_key: '' });
  const [selectedModelKey, setSelectedModelKey] = useState(() => readStoredModelKey());
  const [agentCategories, setAgentCategories] = useState(FALLBACK_AGENT_CATEGORIES);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState(() => readStoredCategory());
  const [selectedMode, setSelectedMode] = useState(() => readStoredMode());
  const [debugModels, setDebugModels] = useState(() => isDebugModelsEnabled());

  const textareaRef = useRef(null);
  const revealAbortRef = useRef(null);

  const projectCodes = useMemo(
    () => dbProjects.map(normalizeProjectCode).filter(Boolean),
    [dbProjects],
  );

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [input, resizeTextarea]);

  const scrollSignature = useMemo(
    () => messages.map((m) => `${m.id}:${m.content?.length || 0}:${m.streaming ? 1 : 0}`).join('|'),
    [messages],
  );
  const { containerRef: messagesContainerRef, endRef: messagesEndRef } = useChatAutoScroll(
    [scrollSignature, loading],
    { behavior: messages.length > 2 ? 'smooth' : 'auto' },
  );

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
        const catalog = status?.model_catalog || {};
        setModelCatalog(catalog);
        const cats = status?.agent_categories || [];
        if (cats.length) {
          setAgentCategories(cats);
          setCategoriesLoading(false);
        } else {
          fetchAgentCategories()
            .then((payload) => {
              const live = payload?.categories || [];
              if (live.length) setAgentCategories(live);
            })
            .catch(() => {})
            .finally(() => setCategoriesLoading(false));
        }
        if (status?.default_agent_category) {
          const storedCat = readStoredCategory();
          const valid = new Set((cats.length ? cats : []).map((c) => c.id));
          if (!valid.size || valid.has(storedCat)) setSelectedCategory(storedCat);
          else setSelectedCategory(status.default_agent_category);
        }
        const stored = readStoredModelKey();
        const defaultKey = catalog?.default_key || '';
        const validKeys = new Set((catalog?.options || []).map((opt) => opt.key));
        const nextKey = stored && validKeys.has(stored) ? stored : defaultKey;
        if (nextKey) {
          setSelectedModelKey(nextKey);
          const picked = parseModelKey(nextKey);
          if (picked.provider) setChatProvider(picked.provider);
          if (picked.model) setChatModel(picked.model);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setChatProvider('mock');
          setChatHealthy(false);
          setCategoriesLoading(false);
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

  const swimmingTopics = useMemo(() => {
    const codes = dbProjects.map(normalizeProjectCode).filter(Boolean);
    if (codes.length) return codes;
    return ['EyeMT', 'SPACE', 'KRAS', 'iPDC_1.0', 'TLS', 'HGSC_scRNAseq', 'SPACEstat'];
  }, [dbProjects]);

  const selectedModel = useMemo(() => parseModelKey(selectedModelKey), [selectedModelKey]);

  const handleModelChange = useCallback((event) => {
    const key = event.target.value;
    setSelectedModelKey(key);
    writeStoredModelKey(key);
    const picked = parseModelKey(key);
    if (picked.provider) setChatProvider(picked.provider);
    if (picked.model) setChatModel(picked.model);
  }, []);

  const handleCategoryChange = useCallback((categoryId) => {
    setSelectedCategory(categoryId);
    writeStoredCategory(categoryId);
  }, []);

  const handleModeChange = useCallback((mode) => {
    setSelectedMode(mode);
    writeStoredMode(mode);
  }, []);

  const handleToggleDebugModels = useCallback((on) => {
    setDebugModels(on);
    setDebugModelsEnabled(on);
  }, []);

  const activeCategoryLabel = useMemo(() => {
    const cat = agentCategories.find((c) => c.id === selectedCategory);
    return cat?.label || 'Lab Research Assistant';
  }, [agentCategories, selectedCategory]);

  const shellCover = useModuleShellCover();
  const libraryScope = useMemo(
    () => (shellCover?.mainId && shellCover?.subId
      ? getLibraryScopeContext(shellCover.mainId, shellCover.subId)
      : null),
    [shellCover?.mainId, shellCover?.subId],
  );

  const sendQuestion = useCallback(
    async (question, { appendUserMessage = true } = {}) => {
      const textToSend = String(question || '').trim();
      if (!textToSend || loading) return;

      if (appendUserMessage) {
        setMessages((prev) => [...prev, makeMessage('user', textToSend)]);
        setInput('');
      }

      const assistantMessage = makeMessage('assistant', '', {
        streaming: true,
        statusText: 'Activating intelligence team…',
      });
      let streamedAssistantId = null;
      const llmProvider = selectedModel.provider || chatProvider;
      const llmModel = selectedModel.model || chatModel || null;
      const useLegacyModelPicker = debugModels;

      if (!useLegacyModelPicker) {
        streamedAssistantId = assistantMessage.id;
        setMessages((prev) => [...prev, assistantMessage]);
      }

      setLoading(true);

      try {
        if (!useLegacyModelPicker) {
          const data = await sendCategoryChat({
            message: textToSend,
            category: selectedCategory,
            mode: selectedMode,
            project_codes: selProjs,
            library_scope: libraryScope,
          });
          const formatted = formatAssistantPayload({
            ...data,
            synthesis_mode: data?.synthesis_mode || 'category_agents',
            provider: 'category_agents',
          });

          revealAbortRef.current?.abort();
          const controller = new AbortController();
          revealAbortRef.current = controller;

          const meta = {
            sources: formatted.sources,
            searchHits: formatted.searchHits,
            queryContext: textToSend,
            limitations: formatted.limitations,
            intent: formatted.intent,
            showSources: formatted.showSources,
            databaseCounts: formatted.databaseCounts,
            isSafe: formatted.isSafe,
            provider: 'category_agents',
            synthesisMode: formatted.synthesisMode,
            agentCategory: data?.category || activeCategoryLabel,
            agentMode: data?.mode || selectedMode,
            agentsUsed: data?.agents_used || [],
            confidence: data?.confidence,
            traceId: data?.trace_id,
          };

          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamedAssistantId
                ? { ...msg, statusText: 'Synthesizing response…', ...meta }
                : msg,
            ),
          );

          await revealTextProgressively(formatted.content, (partial) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === streamedAssistantId
                  ? { ...msg, content: partial, streaming: true }
                  : msg,
              ),
            );
          }, { signal: controller.signal, chunkSize: 5, delayMs: 8 });

          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamedAssistantId
                ? { ...msg, content: formatted.content, streaming: false, statusText: null }
                : msg,
            ),
          );
          return;
        }

        if (streamEnabled) {
          streamedAssistantId = assistantMessage.id;
          setMessages((prev) => [...prev, assistantMessage]);

          let streamedContent = '';
          let streamMeta = {};

          await streamChatMessage({
            message: textToSend,
            project_codes: selProjs,
            provider: llmProvider,
            model: llmModel,
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
          provider: llmProvider,
          model: llmModel,
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
              : error?.status === 429
                ? (error.message || 'Rate limit reached — please wait a moment before asking again.')
              : isRoleBlocked
                ? 'Chat unavailable for this account. Ask an admin or use ⌘K platform search.'
                : (error?.message || 'Connection timed out or API offline. You can retry this message without retyping it.'),
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
    [loading, selProjs, chatProvider, chatModel, selectedModel, streamEnabled, debugModels, selectedCategory, selectedMode, activeCategoryLabel, libraryScope],
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

  const { nav, t: guiT } = useGuiT();
  const mainNav = nav.findMain(shellCover?.mainId || 'ai_assistant');
  const MainIcon = mainNav?.icon;

  const providerLabel = useMemo(() => formatChatProviderLabel(chatProvider), [chatProvider]);

  const providerBadge = useMemo(() => {
    if (!debugModels) {
      const modeLabel = selectedMode.charAt(0).toUpperCase() + selectedMode.slice(1);
      return `${activeCategoryLabel} · ${modeLabel}`;
    }
    const mode = chatProvider === 'mock' ? 'mock' : 'live';
    const label = formatChatProviderLabel(chatProvider);
    if (chatModel && chatProvider !== 'mock') {
      const shortModel = chatModel.replace(/^gemini-/, '').replace(/-flash.*/, '');
      return `${label} · ${shortModel} (${mode})`;
    }
    return `${label} (${mode})`;
  }, [activeCategoryLabel, chatModel, chatProvider, debugModels, providerLabel, selectedMode]);

  const heroStats = useMemo(() => {
    const status = loading
      ? { value: 'Thinking', tone: 'warn' }
      : chatHealthy === false
        ? { value: 'Offline', tone: 'danger' }
        : { value: 'Ready', tone: 'live' };
    return [
      {
        id: 'mode',
        label: 'Mode',
        icon: 'database',
        value: 'RAG',
        tone: 'cyan',
        title: 'Retrieval-augmented generation',
      },
      {
        id: 'team',
        label: 'Team',
        icon: 'team',
        value: debugModels ? (chatModel || 'LLM') : activeCategoryLabel,
        tone: 'primary',
        title: providerBadge,
      },
      {
        id: 'scope',
        label: 'Scope',
        icon: 'scope',
        value: `${selProjs.length || 0} proj`,
        tone: 'neutral',
        title: `${selProjs.length || 0} scoped project(s)`,
      },
      {
        id: 'status',
        label: 'Status',
        icon: 'status',
        value: status.value,
        tone: status.tone,
        title: 'Copilot availability',
      },
    ];
  }, [loading, chatHealthy, debugModels, chatModel, activeCategoryLabel, providerBadge, selProjs.length]);

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
      <div className="assistant-cover-card">
        <Suspense fallback={<div className="ai3d-hero-skeleton" aria-hidden />}>
          <AiAssistant3DScene
            merged
            toolbar={coverToolbar}
            title="OMEIA Copilot"
            subtitle="Spatial-biology RAG · lab protocols · intelligence teams"
            stats={heroStats}
            swimmingTopics={[]}
            compact
            dense
            visual="solar"
            visualPosition="right"
            className="ai3d-hero--module-ai"
          />
        </Suspense>
        <div className="assistant-cover-card__intel">
          <AgentCategorySelector
            layout="cover"
            categories={agentCategories}
            selectedCategory={selectedCategory}
            selectedMode={selectedMode}
            onCategoryChange={handleCategoryChange}
            onModeChange={handleModeChange}
            disabled={loading}
            loading={categoriesLoading}
            showDebug
            modelCatalog={modelCatalog}
            debugModels={debugModels}
            onToggleDebugModels={handleToggleDebugModels}
          />
        </div>
      </div>

      <div className="chat-container assistant-chat-container">
        <AgentCategorySelector
          variant="context"
          categories={agentCategories}
          selectedCategory={selectedCategory}
          selectedMode={selectedMode}
        />
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
                        title={
                          message.agentCategory
                            ? `${message.agentCategory} · ${message.agentMode || 'balanced'} team`
                            : `Synthesis: ${message.synthesisMode || 'unknown'}`
                        }
                      >
                        {message.agentCategory || activeCategoryLabel}
                        {message.agentMode ? ` · ${message.agentMode}` : ''}
                      </span>
                    ) : null}
                    {message.createdAt && !message.isWelcome ? (
                      <time className="chat-bubble__time" dateTime={message.createdAt}>
                        {formatTime(message.createdAt)}
                      </time>
                    ) : null}
                  </span>
                </div>

                {message.streaming && !message.content ? (
                  <div className="chat-streaming-status">
                    <TypingIndicator />
                    <span>{message.statusText || 'Composing answer…'}</span>
                  </div>
                ) : (
                  <MarkdownLite text={message.content} />
                )}
                {message.streaming && message.content ? (
                  <span className="chat-streaming-cursor" aria-hidden="true" />
                ) : null}

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

          <div ref={messagesEndRef} className="chat-scroll-anchor" aria-hidden="true" />
        </div>

        <form onSubmit={handleSend} className="chat-input-area assistant-chat-input-area">
          <div className="assistant-chat-composer">
          {debugModels ? (
            <div className="assistant-chat-model-picker" title="Developer model override">
              <label className="assistant-chat-model-picker__label" htmlFor="assistant-chat-model-select">
                Debug model
              </label>
              <div className="assistant-chat-model-picker__control">
                <select
                  id="assistant-chat-model-select"
                  className="assistant-chat-model-select"
                  value={selectedModelKey}
                  onChange={handleModelChange}
                  disabled={loading || !(modelCatalog?.options || []).length}
                  aria-label="Choose chat model"
                >
                  {(modelCatalog?.groups || []).map((group) => (
                    <optgroup
                      key={group.provider}
                      label={`${group.label}${group.healthy === false ? ' (offline)' : ''}`}
                    >
                      {(group.models || []).map((m) => {
                        const key = `${group.provider}:${m.id}`;
                        return (
                          <option key={key} value={key} disabled={group.healthy === false}>
                            {m.label}
                          </option>
                        );
                      })}
                    </optgroup>
                  ))}
                </select>
                <ChevronDown size={14} className="assistant-chat-model-picker__chevron" aria-hidden />
              </div>
            </div>
          ) : null}
          <div className="assistant-chat-input-wrap">
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder="Ask about CycIF gating, SPACEStat, Ashlar, StarDist, GeoMx, protocols…"
              className="form-input assistant-chat-input"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              aria-label="Ask OMEIA Research Copilot"
            />
            <span className="assistant-chat-input-hint">Enter to send · Shift+Enter for newline</span>
          </div>
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
