import { apiUrl, getAuthToken } from './client.js';
import { AUTH_SKIP_HEADER_VALUE, isAuthSkipActive } from '@/lib/authSkip.js';

function parseFilename(disposition) {
  if (!disposition) return null;
  const match = /filename\*=UTF-8''([^;]+)|filename="([^"]+)"/i.exec(disposition);
  const raw = match?.[1] || match?.[2];
  return raw ? decodeURIComponent(raw) : null;
}

export async function fetchExportFormats(assetId) {
  const { apiFetch } = await import('./client.js'); // lazy to avoid circular import during tests
  return apiFetch(`/api/document-library/export/${encodeURIComponent(assetId)}/formats`);
}

export async function downloadAssetExport(assetId, formatId) {
  const params = new URLSearchParams({ format: formatId });
  const url = apiUrl(`/api/document-library/export/${encodeURIComponent(assetId)}`, params);
  const headers = {};
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  else if (isAuthSkipActive()) headers['X-Platform-Auth-Skip'] = AUTH_SKIP_HEADER_VALUE;

  const response = await fetch(url, { headers });
  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText);
    throw new Error(detail || `Export failed (${response.status})`);
  }

  const blob = await response.blob();
  const filename = parseFilename(response.headers.get('content-disposition'))
    || `${assetId}.${formatId === 'original' ? 'bin' : formatId}`;
  return { blob, filename };
}

export function triggerBrowserDownload(blob, filename) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = 'noopener';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export function buildLocalExportFormats({
  filename = 'document',
  originalUrl,
  text,
  metadata,
}) {
  const base = filename.replace(/\.[^.]+$/, '') || 'document';
  const formats = [];
  if (originalUrl) {
    const ext = (filename.split('.').pop() || 'file').toLowerCase();
    formats.push({ id: 'original', label: `Original (${ext})`, extension: ext });
  }
  if (text) {
    formats.push({ id: 'txt', label: 'Plain text (.txt)', extension: 'txt' });
    formats.push({ id: 'md', label: 'Markdown (.md)', extension: 'md' });
  }
  if (metadata || text) {
    formats.push({ id: 'json', label: 'Metadata (JSON)', extension: 'json' });
  }
  return { base_name: base, filename, formats };
}

export async function downloadLocalExport(local, formatId) {
  const { filename = 'document', originalUrl, text, metadata, title } = local;
  const base = filename.replace(/\.[^.]+$/, '') || 'document';

  if (formatId === 'original') {
    if (!originalUrl) throw new Error('Original file unavailable');
    window.open(originalUrl, '_blank', 'noopener,noreferrer');
    return;
  }

  let blob;
  let outName;
  if (formatId === 'txt') {
    blob = new Blob([text || ''], { type: 'text/plain;charset=utf-8' });
    outName = `${base}.txt`;
  } else if (formatId === 'md') {
    const body = `# ${title || filename}\n\n${text || ''}\n`;
    blob = new Blob([body], { type: 'text/markdown;charset=utf-8' });
    outName = `${base}.md`;
  } else if (formatId === 'json') {
    const payload = {
      filename,
      title: title || filename,
      metadata: metadata || {},
      excerpt: text || null,
      exported_at: new Date().toISOString(),
    };
    blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' });
    outName = `${base}.json`;
  } else {
    throw new Error('Unsupported export format');
  }
  triggerBrowserDownload(blob, outName);
}
