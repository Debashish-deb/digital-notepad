import { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch } from './client.js';
import { useApiContext } from './ApiContext.jsx';

export function useApiUrl() {
  const { API_URL } = useApiContext();
  return API_URL;
}

/**
 * GET (or custom method) with loading / error / data and manual refetch.
 */
export function useApiQuery(path, { params, enabled = true, method = 'GET', deps = [] } = {}) {
  const { authToken } = useApiContext();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(Boolean(enabled && path));
  const generation = useRef(0);

  const refetch = useCallback(async () => {
    if (!path || !enabled) {
      setLoading(false);
      return null;
    }
    const gen = ++generation.current;
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch(path, { method, params });
      if (gen === generation.current) setData(result);
      return result;
    } catch (e) {
      if (gen === generation.current) {
        setError(e);
        setData(null);
      }
      throw e;
    } finally {
      if (gen === generation.current) setLoading(false);
    }
  }, [path, enabled, method, authToken, ...deps]);

  useEffect(() => {
    if (!enabled || !path) {
      setLoading(false);
      return undefined;
    }
    refetch().catch(() => {});
    return () => {
      generation.current += 1;
    };
  }, [refetch, enabled, path]);

  return { data, error, loading, refetch, setData };
}

export function useApiMutation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const mutate = useCallback(async (path, options = {}) => {
    setLoading(true);
    setError(null);
    try {
      return await apiFetch(path, options);
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  return { mutate, loading, error, setError };
}
