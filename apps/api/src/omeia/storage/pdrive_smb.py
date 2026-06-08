"""P-drive mounted path connector — read local mount; no SMB auth in code unless user adds later."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, BinaryIO, Iterator

from omeia.storage.env import pdrive_enabled, pdrive_logical_root, pdrive_mount_path


def is_configured() -> bool:
    if not pdrive_enabled():
        return False
    root = pdrive_mount_path()
    return bool(root) and Path(root).exists()


def _mount_root() -> Path:
    return Path(pdrive_mount_path()).expanduser().resolve()


def _logical_path_for_relative(relative_path: str) -> str:
    rel = (relative_path or "").strip().lstrip("/").replace("\\", "/")
    base = pdrive_logical_root().rstrip("/")
    return f"{base}/{rel}" if rel else base


def _safe_target(relative_path: str) -> Path | None:
    root = _mount_root()
    rel = (relative_path or "").strip().lstrip("/")
    target = (root / rel).resolve() if rel else root
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def list_logical_directory(relative_path: str = "") -> list[dict[str, Any]]:
    target = _safe_target(relative_path)
    if target is None or not target.is_dir():
        return []
    base = _mount_root()
    entries: list[dict[str, Any]] = []
    try:
        for item in sorted(target.iterdir())[:500]:
            rel_item = str(item.relative_to(base)).replace("\\", "/")
            stat = item.stat()
            entries.append({
                "name": item.name,
                "relative_path": rel_item,
                "logical_path": _logical_path_for_relative(rel_item),
                "type": "directory" if item.is_dir() else "file",
                "size_bytes": stat.st_size if item.is_file() else None,
            })
    except OSError:
        return []
    return entries


def object_metadata(relative_path: str) -> dict[str, Any]:
    target = _safe_target(relative_path)
    if target is None or not target.exists():
        return {"provider_id": "pdrive_smb", "found": False, "logical_path": _logical_path_for_relative(relative_path)}
    stat = target.stat()
    return {
        "provider_id": "pdrive_smb",
        "found": True,
        "logical_path": _logical_path_for_relative(relative_path),
        "relative_path": relative_path.strip().lstrip("/"),
        "type": "directory" if target.is_dir() else "file",
        "size_bytes": stat.st_size,
        "modified_at": stat.st_mtime,
    }


def download_stream(relative_path: str) -> Iterator[bytes]:
    target = _safe_target(relative_path)
    if target is None or not target.is_file():
        return iter(())
    try:
        with target.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
    except OSError:
        return iter(())


def scan_tree(relative_path: str = "", *, max_entries: int = 500) -> dict[str, Any]:
    """Walk mounted tree read-only; never delete or rename."""
    if not is_configured():
        return {"ok": False, "entries": [], "truncated": False, "error": "not_configured"}
    root = _safe_target(relative_path)
    if root is None or not root.is_dir():
        return {"ok": False, "entries": [], "error": "invalid_path"}
    manifest: list[dict[str, Any]] = []
    truncated = False
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            rel_dir = str(Path(dirpath).relative_to(_mount_root())).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""
            for name in dirnames:
                if len(manifest) >= max_entries:
                    truncated = True
                    break
                rel_item = f"{rel_dir}/{name}".strip("/") if rel_dir else name
                manifest.append({
                    "name": name,
                    "relative_path": rel_item,
                    "logical_path": _logical_path_for_relative(rel_item),
                    "type": "directory",
                })
            for name in filenames:
                if len(manifest) >= max_entries:
                    truncated = True
                    break
                rel_item = f"{rel_dir}/{name}".strip("/") if rel_dir else name
                fp = Path(dirpath) / name
                try:
                    size = fp.stat().st_size
                except OSError:
                    size = None
                manifest.append({
                    "name": name,
                    "relative_path": rel_item,
                    "logical_path": _logical_path_for_relative(rel_item),
                    "type": "file",
                    "size_bytes": size,
                })
            if truncated:
                break
    except OSError as exc:
        return {"ok": False, "entries": [], "error": str(exc)}
    return {
        "ok": True,
        "provider_id": "pdrive_smb",
        "root_logical_path": pdrive_logical_root(),
        "entries": manifest,
        "count": len(manifest),
        "truncated": truncated,
    }


def build_manifest(relative_path: str = "", *, max_entries: int = 1000) -> dict[str, Any]:
    scan = scan_tree(relative_path, max_entries=max_entries)
    files = [e for e in scan.get("entries", []) if e.get("type") == "file"]
    return {
        "provider_id": "pdrive_smb",
        "root_logical_path": pdrive_logical_root(),
        "generated_from": "pdrive_smb.build_manifest",
        "file_count": len(files),
        "directory_count": sum(1 for e in scan.get("entries", []) if e.get("type") == "directory"),
        "truncated": scan.get("truncated", False),
        "files": files,
    }


def public_status() -> dict[str, Any]:
    return {
        "provider_id": "pdrive_smb",
        "configured": is_configured(),
        "root_logical_path": pdrive_logical_root() if is_configured() else None,
        "role": "secondary_research",
    }
