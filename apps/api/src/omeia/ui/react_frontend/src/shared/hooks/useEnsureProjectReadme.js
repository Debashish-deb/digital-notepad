import { useCallback, useEffect, useRef, useState } from 'react';
import { ensureProjectReadme } from '@/services/datapad.js';
import { normalizeDigitalTwin } from '@/lib/digitalTwinUtils.js';
import { twinHasReadme } from '@/lib/projectReadmeUtils.js';

/**
 * Ensures every project workspace has an editable README.md (any tab).
 * Creates a sample template on disk when missing, then refreshes the twin.
 */
export function useEnsureProjectReadme(projectCode, { twin, setTwin, refreshTwin }) {
  const [ensuring, setEnsuring] = useState(false);
  const [error, setError] = useState(null);
  const attemptedRef = useRef('');

  const ensureReadme = useCallback(async () => {
    if (!projectCode || !twin || twinHasReadme(twin)) {
      setError(null);
      return null;
    }
    setEnsuring(true);
    setError(null);
    try {
      const result = await ensureProjectReadme(projectCode);
      if (result?.twin) {
        setTwin?.(normalizeDigitalTwin(result.twin));
      } else if (result?.created || result?.reason === 'rescanned') {
        await refreshTwin?.();
      }
      window.dispatchEvent(
        new CustomEvent('project-readme-updated', { detail: { projectCode } }),
      );
      return result;
    } catch (e) {
      const message = e?.message || 'Could not create README for this project.';
      setError(message);
      attemptedRef.current = '';
      return null;
    } finally {
      setEnsuring(false);
    }
  }, [projectCode, twin, setTwin, refreshTwin]);

  useEffect(() => {
    if (!projectCode || !twin || twinHasReadme(twin) || ensuring) return;
    const key = `${projectCode}:${twin.processed_at || 'unknown'}`;
    if (attemptedRef.current === key) return;
    attemptedRef.current = key;
    ensureReadme();
  }, [projectCode, twin, ensuring, ensureReadme]);

  return { ensuring, error, ensureReadme };
}
