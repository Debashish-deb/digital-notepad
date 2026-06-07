import { apiFetch } from './client.js';

const CATEGORY_STORAGE_KEY = 'omeia.chat.agentCategory';
const MODE_STORAGE_KEY = 'omeia.chat.agentMode';
const DEBUG_MODELS_KEY = 'omeia.chat.debugModels';

export function readStoredCategory() {
  try {
    return localStorage.getItem(CATEGORY_STORAGE_KEY) || 'general_research';
  } catch {
    return 'general_research';
  }
}

export function writeStoredCategory(id) {
  try {
    if (id) localStorage.setItem(CATEGORY_STORAGE_KEY, id);
  } catch {
    /* ignore */
  }
}

export function readStoredMode() {
  try {
    return localStorage.getItem(MODE_STORAGE_KEY) || 'balanced';
  } catch {
    return 'balanced';
  }
}

export function writeStoredMode(mode) {
  try {
    if (mode) localStorage.setItem(MODE_STORAGE_KEY, mode);
  } catch {
    /* ignore */
  }
}

export function isDebugModelsEnabled() {
  try {
    return localStorage.getItem(DEBUG_MODELS_KEY) === '1';
  } catch {
    return false;
  }
}

export function setDebugModelsEnabled(on) {
  try {
    localStorage.setItem(DEBUG_MODELS_KEY, on ? '1' : '0');
  } catch {
    /* ignore */
  }
}

export async function fetchAgentCategories() {
  return apiFetch('/api/agent-categories', { method: 'GET', timeoutMs: 12_000 });
}

export async function fetchCategoryDetail(categoryId, mode = 'balanced') {
  const params = new URLSearchParams({ mode });
  return apiFetch(`/api/agent-categories/${encodeURIComponent(categoryId)}?${params}`, {
    method: 'GET',
    timeoutMs: 12_000,
  });
}

export async function sendCategoryChat({
  message,
  category,
  mode = 'balanced',
  project_codes = [],
  library_scope = null,
  timeoutMs = 180_000,
} = {}) {
  const text = String(message || '').trim();
  if (!text) throw new Error('Message is required');
  const body = {
    message: text,
    category,
    mode,
    project_codes,
    use_rag: true,
    use_local_models: true,
  };
  if (library_scope) body.library_scope = library_scope;
  return apiFetch('/api/chat/category', {
    method: 'POST',
    timeoutMs,
    body,
  });
}
