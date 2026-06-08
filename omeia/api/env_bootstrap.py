"""Load application environment before auth/security modules read os.environ."""
from __future__ import annotations

import os
from pathlib import Path

_BOOTSTRAPPED = False
_REPO_ROOT = Path(__file__).resolve().parents[2]


def load_application_env() -> None:
    """Idempotent: load configs/.env then optional local overrides."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        _BOOTSTRAPPED = True
        return

    load_dotenv(_REPO_ROOT / "configs" / ".env")
    load_dotenv()
    _BOOTSTRAPPED = True


def repo_root() -> Path:
    return _REPO_ROOT
