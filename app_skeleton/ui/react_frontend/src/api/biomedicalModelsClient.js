import { apiFetch } from './client.js';
import { FALLBACK_BIOMEDICAL_CATALOG, flattenBiomedicalCatalog } from '../data/biomedicalModelsFallback.js';

export async function fetchBiomedicalCatalog() {
  try {
    const data = await apiFetch('/api/biomedical-models/catalog', { method: 'GET', timeoutMs: 12_000 });
    if (data?.error) return { ...FALLBACK_BIOMEDICAL_CATALOG, source: 'bundled', gateway_error: data.error };
    return { ...data, source: 'live' };
  } catch (error) {
    return { ...FALLBACK_BIOMEDICAL_CATALOG, source: 'bundled', gateway_error: error?.message || 'unavailable' };
  }
}

export async function fetchBiomedicalStatus() {
  try {
    return await apiFetch('/api/biomedical-models/status', { method: 'GET', timeoutMs: 12_000 });
  } catch {
    return { gateway: 'offline', services: {} };
  }
}

export async function fetchBiomedicalModelsForUi() {
  const [catalog, status] = await Promise.all([fetchBiomedicalCatalog(), fetchBiomedicalStatus()]);
  return {
    catalog,
    status,
    models: flattenBiomedicalCatalog(catalog, status),
  };
}
