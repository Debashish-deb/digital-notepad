export function countPreviewWords(text) {
  if (!text || typeof text !== 'string') return 0;
  return (text.trim().match(/\S+/g) || []).length;
}

export function computePreviewMetadataScore(doc, previewText) {
  if (!doc) return 0;
  let score = 0;
  if (doc.path) score += 18;
  if (doc.name || doc.title) score += 14;
  if (doc.categoryId || doc.category || doc.section_label) score += 14;
  if (doc.extension) score += 10;
  if (previewText) score += 28;
  else if (doc.excerpt) score += 16;
  if (doc.word_count) score += 8;
  if (doc.document_kind || doc.role) score += 8;
  return Math.min(100, score);
}

export function findCategoryLabelInGroups(groups, categoryId) {
  if (!categoryId || !groups?.length) return null;
  for (const group of groups) {
    for (const cat of group.categories || []) {
      if (cat.id === categoryId) return cat.label;
    }
  }
  return prettifyPreviewLabel(categoryId);
}

export function prettifyPreviewLabel(value) {
  return String(value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

export function buildProjectPreviewMetadata({
  doc,
  projectCode,
  workspaceTab,
  previewKind,
  extension,
  previewText,
  categoryLabel,
}) {
  if (!doc) return [];
  const words = doc.word_count || countPreviewWords(previewText);
  return [
    { label: 'Category', value: categoryLabel || prettifyPreviewLabel(doc.categoryId) },
    { label: 'Tab', value: prettifyPreviewLabel(workspaceTab) },
    { label: 'Type', value: prettifyPreviewLabel(previewKind) },
    { label: 'Extension', value: (extension || doc.extension || '').replace(/^\./, '') },
    { label: 'Project', value: projectCode },
    { label: 'Words', value: words || null },
    { label: 'Section', value: doc.section_label },
  ].filter((item) => item.value != null && item.value !== '');
}

export function buildLabPreviewMetadata({
  doc,
  sectionId,
  previewKind,
  extension,
  previewText,
}) {
  if (!doc) return [];
  const words = doc.word_count || countPreviewWords(previewText);
  return [
    { label: 'Section', value: prettifyPreviewLabel(sectionId) },
    { label: 'Type', value: prettifyPreviewLabel(previewKind) },
    { label: 'Extension', value: (extension || doc.extension || '').replace(/^\./, '') },
    { label: 'Role', value: doc.document_role || doc.role },
    { label: 'Words', value: words || null },
    { label: 'Kind', value: doc.document_kind },
  ].filter((item) => item.value != null && item.value !== '');
}

export function buildExpandedPreviewMetadata({
  doc,
  path,
  previewKind,
  extension,
  previewText,
  assetUrl,
  extra = {},
}) {
  const items = [
    { label: 'Path', value: path || doc?.path },
    { label: 'Filename', value: doc?.name || doc?.title },
    { label: 'Preview kind', value: previewKind },
    { label: 'Extension', value: extension },
    { label: 'Document kind', value: doc?.document_kind },
    { label: 'Section', value: doc?.section_label },
    { label: 'Category', value: doc?.categoryId || doc?.category },
    { label: 'Words', value: doc?.word_count || countPreviewWords(previewText) },
    { label: 'Chars', value: previewText?.length || doc?.char_count },
    { label: 'Indexed', value: doc?.indexed ? 'yes' : doc?.indexed === false ? 'no' : null },
    { label: 'Source', value: assetUrl ? 'available' : null },
    ...Object.entries(extra || {}).map(([label, value]) => ({
      label: prettifyPreviewLabel(label),
      value,
    })),
  ];
  return items.filter((item) => item.value != null && item.value !== '');
}
