/**
 * Gemini Research Copilot chat client — server-side LLM only (no API keys in browser).
 */
import { apiFetch, getApiUrl, getAuthToken } from './client.js';
import { AUTH_SKIP_HEADER_VALUE, isAuthSkipActive } from '../utils/authSkip.js';

export async function getChatStatus() {
  return apiFetch('/api/chat/status', { method: 'GET', timeoutMs: 12_000 });
}

export async function getChatModels() {
  return apiFetch('/api/chat/models', { method: 'GET', timeoutMs: 12_000 });
}

export async function sendChatMessage({
  message,
  project_codes = [],
  provider = null,
  model = null,
  timeoutMs = 120_000,
} = {}) {
  const text = String(message || '').trim();
  if (!text) {
    throw new Error('Message is required');
  }
  const body = {
    message: text,
    project_codes,
    stream: false,
  };
  if (provider) body.provider = provider;
  if (model) body.model = model;
  return apiFetch('/api/chat', {
    method: 'POST',
    timeoutMs,
    body,
  });
}

/**
 * Stream chat deltas via SSE. Invokes onMetadata once, onDelta per chunk, onDone at end.
 */
export async function streamChatMessage({
  message,
  project_codes = [],
  provider = null,
  model = null,
  onMetadata,
  onDelta,
  onDone,
  onError,
  signal,
} = {}) {
  const text = String(message || '').trim();
  if (!text) {
    throw new Error('Message is required');
  }

  const headers = { Accept: 'text/event-stream', 'Content-Type': 'application/json' };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  else if (isAuthSkipActive()) headers['X-Platform-Auth-Skip'] = AUTH_SKIP_HEADER_VALUE;

  const payload = { message: text, project_codes, stream: true };
  if (provider) payload.provider = provider;
  if (model) payload.model = model;

  const response = await fetch(`${getApiUrl()}/api/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText);
    const err = new Error(detail || `${response.status} ${response.statusText}`);
    err.status = response.status;
    if (response.status === 429) {
      err.rateLimit = {
        limit: response.headers.get('X-RateLimit-Limit'),
        remaining: response.headers.get('X-RateLimit-Remaining'),
        reset: response.headers.get('X-RateLimit-Reset'),
      };
      err.message = 'Rate limit reached — please wait a moment before asking again.';
    }
    onError?.(err);
    throw err;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    const err = new Error('Streaming not supported in this browser');
    onError?.(err);
    throw err;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data:')) continue;
        const payload = JSON.parse(line.slice(5).trim());
        if (payload.type === 'metadata') onMetadata?.(payload);
        else if (payload.type === 'delta') onDelta?.(payload.content || '');
        else if (payload.type === 'done') onDone?.();
      }
    }
    onDone?.();
  } catch (error) {
    onError?.(error);
    throw error;
  }
}
