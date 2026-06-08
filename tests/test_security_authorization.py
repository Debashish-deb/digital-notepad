import pytest
from fastapi import HTTPException
from omeia.security.permissions import has_role, require_role, can_write_project, can_delete_project

def test_has_role():
    user = {"email": "test@test.com", "role": "admin"}
    assert has_role(user, ["admin"]) is True
    assert has_role(user, ["editor"]) is False

def test_require_role():
    user = {"email": "test@test.com", "role": "viewer"}
    with pytest.raises(HTTPException) as exc:
        require_role(user, ["admin", "editor"])
    assert exc.value.status_code == 403

def test_can_write_project():
    editor = {"role": "editor"}
    viewer = {"role": "viewer"}
    admin = {"role": "admin"}
    
    assert can_write_project(editor, "proj") is True
    assert can_write_project(admin, "proj") is True
    assert can_write_project(viewer, "proj") is False

def test_can_delete_project():
    editor = {"role": "editor"}
    admin = {"role": "admin"}
    
    assert can_delete_project(admin, "proj") is True
    assert can_delete_project(editor, "proj") is False
