/** Load lab database section twins from public/processed (works without API). */

import {
  cleanExtractedText,
  humanizeFilenameLabel,
  isJunkDisplayName,
} from './textCleanup.js';

const JUNK_TITLE_RE =
  /^(?:#+\s*)?(?:page\s*\d+(?:\s+of\s+\d+)?|slide\s*\d+|ppt\/slides\/|word\/document|\d{1,2}\.\d{1,2}\.\d{4})$/i;

export function humanizeFilename(name) {
  return humanizeFilenameLabel(name);
}

export function isJunkTitleLine(line) {
  const s = (line || '').trim();
  if (!s || s.length < 8) return true;
  if (JUNK_TITLE_RE.test(s)) return true;
  if (s.startsWith('### ') && (s.includes('/') || /\.xml$/i.test(s))) return true;
  if (s.startsWith('## Page ') || s.startsWith('## Slide ')) return true;
  return false;
}

/** Prefer filename-based labels over extractor scaffolding and junk first lines. */
export function documentDisplayTitle(doc) {
  const path = (doc.path || doc.relative_path || '').replace(/\\/g, '/');
  const fileName = path.split('/').pop() || '';
  const humanFile = humanizeFilenameLabel(fileName);

  const candidates = [doc.display_title, doc.title, doc.name]
    .map((v) => (v || '').trim().replace(/\s+/g, ' '))
    .filter(Boolean);

  for (const raw of candidates) {
    if (
      raw &&
      !isJunkTitleLine(raw) &&
      !isJunkDisplayName(raw, fileName) &&
      raw.length <= 120 &&
      raw.toLowerCase() !== humanFile.toLowerCase()
    ) {
      return raw;
    }
  }

  return humanFile;
}

export function documentDisplayExcerpt(doc, maxChars = 500) {
  const excerpt = (doc.excerpt || '').trim();
  if (!excerpt) return null;
  const cleaned = cleanExtractedText(excerpt.replace(/\s+/g, ' '), { maxChars });
  if (!cleaned || isJunkTitleLine(cleaned)) return null;
  return cleaned || null;
}

export function labDatabaseAssetUrl(relativeRoot, relativePath) {
  const root = (relativeRoot || '').replace(/\\/g, '/').replace(/\/$/, '');
  const file = (relativePath || '').replace(/\\/g, '/').replace(/^\//, '');
  const combined = [root, file].filter(Boolean).join('/');
  return `/database-static/${combined.split('/').map((seg) => encodeURIComponent(seg)).join('/')}`;
}

export function documentPreviewRow(doc, relativeRoot) {
  const path = (doc.path || doc.relative_path || '').replace(/\\/g, '/');
  return {
    path,
    name: doc.name || path.split('/').pop() || path,
    title: documentDisplayTitle(doc),
    excerpt: documentDisplayExcerpt(doc),
    extraction_status: doc.extraction_status || doc.status,
    extension: doc.extension,
    word_count: doc.word_count,
    open_url: relativeRoot && path ? labDatabaseAssetUrl(relativeRoot, path) : null,
  };
}

/** Map a processed twin JSON file to the shape returned by GET /api/lab/section/{id}. */
export function sectionDetailFromTwin(twin, sectionId) {
  if (!twin) return null;
  const docIndex = twin.document_index || [];
  const relativeRoot = twin.relative_root;
  const preview = docIndex.slice(0, 50).map((doc) => documentPreviewRow(doc, relativeRoot));
  const metrics = twin.metrics || {};
  const key = twin.storage_key || `lab__${sectionId}`;
  return {
    section_id: twin.section_id || sectionId,
    section_label: twin.section_label,
    description: twin.description,
    relative_root: relativeRoot,
    storage_key: key,
    source: 'public_processed_json',
    twin_file: `${key}.json`,
    metrics,
    processed_at: twin.processed_at,
    extraction: twin.extraction,
    document_index_count: docIndex.length,
    document_index_preview: preview,
    folder_tree: (twin.folder_tree || []).slice(0, 200),
    vault_asset_count: null,
  };
}

export async function fetchLabSectionProcessed(sectionId) {
  if (!sectionId) return null;
  const key = encodeURIComponent(`lab__${sectionId}`);
  try {
    const res = await fetch(`/processed/${key}.json`, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    console.warn('Lab section processed JSON unavailable', sectionId, e);
    return null;
  }
}

/** If API returns counts but an empty preview, rebuild from cached processed JSON. */
export async function hydrateSectionDocuments(data, sectionId) {
  const preview = data?.document_index_preview || [];
  if (preview.length > 0) {
    return {
      detail: data,
      documents: preview,
      docTotal: data.document_index_count ?? preview.length,
    };
  }
  const count = data?.document_index_count ?? 0;
  if (!count) {
    return { detail: data, documents: [], docTotal: 0 };
  }
  const twin = await fetchLabSectionProcessed(sectionId);
  const fallback = sectionDetailFromTwin(twin, sectionId);
  if (fallback?.document_index_preview?.length) {
    return {
      detail: { ...data, document_index_preview: fallback.document_index_preview },
      documents: fallback.document_index_preview,
      docTotal: fallback.document_index_count ?? count,
    };
  }
  return { detail: data, documents: [], docTotal: count };
}

export async function fetchLabProcessedSummary() {
  try {
    const res = await fetch('/processed/lab__manifest.json', { cache: 'no-store' });
    if (res.ok) return await res.json();
  } catch {
    // fall through
  }
  return null;
}

/** Client-side search over loaded twin chunks + document excerpts. */
export function searchLabTwinLocally(twin, query, limit = 20) {
  const q = (query || '').trim().toLowerCase();
  if (!q || !twin) return [];
  const tokens = q.split(/\s+/).filter((t) => t.length >= 2);
  if (!tokens.length) return [];

  const hits = [];
  const seen = new Set();

  for (const chunk of twin.vector_chunks || []) {
    const text = (chunk.text || '').toLowerCase();
    const score = tokens.reduce((s, t) => s + (text.includes(t) ? 3 : 0), 0);
    if (score <= 0) continue;
    const id = chunk.chunk_id || `${chunk.source_file}-${chunk.chunk_index}`;
    if (seen.has(id)) continue;
    seen.add(id);
    hits.push({
      section_id: twin.section_id,
      section_label: twin.section_label,
      chunk_id: id,
      source_file: chunk.source_file,
      chunk_index: chunk.chunk_index,
      text_preview: (chunk.text || '').slice(0, 1600),
      score,
      scope: 'lab',
    });
  }

  for (const doc of twin.document_index || []) {
    const blob = `${documentDisplayTitle(doc)} ${doc.path || ''} ${doc.excerpt || ''}`.toLowerCase();
    const score = tokens.reduce((s, t) => s + (blob.includes(t) ? 2 : 0), 0);
    if (score <= 0) continue;
    const id = `doc::${doc.path}`;
    if (seen.has(id)) continue;
    seen.add(id);
    hits.push({
      section_id: twin.section_id,
      section_label: twin.section_label,
      chunk_id: id,
      source_file: doc.path,
      text_preview: (documentDisplayExcerpt(doc) || documentDisplayTitle(doc) || '').slice(0, 1600),
      score,
      scope: 'lab',
    });
  }

  hits.sort((a, b) => b.score - a.score);
  return hits.slice(0, limit);
}

export function getChunkTextForFile(twin, relativePath) {
  if (!twin?.vector_chunks?.length || !relativePath) return null;
  const norm = relativePath.replace(/\\/g, '/');
  const parts = (twin.vector_chunks || [])
    .filter((c) => (c.source_file || '').replace(/\\/g, '/') === norm)
    .sort((a, b) => (a.chunk_index || 0) - (b.chunk_index || 0));
  if (!parts.length) return null;
  return parts.map((c) => c.text || '').join('\n\n');
}
