"""Test-only auth override for in-process FastAPI TestClient.

Never import or use this module from production code paths. It exists solely so
unit tests and evaluation scripts can authenticate as researcher/viewer/editor/admin
without a live Firebase token.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Literal

from omeia.api.main import app
from omeia.security.auth import require_platform_user

TestRole = Literal["researcher", "viewer", "editor", "admin"]
_VALID_ROLES: frozenset[str] = frozenset({"researcher", "viewer", "editor", "admin"})


def test_user(role: TestRole = "admin", **extra: Any) -> dict[str, Any]:
    """Build a synthetic platform user dict for TestClient dependency overrides."""
    if role not in _VALID_ROLES:
        raise ValueError(f"Invalid test role {role!r}; expected one of {sorted(_VALID_ROLES)}")
    return {
        "uid": f"test-{role}-user",
        "email": f"{role}@test.local",
        "role": role,
        "verified": True,
        "test_auth": True,
        **extra,
    }


def apply_auth_override(role: TestRole = "admin", **extra: Any) -> dict[str, Any]:
    """Register a TestClient auth override; returns the synthetic user dict."""
    user = test_user(role, **extra)

    async def _override() -> dict[str, Any]:
        return user

    app.dependency_overrides[require_platform_user] = _override
    return user


def clear_auth_override() -> None:
    """Remove the TestClient auth override if present."""
    app.dependency_overrides.pop(require_platform_user, None)


@contextmanager
def auth_override(role: TestRole = "admin", **extra: Any) -> Generator[dict[str, Any], None, None]:
    """Context manager that applies and clears a test auth override."""
    user = apply_auth_override(role, **extra)
    try:
        yield user
    finally:
        clear_auth_override()
