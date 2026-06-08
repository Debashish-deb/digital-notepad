#!/usr/bin/env python3
"""Linux workstation sync health — verify data roots, twins, and media readability."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
_API_SRC = REPO_ROOT / "apps" / "api" / "src"
for entry in (str(_API_SRC), str(REPO_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)


def _check_path(path: Path, *, must_be_dir: bool = True) -> dict[str, Any]:
    exists = path.exists()
    ok = path.is_dir() if must_be_dir else path.is_file()
    return {
        "path": str(path),
        "exists": exists,
        "ok": ok,
        "readable": os.access(path, os.R_OK) if exists else False,
    }


def _sample_readable_file(root: Path, *, limit: int = 3) -> dict[str, Any]:
    if not root.is_dir():
        return {"ok": False, "samples": [], "message": "root missing"}
    samples: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".json", ".md", ".txt", ".pdf", ".tif", ".tiff", ".png", ".jpg"}:
            try:
                with path.open("rb") as fh:
                    fh.read(64)
                samples.append(str(path.relative_to(root)))
                if len(samples) >= limit:
                    break
            except OSError:
                return {"ok": False, "samples": samples, "message": f"unreadable: {path}"}
    return {"ok": bool(samples), "samples": samples}


def _runtime_roots() -> tuple[Path, Path, Path, Path]:
    """Resolve roots at call time so DATABASE_ROOT/PROJECTS_ROOT env overrides apply."""
    from app_skeleton.api.paths import (
        CSC_MEDIA_DIR,
        PUBLIC_PROCESSED_DIR,
        _default_database_root,
        _default_projects_root,
    )

    return _default_database_root(), _default_projects_root(), PUBLIC_PROCESSED_DIR, CSC_MEDIA_DIR


def run_checks() -> dict[str, Any]:
    from app_skeleton.api.data_layout import LEGACY_PROCESSED_DIR, inventory_json

    DATABASE_ROOT, PROJECTS_ROOT, PUBLIC_PROCESSED_DIR, CSC_MEDIA_DIR = _runtime_roots()

    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: dict[str, Any]) -> None:
        checks.append({"name": name, "ok": ok, **detail})

    db = _check_path(DATABASE_ROOT)
    add("database_root", db["ok"], db)

    projects = _check_path(PROJECTS_ROOT)
    add("projects_root", projects["ok"], projects)

    for sub in ("WET_LAB", "projects", "media"):
        candidate = DATABASE_ROOT / sub
        if candidate.exists():
            add(f"database_{sub.lower()}", candidate.is_dir(), _check_path(candidate))

    inv = inventory_json()
    inv_check = _check_path(inv, must_be_dir=False)
    add("vault_inventory_json", inv_check["ok"], inv_check)

    twin_dirs = [
        ("legacy_processed_twins", LEGACY_PROCESSED_DIR),
        ("public_processed_twins", PUBLIC_PROCESSED_DIR),
    ]
    twin_ok = False
    for label, twin_dir in twin_dirs:
        if not twin_dir.is_dir():
            add(label, False, {"path": str(twin_dir), "exists": False})
            continue
        json_files = list(twin_dir.glob("*.json"))[:5]
        ok = len(json_files) > 0
        twin_ok = twin_ok or ok
        add(label, ok, {"path": str(twin_dir), "sample_files": [p.name for p in json_files]})
    add("processed_twins_present", twin_ok, {"message": "at least one processed twin directory has JSON"})

    media_probe = _sample_readable_file(PROJECTS_ROOT)
    add("project_media_readable", media_probe["ok"], media_probe)
    if CSC_MEDIA_DIR.is_dir():
        add("csc_media_readable", _sample_readable_file(CSC_MEDIA_DIR)["ok"], _sample_readable_file(CSC_MEDIA_DIR))

    failed = [c for c in checks if not c.get("ok")]
    return {
        "ok": len(failed) == 0,
        "database_root": str(DATABASE_ROOT),
        "projects_root": str(PROJECTS_ROOT),
        "checks": checks,
        "failed": [c["name"] for c in failed],
    }


def main() -> int:
    report = run_checks()
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
