import { useEffect, useState } from 'react';
import { fetchCatalogPreviewPayload } from '../utils/catalogPreviewUtils.js';

/**
 * Loads catalog extraction in parallel with static file fetches.
 * Provides spreadsheet sheet models and/or display text when originals are offline.
 */
export function useCatalogDocumentPreview(relativePath, fileName = null, enabled = true) {
  const [state, setState] = useState({
    loading: false,
    sheets: null,
    displayText: null,
    doc: null,
    error: null,
  });

  useEffect(() => {
    if (!enabled || !relativePath) {
      setState({ loading: false, sheets: null, displayText: null, doc: null, error: null });
      return undefined;
    }

    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    fetchCatalogPreviewPayload(relativePath, fileName)
      .then((payload) => {
        if (cancelled) return;
        if (!payload) {
          setState({ loading: false, sheets: null, displayText: null, doc: null, error: null });
          return;
        }
        setState({
          loading: false,
          sheets: payload.sheets,
          displayText: payload.displayText,
          doc: payload.doc,
          error: null,
        });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            loading: false,
            sheets: null,
            displayText: null,
            doc: null,
            error: err.message || 'Catalog preview failed',
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [relativePath, fileName, enabled]);

  return state;
}
