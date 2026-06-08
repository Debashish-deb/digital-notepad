#!/usr/bin/env python3
"""Smoke test for Gemini Research Copilot chat endpoints."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / "configs" / ".env")

API_URL = os.getenv("CHAT_TEST_API_URL", "http://127.0.0.1:8000").rstrip("/")
AUTH_SKIP = os.getenv("PLATFORM_AUTH_DISABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
if AUTH_SKIP:
    HEADERS["X-Platform-Auth-Skip"] = "dev-local"


def _post(path: str, payload: dict) -> requests.Response:
    return requests.post(f"{API_URL}{path}", headers=HEADERS, json=payload, timeout=120)


def _get(path: str) -> requests.Response:
    return requests.get(f"{API_URL}{path}", headers=HEADERS, timeout=30)


def _inprocess_chat() -> tuple[dict, dict]:
    """Fallback when live API requires Firebase auth."""
    from fastapi.testclient import TestClient
    from unittest.mock import patch

    from omeia.api.main import app
    from omeia.security.auth import _dev_user, require_platform_user

    async def _auth_override():
        return _dev_user()

    app.dependency_overrides[require_platform_user] = _auth_override
    try:
        client = TestClient(app)
        with patch("omeia.api.routers.chat.require_role"):
            status = client.get("/api/chat/status")
            chat = client.post(
                "/api/chat",
                json={
                    "message": "What spatial biology methods does the Färkkilä lab use for ovarian cancer research?",
                    "project_codes": ["SPACE", "EyeMT"],
                    "stream": False,
                },
            )
        if status.status_code != 200 or chat.status_code != 200:
            raise RuntimeError(f"in-process fallback failed status={status.status_code} chat={chat.status_code}")
        return status.json(), chat.json()
    finally:
        app.dependency_overrides.pop(require_platform_user, None)


def main() -> int:
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
    print(f"API: {API_URL}")
    print(f"GEMINI_API_KEY configured: {has_gemini_key}")

    status = _get("/api/chat/status")
    print(f"GET /api/chat/status -> {status.status_code}")
    used_inprocess = False
    if status.status_code == 401:
        print("Live API requires auth — using in-process TestClient fallback.")
        status_json, body = _inprocess_chat()
        used_inprocess = True
    elif status.status_code != 200:
        print(status.text[:500])
        return 1
    else:
        status_json = status.json()
        payload = {
            "message": "What spatial biology methods does the Färkkilä lab use for ovarian cancer research?",
            "project_codes": ["SPACE", "EyeMT"],
            "stream": False,
        }
        chat = _post("/api/chat", payload)
        print(f"POST /api/chat -> {chat.status_code}")
        if chat.status_code != 200:
            print(chat.text[:800])
            return 1
        body = chat.json()

    print(json.dumps({
        "chat_provider": status_json.get("chat_provider"),
        "chat_model": status_json.get("chat_model"),
        "healthy": (status_json.get("llm") or {}).get("healthy"),
        "api_key_configured": (status_json.get("llm") or {}).get("api_key_configured"),
        "inprocess_fallback": used_inprocess,
    }, indent=2))
    answer = (body.get("answer") or "").strip()
    print(f"provider={body.get('provider')} sources={len(body.get('sources') or [])} hits={len(body.get('search_hits') or [])}")
    print(f"answer_preview={answer[:240]}{'…' if len(answer) > 240 else ''}")

    if not answer:
        print("ERROR: empty answer")
        return 1

    if body.get("provider") == "mock" and has_gemini_key:
        print("WARN: GEMINI_API_KEY is set but provider fell back to mock — check LLM_PROVIDER/CHAT_LLM_PROVIDER.")

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
