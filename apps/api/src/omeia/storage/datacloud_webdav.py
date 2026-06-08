"""DataCloud WebDAV connector — server-side only; never expose creds or raw URLs to frontend."""
from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from typing import Any, Iterator
from urllib.parse import quote, unquote

from omeia.storage.env import (
    datacloud_app_password,
    datacloud_logical_root,
    datacloud_username,
    datacloud_webdav_base_url,
)

DAV_NS = {"d": "DAV:"}


def is_configured() -> bool:
    return bool(datacloud_webdav_base_url() and datacloud_app_password())


def _auth() -> tuple[str, str]:
    return datacloud_username(), datacloud_app_password()


def _logical_to_relative(logical_path: str) -> str:
    """Map logical path under DATACLOUD_ROOT to WebDAV-relative segment."""
    lp = (logical_path or "").strip().replace("\\", "/")
    root = datacloud_logical_root().rstrip("/")
    if lp.startswith(root):
        return lp[len(root) :].lstrip("/")
    return lp.lstrip("/")


def _relative_to_logical(relative_path: str) -> str:
    rel = (relative_path or "").strip().lstrip("/")
    root = datacloud_logical_root().rstrip("/")
    return f"{root}/{rel}".rstrip("/") if rel else root


def _webdav_url_for_relative(relative_path: str) -> str:
    base = datacloud_webdav_base_url()
    rel = (relative_path or "").strip().lstrip("/")
    if not rel:
        return base
    segments = [quote(s, safe="") for s in rel.split("/") if s]
    return f"{base}/{'/'.join(segments)}"


def _request(method: str, relative_path: str, *, depth: int | None = None, body: bytes | None = None):
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("httpx required for DataCloud WebDAV") from exc

    headers: dict[str, str] = {}
    if depth is not None:
        headers["Depth"] = str(max(1, min(depth, 5)))
    url = _webdav_url_for_relative(relative_path)
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        return client.request(method, url, auth=_auth(), headers=headers, content=body)


def _parse_propfind_entries(xml_text: str, base_relative: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return entries

    base_rel = (base_relative or "").strip().lstrip("/")
    for resp in root.findall(".//d:response", DAV_NS):
        href_el = resp.find("d:href", DAV_NS)
        if href_el is None or not (href_el.text or "").strip():
            continue
        href = unquote(href_el.text.strip())
        prop = resp.find(".//d:propstat[d:status[contains(., '200')]]/d:prop", DAV_NS)
        if prop is None:
            prop = resp.find(".//d:prop", DAV_NS)
        res_type = prop.find("d:resourcetype", DAV_NS) if prop is not None else None
        is_dir = res_type is not None and res_type.find("d:collection", DAV_NS) is not None
        name = href.rstrip("/").split("/")[-1] if href else ""
        rel = name if not base_rel else f"{base_rel}/{name}".strip("/")
        if base_rel and rel == base_rel:
            continue
        getlen = prop.find("d:getcontentlength", DAV_NS) if prop is not None else None
        getetag = prop.find("d:getetag", DAV_NS) if prop is not None else None
        gettype = prop.find("d:getcontenttype", DAV_NS) if prop is not None else None
        entries.append({
            "name": name,
            "relative_path": rel,
            "logical_path": _relative_to_logical(rel),
            "type": "directory" if is_dir else "file",
            "size_bytes": int(getlen.text) if getlen is not None and (getlen.text or "").isdigit() else None,
            "etag": (getetag.text or "").strip('"') if getetag is not None else None,
            "mime_type": gettype.text if gettype is not None else None,
        })
    return entries


def list_logical_directory(relative_path: str = "", *, depth: int = 1) -> list[dict[str, Any]]:
    """List children under canonical root. Returns logical paths only."""
    if not is_configured():
        return []
    rel = (relative_path or "").strip().lstrip("/")
    try:
        resp = _request("PROPFIND", rel, depth=depth)
        if resp.status_code not in (200, 207):
            return []
        return _parse_propfind_entries(resp.text, rel)
    except Exception:
        return []


def create_directory(relative_path: str) -> dict[str, Any]:
    """MKCOL under canonical root."""
    if not is_configured():
        return {"ok": False, "error": "not_configured"}
    rel = (relative_path or "").strip().lstrip("/")
    if not rel:
        return {"ok": False, "error": "invalid_path"}
    try:
        resp = _request("MKCOL", rel)
        ok = resp.status_code in (201, 405)
        return {
            "ok": ok,
            "logical_path": _relative_to_logical(rel),
            "status_code": resp.status_code,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def upload_bytes(relative_path: str, data: bytes, *, content_type: str = "application/octet-stream") -> dict[str, Any]:
    if not is_configured():
        return {"ok": False, "error": "not_configured"}
    rel = (relative_path or "").strip().lstrip("/")
    try:
        import httpx

        url = _webdav_url_for_relative(rel)
        with httpx.Client(timeout=120.0) as client:
            resp = client.put(url, auth=_auth(), content=data, headers={"Content-Type": content_type})
        checksum = hashlib.sha256(data).hexdigest()
        return {
            "ok": resp.status_code in (200, 201, 204),
            "logical_path": _relative_to_logical(rel),
            "size_bytes": len(data),
            "checksum_sha256": checksum,
            "status_code": resp.status_code,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def download_stream(relative_path: str) -> Iterator[bytes]:
    if not is_configured():
        return iter(())
    rel = (relative_path or "").strip().lstrip("/")
    try:
        import httpx

        url = _webdav_url_for_relative(rel)
        with httpx.Client(timeout=120.0) as client:
            with client.stream("GET", url, auth=_auth()) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_bytes():
                    yield chunk
    except Exception:
        return iter(())


def object_metadata(relative_path: str) -> dict[str, Any]:
    entries = list_logical_directory(
        "/".join((relative_path or "").strip().lstrip("/").split("/")[:-1]),
        depth=1,
    )
    rel = (relative_path or "").strip().lstrip("/")
    for ent in entries:
        if ent.get("relative_path") == rel:
            return {
                "provider_id": "datacloud_webdav",
                "logical_path": ent.get("logical_path"),
                **ent,
            }
    try:
        resp = _request("PROPFIND", rel, depth=0)
        if resp.status_code in (200, 207):
            parsed = _parse_propfind_entries(resp.text, rel)
            if parsed:
                return {"provider_id": "datacloud_webdav", **parsed[0]}
    except Exception:
        pass
    return {"provider_id": "datacloud_webdav", "logical_path": _relative_to_logical(rel), "found": False}


def scan_tree(relative_path: str = "", *, max_entries: int = 500) -> dict[str, Any]:
    """Non-destructive breadth-first scan; does not move or delete files."""
    if not is_configured():
        return {"ok": False, "entries": [], "truncated": False, "error": "not_configured"}
    queue = [(relative_path or "").strip().lstrip("/")]
    seen_dirs: set[str] = set()
    manifest: list[dict[str, Any]] = []
    truncated = False
    while queue and len(manifest) < max_entries:
        current = queue.pop(0)
        if current in seen_dirs:
            continue
        seen_dirs.add(current)
        children = list_logical_directory(current, depth=1)
        for child in children:
            if len(manifest) >= max_entries:
                truncated = True
                break
            manifest.append(child)
            if child.get("type") == "directory" and child.get("relative_path"):
                queue.append(child["relative_path"])
        if truncated:
            break
    return {
        "ok": True,
        "provider_id": "datacloud_webdav",
        "root_logical_path": datacloud_logical_root(),
        "entries": manifest,
        "count": len(manifest),
        "truncated": truncated,
    }


def build_manifest(relative_path: str = "", *, max_entries: int = 1000) -> dict[str, Any]:
    """Manifest for ingestion workers (logical paths + checksum placeholders)."""
    scan = scan_tree(relative_path, max_entries=max_entries)
    files = [e for e in scan.get("entries", []) if e.get("type") == "file"]
    return {
        "provider_id": "datacloud_webdav",
        "root_logical_path": datacloud_logical_root(),
        "generated_from": "datacloud_webdav.build_manifest",
        "file_count": len(files),
        "directory_count": sum(1 for e in scan.get("entries", []) if e.get("type") == "directory"),
        "truncated": scan.get("truncated", False),
        "files": files,
    }


def public_status() -> dict[str, Any]:
    return {
        "provider_id": "datacloud_webdav",
        "configured": is_configured(),
        "root_logical_path": datacloud_logical_root(),
        "role": "primary_research",
    }
