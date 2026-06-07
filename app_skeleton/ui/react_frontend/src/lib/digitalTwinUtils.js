import { fetchWithTimeout } from './projectUtils.js';

export function normalizeDigitalTwin(data) {
  if (!data) return null;
  const out = structuredClone(data);
  const identity = { ...(out.identity || {}) };

  const rq = (identity.research_question || '').trim();
  const summary = (identity.project_summary || '').trim();
  if (rq && summary && rq.toLowerCase() === summary.toLowerCase()) {
    identity.research_question = '';
  } else if (rq && rq.length < 20 && summary) {
    identity.research_question = '';
  }
  out.identity = identity;

  const seenNames = new Set();
  out.personnel = (out.personnel || []).filter((p) => {
    const name = (p.name || '').trim();
    if (!name || seenNames.has(name.toLowerCase())) return false;
    seenNames.add(name.toLowerCase());
    if (p.focus && p.role && p.focus.toLowerCase() === p.role.toLowerCase()) {
      p.focus = p.role;
    }
    return true;
  });

  const seenMod = new Set();
  out.modalities = (out.modalities || []).filter((m) => {
    const name = (typeof m === 'string' ? m : m.name || '').trim();
    const key = name.toLowerCase().replace(/[^a-z0-9]/g, '');
    if (!key || seenMod.has(key)) return false;
    seenMod.add(key);
    return true;
  });

  const batchMap = new Map();
  for (const c of out.cohorts || []) {
    const key = (c.batch_id || 'Primary').toLowerCase().replace(/[^a-z0-9]/g, '');
    if (batchMap.has(key)) {
      const ex = batchMap.get(key);
      if (c.sample_count && !ex.sample_count) ex.sample_count = c.sample_count;
      ex.exclusions = [...new Set([...(ex.exclusions || []), ...(c.exclusions || [])])];
    } else {
      batchMap.set(key, { ...c });
    }
  }
  out.cohorts = [...batchMap.values()];

  const assets = { ...(out.data_assets || {}) };
  const pathSet = new Set();
  assets.storage_paths = (assets.storage_paths || [])
    .map((p) => p.trim().replace(/\/$/, ''))
    .filter((p) => p && !/^https?:\/\//i.test(p) && !pathSet.has(p.toLowerCase()) && pathSet.add(p.toLowerCase()));
  const repoSet = new Set();
  assets.repositories = (assets.repositories || [])
    .map((r) => r.trim().replace(/\/$/, ''))
    .filter((r) => r && !repoSet.has(r.toLowerCase()) && repoSet.add(r.toLowerCase()));
  out.data_assets = assets;

  const outputSet = new Set();
  const outputs = [];
  for (const item of [...(out.dissemination || []), ...(out.publications || []), ...(out.outputs || [])]) {
    const key = (item.source_file || item.doi || item.title || '').toLowerCase();
    if (!key || outputSet.has(key)) continue;
    outputSet.add(key);
    outputs.push({
      title: item.title || 'Untitled',
      author: item.author || '',
      conference: item.conference || item.source || '',
      year: item.year ?? null,
      doi: item.doi || null,
      type: item.type || (item.doi ? 'publication' : 'abstract'),
      source_file: item.source_file || '',
    });
  }
  out.outputs = outputs;

  const tlSet = new Set();
  out.timeline = (out.timeline || []).filter((e) => {
    if (e.date?.toLowerCase() === 'undated' && (e.summary || '').length > 500) return false;
    const key = `${e.date}|${e.title}`;
    if (tlSet.has(key)) return false;
    tlSet.add(key);
    return true;
  });

  return out;
}

export async function fetchProcessedTwin(projectCode) {
  const code = encodeURIComponent(projectCode);
  try {
    const res = await fetch(`/processed/${code}.json`, { cache: 'no-store' });
    if (res.ok) return normalizeDigitalTwin(await res.json());
  } catch (e) {
    console.warn('Processed twin JSON unavailable', e);
  }
  return null;
}

/** Load pre-built twin from public/processed (fast, no API). */
export async function fetchDigitalTwin(projectCode, API_URL, { refresh = false } = {}) {
  if (!refresh) {
    return fetchProcessedTwin(projectCode);
  }

  const code = encodeURIComponent(projectCode);
  try {
    const res = await fetchWithTimeout(
      `${API_URL}/api/projects/${code}/digital-twin?refresh=true`,
      {},
      120000
    );
    if (res.ok) return normalizeDigitalTwin(await res.json());
  } catch (e) {
    console.warn('Digital twin rescan failed', e);
  }

  return fetchProcessedTwin(projectCode);
}

export async function saveDigitalTwin(projectCode, payload, API_URL) {
  const code = encodeURIComponent(projectCode);
  const res = await fetchWithTimeout(
    `${API_URL}/api/projects/${code}/digital-twin`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    10000
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to save digital record.');
  }
  return normalizeDigitalTwin(await res.json());
}

export function formatSampleCount(count) {
  if (count == null || Number.isNaN(count)) return '—';
  return count.toLocaleString();
}

export function categoryColor(category) {
  const map = {
    meeting: 'var(--color-accent)',
    analysis: 'var(--color-primary)',
    protocol: 'var(--color-success)',
    update: 'var(--text-muted)',
    dissemination: 'var(--color-warning)',
  };
  return map[category] || 'var(--text-secondary)';
}

/**
 * URL to open/download a project file from disk (API resolves content_root).
 * Prefer same-origin /api/... so Vite dev proxy and co-hosted prod both work.
 */
export function projectAssetUrl(projectCode, relativePath, API_URL = '') {
  const rel = (relativePath || '').replace(/^\/+/, '').replace(/\\/g, '/');
  if (!projectCode || !rel) return '#';

  const params = new URLSearchParams({ path: rel });
  const code = encodeURIComponent(projectCode);
  const relativeApi = `/api/projects/${code}/asset?${params}`;

  if (typeof window !== 'undefined') {
    const apiBase = (API_URL || '').replace(/\/$/, '');
    if (!apiBase) return relativeApi;
    try {
      const apiOrigin = new URL(apiBase).origin;
      if (apiOrigin === window.location.origin) return relativeApi;
    } catch {
      return relativeApi;
    }
    return `${apiBase}/api/projects/${code}/asset?${params}`;
  }

  const base = (API_URL || 'http://localhost:8000').replace(/\/$/, '');
  return `${base}/api/projects/${code}/asset?${params}`;
}

export function cloneTwin(twin) {
  return structuredClone(twin);
}
