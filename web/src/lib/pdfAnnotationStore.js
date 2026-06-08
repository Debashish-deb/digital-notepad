const STORAGE_PREFIX = 'omeia-pdf-annotations:';

export function pdfAnnotationKey(documentKey) {
  if (!documentKey) return null;
  return `${STORAGE_PREFIX}${documentKey}`;
}

export function loadPdfAnnotations(documentKey) {
  const key = pdfAnnotationKey(documentKey);
  if (!key) return { version: 1, pages: {} };
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return { version: 1, pages: {} };
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return { version: 1, pages: {} };
    return {
      version: 1,
      pages: parsed.pages && typeof parsed.pages === 'object' ? parsed.pages : {},
    };
  } catch {
    return { version: 1, pages: {} };
  }
}

export function savePdfAnnotations(documentKey, data) {
  const key = pdfAnnotationKey(documentKey);
  if (!key) return;
  try {
    sessionStorage.setItem(key, JSON.stringify(data));
  } catch {
    /* session quota */
  }
}

export function emptyPageAnnotations() {
  return { highlights: [], notes: [], strokes: [] };
}

export function getPageAnnotations(data, pageNum) {
  const pageKey = String(pageNum);
  const page = data.pages[pageKey];
  if (!page) return emptyPageAnnotations();
  return {
    highlights: Array.isArray(page.highlights) ? page.highlights : [],
    notes: Array.isArray(page.notes) ? page.notes : [],
    strokes: Array.isArray(page.strokes) ? page.strokes : [],
  };
}

export function setPageAnnotations(data, pageNum, pageData) {
  return {
    ...data,
    pages: {
      ...data.pages,
      [String(pageNum)]: pageData,
    },
  };
}
