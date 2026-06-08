"""Storage connector environment resolution (canonical names + backward-compat aliases)."""
from __future__ import annotations

import os

CANONICAL_DATACLOUD_ROOT = "/farkkila/LAB-ASSISTANT-PLATFORM"

# deprecated_storage_provider — do not use in new code or migrations
DEPRECATED_STORAGE_PROVIDERS: frozenset[str] = frozenset({"cloudflare_r2"})

VALID_STORAGE_PROVIDERS: frozenset[str] = frozenset({
    "datacloud_webdav",
    "pdrive_smb",
    "supabase_storage",
    "supabase_postgres",
    "local_database_mirror",
    "local_dev",
    "unknown",
})


def datacloud_webdav_base_url() -> str:
    return (
        os.getenv("DATACLOUD_WEBDAV_BASE_URL", "").strip()
        or os.getenv("DATACLOUD_WEBDAV_URL", "").strip()
    ).rstrip("/")


def datacloud_username() -> str:
    return (
        os.getenv("DATACLOUD_USERNAME", "").strip()
        or os.getenv("DATACLOUD_WEBDAV_USER", "").strip()
    )


def datacloud_app_password() -> str:
    return (
        os.getenv("DATACLOUD_APP_PASSWORD", "").strip()
        or os.getenv("DATACLOUD_WEBDAV_PASSWORD", "").strip()
    )


def datacloud_logical_root() -> str:
    root = os.getenv("DATACLOUD_ROOT", CANONICAL_DATACLOUD_ROOT).strip()
    return root or CANONICAL_DATACLOUD_ROOT


def pdrive_enabled() -> bool:
    val = os.getenv("PDRIVE_ENABLED", "").strip().lower()
    if val in ("0", "false", "no"):
        return False
    if val in ("1", "true", "yes"):
        return True
    return bool(pdrive_mount_path())


def pdrive_mount_path() -> str:
    return (
        os.getenv("PDRIVE_MOUNT_PATH", "").strip()
        or os.getenv("PDRIVE_SMB_ROOT", "").strip()
    )


def pdrive_logical_root() -> str:
    return (
        os.getenv("PDRIVE_LOGICAL_ROOT", "").strip()
        or "pdrive://"
    )
