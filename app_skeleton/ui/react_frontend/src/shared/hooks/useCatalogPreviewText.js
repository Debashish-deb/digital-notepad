import { useCatalogDocumentPreview } from './useCatalogDocumentPreview.js';

/** @deprecated Prefer useCatalogDocumentPreview */
export function useCatalogPreviewText(relativePath, enabled = true) {
  const state = useCatalogDocumentPreview(relativePath, null, enabled);
  return {
    loading: state.loading,
    text: state.displayText,
    error: state.error,
  };
}
