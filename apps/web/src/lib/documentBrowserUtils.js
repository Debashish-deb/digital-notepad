/** Shared helpers for lab document browsers (billing, overview, etc.). */

import { normalizeDocPath, normalizeRelPath } from './folderBrowserUtils.js';

/** Canonical lab corpus sections — preferred when the same path appears in multiple twins. */
const CANONICAL_SECTION_PRIORITY = {
  overview_documents: 90,
  overview_guidelines: 90,
  overview_onboarding: 90,
  overview_cleaning: 85,
  overview_personnel: 85,
  overview_research_materials: 80,
  orders_billing: 70,
  orders_archive: 70,
  meetings: 65,
  wet_lab_files: 60,
  social_misc: 50,
};

function documentRichnessScore(doc) {
  let score = 0;
  const excerpt = String(doc?.excerpt || doc?.summary || '');
  const inline = String(doc?.inlineContent || doc?.content || '');
  score += Math.min(excerpt.length, 8000);
  score += Math.min(inline.length, 12000) * 1.2;
  if (doc?.display_title) score += 12;
  if (doc?.document_id) score += 8;
  if (doc?.page_count) score += 4;
  const section = doc?.sourceSection || '';
  score += CANONICAL_SECTION_PRIORITY[section] || 0;
  return score;
}

/** Keep one record per normalized path, preferring richer metadata and canonical sections. */
export function deduplicateDocumentsByPath(docs) {
  const byPath = new Map();

  for (const doc of docs) {
    const key = normalizeDocPath(doc?.path);
    if (!key) continue;
    const existing = byPath.get(key);
    if (!existing) {
      byPath.set(key, doc);
      continue;
    }
    byPath.set(
      key,
      documentRichnessScore(doc) >= documentRichnessScore(existing) ? doc : existing,
    );
  }

  return [...byPath.values()];
}

const PROJECT_ASSET_KEYS = [
  'documents',
  'figures',
  'presentations',
  'data_files',
  'text_files',
  'videos',
  'code_scripts',
];

export function collectProjectDocuments(twin, { categorizePath, documentTitle, tabFilter }) {
  const lib = twin?.content_library;
  if (!lib?.sections?.length) return [];

  const indexByPath = new Map();
  for (const entry of twin?.document_index || []) {
    const p = normalizeRelPath(entry.path);
    if (p) indexByPath.set(p, entry);
  }

  const seen = new Set();
  const docs = [];

  for (const section of lib.sections) {
    for (const key of PROJECT_ASSET_KEYS) {
      for (const item of section[key] || []) {
        const path = normalizeRelPath(item.path);
        if (!path || seen.has(path)) continue;
        if (tabFilter && !tabFilter(path)) continue;
        seen.add(path);
        const indexed = indexByPath.get(path);
        const merged = { ...item, ...(indexed || {}), path, section_label: section.label };
        docs.push({
          ...merged,
          display_title: documentTitle(merged),
          categoryId: categorizePath(path),
          asset_bucket: item.asset_type || key,
        });
      }
    }
    for (const doc of section.documents || []) {
      const path = normalizeRelPath(doc.path);
      if (!path || seen.has(path)) continue;
      if (tabFilter && !tabFilter(path)) continue;
      seen.add(path);
      const indexed = indexByPath.get(path);
      const merged = { ...doc, ...(indexed || {}), path, section_label: section.label };
      docs.push({
        ...merged,
        display_title: documentTitle(merged),
        categoryId: categorizePath(path),
        asset_bucket: doc.asset_type || 'documents',
      });
    }
  }

  for (const entry of twin?.document_index || []) {
    const path = normalizeRelPath(entry.path || entry.relative_path);
    if (!path || seen.has(path)) continue;
    if (tabFilter && !tabFilter(path)) continue;
    seen.add(path);
    docs.push({
      ...entry,
      path,
      display_title: documentTitle({ ...entry, path }),
      categoryId: categorizePath(path),
      asset_bucket: entry.asset_type || 'document_index',
    });
  }

  return docs;
}

export function collectSectionDocuments(twin, { categorizePath, documentTitle }) {
  const lib = twin?.content_library;
  if (!lib?.sections?.length) return [];

  const indexByPath = new Map();
  for (const entry of twin?.document_index || []) {
    const p = (entry.path || '').replace(/\\/g, '/');
    if (p) indexByPath.set(p, entry);
  }

  const seen = new Set();
  const docs = [];

  for (const section of lib.sections) {
    for (const doc of section.documents || []) {
      const path = (doc.path || '').replace(/\\/g, '/');
      if (!path || seen.has(path)) continue;
      seen.add(path);
      const indexed = indexByPath.get(path);
      docs.push({
        ...doc,
        ...(indexed || {}),
        path,
        display_title: documentTitle({ path, ...doc, ...(indexed || {}) }),
        categoryId: categorizePath(path),
      });
    }
  }

  return docs;
}

export function groupDocumentsByCategory(docs, categoryOrder) {
  const grouped = Object.fromEntries(categoryOrder.map((id) => [id, []]));
  for (const doc of docs) {
    const cat = doc.categoryId || categoryOrder[0];
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(doc);
  }
  for (const id of Object.keys(grouped)) {
    grouped[id].sort((a, b) => (a.path || '').localeCompare(b.path || ''));
  }
  return grouped;
}

export function findCategoryMeta(categoryGroups, categoryId) {
  for (const group of categoryGroups) {
    const cat = group.categories.find((c) => c.id === categoryId);
    if (cat) return { ...cat, groupLabel: group.label };
  }
  return null;
}

export function flattenCategoryOrder(categoryGroups) {
  return categoryGroups.flatMap((g) => g.categories.map((c) => c.id));
}

/** Filter documents by search query (path, title, excerpt). */
export function filterDocsByQuery(docs, fileQuery, documentTitle) {
  const q = String(fileQuery || '').trim().toLowerCase();
  if (!q) return docs;
  const tokens = q.split(/\s+/).filter(Boolean);
  return docs.filter((doc) => {
    const title = documentTitle(doc).toLowerCase();
    const path = (doc.path || '').toLowerCase();
    const excerpt = String(doc.excerpt || doc.inlineContent || doc.summary || '').toLowerCase();
    const haystack = `${path} ${title} ${excerpt}`;
    if (haystack.includes(q)) return true;
    return tokens.every((tok) => haystack.includes(tok));
  });
}

const MIN_CATEGORIES_FOR_TAB_ROW = 2;
const MIN_SUBFOLDERS_FOR_TAB_ROW = 2;

/**
 * Build navigable group → category structure with file counts (search-aware).
 */
export function buildDocumentCategoryBlocks(categoryGroups, grouped, fileQuery, documentTitle) {
  const blocks = [];

  for (const group of categoryGroups) {
    const categories = group.categories
      .map((cat) => {
        const files = filterDocsByQuery(grouped[cat.id] || [], fileQuery, documentTitle);
        if (!files.length) return null;
        return { cat, files };
      })
      .filter(Boolean);

    if (!categories.length) continue;

    blocks.push({
      groupId: group.id,
      groupLabel: group.label,
      categories,
      fileCount: categories.reduce((sum, { files }) => sum + files.length, 0),
    });
  }

  return blocks;
}

export function shouldShowGroupTabs(blocks) {
  return blocks.length > 1;
}

export function shouldShowCategoryTabs(categories, fileCount) {
  return categories.length >= MIN_CATEGORIES_FOR_TAB_ROW && fileCount >= 4;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export function extractSubfolderKey(path) {
  const parts = String(path || '').replace(/\\/g, '/').split('/').filter(Boolean);
  if (parts.length < 2) return null;
  return parts.length >= 3 ? parts[parts.length - 2] : parts[0];
}

function humanizeSubfolderLabel(folder) {
  return String(folder || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDayMonth(day, monthIndex, year) {
  const month = MONTH_NAMES[Math.max(0, Math.min(11, monthIndex - 1))];
  if (!month) return `${day} ${year}`.trim();
  return `${Number(day)} ${month} ${year}`.trim();
}

/** Turn raw folder names into human-friendly album titles. */
export function parseAlbumFolderName(folderId) {
  const raw = String(folderId || '').replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  const lower = raw.toLowerCase();

  const retreatMatch = lower.match(
    /(\d{1,2})[-\s](\d{1,2})\.(\d{1,2})\.?(\d{4})?\.?\s*(\d{4})?\s*lab\s*retreat\s*nuuksio/
  );
  if (retreatMatch) {
    const [, startDay, endDay, month, yearAttached, yearSpaced] = retreatMatch;
    const year = yearAttached || yearSpaced || (Number(month) >= 9 ? '2025' : '2024');
    const start = formatDayMonth(startDay, Number(month), year);
    const end = formatDayMonth(endDay, Number(month), year);
    return {
      title: 'Lab Retreat · Nuuksio',
      subtitle: start === end ? start : `${start} – ${end}`,
      kind: 'retreat',
      sortKey: `${year}-${month.padStart(2, '0')}-${startDay.padStart(2, '0')}`,
    };
  }

  if (/photoshoot/i.test(lower)) {
    const when = raw.match(/(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}/i);
    return {
      title: 'Lab Photoshoot',
      subtitle: when ? when[0] : raw.replace(/färkkilä lab photoshoot/i, '').trim() || null,
      kind: 'photoshoot',
      sortKey: when?.[0] || raw,
    };
  }

  if (/group photo/i.test(lower)) {
    const year = raw.match(/\b(20\d{2})\b/)?.[1];
    return {
      title: 'Group Photo',
      subtitle: year ? `Biomedicum · ${year}` : 'Team portrait',
      kind: 'group',
      sortKey: year || raw,
    };
  }

  if (/halloween/i.test(lower)) {
    return { title: 'Halloween Party', subtitle: null, kind: 'event', sortKey: raw };
  }

  if (/grilling/i.test(lower)) {
    return { title: 'Grilling Party', subtitle: null, kind: 'event', sortKey: raw };
  }

  const generic = humanizeSubfolderLabel(folderId);
  return { title: generic, subtitle: null, kind: 'folder', sortKey: generic };
}

/** Nested albums within a category — not top-level tabs. */
export function deriveSubfolderAlbums(files) {
  if (!files?.length) return [];

  const counts = new Map();
  for (const doc of files) {
    const key = extractSubfolderKey(doc.path);
    if (!key) continue;
    counts.set(key, (counts.get(key) || 0) + 1);
  }

  if (counts.size < MIN_SUBFOLDERS_FOR_TAB_ROW) return [];

  return [...counts.entries()]
    .map(([id, count]) => {
      const meta = parseAlbumFolderName(id);
      return {
        id,
        count,
        title: meta.title,
        subtitle: meta.subtitle,
        kind: meta.kind,
        sortKey: meta.sortKey || id,
      };
    })
    .sort((a, b) => String(b.sortKey).localeCompare(String(a.sortKey)));
}

/** @deprecated Use deriveSubfolderAlbums */
export function deriveSubfolderTabs(files) {
  return deriveSubfolderAlbums(files).map((album) => ({
    id: album.id,
    label: album.subtitle ? `${album.title} · ${album.subtitle}` : album.title,
    count: album.count,
  }));
}

export function filterFilesBySubfolder(files, subfolderId) {
  if (!subfolderId) return files;
  return files.filter((doc) => extractSubfolderKey(doc.path) === subfolderId);
}
