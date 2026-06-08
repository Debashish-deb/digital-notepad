# Supporting Articles Index

Categorized design rationale articles for OMEIA. Each entry explains **what app behavior it supports** and how it is categorized.

## Document Library & taxonomy

| Article | What it supports | Category |
|---------|------------------|----------|
| [document_library_folder_tree.md](./document_library_folder_tree.md) | Left-panel folder tree, breadcrumbs, `path_prefix` search filter, explorer presets | **Navigation / IA** |

## ELN industry research

| Article | What it supports | Category |
|---------|------------------|----------|
| [../eln_folder_taxonomy_research.md](../eln_folder_taxonomy_research.md) | Top-10 ELN comparison; justification for scoped roots and flat folder contents | **Research / UX** |

## Categorization rules

Articles are grouped by concern:

- **Navigation / IA** — how users move through files and scopes
- **Research / UX** — external product comparisons and citations
- **API / data** — backend filters and inventory-derived trees (see code comments and `category_tree_*.json`)

When adding a new article:

1. Place it in this folder (or parent for surveys)
2. Add a row to the table above with category
3. Link from [../README.md](../README.md)
