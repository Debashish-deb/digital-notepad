import { apiFetch } from '../api/client.js';

export async function getResearchKnowledgeStatus() {
  return apiFetch('/api/research-knowledge/status');
}

export async function crawlFarkkilaSite({ maxPages = 50 } = {}) {
  const params = new URLSearchParams({ max_pages: String(maxPages) });
  return apiFetch(`/api/research-knowledge/crawl/farkkila?${params}`, { method: 'POST' });
}

export async function ingestPublications() {
  return apiFetch('/api/research-knowledge/ingest-publications', { method: 'POST' });
}

export async function seedResearchDatasets() {
  return apiFetch('/api/research-knowledge/seed-datasets', { method: 'POST' });
}

export async function searchResearchKnowledge({ q, limit = 20, signal } = {}) {
  const query = String(q || '').trim();
  if (!query) return { query: '', count: 0, hits: [] };
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return apiFetch(`/api/research-knowledge/search?${params}`, { method: 'GET', signal });
}
