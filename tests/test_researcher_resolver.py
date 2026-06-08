"""Phase 4 researcher identity resolver."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from omeia.security.auth import (
    ResolvedResearcher,
    _username_from_user,
    resolve_researcher,
    resolve_researcher_id,
)


def test_username_from_dev_user_maps_legacy_row() -> None:
    assert _username_from_user({"email": "dev@localhost"}) == "local_dev"


def test_username_from_email() -> None:
    assert _username_from_user({"email": "jane.doe@lab.fi"}) == "jane.doe"


def test_username_missing_email_raises() -> None:
    with pytest.raises(HTTPException) as exc:
        _username_from_user({})
    assert exc.value.status_code == 401


def test_resolve_researcher_id_existing_by_firebase_uid() -> None:
    cur = MagicMock()
    cur.fetchone.return_value = ("uuid-existing", "jane", "jane@lab.fi", "fb-1")
    rid = resolve_researcher_id(
        cur,
        {"email": "jane@lab.fi", "uid": "fb-1", "role": "researcher"},
    )
    assert rid == "uuid-existing"
    assert cur.execute.call_count >= 2


def test_resolve_researcher_creates_on_miss() -> None:
    cur = MagicMock()
    cur.fetchone.side_effect = [
        None,  # firebase lookup
        None,  # email lookup
        None,  # username lookup
        ("uuid-new", "new.user", "new.user@lab.fi", "fb-new"),
    ]
    resolved = resolve_researcher(
        cur,
        {"email": "new.user@lab.fi", "uid": "fb-new", "role": "admin"},
    )
    assert isinstance(resolved, ResolvedResearcher)
    assert resolved.researcher_id == "uuid-new"
    assert resolved.email == "new.user@lab.fi"
    assert cur.execute.call_count == 4


def test_decision_create_model_no_hardcoded_debdeba() -> None:
    from omeia.api.common import DecisionCreate

    req = DecisionCreate(
        project_code="SPACE",
        title="Test",
        decision_details="d",
        rationale="r",
    )
    assert req.decided_by_username is None
