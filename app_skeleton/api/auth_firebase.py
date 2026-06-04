"""Firebase Email/Password token verification with dev bypass (LUMI-W060).

Users sign in with email + password in Firebase Auth (no Google Sign-In).
Backend verifies Firebase ID tokens via Admin SDK service account.
"""
from __future__ import annotations

import os
from typing import Any

import psycopg
from fastapi import Depends, HTTPException, Request

from app_skeleton.api.platform_admin import is_platform_admin

APP_ENV = os.getenv("APP_ENV", "development")
AUTH_DISABLED = os.getenv("PLATFORM_AUTH_DISABLED", "true" if APP_ENV == "development" else "false").lower() in (
    "1", "true", "yes",
)


def _dev_user() -> dict[str, Any]:
    return {
        "uid": "dev-local-user",
        "email": "dev@localhost",
        "role": "admin",
        "verified": True,
    }


async def require_firebase_user(request: Request) -> dict[str, Any]:
    """Verify Firebase Bearer token on protected routes (dev bypass when auth disabled)."""
    if AUTH_DISABLED:
        return _dev_user()

    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = auth_header[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty Bearer token")

    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Firebase Admin SDK not installed. Set PLATFORM_AUTH_DISABLED=true for dev.",
        ) from exc

    if not firebase_admin._apps:
        raise HTTPException(status_code=503, detail="Firebase not initialized on server")

    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    email = (decoded.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=401, detail="Token missing email claim")

    sign_in_provider = (decoded.get("firebase") or {}).get("sign_in_provider")
    if sign_in_provider and sign_in_provider not in ("password", "custom"):
        raise HTTPException(
            status_code=403,
            detail="Only email/password sign-in is allowed for this platform.",
        )

    if not _email_allowlisted(email):
        raise HTTPException(status_code=403, detail="Email not on lab allowlist")

    role = "admin" if is_platform_admin(email) else "researcher"
    return {
        "uid": decoded.get("uid") or decoded.get("sub"),
        "email": email,
        "role": role,
        "verified": True,
    }


def _email_allowlisted(email: str) -> bool:
    if is_platform_admin(email):
        return True
    from app_skeleton.api.supabase_config import postgres_conn

    conn_str = postgres_conn().strip()
    if not conn_str:
        return True
    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM platform.allowed_email
                    WHERE lower(email) = lower(%s) AND status = 'approved';
                    """,
                    (email,),
                )
                return cur.fetchone() is not None
    except Exception:
        return False


# Backward-compatible alias used across the codebase.
require_user = require_firebase_user


async def require_admin(user: dict[str, Any] = Depends(require_firebase_user)) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


FirebaseUser = Depends(require_firebase_user)
OptionalUser = FirebaseUser
AdminUser = Depends(require_admin)
