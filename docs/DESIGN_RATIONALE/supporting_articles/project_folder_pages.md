# Project Folder Pages — Design Support

## What this supports in OMEIA

The **Project files** tab inside an individual project workspace (`WorkspaceScreen` → `folders`). Gives each project a professional ELN-style hub without changing main site navigation.

## Behaviors backed by research

| OMEIA feature | ELN inspiration | Why |
|---------------|-----------------|-----|
| `ProjectFolderPage` header (name, code, status, lead, counts) | SciNote project dashboard, Labguru project header | Researchers expect project context before browsing files |
| Left `DocumentFolderTree` scoped to `projects/{code}` | SciNote nested folders, LabArchives tree | Matches on-disk project layout under `/projects` |
| `DocumentFolderBreadcrumb` | Universal ELN path trail | Orientation in deep folder structures |
| Files / Notes / Activity section tabs | Benchling entries, eLabJournal studies | Separates file inventory from narrative work (Notes/Activity stubbed) |
| `path_prefix` document search | Internal — same as Document Library folder tree | Consistent backend filter across library and project scopes |
| `summarizeProjectFolderTree()` | — | Quick stats in header without extra API round-trip |

## Category

**Navigation / IA** — project-scoped file browsing inside portfolio workspace.

## Related articles

- [document_library_folder_tree.md](./document_library_folder_tree.md) — shared tree components and `path_prefix`
- [../eln_project_folder_research.md](../eln_project_folder_research.md) — full product comparison

## Code entry points

- `web/src/features/projects/components/ProjectFolderPage.jsx`
- `web/src/lib/projectFolderPage.js`
- `web/src/pages/WorkspaceScreen.jsx` (tab `folders`)
- `web/src/features/projects/hooks/useWorkspaceTabs.js`
