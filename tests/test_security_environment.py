import os
import pytest
from app_skeleton.security.environment import validate_environment
from app_skeleton.security.cors import get_cors_origins

def test_production_auth_disabled_fails(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PLATFORM_AUTH_DISABLED", "true")
    with pytest.raises(RuntimeError, match="PLATFORM_AUTH_DISABLED cannot be true in production"):
        validate_environment()

def test_production_auth_allow_skip_fails(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PLATFORM_AUTH_DISABLED", "false")
    monkeypatch.setenv("PLATFORM_AUTH_ALLOW_SKIP", "true")
    with pytest.raises(RuntimeError, match="PLATFORM_AUTH_ALLOW_SKIP cannot be true in production"):
        validate_environment()

def test_production_cors_wildcard_fails(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PLATFORM_AUTH_DISABLED", "false")
    monkeypatch.setenv("PLATFORM_AUTH_ALLOW_SKIP", "false")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be set to strict frontend origins"):
        validate_environment()

def test_production_missing_firebase_fails(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PLATFORM_AUTH_DISABLED", "false")
    monkeypatch.setenv("PLATFORM_AUTH_ALLOW_SKIP", "false")
    monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
    # Missing FIREBASE_SERVICE_ACCOUNT_PATH
    if "FIREBASE_SERVICE_ACCOUNT_PATH" in os.environ:
        monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS")
        
    with pytest.raises(RuntimeError, match="Firebase credentials must be provided"):
        validate_environment()

def test_cors_parsing_strict_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.com, https://b.com ")
    origins = get_cors_origins()
    assert origins == ["https://a.com", "https://b.com"]

    monkeypatch.setenv("CORS_ORIGINS", "https://a.com,*")
    with pytest.raises(RuntimeError, match="cannot contain wildcard"):
        get_cors_origins()
