import { useEffect, useState } from 'react';
import { isSpreadsheetPreviewable } from '../utils/folderBrowserUtils.js';

export function useSpreadsheetPreview(fileUrl, extension) {
  const [state, setState] = useState({
    loading: false,
    sheets: null,
    repairNotes: [],
    error: null,
    strategy: null,
  });

  useEffect(() => {
    if (!fileUrl || !isSpreadsheetPreviewable(extension)) {
      setState({ loading: false, sheets: null, repairNotes: [], error: null, strategy: null });
      return undefined;
    }

    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    import('../utils/spreadsheetPreview.js')
      .then(({ loadSpreadsheetFromUrl }) => loadSpreadsheetFromUrl(fileUrl, extension))
      .then((result) => {
        if (cancelled) return;
        if (result.ok) {
          setState({
            loading: false,
            sheets: result.sheets,
            repairNotes: result.repairNotes || [],
            error: null,
            strategy: result.strategy || null,
          });
        } else {
          setState({
            loading: false,
            sheets: null,
            repairNotes: result.repairNotes || [],
            error: result.error || 'Could not open spreadsheet',
            strategy: null,
          });
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setState({
          loading: false,
          sheets: null,
          repairNotes: [],
          error: err.message || 'Could not open spreadsheet',
          strategy: null,
        });
      });

    return () => {
      cancelled = true;
    };
  }, [fileUrl, extension]);

  return state;
}
