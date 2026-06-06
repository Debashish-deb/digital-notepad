/**
 * Image asset streaming API client.
 */
import { apiFetch, getApiUrl, getAuthToken } from './client.js';
import { AUTH_SKIP_HEADER_VALUE, isAuthSkipActive } from '../utils/authSkip.js';

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
  const headers = { Accept: 'image/*' };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  else if (isAuthSkipActive()) headers['X-Platform-Auth-Skip'] = AUTH_SKIP_HEADER_VALUE;
  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error('Thumbnail unavailable');
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
