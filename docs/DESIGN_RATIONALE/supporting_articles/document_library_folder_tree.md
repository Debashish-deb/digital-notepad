# Document Library Folder Tree

**Category:** Navigation / IA  
**Supports:** Document Library explorer only (`ScientificFileExplorer`, `LabDocumentExplorer`)

## Problem

OMEIA indexes thousands of lab files across `WET_LAB`, `projects`, `Overview`, orders archives, and social folders. Taxonomy chips and domain tabs help semantic filtering but do not mirror how researchers already store files on disk — the pattern every major ELN still provides (see [eln_folder_taxonomy_research.md](../eln_folder_taxonomy_research.md)).

## Solution

A **left-panel folder tree** built from `category_tree_folder_derived.json`, scoped per navigation preset:

| Preset context | `folderTreeRoot` |
|----------------|------------------|
| Wet lab (files, protocols, inventory, CyCIF) | `WET_LAB` |
| Orders (all sub-tabs) | `ORDERS & RELATED INFORMATION` |
| Overview (except social) | `Overview` |
| Overview → social | `SOCIAL & MISCELLANEOUS` |
| Projects | `projects` |
| Full library / all files | `null` (all top-level roots) |

### User flow

1. User opens a scoped Document Library view (e.g. Lab Operations).
2. Tree loads via `GET /api/document-library/category-trees` → `category_tree_folder_derived.nodes`.
3. User expands/selects a folder → `path_prefix` sent to search/facets APIs.
4. Breadcrumb appears; clicking a segment navigates up.
5. File list shows **flat contents** for that folder; taxonomy chips still apply.

## ELN pattern mapping

| ELN pattern | OMEIA component |
|-------------|-----------------|
| SciNote nested project folders | `DocumentFolderTree` expand/collapse |
| Labguru project → folder hierarchy | `folderTreeRoot` in `documentExplorerPresets.js` |
| eLabJournal group / study paths | `DocumentFolderBreadcrumb` |
| Benchling project hub file counts | `file_count` badges on tree nodes |

## Technical artifacts

| Layer | File | Role |
|-------|------|------|
| Data | `config/env/document_library/category_tree_folder_derived.json` | Flat nodes with `path`, `label`, `depth`, `file_count` |
| API | `omeia/api/document_library_service.py` | `_apply_filters` → `path_prefix` on `logical_path` |
| API | `omeia/api/routers/document_library.py` | `path_prefix` query param on search + facets |
| Client | `web/src/services/documentLibraryClient.js` | `fetchCategoryTrees()` |
| Tree build | `web/src/lib/documentFolderTree.js` | `buildFolderTreeFromNodes(nodes, rootPrefix)` |
| UI | `DocumentFolderTree.jsx`, `DocumentFolderBreadcrumb.jsx` | Tree + breadcrumb |
| Layout | `ScientificFileExplorer.css` | 3-column: tree \| list \| metadata |
| State | `useDocumentLibrary.js` | `selectedFolderPath` → `path_prefix` |

## Boundaries

- Does **not** modify `web/src/config/navigation.js` main tabs.
- Does **not** replace smart taxonomy chips — they remain parallel filters.
- Does **not** implement file move/rename (read-only browse).

## Related citations

See [eln_folder_taxonomy_research.md](../eln_folder_taxonomy_research.md) for vendor URLs and comparison table.
