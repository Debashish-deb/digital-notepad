# Metadata Rules

## Project folders (structural truth)

1. Never move, rename, or flatten project folders.
2. Never replace `project_category_original` with global categories.
3. Enrich search, display titles, scientific tags, and status inside existing folders.
4. `do_not_change_project_category` is always true for `projects/*` paths.

## Non-project files

1. Propose `cleaned_domain` / `cleaned_category` / `cleaned_subcategory` only in suggested metadata.
2. Merge tiny categories in browse proposals, not on disk.
3. Physical rename/move requires human approval via CSV review queues.

## Display titles

1. `display_title` is UI-only; `original_filename` remains searchable.
2. `rename_needed=no` when existing name is already clear.
3. Project pattern: `[Project] — [Folder Category] — [Topic] — [Role] — [Date]`

## Duplicates

1. Never auto-delete.
2. `exact_duplicate`: one canonical copy; safe duplicates may be hidden from browse.
3. `version_variant` / `same_name_different_content`: human review required.
4. `system_artifact`: hide from normal browse; deletion only after review.

## Classification signals (priority)

1. Existing inventory metadata
2. Project folder rule
3. Folder path
4. Filename + extension
5. Extracted text / processed twin
6. Heuristic rules (no silent overwrite of approved metadata)

## Review

- `auto_high_confidence` ≥0.82
- `auto_medium_confidence` ≥0.60
- `needs_human_review` otherwise or unknown type
