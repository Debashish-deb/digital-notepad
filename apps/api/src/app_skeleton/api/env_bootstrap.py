"""Load application environment before auth/security modules read os.environ."""
from __future__ import annotations

import os
from pathlib import Path

_BOOTSTRAPPED = False


def _find_repo_root() -> Path:
    from app_skeleton._repo import find_repo_root

    return find_repo_root()


_REPO_ROOT = _find_repo_root()


def _env_file_candidates() -> list[Path]:
    return [
        _REPO_ROOT / "config" / "env" / ".env",
        _REPO_ROOT / "configs" / ".env",
    ]


def load_application_env() -> None:
    """Idempotent: load config/env/.env (or legacy configs/.env) then optional overrides."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        _BOOTSTRAPPED = True
        return

    for env_path in _env_file_candidates():
        if env_path.is_file():
            load_dotenv(env_path)
            break
    load_dotenv()
    _BOOTSTRAPPED = True


def repo_root() -> Path:
    return _REPO_ROOT
