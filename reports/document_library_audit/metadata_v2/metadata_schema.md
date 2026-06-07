# OMEIA Document Library — Metadata Schema v2

Read-only enrichment layer. Physical files and paths are never modified by this schema.

## Layers

| Layer | Purpose |
|-------|---------|
| `current_metadata` | Truth from inventory scan (filename, path, domain, extraction) |
| `suggested_metadata` | Auto-enriched fields awaiting or passing review |
| `approved_metadata` | Human-approved overrides (empty until review) |

Production UI uses `approved_metadata` when present, else `suggested_metadata`.

## Field groups

### A. Identity
`asset_id`, `original_filename`, `normalized_filename`, `original_path`, `canonical_path`, `source_domain`, `source_section`, `source_page`, `checksum_sha256`, `duplicate_group_id`, `canonical_copy_asset_id`, `exists_locally`

### B. Display
`display_title`, `short_title`, `subtitle`, `professional_title`, `search_aliases`, `legacy_aliases`, `rename_needed`, `rename_confidence`, `rename_reason`, `suggested_filename_for_later`

### C. Structural
`is_project_file`, `domain`, `page_id`, `page_label`, `section`, `current_category`, `current_subcategory`, `folder_category`, `cleaned_domain`, `cleaned_category`, `cleaned_subcategory`, `category_confidence`, `category_source`, `category_review_status`

### D. Project overlay (project files only)
`project_id`, `project_name`, `project_root`, `project_category_original`, `project_category_normalized`, `project_folder_level_1/2/3`, `project_relative_path`, `do_not_change_project_category=yes`

**Rule:** `current_category` for project files equals `project_category_original`. Never overridden by cleaned taxonomy.

### E. Non-project overlay
`cleaned_domain`, `cleaned_category`, `cleaned_subcategory`, `suggested_browse_group`

### F. Scientific
`assay`, `platform`, `marker_terms`, `tissue_or_site`, `sample_id`

### G. Document role
Controlled vocabulary: protocol, SOP, instruction, inventory, presentation, manuscript, figure, spreadsheet, project_plan, project_log, system_artifact, unknown, …

### H. Digitalization
`extraction_status`, `has_text`, `has_preview`, `has_embedding`, `indexed_in_search`, `preview_status`, `needs_redigitalization`, `OCR_needed`

### I. Quality
`confidence_score`, `review_status`, `metadata_score`, `metadata_grade`, `duplicate_type`, `safe_to_hide_from_browse`, `unknown_type`

## Scoring

`metadata_score` 0–100 from weighted field presence. Grades: excellent ≥85, good ≥70, usable ≥55, weak ≥40, poor <40.
