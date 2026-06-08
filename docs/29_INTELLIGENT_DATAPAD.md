# 29 — Intelligent Data Pad

The **Data Pad** (Disk pad) is the project workspace file browser with an integrated section-scoped editor: safe writes, versioned backups, heading assists, and proofreading.

## Capabilities

| Feature | Description |
|---------|-------------|
| Section scope | Browse content library sections; banner shows section name and editable file count |
| Read / edit toggle | Preview indexed text; switch to edit for `.md`, `.txt`, `.html`, `.rtf` |
| Save with backup | Pre-write copy to `99_ARCHIVE/.datapad_backups/` or `{file}.omeia_backup.{timestamp}` |
| Conflict detection | `etag` from mtime+size; stale save returns **409** |
| Suggest headings | LLM (when configured) or rule-based outline improvements |
| Proofread | Grammar/spelling fixes with line diff before apply |
| Audit | `platform.datapad_edit_log` (sql/120) or fallback `vault_audit_event` |

## Safety (doc 22)

- Writes only under resolved `PROJECTS_ROOT` / `LAB_STORAGE_ROOT` project folders
- Path traversal blocked via `safe_relative_path`
- Originals are never deleted; backups created before overwrite when `create_backup=true`
- `DATAPAD_EDIT_ENABLED=false` disables all saves server-side

## Enable

1. Copy variables from `configs/.env.example`:
   - `DATAPAD_EDIT_ENABLED=true`
   - `DATAPAD_AI_ENABLED=true` (optional)
   - `GROQ_API_KEY` or `OPENAI_API_KEY` / `LLM_PROVIDER` for AI assists
2. Apply SQL: `sql/120_datapad_edits.sql` (local or Supabase migration)
3. Rebuild frontend: `cd apps/web && npm run build`
4. With production auth: `PLATFORM_AUTH_DISABLED=false` — Data Pad routes require Firebase Bearer token

Public config (no auth): `GET /api/datapad/config`

## API

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/datapad/document?project_code=&relative_path=` | Firebase when auth on |
| PUT | `/api/datapad/document` | Firebase when auth on |
| POST | `/api/datapad/suggest-headings` | Firebase when auth on |
| POST | `/api/datapad/proofread` | Firebase when auth on |
| POST | `/api/datapad/apply-patches` | Firebase when auth on |
| POST | `/api/datapad/restore-backup` | Firebase when auth on |
| GET | `/api/datapad/section-summary?project_code=&section_id=` | Firebase when auth on |

## Example user flow

1. Open **Workspace** → project **Data Pad**
2. Select section **Management & Planning** (banner: “Editing: …”, N editable files)
3. Click a `.md` file → preview loads from disk or index
4. Click **Edit** → toolbar (H1–H3, bold, list) and textarea
5. **Proofread** → review diff table → **Apply fixes** → **Save** (backup written automatically)
6. If another process changed the file: reload or **Revert** from recent backups list

## Implementation map

| Layer | Path |
|-------|------|
| Service | `omeia/api/datapad_service.py` |
| Routes | `omeia/api/main.py` |
| SQL | `sql/120_datapad_edits.sql` |
| API client | `apps/web/src/api/datapad.js` |
| UI | `DataPadEditor.jsx`, `ProjectFolderBrowser.jsx` |
| Tests | `tests/test_datapad_service.py` |

## AI requirements

- **Rules mode** (default): no API keys; basic heading/outline and typo patterns
- **LLM mode**: `DATAPAD_AI_ENABLED=true` and `GROQ_API_KEY` or configured `LLM_PROVIDER` via `llm_client.py`
- Mock/offline: LLM falls back to rules when providers fail
