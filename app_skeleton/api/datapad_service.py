"""Intelligent Data Pad — safe section document read/write with backups and AI assists."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app_skeleton.api.llm_client import LLMClient
from app_skeleton.api.paths import PROJECTS_ROOT, lab_storage_root, projects_roots_for_scan, safe_relative_path
from app_skeleton.api.project_processor import (
    LIFECYCLE_RULES,
    find_project_folder,
    get_content_root,
    get_digital_twin,
    _normalize_project_rel_path,
)
from app_skeleton.api.supabase_config import postgres_conn, supabase_db_configured

LOGGER = logging.getLogger(__name__)

DATAPAD_EDIT_ENABLED = os.getenv("DATAPAD_EDIT_ENABLED", "true").lower() in ("1", "true", "yes")
DATAPAD_AI_ENABLED = os.getenv("DATAPAD_AI_ENABLED", "true").lower() in ("1", "true", "yes")
DATAPAD_EDITABLE_EXTENSIONS = {".md", ".txt", ".html", ".rtf"}
MAX_DATAPAD_BYTES = int(os.getenv("MAX_DATAPAD_BYTES", str(2 * 1024 * 1024)))
BACKUP_DIR_NAME = ".datapad_backups"
ARCHIVE_SEGMENT = "99_ARCHIVE"

_llm: LLMClient | None = None


def _llm_client() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm


def datapad_ai_available() -> bool:
    if not DATAPAD_AI_ENABLED:
        return False
    if os.getenv("GROQ_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip():
        return True
    if os.getenv("LLM_PROVIDER", "mock").strip().lower() not in ("", "mock"):
        return bool(os.getenv("LLM_API_KEY", "").strip())
    return False


def _require_edit_enabled() -> None:
    if not DATAPAD_EDIT_ENABLED:
        raise PermissionError("Data Pad editing is disabled (set DATAPAD_EDIT_ENABLED=true).")


def _is_editable(path: Path) -> bool:
    return path.suffix.lower() in DATAPAD_EDITABLE_EXTENSIONS


def _project_roots(project_code: str) -> list[Path]:
    roots: list[Path] = []
    content = get_content_root(project_code)
    if content and content.is_dir():
        roots.append(content.resolve())
    wrapper = find_project_folder(project_code)
    if wrapper and wrapper.is_dir():
        wr = wrapper.resolve()
        if wr not in roots:
            roots.append(wr)
    for scan_root in projects_roots_for_scan():
        if scan_root.is_dir() and scan_root not in roots:
            roots.append(scan_root.resolve())
    if PROJECTS_ROOT.is_dir() and PROJECTS_ROOT.resolve() not in roots:
        roots.append(PROJECTS_ROOT.resolve())
    lr = lab_storage_root()
    if lr and lr not in roots:
        roots.append(lr)
    return roots


def resolve_section_document(project_code: str, relative_path: str) -> tuple[Path, Path]:
    """Return (absolute_path, project_root) for a relative path under an allowed root."""
    norm = _normalize_project_rel_path(relative_path)
    if not norm or norm.startswith(".."):
        raise ValueError("Invalid relative path")
    last_err: Exception | None = None
    for root in _project_roots(project_code):
        try:
            candidate = safe_relative_path(root, norm)
        except ValueError as exc:
            last_err = exc
            continue
        if candidate.is_file():
            if not _is_editable(candidate):
                raise ValueError(f"Extension not editable: {candidate.suffix}")
            return candidate, root
    if last_err:
        raise FileNotFoundError(f"File not found: {norm}") from last_err
    raise FileNotFoundError(f"File not found: {norm}")


def _content_etag(path: Path) -> str:
    stat = path.stat()
    digest = hashlib.sha256(f"{stat.st_mtime_ns}:{stat.st_size}".encode()).hexdigest()[:16]
    return f'"{digest}"'


def _backup_path(project_root: Path, abs_path: Path) -> Path:
    rel = abs_path.relative_to(project_root)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_root = project_root / ARCHIVE_SEGMENT / BACKUP_DIR_NAME
    safe_name = str(rel).replace("/", "__").replace("\\", "__")
    archive_root.mkdir(parents=True, exist_ok=True)
    return archive_root / f"{safe_name}.{ts}.bak"


def _sibling_backup_path(abs_path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return abs_path.parent / f"{abs_path.name}.omeia_backup.{ts}"


def _write_backup(abs_path: Path, project_root: Path) -> str | None:
    if not abs_path.is_file():
        return None
    try:
        rel_archive = project_root / ARCHIVE_SEGMENT
        if rel_archive.exists() or (project_root / ARCHIVE_SEGMENT.split("/")[0]).exists():
            dest = _backup_path(project_root, abs_path)
        else:
            dest = _sibling_backup_path(abs_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(abs_path.read_bytes())
        try:
            return str(dest.relative_to(project_root))
        except ValueError:
            return str(dest.name)
    except OSError as exc:
        LOGGER.warning("Data Pad backup failed for %s: %s", abs_path, exc)
        return None


def _audit_edit(
    *,
    project_code: str,
    relative_path: str,
    event_type: str,
    actor: str,
    details: dict[str, Any],
) -> None:
    if not supabase_db_configured():
        return
    payload = json.dumps({**details, "project_code": project_code, "relative_path": relative_path})
    try:
        import psycopg

        with psycopg.connect(postgres_conn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.datapad_edit_log
                        (project_code, relative_path, event_type, actor, details)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (project_code, relative_path, event_type, actor or "unknown", payload),
                )
            conn.commit()
    except Exception:
        try:
            import psycopg

            asset_id = f"datapad:{project_code}:{relative_path}"
            with psycopg.connect(postgres_conn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO platform.vault_audit_event (asset_id, event_type, actor, details)
                        VALUES (%s, %s, %s, %s::jsonb)
                        """,
                        (asset_id, f"datapad_{event_type}", actor or "unknown", payload),
                    )
                conn.commit()
        except Exception as exc:
            LOGGER.debug("Data Pad audit skipped: %s", exc)


def read_section_document(project_code: str, relative_path: str) -> dict[str, Any]:
    abs_path, root = resolve_section_document(project_code, relative_path)
    if abs_path.stat().st_size > MAX_DATAPAD_BYTES:
        raise ValueError("File too large for Data Pad editor")
    content = abs_path.read_text(encoding="utf-8", errors="replace")
    norm = _normalize_project_rel_path(relative_path)
    doc_type = "markdown" if abs_path.suffix.lower() == ".md" else "text"
    backups = list_recent_backups(project_code, norm, limit=5)
    return {
        "project_code": project_code,
        "relative_path": norm,
        "content": content,
        "size_bytes": abs_path.stat().st_size,
        "modified_at": datetime.fromtimestamp(abs_path.stat().st_mtime, tz=timezone.utc).isoformat(),
        "etag": _content_etag(abs_path),
        "editable": DATAPAD_EDIT_ENABLED,
        "doc_type": doc_type,
        "extension": abs_path.suffix.lower(),
        "ai_enabled": datapad_ai_available(),
        "backups": backups,
    }


def save_section_document(
    project_code: str,
    relative_path: str,
    content: str,
    *,
    actor: str = "unknown",
    create_backup: bool = True,
    expected_etag: str | None = None,
) -> dict[str, Any]:
    _require_edit_enabled()
    abs_path, root = resolve_section_document(project_code, relative_path)
    norm = _normalize_project_rel_path(relative_path)
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_DATAPAD_BYTES:
        raise ValueError("Content too large for Data Pad editor")

    current_etag = _content_etag(abs_path)
    if expected_etag and expected_etag.strip('"') != current_etag.strip('"'):
        raise ConflictError(
            "File changed on disk since last load. Reload or revert to backup.",
            current_etag=current_etag,
        )

    backup_rel = None
    if create_backup and abs_path.is_file():
        backup_rel = _write_backup(abs_path, root)

    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")

    _audit_edit(
        project_code=project_code,
        relative_path=norm,
        event_type="save",
        actor=actor,
        details={"backup_path": backup_rel, "size_bytes": len(encoded)},
    )
    return {
        "status": "saved",
        "project_code": project_code,
        "relative_path": norm,
        "size_bytes": len(encoded),
        "etag": _content_etag(abs_path),
        "backup_path": backup_rel,
    }


class ConflictError(Exception):
    def __init__(self, message: str, *, current_etag: str = "") -> None:
        super().__init__(message)
        self.current_etag = current_etag


def list_recent_backups(project_code: str, relative_path: str, *, limit: int = 10) -> list[dict[str, Any]]:
    norm = _normalize_project_rel_path(relative_path)
    try:
        abs_path, root = resolve_section_document(project_code, norm)
    except FileNotFoundError:
        return []
    safe_name = str(abs_path.relative_to(root)).replace("/", "__").replace("\\", "__")
    archive_dir = root / ARCHIVE_SEGMENT / BACKUP_DIR_NAME
    out: list[dict[str, Any]] = []
    if archive_dir.is_dir():
        for p in sorted(archive_dir.glob(f"{safe_name}.*.bak"), reverse=True)[:limit]:
            out.append({
                "path": str(p.relative_to(root)),
                "name": p.name,
                "modified_at": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
                "size_bytes": p.stat().st_size,
            })
    for p in sorted(abs_path.parent.glob(f"{abs_path.name}.omeia_backup.*"), reverse=True)[:limit]:
        out.append({
            "path": p.name,
            "name": p.name,
            "modified_at": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
            "size_bytes": p.stat().st_size,
        })
    return out[:limit]


def restore_backup(
    project_code: str,
    relative_path: str,
    backup_path: str,
    *,
    actor: str = "unknown",
) -> dict[str, Any]:
    _require_edit_enabled()
    abs_path, root = resolve_section_document(project_code, relative_path)
    norm = _normalize_project_rel_path(relative_path)
    backup_candidate = (root / backup_path).resolve()
    try:
        backup_candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Backup path escapes project root") from exc
    if not backup_candidate.is_file():
        alt = abs_path.parent / backup_path
        if alt.is_file():
            backup_candidate = alt
        else:
            raise FileNotFoundError("Backup file not found")
    content = backup_candidate.read_text(encoding="utf-8", errors="replace")
    return save_section_document(
        project_code,
        norm,
        content,
        actor=actor,
        create_backup=True,
        expected_etag=None,
    )


def _rule_based_outline(content: str, doc_type: str) -> dict[str, Any]:
    lines = content.splitlines()
    headings: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if m:
            headings.append({"line": i + 1, "level": len(m.group(1)), "text": m.group(2).strip()})
    suggestions: list[dict[str, Any]] = []
    if not headings and content.strip():
        first_line = next((ln.strip() for ln in lines if ln.strip()), "Document")
        suggestions.append({
            "action": "add",
            "line": 1,
            "level": 1,
            "suggested": f"# {first_line[:80]}",
            "reason": "Document has no headings; add a top-level title.",
        })
    long_blocks = []
    para_start = 0
    para_len = 0
    for i, line in enumerate(lines):
        if line.strip():
            if para_len == 0:
                para_start = i
            para_len += len(line)
        elif para_len > 400:
            long_blocks.append((para_start + 1, para_len))
            para_len = 0
    for line_no, plen in long_blocks[:3]:
        suggestions.append({
            "action": "split",
            "line": line_no,
            "suggested": "## Section",
            "reason": f"Long paragraph (~{plen} chars) — consider a subheading.",
        })
    dup_levels = [h for h in headings if h["level"] > 3]
    for h in dup_levels[:3]:
        suggestions.append({
            "action": "demote",
            "line": h["line"],
            "level": min(h["level"], 3),
            "suggested": "#" * min(h["level"], 3) + f" {h['text']}",
            "reason": "Prefer H1–H3 for lab notebook structure.",
        })
    improved = content
    if suggestions and suggestions[0]["action"] == "add":
        improved = suggestions[0]["suggested"] + "\n\n" + content
    return {
        "headings": headings,
        "suggestions": suggestions,
        "improved_outline": improved if improved != content else None,
        "mode": "rules",
        "doc_type": doc_type,
    }


def suggest_headings(content: str, doc_type: str = "markdown") -> dict[str, Any]:
    if not content.strip():
        return {"headings": [], "suggestions": [], "improved_outline": "# New section\n\n", "mode": "rules", "doc_type": doc_type}
    if datapad_ai_available():
        prompt = (
            "Analyze this lab document and return JSON only with keys: "
            "headings (list of {line, level, text}), suggestions (list of {action, line, suggested, reason}), "
            "improved_outline (full markdown string with better structure).\n\n"
            f"Document type: {doc_type}\n\n---\n{content[:12000]}"
        )
        system = (
            "You are a scientific writing assistant. Improve heading hierarchy (H1–H3), "
            "section titles, and clarity. Output valid JSON only."
        )
        try:
            raw = _llm_client().generate(prompt, system)
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                data = json.loads(m.group(0))
                data["mode"] = "llm"
                data["doc_type"] = doc_type
                return data
        except (json.JSONDecodeError, Exception) as exc:
            LOGGER.warning("Data Pad heading LLM failed: %s", exc)
    return _rule_based_outline(content, doc_type)


def _basic_proofread(content: str) -> dict[str, Any]:
    fixes: list[dict[str, Any]] = []
    corrected = content
    patterns = [
        (r"\bteh\b", "the", "Common typo"),
        (r"\brecieve\b", "receive", "Spelling"),
        (r"\boccured\b", "occurred", "Spelling"),
        (r"\bseperat(e|ion|ed|ing)\b", r"separat\1", "Spelling"),
        (r"  +", " ", "Double spaces"),
        (r"\n{4,}", "\n\n\n", "Excessive blank lines"),
    ]
    for pattern, repl, reason in patterns:
        for match in re.finditer(pattern, corrected, flags=re.I):
            old = match.group(0)
            new = re.sub(pattern, repl, old, flags=re.I)
            if old != new:
                fixes.append({
                    "start": match.start(),
                    "end": match.end(),
                    "original": old,
                    "replacement": new,
                    "reason": reason,
                })
        corrected = re.sub(pattern, repl, corrected, flags=re.I)
    return {"fixes": fixes, "corrected_text": corrected, "mode": "rules"}


def proofread_content(content: str) -> dict[str, Any]:
    if not content.strip():
        return {"fixes": [], "corrected_text": content, "mode": "rules"}
    if datapad_ai_available():
        prompt = (
            "Proofread this markdown/text for grammar and spelling. Return JSON only with keys: "
            "fixes (list of {start, end, original, replacement, reason}), corrected_text (full string).\n\n"
            f"---\n{content[:12000]}"
        )
        system = "You are a copy editor for scientific lab notes. Preserve meaning and markdown syntax."
        try:
            raw = _llm_client().generate(prompt, system)
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                data = json.loads(m.group(0))
                data.setdefault("fixes", [])
                data.setdefault("corrected_text", content)
                data["mode"] = "llm"
                return data
        except (json.JSONDecodeError, Exception) as exc:
            LOGGER.warning("Data Pad proofread LLM failed: %s", exc)
    return _basic_proofread(content)


def apply_edits(path: str, patches: list[dict[str, Any]], *, project_code: str, actor: str = "unknown") -> dict[str, Any]:
    """Apply structured patches: {op: replace|insert, start, end?, text}."""
    _require_edit_enabled()
    doc = read_section_document(project_code, path)
    text = doc["content"]
    ordered = sorted(patches, key=lambda p: p.get("start", 0), reverse=True)
    for patch in ordered:
        op = (patch.get("op") or "replace").lower()
        start = int(patch.get("start", 0))
        end = int(patch.get("end", start))
        fragment = patch.get("text", "")
        if op == "insert":
            text = text[:start] + fragment + text[start:]
        else:
            text = text[:start] + fragment + text[end:]
    return save_section_document(
        project_code,
        path,
        text,
        actor=actor,
        create_backup=True,
        expected_etag=doc.get("etag"),
    )


def section_summary(project_code: str, section_id: str | None = None) -> dict[str, Any]:
    twin = get_digital_twin(project_code, refresh=False)
    sections_out: list[dict[str, Any]] = []
    lib = twin.get("content_library") or {}
    for sec in lib.get("sections") or []:
        sid = sec.get("id") or ""
        if section_id and sid != section_id:
            continue
        editable: list[dict[str, Any]] = []
        for key in ("text_files", "documents"):
            for item in sec.get(key) or []:
                ext = (item.get("extension") or Path(item.get("path", "")).suffix).lower()
                if ext not in DATAPAD_EDITABLE_EXTENSIONS:
                    continue
                norm = _normalize_project_rel_path(item.get("path") or "")
                status = item.get("extraction_status") or item.get("status") or "unknown"
                editable.append({
                    "path": norm,
                    "name": item.get("name") or Path(norm).name,
                    "extension": ext,
                    "extraction_status": status,
                    "editable": True,
                })
        sections_out.append({
            "id": sid,
            "label": sec.get("label") or sid,
            "editable_count": len(editable),
            "editable_files": editable,
        })
    if section_id and not sections_out:
        label = next((lbl for rid, lbl, _ in LIFECYCLE_RULES if rid == section_id), section_id)
        sections_out.append({"id": section_id, "label": label, "editable_count": 0, "editable_files": []})
    return {
        "project_code": project_code,
        "edit_enabled": DATAPAD_EDIT_ENABLED,
        "ai_enabled": datapad_ai_available(),
        "sections": sections_out,
    }
