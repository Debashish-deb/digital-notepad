import os
from typing import Any, Optional

import psycopg
from fastapi import Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app_skeleton.api.platform_admin import is_platform_admin
from app_skeleton.security.audit_log import log_failed_auth, log_dev_bypass_attempt

APP_ENV = os.getenv("APP_ENV", "development").lower()
AUTH_DISABLED = os.getenv("PLATFORM_AUTH_DISABLED", "true" if APP_ENV == "development" else "false").lower() in ("1", "true", "yes")
AUTH_ALLOW_SKIP = os.getenv("PLATFORM_AUTH_ALLOW_SKIP", "false").lower() in ("1", "true", "yes")
AUTH_SKIP_HEADER = "testing"

def _dev_user() -> dict[str, Any]:
    return {
        "uid": "dev-local-user",
        "email": "dev@localhost",
        "role": "admin",
        "verified": True,
    }

import time

_allowlist_cache = {}
CACHE_TTL = 300  # 5 minutes

def _email_allowlisted(email: str) -> bool:
    if is_platform_admin(email):
        return True
    
    try:
        from app_skeleton.api.supabase_config import postgres_conn
        conn_str = postgres_conn().strip()
        if not conn_str:
            return True # Fallback if no DB configured
        
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
    except Exception as e:
        # In strict mode, failing DB connection should probably block access, 
        # but for compatibility keeping fallback to False
        return False

def _email_allowlisted_cached(email: str) -> bool:
    now = time.time()
    if email in _allowlist_cache:
        val, ts = _allowlist_cache[email]
        if now - ts < CACHE_TTL:
            return val
            
    val = _email_allowlisted(email)
    _allowlist_cache[email] = (val, now)
    return val

async def require_platform_user(request: Request) -> dict[str, Any]:
    """Verify Firebase Bearer token on protected routes."""
    ip_address = request.client.host if request.client else "unknown"
    
    if APP_ENV == "development" and AUTH_DISABLED:
        return _dev_user()

    if request.headers.get("X-Platform-Auth-Skip") == AUTH_SKIP_HEADER:
        if APP_ENV == "production" or not AUTH_ALLOW_SKIP:
            log_dev_bypass_attempt(ip_address)
            raise HTTPException(status_code=403, detail="Dev bypass disabled")
        user = _dev_user()
        user["auth_skip"] = True
        return user

    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        log_failed_auth("Missing Bearer token", ip_address)
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = auth_header[7:].strip()
    if not token:
        log_failed_auth("Empty Bearer token", ip_address)
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
        decoded = await run_in_threadpool(firebase_auth.verify_id_token, token)
    except Exception as exc:
        log_failed_auth(f"Invalid token: {exc}", ip_address)
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    email = (decoded.get("email") or "").lower()
    if not email:
        log_failed_auth("Token missing email claim", ip_address)
        raise HTTPException(status_code=401, detail="Token missing email claim")

    sign_in_provider = (decoded.get("firebase") or {}).get("sign_in_provider")
    if sign_in_provider and sign_in_provider not in ("password", "custom"):
        log_failed_auth(f"Invalid sign-in provider {sign_in_provider}", ip_address)
        raise HTTPException(
            status_code=403,
            detail="Only email/password sign-in is allowed for this platform.",
        )

    if not _email_allowlisted_cached(email):
        log_failed_auth("Email not on allowlist", ip_address)
        raise HTTPException(status_code=403, detail="Email not on allowlist")

    role = "admin" if is_platform_admin(email) else "researcher"
    return {
        "uid": decoded.get("uid") or decoded.get("sub"),
        "email": email,
        "role": role,
        "verified": True,
    }

async def require_admin_user(user: dict[str, Any] = Depends(require_platform_user)) -> dict[str, Any]:
    """Requires the authenticated user to be an admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user

async def optional_public_user(request: Request) -> Optional[dict[str, Any]]:
    """Tries to get a user, but returns None if unauthenticated."""
    if not request.headers.get("Authorization"):
        return None
    try:
        return await require_platform_user(request)
    except HTTPException:
        return None
