/**
 * Dossier alias — navigation helpers live in searchHits.js.
 * Chat-specific helpers for provider labels and source cards.
 */
export * from './searchHits.js';

const PROVIDER_LABELS = {
  gemini: 'Gemini',
  openai: 'OpenAI',
  groq: 'Groq',
  openrouter: 'OpenRouter',
  together: 'Together',
  deepseek: 'DeepSeek',
  ollama: 'Ollama (local)',
  mock: 'Mock (offline)',
};

export function formatChatProviderLabel(provider) {
  const key = String(provider || 'mock').trim().toLowerCase();
  return PROVIDER_LABELS[key] || key;
}

export function chatSourceKey(source, index = 0) {
  return source?.chunk_id || source?.source_uuid || `source-${index}`;
}
