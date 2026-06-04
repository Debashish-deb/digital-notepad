# 18 — DataCloud folder validation

**Root:** `/farkkila/LAB-ASSISTANT-PLATFORM`  
**Rule:** Scan and map only. **Do not** auto-delete, move, or rename existing folders/files.

## Expected top-level tree (user-provided)

Validate presence via `GET /api/storage/datacloud/scan?relative_path=` (depth-limited):

| Folder | Purpose |
|--------|---------|
| `00_ADMIN` | Policies, governance, platform admin |
| `01_PLATFORM` | OMEIA platform assets, configs (non-secret) |
| `02_PROJECTS` | Project portfolios and digital-twin inputs |
| `03_RESEARCH_HUB` | Cross-project research materials |
| `04_COMPUTATIONAL` | HPC scripts, environments, pipeline defs |
| `05_CYCIF_IMAGING` | CyCIF / WSI / masks (large binaries) |
| `06_WET_LAB` | Protocols, reagents, wet-lab files |
| `07_ORDERS_PROCUREMENT` | Billing, orders (restricted) |
| `08_PERSONNEL` | HR-adjacent docs (restricted) |
| `09_SOCIAL_MISC` | Lab social memory |
| `10_KNOWLEDGE_BASE` | Curated docs for RAG |
| `11_NOTEBOOK_WIKI` | Living notebook exports |
| `12_TASKS_DECISIONS` | Task/decision registers |
| `20_CLINICAL_RESTRICTED` | Clinical — metadata-first, tight RBAC |
| `99_ARCHIVE` | Cold storage / superseded exports |

**NEEDS_USER_DECISION:** Confirm exact folder names match live DataCloud; adjust table after first successful scan.

## Validation procedure

1. Set DataCloud env (see `configs/DATACLOUD_WEBDAV_SETUP.md`).
2. Call `GET /api/storage/datacloud/list` at root — compare children to table above.
3. For each missing expected folder: record in validation report as `missing_on_datacloud` (do not create without approval).
4. For extra folders on DataCloud: record as `extra_on_datacloud` — map proposal only.
5. Conflicts (same logical role, two folders): set `needs_user_decision` on `storage_objects` / vault rows.

## Local mirror mapping

| Local (dev) | DataCloud logical |
|-------------|-------------------|
| `database/projects/` | `02_PROJECTS/` |
| `database/WET_LAB/` | `06_WET_LAB/` |
| `database/OVERVIEW/` | `00_ADMIN/` or `08_PERSONNEL/` (NEEDS_USER_DECISION) |

## Safe operations

| Op | Automation |
|----|------------|
| PROPFIND scan | Yes |
| Manifest export | Yes |
| Metadata upsert | Yes |
| mkdir/upload | Admin-approved jobs only |
| delete/move/rename | **Never** without explicit user ticket |
