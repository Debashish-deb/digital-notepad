"""Production connector readiness (no secrets in responses)."""
from __future__ import annotations

import os

from omeia.api.firebase_app import firebase_configured
from omeia.api.firebase_config import firebase_project_metadata
from omeia.storage import datacloud_webdav, pdrive_smb


def supabase_hosted_configured() -> bool:
    from omeia.api.supabase_config import supabase_configured

    return supabase_configured()


def _supabase_sync_block() -> dict:
    from omeia.api.supabase_sync import supabase_sync_status

    return supabase_sync_status()


def _firebase_initialized() -> bool:
    try:
        import firebase_admin
        return bool(firebase_admin._apps)
    except ImportError:
        return False


def production_connectors_summary() -> dict:
    """Flags for Administration / health — primary storage: DataCloud + P-drive."""
    supabase_storage_ready = bool(
        os.getenv("SUPABASE_URL", "").strip()
        and (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
            or os.getenv("SERVICE_ROLE_KEY", "").strip()
        )
    )
    return {
        "firebase": {
            **firebase_project_metadata(),
            "configured": firebase_configured(),
            "initialized": _firebase_initialized(),
            "auth_disabled": os.getenv("PLATFORM_AUTH_DISABLED", "true").lower() in ("1", "true", "yes"),
            "service_account_configured": bool(
                os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
                or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
                or os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
            ),
        },
        "supabase": {
            "project_name": os.getenv("SUPABASE_PROJECT_NAME", "farkki digital platform").strip(),
            "project_ref": os.getenv("SUPABASE_PROJECT_REF", "ccpvupyiqxubcupvtrtp").strip(),
            "region": os.getenv("SUPABASE_REGION", "eu-central-1").strip(),
            "url": os.getenv("SUPABASE_URL", "https://ccpvupyiqxubcupvtrtp.supabase.co").strip(),
            "hosted_configured": supabase_hosted_configured(),
            "has_anon_key": bool(os.getenv("SUPABASE_ANON_KEY", "").strip()),
            "has_service_role_key": bool(
                os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
                or os.getenv("SERVICE_ROLE_KEY", "").strip()
            ),
            "db_password_set": bool(os.getenv("SUPABASE_DB_PASSWORD", "").strip()),
            "pooler_host": os.getenv("SUPABASE_POOLER_HOST", "aws-1-eu-central-1.pooler.supabase.com"),
            "dev_fallback": "local POSTGRES_CONN when SUPABASE_DB_PASSWORD unset",
            "storage_optional_small_files": supabase_storage_ready,
            "supabase_sync": _supabase_sync_block(),
        },
        "storage_primary": {
            "datacloud_webdav": {
                **datacloud_webdav.public_status(),
                "required_for_production_files": True,
            },
            "pdrive_smb": {
                **pdrive_smb.public_status(),
                "required_for_production_files": False,
            },
            "supabase_storage": {
                "provider_id": "supabase_storage",
                "configured": supabase_storage_ready,
                "required_for_production_files": False,
                "role": "small_files_previews",
            },
        },
    }
