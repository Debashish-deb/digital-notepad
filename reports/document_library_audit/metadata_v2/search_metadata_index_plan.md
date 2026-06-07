# Search Metadata Index Plan

## Indexed fields (weighted)

| Weight | Field |
|--------|-------|
| 5.0 | exact `original_filename` |
| 4.5 | `display_title` |
| 4.0 | `search_aliases` |
| 3.5 | `project_id` / `project_name` |
| 3.0 | `current_category` (project folder category) |
| 3.0 | `sample_id` |
| 2.5 | `assay` / `platform` |
| 2.5 | `document_role` |
| 2.0 | `tissue_or_site` / `marker_terms` |
| 2.0 | extracted text / `processed_excerpt` |
| 1.5 | `section` / `cleaned_category` |
| 1.0 | `logical_path` (legacy path search) |

## Behavior

- Fuzzy: token overlap on display title + aliases
- Scoped: respect active page `section` / project context filters
- Legacy: original filename and full path always searchable
- Hidden: duplicate copies excluded unless Duplicates view

## Implementation

`document_library_service._search_blob()` merges display_title, search_aliases, and enriched fields into the search blob. Vector index should mirror the same alias expansion when embeddings are rebuilt.
