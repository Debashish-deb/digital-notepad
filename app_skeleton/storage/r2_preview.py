"""deprecated_storage_provider: cloudflare_r2 — removed from architecture; stub retained for audit only."""
from __future__ import annotations

import os
from typing import Any

# deprecated_storage_provider — do not configure in production (.env.example documents removal)


def is_configured() -> bool:
    return False


def preview_url_for_key(preview_key: str) -> str | None:
    """Deprecated: use Supabase Storage or backend-generated previews instead."""
    return None


def public_status() -> dict[str, Any]:
    return {
        "provider_id": "cloudflare_r2",
        "configured": False,
        "deprecated": True,
        "deprecated_storage_provider": True,
        "role": "removed",
        "message": "Cloudflare R2 removed from platform architecture; use datacloud_webdav + supabase_storage.",
    }
