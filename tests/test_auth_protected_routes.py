"""Firebase auth on protected API routes when PLATFORM_AUTH_DISABLED=false."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app_skeleton.api.main import app


class TestAuthProtectedRoutes(unittest.TestCase):
    @patch("app_skeleton.security.auth.AUTH_DISABLED", False)
    @patch("app_skeleton.security.auth.APP_ENV", "production")
    def test_storage_roots_without_token_returns_401(self) -> None:
        client = TestClient(app)
        response = client.get("/api/storage/roots")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Bearer", response.json().get("detail", ""))

    @patch("app_skeleton.security.auth.AUTH_DISABLED", False)
    @patch("app_skeleton.security.auth.APP_ENV", "production")
    def test_vault_summary_without_token_returns_401(self) -> None:
        client = TestClient(app)
        response = client.get("/api/vault/summary")
        self.assertEqual(response.status_code, 401)

    def test_health_remains_public(self) -> None:
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)

    @patch("app_skeleton.security.auth.AUTH_DISABLED", False)
    @patch("app_skeleton.security.auth.APP_ENV", "production")
    def test_auth_config_reports_auth_enabled(self) -> None:
        client = TestClient(app)
        response = client.get("/api/auth/config")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json().get("auth_disabled"))


if __name__ == "__main__":
    unittest.main()
