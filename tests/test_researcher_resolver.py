"""Phase 1 researcher identity resolver."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app_skeleton.security.auth import _username_from_user, resolve_researcher_id


def test_username_from_dev_user() -> None:
    assert _username_from_user({"email": "dev@localhost"}) == "debdeba"


def test_username_from_email() -> None:
    assert _username_from_user({"email": "jane.doe@lab.fi"}) == "jane.doe"


def test_username_missing_email_raises() -> None:
    with pytest.raises(HTTPException) as exc:
        _username_from_user({})
    assert exc.value.status_code == 401


def test_resolve_researcher_id_existing() -> None:
    cur = MagicMock()
    cur.fetchone.return_value = ("uuid-existing",)
    rid = resolve_researcher_id(cur, {"email": "jane@lab.fi", "role": "researcher"})
    assert rid == "uuid-existing"
    cur.execute.assert_called_once()


def test_resolve_researcher_id_creates_on_miss() -> None:
    cur = MagicMock()
    cur.fetchone.side_effect = [None, ("uuid-new",)]
    rid = resolve_researcher_id(cur, {"email": "new.user@lab.fi", "role": "admin"})
    assert rid == "uuid-new"
    assert cur.execute.call_count == 2
