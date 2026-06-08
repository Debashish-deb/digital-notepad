# ELN Folder Taxonomy Research (Top 10 Comparison)

Survey of how leading electronic lab notebooks organize projects, folders, and files — informing OMEIA Document Library folder navigation (not main site tabs).

## Summary table

| Product | Hierarchy model | Navigation pattern | Move / organize | URL |
|---------|-----------------|--------------------|-----------------|-----|
| **Benchling** | Project → folders → entries | Project-centric hub; registry-linked entities | Drag-and-drop, bulk move in project tree | https://www.benchling.com/products/notebook |
| **SciNote** | Team → project → nested folders | One level at a time in sidebar; move dialog | Folder move dialog, nested project folders | https://scinote.net/features/ |
| **Labguru** | Project → folders → experiments | Project dashboard with folder sidebar | Experiments assigned to folders | https://www.labguru.com/electronic-lab-notebook |
| **eLabJournal** | Project groups → studies → items | Grouped studies under organizational units | Study-level organization within groups | https://www.elabjournal.com/ |
| **RSpace** | Workspace → notebook → document | Workspace tree; document-centric | Import/export, notebook grouping | https://www.researchspace.com/ |
| **LabArchives** | Notebook → folder → page | Classic notebook hierarchy | Folder creation, page move | https://www.labarchives.com/ |
| **Signals Notebook** | Project → experiment → section | PerkinElmer project workflow | Template-driven experiment folders | https://www.perkinelmer.com/product/signals-notebook |
| **eLabFTW** | Team → items / experiments | Open-source; tag + category hybrid | Category tags plus folder paths | https://www.elabftw.net/ |
| **Sapio Sciences** | LIMS + ELN unified hierarchy | Sample-centric with document attachments | Plate/sample linked documents | https://www.sapiosciences.com/ |
| **CDD Vault** | Vault → project → protocol/assay | Registration-first; documents on entities | Molecule/protocol linked files | https://www.collaborativedrug.com/pages/vault |

## Patterns adopted in OMEIA

### 1. Scoped folder root per library context (SciNote / Labguru)

When a user opens Wet Lab, Orders, or Overview in the Document Library, the left tree is **rooted** at the matching disk folder (`WET_LAB`, `ORDERS & RELATED INFORMATION`, `Overview`, etc.) rather than showing the entire repository. This mirrors SciNote’s project-scoped sidebar and Labguru’s project → folder drill-down.

### 2. Expandable tree with file counts (LabArchives / Benchling)

Folders show **indexed file counts** from `category_tree_folder_derived.json`, similar to Benchling and LabArchives folder badges that communicate content density before opening.

### 3. Breadcrumb for current folder (eLabJournal / RSpace)

Selecting a deep folder shows a **breadcrumb trail** so users never lose context — aligned with eLabJournal study paths and RSpace workspace location bars.

### 4. Flat file list inside a folder (SciNote)

When a folder is active, the file list disables document-type grouping (`groupByDocumentType={false}`) and lists contents flatly, matching SciNote’s “contents of this folder” view.

### 5. Semantic taxonomy chips preserved (eLabFTW / CDD Vault)

Taxonomy scope chips remain as **semantic shortcuts** (protocol-only, CyCIF app page, orders archive) layered on top of folder paths — similar to eLabFTW tags and CDD entity filters that coexist with physical organization.

## Explicit non-goals

- **No change to main navigation tabs** — site IA stays in `navigation.js`; folder tree is Document Library only.
- **No Benchling-style entity registry** — OMEIA does not model registry objects in this iteration; only path-derived folders.
- **No drag-and-drop move** — read-only browse; file moves remain out of scope.

## OMEIA implementation references

- Tree UI: `web/src/features/documents/components/DocumentFolderTree.jsx`
- API filter: `path_prefix` in `omeia/api/document_library_service.py`
- Preset roots: `web/src/lib/documentExplorerPresets.js`

See [document_library_folder_tree.md](./supporting_articles/document_library_folder_tree.md) for the feature mapping article.
