"""Phase 4 — project RBAC and researcher binding."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app_skeleton.api.platform_flags import project_rbac_enabled
from app_skeleton.security.auth import resolve_researcher
from app_skeleton.security.permissions import (
    can_access_project,
    ensure_project_access,
    filter_projects_for_user,
)


def test_project_rbac_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROJECT_RBAC_ENABLED", raising=False)
    assert project_rbac_enabled() is False


def test_can_access_project_open_when_rbac_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_RBAC_ENABLED", "false")
    user = {"email": "guest@lab.fi", "role": "viewer"}
    assert can_access_project(user, "SECRET") is True


def test_can_access_project_admin_when_rbac_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_RBAC_ENABLED", "true")
    user = {"email": "admin@lab.fi", "role": "admin", "uid": "uid-admin"}
    assert can_access_project(user, "ANYPROJECT") is True


def test_can_access_project_blocks_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_RBAC_ENABLED", "true")
    user = {"email": "jane@lab.fi", "role": "researcher", "uid": "uid-jane"}
    cur = MagicMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app_skeleton.security.permissions.project_codes_for_user",
            lambda _cur, _user: {"SPACE"},
        )
        assert can_access_project(user, "SPACE", cur=cur) is True
        assert can_access_project(user, "KRAS", cur=cur) is False


def test_ensure_project_access_raises_403(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_RBAC_ENABLED", "true")
    user = {"email": "jane@lab.fi", "role": "researcher", "uid": "uid-jane"}
    cur = MagicMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app_skeleton.security.permissions.project_codes_for_user",
            lambda _cur, _user: {"SPACE"},
        )
        ensure_project_access(user, "SPACE", cur=cur)
        with pytest.raises(HTTPException) as exc:
            ensure_project_access(user, "KRAS", cur=cur)
        assert exc.value.status_code == 403


def test_filter_projects_for_user_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_RBAC_ENABLED", "true")
    cur = MagicMock()
    projects = [
        {"project_code": "SPACE"},
        {"project_code": "KRAS"},
        {"project_code": "EyeMT"},
    ]
    user = {"email": "jane@lab.fi", "role": "researcher", "uid": "uid-jane"}

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app_skeleton.security.permissions.project_codes_for_user",
            lambda _cur, _user: {"SPACE", "EYEMT"},
        )
        filtered = filter_projects_for_user(user, projects, cur)
    codes = {p["project_code"] for p in filtered}
    assert codes == {"SPACE", "EyeMT"}


def test_resolve_researcher_binds_firebase_uid() -> None:
    cur = MagicMock()
    cur.fetchone.return_value = ("rid-1", "jane.doe", "jane@lab.fi", "firebase-123")
    resolved = resolve_researcher(
        cur,
        {"email": "jane@lab.fi", "uid": "firebase-123", "role": "researcher"},
    )
    assert resolved.researcher_id == "rid-1"
    assert resolved.email == "jane@lab.fi"
    assert resolved.firebase_uid == "firebase-123"
    cur.execute.assert_called()
