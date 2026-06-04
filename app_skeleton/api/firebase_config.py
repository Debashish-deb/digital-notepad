"""Firebase public + project metadata (no secrets in API responses)."""
from __future__ import annotations

import os

# User sign-in: Email/Password only — do not enable Google Sign-In in Firebase console.
FIREBASE_AUTH_METHOD = "email_password"
FIREBASE_AUTH_PROVIDERS_DISABLED = ("google.com", "google", "oauth")

DEFAULT_PROJECT_ID = "farkki-digital-notebook"
DEFAULT_PROJECT_NUMBER = "570069536455"
DEFAULT_PROJECT_NAME = "Farkki-digital-notebook"
# Firebase / Google Cloud console owner (not end-user lab login)
DEFAULT_CONSOLE_EMAIL = "farkkilalab@gmail.com"
DEFAULT_WEB_APP_NICKNAME = "OMEIA.AI"
DEFAULT_WEB_APP_ID = "1:570069536455:web:4c4623a81262e6c4eef8e2"
DEFAULT_STORAGE_BUCKET = "farkki-digital-notebook.firebasestorage.app"
DEFAULT_MESSAGING_SENDER_ID = "570069536455"
DEFAULT_MEASUREMENT_ID = "G-24JLFQYRTG"


def firebase_project_metadata() -> dict:
    project_id = os.getenv("FIREBASE_PROJECT_ID", DEFAULT_PROJECT_ID).strip()
    return {
        "project_name": os.getenv("FIREBASE_PROJECT_NAME", DEFAULT_PROJECT_NAME).strip(),
        "project_id": project_id,
        "project_number": os.getenv("FIREBASE_PROJECT_NUMBER", DEFAULT_PROJECT_NUMBER).strip(),
        "console_email": os.getenv("FIREBASE_CONSOLE_EMAIL", DEFAULT_CONSOLE_EMAIL).strip(),
        "auth_method": FIREBASE_AUTH_METHOD,
        "sign_in_providers": ["password"],
        "sign_in_providers_disabled": list(FIREBASE_AUTH_PROVIDERS_DISABLED),
        "auth_domain": os.getenv(
            "FIREBASE_AUTH_DOMAIN",
            f"{project_id}.firebaseapp.com",
        ).strip(),
    }


def firebase_client_config_public() -> dict:
    """Values safe to expose to the React app (Firebase web SDK)."""
    meta = firebase_project_metadata()
    api_key = os.getenv("FIREBASE_WEB_API_KEY", "").strip() or os.getenv("VITE_FIREBASE_API_KEY", "").strip()
    app_id = (
        os.getenv("FIREBASE_WEB_APP_ID", "").strip()
        or os.getenv("VITE_FIREBASE_APP_ID", "").strip()
        or DEFAULT_WEB_APP_ID
    )
    app_nickname = os.getenv("FIREBASE_WEB_APP_NICKNAME", DEFAULT_WEB_APP_NICKNAME).strip()
    return {
        **meta,
        "app_nickname": app_nickname,
        "storage_bucket": os.getenv("FIREBASE_STORAGE_BUCKET", DEFAULT_STORAGE_BUCKET).strip(),
        "messaging_sender_id": os.getenv(
            "FIREBASE_MESSAGING_SENDER_ID", DEFAULT_MESSAGING_SENDER_ID
        ).strip(),
        "measurement_id": os.getenv("FIREBASE_MEASUREMENT_ID", DEFAULT_MEASUREMENT_ID).strip(),
        "analytics_enabled": bool(os.getenv("FIREBASE_MEASUREMENT_ID", DEFAULT_MEASUREMENT_ID).strip()),
        "api_key_configured": bool(api_key),
        "app_id_configured": bool(app_id),
        "api_key": api_key or None,
        "app_id": app_id,
        "sdk_version_npm": "12.14.0",
        "sdk_cdn_base": "https://www.gstatic.com/firebasejs/12.14.0/",
        "measurement_id_optional": True,
        "setup_note": "configs/FIREBASE_WEB_SETUP.md",
    }
