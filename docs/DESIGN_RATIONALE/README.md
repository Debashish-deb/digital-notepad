# Design Rationale Index

This directory records **why** OMEIA features are shaped the way they are — grounded in product research, lab workflow constraints, and cited external references.

## Purpose

- Preserve design decisions that are not obvious from code alone
- Link implementation choices to ELN / LIMS industry patterns
- Give reviewers a single place to audit UX and taxonomy decisions

## Citation policy

1. **Primary sources preferred** — vendor documentation, product tours, published case studies, and peer-reviewed reviews of ELN systems.
2. **URLs required** — every external claim in a design article must include a stable link (product page, help center, or archived reference).
3. **OMEIA mapping required** — each article states which app surfaces it supports (Document Library, Project Data Pad, navigation scope, API filters, etc.).
4. **No navigation tab changes from research alone** — main site tabs in `web/src/config/navigation.js` are governed separately; Document Library folder UX applies only inside the library explorer.
5. **Living documents** — when behavior changes, update the supporting article in the same PR.

## Articles

| Document | Category | Supports in OMEIA |
|----------|----------|-------------------|
| [eln_folder_taxonomy_research.md](./eln_folder_taxonomy_research.md) | ELN industry survey | Document Library folder tree scope and hierarchy |
| [supporting_articles/INDEX.md](./supporting_articles/INDEX.md) | Supporting articles index | Cross-links all rationale docs |
| [supporting_articles/document_library_folder_tree.md](./supporting_articles/document_library_folder_tree.md) | Feature mapping | `DocumentFolderTree`, `path_prefix` API, presets |

## Related code

- `web/src/features/documents/components/ScientificFileExplorer.jsx`
- `web/src/lib/documentExplorerPresets.js`
- `omeia/api/document_library_service.py` (`path_prefix` filter)
- `config/env/document_library/category_tree_folder_derived.json`
