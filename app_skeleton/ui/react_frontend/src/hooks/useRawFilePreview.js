import { useEffect, useState } from 'react';
import { apiGet } from '../api/client.js';
import { shouldFetchRawFile } from '../utils/filePreviewKind.js';

async function fetchAssetText(fileUrl) {
  const res = await fetch(fileUrl, {
    cache: 'no-store',
    headers: { Accept: 'text/plain, text/*, application/json, */*' },
  });
  if (!res.ok) throw new Error(`Could not load file (HTTP ${res.status})`);
  return res.text();
}

async function fetchProjectPreviewText(projectCode, relativePath) {
  const data = await apiGet('/api/project-files/preview-text', {
    params: new URLSearchParams({
      project_code: projectCode,
      relative_path: relativePath,
    }),
  });
  const text = (data?.content || '').trim();
  if (!text) throw new Error('No preview text available');
  return text;
}

async function fetchProjectReadText(projectCode, relativePath) {
  const data = await apiGet('/api/project-files/read', {
    params: new URLSearchParams({
      project_code: projectCode,
      relative_path: relativePath,
    }),
  });
  const text = (data?.content || '').trim();
  if (!text) throw new Error('File is empty');
  return text;
}

async function resolveRawFileContent(fileUrl, kind, options = {}) {
  const { projectCode, relativePath, fallbackText } = options;
  const errors = [];

  if (fileUrl && fileUrl !== '#') {
    try {
      return await fetchAssetText(fileUrl);
    } catch (err) {
      errors.push(err.message || 'Asset fetch failed');
    }
  }

  if (projectCode && relativePath) {
    try {
      return await fetchProjectReadText(projectCode, relativePath);
    } catch (err) {
      errors.push(err.message || 'Read API failed');
    }
    try {
      return await fetchProjectPreviewText(projectCode, relativePath);
    } catch (err) {
      errors.push(err.message || 'Preview API failed');
    }
  }

  const fallback = (fallbackText || '').trim();
  if (fallback) return fallback;

  throw new Error(errors[0] || 'Could not load file');
}

/**
 * @param {object} [options]
 * @param {string} [options.projectCode]
 * @param {string} [options.relativePath]
 * @param {string} [options.fallbackText] indexed chunk / excerpt fallback
 */
export function useRawFilePreview(fileUrl, kind, options = {}) {
  const { projectCode, relativePath, fallbackText } = options;
  const [state, setState] = useState({
    loading: false,
    content: null,
    error: null,
  });

  useEffect(() => {
    if (!shouldFetchRawFile(kind)) {
      setState({ loading: false, content: null, error: null });
      return undefined;
    }

    const canLoad =
      (fileUrl && fileUrl !== '#')
      || (projectCode && relativePath)
      || (fallbackText || '').trim();

    if (!canLoad) {
      setState({ loading: false, content: null, error: null });
      return undefined;
    }

    let cancelled = false;
    setState({ loading: true, content: null, error: null });

    resolveRawFileContent(fileUrl, kind, { projectCode, relativePath, fallbackText })
      .then((text) => {
        if (cancelled) return;
        setState({ loading: false, content: text, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        setState({
          loading: false,
          content: null,
          error: err.message || 'Could not load file',
        });
      });

    return () => {
      cancelled = true;
    };
  }, [fileUrl, kind, projectCode, relativePath, fallbackText]);

  return state;
}
