"""Lifespan-managed Postgres connection pool (psycopg_pool)."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg

LOGGER = logging.getLogger(__name__)

_pool: Any | None = None


def _pool_bounds() -> tuple[int, int]:
    min_size = max(1, int(os.getenv("POSTGRES_POOL_MIN", "1") or 1))
    max_size = max(min_size, int(os.getenv("POSTGRES_POOL_MAX", "10") or 10))
    return min_size, max_size


def init_pool(conninfo: str) -> None:
    """Open a shared pool; safe to call once at app startup."""
    global _pool
    conninfo = (conninfo or "").strip()
    if not conninfo:
        LOGGER.warning("Postgres pool skipped: empty connection string")
        return
    if _pool is not None:
        return
    try:
        from psycopg_pool import ConnectionPool

        min_size, max_size = _pool_bounds()
        _pool = ConnectionPool(
            conninfo,
            min_size=min_size,
            max_size=max_size,
            kwargs={"connect_timeout": 5},
            open=True,
        )
        LOGGER.info("Postgres pool opened (min=%s max=%s)", min_size, max_size)
    except Exception as exc:
        LOGGER.warning("Postgres pool unavailable, using direct connections: %s", exc)
        _pool = None


def close_pool() -> None:
    global _pool
    if _pool is not None:
        try:
            _pool.close()
        except Exception as exc:
            LOGGER.warning("Postgres pool close failed: %s", exc)
        _pool = None


def pool_available() -> bool:
    return _pool is not None


@contextmanager
def get_db_connection() -> Iterator[Any]:
    """Borrow a connection from the pool, or open a one-off connection."""
    if _pool is not None:
        with _pool.connection() as conn:
            yield conn
        return
    from app_skeleton.api.supabase_config import postgres_conn

    with psycopg.connect(postgres_conn(), connect_timeout=5) as conn:
        yield conn


# Aliases for explicit naming in new code
init_db_pool = init_pool
close_db_pool = close_pool
