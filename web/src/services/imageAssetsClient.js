/**
 * Image asset streaming API client.
 */
import { apiFetch, getApiUrl, getAuthToken } from './client.js';
import { AUTH_SKIP_HEADER_VALUE, isAuthSkipActive } from '@/lib/authSkip.js';

function authImageHeaders(extra = {}) {
  const headers = { Accept: 'image/*', ...extra };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  else if (isAuthSkipActive()) headers['X-Platform-Auth-Skip'] = AUTH_SKIP_HEADER_VALUE;
  return headers;
}

export async function fetchImageMetadata(assetId) {
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/metadata`);
}

export async function fetchImageManifest(assetId) {
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/manifest`);
}

export function buildThumbnailUrl(assetId) {
  const base = getApiUrl();
  return `${base}/api/assets/${encodeURIComponent(assetId)}/image/thumbnail`;
}

export function buildTileUrl(assetId, params = {}) {
  const base = getApiUrl();
  const sp = new URLSearchParams();
  const {
    level = 0,
    x = 0,
    y = 0,
    width = 256,
    height = 256,
    channel = 0,
    z = 0,
    t = 0,
    series = 0,
    format = 'png',
  } = params;
  sp.set('level', String(level));
  sp.set('x', String(x));
  sp.set('y', String(y));
  sp.set('width', String(width));
  sp.set('height', String(height));
  sp.set('channel', String(channel));
  sp.set('z', String(z));
  sp.set('t', String(t));
  sp.set('series', String(series));
  sp.set('format', format);
  return `${base}/api/assets/${encodeURIComponent(assetId)}/image/tile?${sp}`;
}

export function buildViewerHash(assetId) {
  return `#viewer/image/${encodeURIComponent(assetId)}`;
}

export function parseViewerHash(hash = '') {
  const match = String(hash || '').match(/^#viewer\/image\/([^/?#]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function fetchImageReadiness() {
  return apiFetch('/api/admin/image-streaming/readiness');
}

export async function inspectImageAssets(assetIds) {
  return apiFetch('/api/admin/image-streaming/inspect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ asset_ids: assetIds }),
  });
}

export async function retryFailedImageJobs() {
  return apiFetch('/api/admin/image-streaming/retry-failed', { method: 'POST' });
}

/** Fetch thumbnail with auth headers; returns object URL (caller should revoke on unmount). */
export async function loadThumbnailBlobUrl(assetId) {
  const url = buildThumbnailUrl(assetId);
  const response = await fetch(url, { headers: authImageHeaders() });
  if (!response.ok) throw new Error('Thumbnail unavailable');
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

/** Load a pyramid tile as ImageBitmap for canvas rendering. */
export async function loadTileBitmap(assetId, params) {
  const url = buildTileUrl(assetId, params);
  const response = await fetch(url, { headers: authImageHeaders() });
  if (!response.ok) throw new Error(`Tile unavailable (${response.status})`);
  const blob = await response.blob();
  return createImageBitmap(blob);
}

// --- Phase 7B viewer extensions ---

export async function fetchImageRois(assetId) {
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/rois`);
}

export async function createImageRoi(assetId, body) {
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/rois`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function deleteImageRoi(assetId, roiId) {
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/rois/${encodeURIComponent(roiId)}`, {
    method: 'DELETE',
  });
}

export async function fetchImageOverlays(assetId) {
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/overlays`);
}

/** Raw pixel probe at image coordinates (preserves source dtype). */
export async function fetchPixelProbe(assetId, params = {}) {
  const sp = new URLSearchParams();
  sp.set('x', String(params.x ?? 0));
  sp.set('y', String(params.y ?? 0));
  if (params.z != null) sp.set('z', String(params.z));
  if (params.t != null) sp.set('t', String(params.t));
  if (params.level != null) sp.set('level', String(params.level));
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/pixel?${sp}`);
}

export async function createImageOverlay(assetId, body) {
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/overlays`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function deleteImageOverlay(assetId, overlayId) {
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/overlays/${encodeURIComponent(overlayId)}`, {
    method: 'DELETE',
  });
}

export async function fetchChannelPresets() {
  return apiFetch('/api/users/me/image/channel-presets');
}

export async function saveChannelPreset(body) {
  return apiFetch('/api/users/me/image/channel-presets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function deleteChannelPreset(presetId) {
  return apiFetch(`/api/users/me/image/channel-presets/${encodeURIComponent(presetId)}`, {
    method: 'DELETE',
  });
}

export async function fetchCellInspection(assetId, cellId) {
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/cells/${encodeURIComponent(cellId)}`);
}

export async function fetchImageHistogram(assetId, params = {}) {
  const sp = new URLSearchParams();
  const {
    channel = 0,
    z = 0,
    t = 0,
    x = 0,
    y = 0,
    width = 256,
    height = 256,
    bins = 256,
  } = params;
  sp.set('channel', String(channel));
  sp.set('z', String(z));
  sp.set('t', String(t));
  sp.set('x', String(x));
  sp.set('y', String(y));
  sp.set('width', String(width));
  sp.set('height', String(height));
  sp.set('bins', String(bins));
  return apiFetch(`/api/assets/${encodeURIComponent(assetId)}/image/histogram?${sp}`);
}
