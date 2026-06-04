import { useState, useEffect, useCallback } from 'react';
import { fetchDigitalTwin, fetchProcessedTwin, saveDigitalTwin } from '../utils/digitalTwinUtils.js';

export function useDigitalTwin(projectCode, API_URL) {
  const [twin, setTwin] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (refresh = false) => {
    if (!projectCode) return;
    setError(null);

    let hadCached = false;
    if (!refresh) {
      const cached = await fetchProcessedTwin(projectCode);
      if (cached) {
        setTwin(cached);
        hadCached = true;
        setLoading(false);
      } else {
        setLoading(true);
      }
    } else {
      setLoading(true);
    }

    try {
      const data = await fetchDigitalTwin(projectCode, API_URL, { refresh });
      if (data) {
        setTwin(data);
        setError(null);
      } else if (!hadCached) {
        setError(
          'No digital record for this project. Click “Scan project folder” to build one from files under /projects.'
        );
      } else if (refresh) {
        setError('Scan failed or project folder missing on disk.');
      }
    } catch (e) {
      if (!hadCached) setError(e.message || 'Failed to load digital record.');
    } finally {
      setLoading(false);
    }
  }, [projectCode, API_URL]);

  const save = useCallback(async (payload) => {
    setSaving(true);
    setError(null);
    try {
      const saved = await saveDigitalTwin(projectCode, payload, API_URL);
      setTwin(saved);
      return saved;
    } catch (e) {
      setError(e.message || 'Failed to save digital twin.');
      throw e;
    } finally {
      setSaving(false);
    }
  }, [projectCode, API_URL]);

  useEffect(() => {
    load(false);
  }, [load]);

  return { twin, loading, saving, error, refresh: () => load(true), save, setTwin };
}
