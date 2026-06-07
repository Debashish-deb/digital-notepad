# UI Metadata Display Plan

## Level 1 — File list row (minimal)

- File type icon
- **display_title** (primary)
- **short_title** fallback on narrow layouts
- Muted **original filename** only when different from display title
- One breadcrumb: project category OR cleaned category
- Modified date, size
- **Max 3 badges** (priority: Not indexed → Preview missing → Duplicate → Needs review → Unknown type)

## Level 2 — Preview panel

- display_title + original filename
- Path breadcrumb
- document_role + 2–4 scientific tags
- Extraction / index status
- Duplicate warning if applicable
- Text/thumbnail preview
- Related files (same project, assay, duplicate group)
- **View full metadata** button → drawer

## Level 3 — Details drawer

All enriched fields from `suggested_metadata` / `approved_metadata`, metadata score, review status, duplicate plan, rename suggestion.

## Level 4 — Admin / review

Dense tables from CSV queues: duplicates, unknown types, low confidence, redigitalization.

## Not shown in default UI

checksum, internal confidence breakdown, raw JSON metadata_json, vector IDs, full alias lists (search only).
