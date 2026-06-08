"""Repository root resolution shared by API and ops scripts."""
from __future__ import annotations

from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    here = (start or Path(__file__)).resolve()
    for parent in here.parents:
        if (parent / ".git").is_dir():
            return parent
    for parent in here.parents:
        if (parent / "infra").is_dir() and (parent / "apps").is_dir():
            return parent
    return here.parents[4]
