/**
 * Shared API client — base URL from VITE_API_URL, Bearer token when available.
 */

const TOKEN_KEY = 'farkki_id_token';

export function getApiUrl() {
  // Dev: same-origin so Vite proxies /api → backend (works at localhost:5173 and LAN IP:5173).
  if (import.meta.env.DEV && typeof window !== 'undefined') {
    return '';
  }
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv && String(fromEnv).trim()) {
    return String(fromEnv).replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return `http://${window.location.hostname}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

export function getAuthToken() {
  try {
    return window.localStorage.getItem(TOKEN_KEY) || null;
  } catch {
    return null;
  }
}

export function setAuthToken(token) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore
  }
}

export function clearAuthToken() {
  setAuthToken(null);
}

export function apiUrl(path, params) {
  const base = getApiUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const query = params ? `?${params.toString()}` : '';
  return `${base}${cleanPath}${query}`;
}

function buildHeaders(extra = {}, body) {
  const headers = { Accept: 'application/json', ...extra };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined && body !== null && !(body instanceof FormData)) {
    if (!headers['Content-Type']) headers['Content-Type'] = 'application/json';
  }
  return headers;
}

export async function apiFetch(path, options = {}) {
  const { params, timeoutMs = 30_000, signal: parentSignal, body, ...rest } = options;
  const url = apiUrl(path, params);
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const onParentAbort = () => controller.abort(parentSignal?.reason);
  if (parentSignal) {
    if (parentSignal.aborted) onParentAbort();
    else parentSignal.addEventListener('abort', onParentAbort, { once: true });
  }

  const init = {
    ...rest,
    signal: controller.signal,
    headers: buildHeaders(rest.headers, body),
  };
  if (body !== undefined) {
    init.body = body instanceof FormData || typeof body === 'string' ? body : JSON.stringify(body);
  }

  try {
    const response = await fetch(url, init);
    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? await response.json().catch(() => null) : null;
    if (!response.ok) {
      const detail = data?.detail ?? data?.message ?? response.statusText;
      const err = new Error(typeof detail === 'string' ? detail : `${response.status} ${response.statusText}`);
      err.status = response.status;
      err.data = data;
      throw err;
    }
    return data;
  } finally {
    window.clearTimeout(timeout);
    parentSignal?.removeEventListener?.('abort', onParentAbort);
  }
}

export async function apiGet(path, options = {}) {
  return apiFetch(path, { ...options, method: 'GET' });
}

export async function apiPost(path, options = {}) {
  return apiFetch(path, { ...options, method: 'POST' });
}

export async function apiPatch(path, options = {}) {
  return apiFetch(path, { ...options, method: 'PATCH' });
}

export async function apiPut(path, options = {}) {
  return apiFetch(path, { ...options, method: 'PUT' });
}

export async function apiDelete(path, options = {}) {
  return apiFetch(path, { ...options, method: 'DELETE' });
}
