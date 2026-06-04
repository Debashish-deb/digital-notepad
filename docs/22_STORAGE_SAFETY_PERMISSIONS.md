# 22 — Storage safety & permissions

## Trust boundaries

| Zone | Trust level | Exposure |
|------|-------------|----------|
| Browser | Untrusted | Logical paths, public Firebase config |
| FastAPI | Trusted | WebDAV creds, mount paths, `original_path` |
| DataCloud / P-drive | Data plane | Binary blobs |
| Supabase | Control plane | Metadata, allowlist, audit |

## Request flow (production)

1. `Authorization: Bearer <Firebase ID token>`
2. Verify with Firebase Admin (`auth_firebase.py`)
3. Email ∈ `platform.allowed_email` (or `PLATFORM_ADMIN_EMAILS` bootstrap)
4. Sensitivity check (`ALLOW_PATIENT_DATA`, clinical paths)
5. Connector operation

Dev: `PLATFORM_AUTH_DISABLED=true` skips steps 1–3.

## Data rules

- **No** WebDAV credentials or raw DAV URLs in frontend env.
- **No** `original_path` in JSON for React.
- **No** auto-delete/move/rename on DataCloud (see doc 18).
- **No** large binaries in Supabase Storage (use DataCloud); cap previews in `supabase_storage`.
- OME-TIFF / masks: `vector_status = metadata_summary_only`.

## Sensitivity

| Path pattern | Default |
|--------------|---------|
| `20_CLINICAL_RESTRICTED/**` | Block external AI; review required |
| `07_ORDERS_PROCUREMENT/**` | Metadata-first |
| `08_PERSONNEL/**` | Tentative until HR confirm |

## Audit

- `platform.vault_audit_event` (115) for classification changes.
- Ingestion jobs record actor in `config` jsonb when auth enabled.

## NEEDS_USER_DECISION

- Final RBAC matrix per domain (Supabase RLS policies) when hosted project is live.
- Second admin for Digital Pathology if required beyond `PLATFORM_ADMIN_EMAILS`.
