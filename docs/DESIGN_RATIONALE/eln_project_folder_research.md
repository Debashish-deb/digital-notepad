# ELN Project Folder Hub — Industry Research

Survey of how leading electronic lab notebooks organize **individual project workspaces** (not global libraries). Used to design OMEIA `ProjectFolderPage`.

## Products compared

| Product | Project hub pattern | Folder hierarchy | Header / metadata | Sources |
|---------|---------------------|------------------|-------------------|---------|
| **Benchling** | Project-centric hub; folders + entries + registry | Nested folders under project | Project name, collaborators, status | [Benchling Projects](https://www.benchling.com/products/notebook) |
| **SciNote** | Projects → folders → experiments → tasks | Deep nested folders; move between folders | Project dashboard, team, activity | [SciNote Projects](https://scinote.net/features/projects/) |
| **Labguru** | Projects → milestones → experiments | Folder tree per project | PI, dates, milestones | [Labguru ELN](https://www.labguru.com/electronic-lab-notebook) |
| **eLabJournal** | Project groups → studies → experiments | Study-level grouping | Group metadata, audit trail | [eLabJournal](https://www.elabjournal.com/) |
| **RSpace** | Workspace notebooks + folder tree | User-defined folder nesting | Notebook metadata, sharing | [RSpace](https://www.researchspace.com/) |
| **LabArchives** | Notebook folders hierarchy | Classic tree navigation | Notebook title, contributors | [LabArchives](https://www.labarchives.com/) |
| **Signals Notebook** | Project-centric organization | Project → content sections | Project summary, team | [Revvity Signals](https://revvity.com/signals/notebook) |
| **Sapio Sciences** | Sample + experiment tracking under projects | Structured project records | LIMS-style project header | [Sapio ELN](https://www.sapiosciences.com/electronic-lab-notebook/) |

## Patterns adopted in OMEIA

1. **Project header band** — name, code, status badge, lead, file/folder counts (SciNote, Labguru, Benchling).
2. **Left folder tree** scoped to `projects/{CODE}/` — reuse Document Library tree component (SciNote, LabArchives).
3. **Breadcrumb drill-down** — Project › subfolder › file (universal ELN pattern).
4. **Section tabs** — Files (live), Notes / Activity (stubs for future twin integration) (Benchling entries, Labguru milestones).
5. **Three-column layout** — tree | file list | metadata panel (professional ELN file browsers).

## Patterns not copied

- Benchling registry / entity graph (out of scope for file library).
- SciNote experiment/task objects (OMEIA uses digital twin sections separately).
- Full LIMS sample lineage (Sapio) — handled elsewhere in OMEIA wet-lab modules.

## OMEIA implementation

- Component: `web/src/features/projects/components/ProjectFolderPage.jsx`
- Workspace tab: **Project files** (`folders`) in `WorkspaceScreen.jsx`
- Data: `category_tree_folder_derived.json` + `path_prefix` document search
