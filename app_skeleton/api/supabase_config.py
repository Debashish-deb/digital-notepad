"""Supabase project metadata and Postgres connection resolution."""
from __future__ import annotations

import os
from urllib.parse import quote_plus

DEFAULT_PROJECT_REF = "ccpvupyiqxubcupvtrtp"
DEFAULT_REGION = "eu-central-1"
DEFAULT_POOLER_HOST = "aws-1-eu-central-1.pooler.supabase.com"


def supabase_project_ref() -> str:
    return os.getenv("SUPABASE_PROJECT_REF", DEFAULT_PROJECT_REF).strip()


def supabase_url() -> str:
    return os.getenv(
        "SUPABASE_URL",
        f"https://{supabase_project_ref()}.supabase.co" if supabase_project_ref() else "",
    ).strip()


def postgres_conn() -> str:
    """
    Prefer hosted Supabase pooler when SUPABASE_DB_PASSWORD is set;
    otherwise use POSTGRES_CONN (local Docker dev).
    """
    explicit = os.getenv("POSTGRES_CONN", "").strip()
    password = os.getenv("SUPABASE_DB_PASSWORD", "").strip()
    ref = supabase_project_ref()
    if password and ref:
        host = os.getenv("SUPABASE_POOLER_HOST", DEFAULT_POOLER_HOST).strip()
        port = os.getenv("SUPABASE_POOLER_PORT", "5432").strip()
        user = os.getenv("SUPABASE_DB_USER", f"postgres.{ref}").strip()
        dbname = os.getenv("SUPABASE_DB_NAME", "postgres").strip()
        return (
            f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{dbname}"
        )
    return explicit or "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai"


def _service_role_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SERVICE_ROLE_KEY", "").strip()
    )


def supabase_configured() -> bool:
    return bool(supabase_url() and _service_role_key())


def supabase_db_configured() -> bool:
    return bool(os.getenv("SUPABASE_DB_PASSWORD", "").strip()) or bool(
        os.getenv("POSTGRES_CONN", "").strip()
    )
