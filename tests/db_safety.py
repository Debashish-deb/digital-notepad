"""Database test safety helpers — never route pytest to production Supabase by default."""
from __future__ import annotations

import os
import socket
from functools import lru_cache
from typing import Callable, TypeVar
from urllib.parse import urlparse

import pytest

F = TypeVar("F", bound=Callable[..., object])

PRODUCTION_SUPABASE_HOST_HINTS = (
    "pooler.supabase.com",
    ".supabase.co",
)

SKIP_REASON_NO_DB = (
    "Test database unavailable. Set TEST_DATABASE_URL (or TEST_SUPABASE_URL) "
    "or local POSTGRES_CONN, then start Postgres. "
    "Production Supabase is blocked during pytest unless OMEIA_ALLOW_PRODUCTION_DB_TESTS=1."
)


def is_pytest_running() -> bool:
    return os.getenv("OMEIA_PYTEST", "").strip().lower() in ("1", "true", "yes")


def production_db_tests_allowed() -> bool:
    return os.getenv("OMEIA_ALLOW_PRODUCTION_DB_TESTS", "").strip().lower() in ("1", "true", "yes")


def _conn_host(conn_str: str) -> str:
    try:
        return (urlparse(conn_str).hostname or "").lower()
    except Exception:
        return ""


def looks_like_production_supabase(conn_str: str) -> bool:
    host = _conn_host(conn_str)
    if not host:
        return False
    return any(hint in host for hint in PRODUCTION_SUPABASE_HOST_HINTS)


@lru_cache(maxsize=1)
def resolve_test_postgres_conn() -> str:
    """Resolve the Postgres DSN pytest should use (never silent production fallback)."""
    test_url = (
        os.getenv("TEST_DATABASE_URL", "").strip()
        or os.getenv("TEST_SUPABASE_URL", "").strip()
    )
    if test_url:
        return test_url

    local = os.getenv("POSTGRES_CONN", "").strip()
    if local:
        return local

    if production_db_tests_allowed():
        from app_skeleton.api.supabase_config import postgres_conn

        return postgres_conn()

    # Default local dev DSN — same as supabase_config fallback, but explicit in tests.
    return "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai"


@lru_cache(maxsize=4)
def postgres_reachable(conn_str: str | None = None, timeout: float = 2.5) -> bool:
    dsn = (conn_str or resolve_test_postgres_conn()).strip()
    if not dsn:
        return False
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=max(1, int(timeout))) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        host = _conn_host(dsn)
        port = urlparse(dsn).port or 5432
        if not host:
            return False
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return False
        except OSError:
            return False


def skip_if_no_database(reason: str | None = None) -> None:
    if not postgres_reachable():
        pytest.skip(reason or SKIP_REASON_NO_DB)


requires_database = pytest.mark.requires_database

requires_production_db = pytest.mark.skipif(
    not production_db_tests_allowed(),
    reason="Set OMEIA_ALLOW_PRODUCTION_DB_TESTS=1 to run production Supabase integration tests.",
)
