import pytest
from fastapi import Request, HTTPException
from app_skeleton.security.auth import require_platform_user, require_admin_user
import app_skeleton.security.auth as auth
import os

class MockRequest:
    def __init__(self, headers=None, client_host="127.0.0.1"):
        self.headers = headers or {}
        class Client:
            host = client_host
        self.client = Client()

import asyncio

def test_auth_missing_token(monkeypatch):
    monkeypatch.setattr(auth, "APP_ENV", "production")
    monkeypatch.setattr(auth, "AUTH_DISABLED", False)
    
    req = MockRequest()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_platform_user(req))
    assert exc.value.status_code == 401
    assert "Missing Bearer token" in exc.value.detail

def test_auth_skip_disabled_in_production(monkeypatch):
    monkeypatch.setattr(auth, "APP_ENV", "production")
    monkeypatch.setattr(auth, "AUTH_ALLOW_SKIP", True)
    
    req = MockRequest(headers={"X-Platform-Auth-Skip": "testing"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_platform_user(req))
    assert exc.value.status_code == 403
    assert "Dev bypass disabled" in exc.value.detail

def test_auth_skip_allowed_in_dev(monkeypatch):
    monkeypatch.setattr(auth, "APP_ENV", "development")
    monkeypatch.setattr(auth, "AUTH_ALLOW_SKIP", True)
    monkeypatch.setattr(auth, "AUTH_DISABLED", False)
    
    req = MockRequest(headers={"X-Platform-Auth-Skip": "testing"})
    user = asyncio.run(require_platform_user(req))
    assert user["uid"] == "dev-local-user"
    assert user["auth_skip"] is True
