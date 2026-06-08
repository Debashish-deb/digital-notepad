"""Repository root resolution shared by API and ops scripts."""
from __future__ import annotations

from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    here = (start or Path(__file__)).resolve()
    markers = (".git", "Makefile", "pyproject.toml")
    for parent in here.parents:
        if any((parent / name).exists() for name in markers):
            return parent
    return here.parents[4]
