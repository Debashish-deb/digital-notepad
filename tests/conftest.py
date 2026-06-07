"""Pytest session guards — block accidental production Supabase use during tests."""
from __future__ import annotations

import os

import pytest

from tests.db_safety import (
    SKIP_REASON_NO_DB,
    looks_like_production_supabase,
    postgres_reachable,
    production_db_tests_allowed,
    is_pytest_running,
    resolve_test_postgres_conn,
)


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault("OMEIA_PYTEST", "1")
    os.environ.setdefault("PLATFORM_AUTH_DISABLED", "true")

    if production_db_tests_allowed():
        return

    # Strip hosted Supabase credentials loaded from configs/.env so unit tests
    # never hit production unless explicitly opted in.
    if os.getenv("SUPABASE_DB_PASSWORD", "").strip():
        os.environ.pop("SUPABASE_DB_PASSWORD", None)
    if os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip():
        os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
    if os.getenv("SERVICE_ROLE_KEY", "").strip():
        os.environ.pop("SERVICE_ROLE_KEY", None)


def pytest_runtest_setup(item: pytest.Item) -> None:
    if item.get_closest_marker("requires_database"):
        postgres_reachable.cache_clear()
        if not postgres_reachable():
            pytest.skip(SKIP_REASON_NO_DB)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if item.get_closest_marker("requires_production_db"):
            continue
        if "integration" in item.name.lower() and "supabase" in item.nodeid.lower():
            item.add_marker(pytest.mark.requires_production_db)


@pytest.fixture(scope="session")
def test_postgres_conn() -> str:
    conn = resolve_test_postgres_conn()
    if is_pytest_running() and looks_like_production_supabase(conn) and not production_db_tests_allowed():
        pytest.fail(
            "pytest resolved a production Supabase DSN without OMEIA_ALLOW_PRODUCTION_DB_TESTS=1"
        )
    return conn
