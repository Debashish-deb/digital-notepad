"""Firebase Admin SDK bootstrap — verifies Email/Password ID tokens (not Google Sign-In).

Server credentials: service account JSON path (FIREBASE_SERVICE_ACCOUNT_PATH or
GOOGLE_APPLICATION_CREDENTIALS). That file is for Admin SDK only, not user OAuth.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def _service_account_path() -> str:
    return (
        os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )


def firebase_configured() -> bool:
    project_id = os.getenv("FIREBASE_PROJECT_ID", "farkki-digital-notebook").strip()
    if not project_id:
        return False
    return bool(_service_account_path() or os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip())


def init_firebase_if_configured() -> bool:
    """Initialize Firebase Admin when project + credentials are set. No-op in dev."""
    if not firebase_configured():
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        LOGGER.warning("firebase-admin not installed; auth will fail when PLATFORM_AUTH_DISABLED=false")
        return False

    if firebase_admin._apps:
        return True

    project_id = os.getenv("FIREBASE_PROJECT_ID", "farkki-digital-notebook").strip()
    cred = None
    sa_path = _service_account_path()
    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if sa_path and Path(sa_path).is_file():
        cred = credentials.Certificate(sa_path)
    elif sa_json:
        cred = credentials.Certificate(json.loads(sa_json))

    if cred is None:
        LOGGER.warning("Firebase project set but no valid service account credentials")
        return False

    firebase_admin.initialize_app(cred, {"projectId": project_id})
    LOGGER.info("Firebase Admin initialized for project %s", project_id)
    return True
