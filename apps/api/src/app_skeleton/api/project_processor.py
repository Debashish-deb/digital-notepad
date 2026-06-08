"""Transform raw project folder documents into structured digital records."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app_skeleton.api import document_extraction as de
from app_skeleton.api.paths import (
    PROJECTS_ROOT,
    CATALOG_PATH,
    PROCESSED_DIR,
    PUBLIC_PROCESSED_DIR,
    projects_roots_for_scan,
    safe_relative_path,
)

_LAB_STORAGE_SUBPATHS = ("", "Data", "afarkkilab/Data", "projects")

TEXT_EXTENSIONS = {".txt", ".md", ".py", ".r", ".sh", ".json", ".yaml", ".yml", ".sql", ".csv", ".tsv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".tif", ".tiff", ".bmp"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".dotx"}
PRESENTATION_EXTENSIONS = {".pptx", ".ppt"}
DATA_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
SCANNABLE_EXTENSIONS = (
    TEXT_EXTENSIONS | IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS
    | PRESENTATION_EXTENSIONS | DATA_EXTENSIONS | VIDEO_EXTENSIONS | {".drawio"}
)
SKIP_PARTS = {".git", "node_modules", ".venv", "__pycache__", "media", ".DS_Store", ".dart_tool", "build"}

LIFECYCLE_RULES: list[tuple[str, str, str]] = [
    ("management", "Management & Planning", r"management|planning"),
    ("methods", "Methods & Experiments", r"method|experiment|protocol|wet.?lab|cycif|geomx|xenium"),
    ("data_figures", "Data & Figures", r"data.*figure|data & figure|data and figure|\bfigures?\b|\bdata/|\bdata\\"),
    ("meetings", "Meetings & Updates", r"meeting|update"),
    ("writing", "Writing & Dissemination", r"writing|dissemination|manuscript|abstract|poster|final_manuscript"),
    ("presentations", "Presentations & Slides", r"presentation|slide|poster"),
    ("archive", "Archive", r"archive"),
    ("root", "Project Root", r"^$"),
]

FIGURE_PATH_HINTS = re.compile(
    r"figure|fig[\d_\-.]|snapshot|screenshot|plot|spatial|tsi|rcn|thesis|finished.?fig|images and fig|supplementary.?fig",
    re.I,
)
FIGURE_NAME_HINTS = re.compile(r"^fig[\d_\-.]|^s\d+_p|\.png$|\.svg$|\.jpeg$|\.jpg$", re.I)

DATE_HEADER = re.compile(
    r"^#{1,3}\s*\*{0,2}(\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{4}-\d{2}-\d{2})\*{0,2}\s*$"
)
SECTION_HEADER = re.compile(r"^(#{1,4})\s+\*{0,2}(.+?)\*{0,2}\s*$")
BATCH_PATTERN = re.compile(
    r"(?:(\d+(?:st|nd|rd|th))\s+batch|Batch\s*(\d+))[^\n]{0,100}?(?:\\?\->|→|:)\s*(\d+)\s*(?:chemo-naive\s+)?(?:HGSC\s+)?(?:samples?|patients?)?",
    re.I,
)
SAMPLE_COUNT = re.compile(r"\bn\s*=\s*(\d+)|(\d+)\s+samples?|\b(\d+)\s+patients?", re.I)
GITHUB_URL = re.compile(r"https?://(?:www\.)?github\.com/[\w\-./]+", re.I)
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\])>]+", re.I)
WIN_PATH = re.compile(r"(?:[PLF]:\\[^\s\])>`\"']+|h\d{4,5}/[\w\-./]+)", re.I)
URL_LIKE = re.compile(r"https?://|//docs\.|//doi\.|//bitbucket|//ad\.helsinki", re.I)
NAME_LIKE = re.compile(r"^[A-Z][a-zäöåÄÖÅ\-]+(?:\s+[A-Z][a-zäöåÄÖÅ\-]+){0,3}(?:,\s*[A-Za-z\.]+)?$")
UNIX_PATH = re.compile(r"(?:/[\w\-./]+){2,}")
RESPONSIBLE = re.compile(r"\*\*Responsible:?\s*(.+?)\*\*", re.I)
RESPONSIBLE_LINE = re.compile(
    r"^\*{0,2}Responsible(?:\s+personnel)?:?\s*\*{0,2}\s*(.+?)\s*\*{0,2}\s*$",
    re.I | re.M,
)
PERSONNEL_BULLET = re.compile(
    r"^[-*]\s+\*?([A-Z][A-Za-zäöåÄÖÅ][A-Za-zäöåÄÖÅ\-.'\s]*?)(?:\s*\(([^)]+)\))?\*?\s*$",
    re.M,
)
DATE_ONLY_ROLE = re.compile(r"^(\d{2}\.\d{4}|\d{4})[\s\-–]*$")
INVALID_PERSON_RE = re.compile(
    r"^(personnel|tbd|n/?a|none|role|focus|owner|members?|name|project\s+leader|responsible)\s*:?\s*$",
    re.I,
)
TIMELINE_RANGE = re.compile(r"(\d{2}\.\d{4}|\d{4}\.\d{2}|\d{4})\s*[-–]\s*(?:now|Present|\d{2}\.\d{4}|\d{4})", re.I)
LAB_PI = "Anniina Färkkilä, MD, PhD"
TODO_ITEM = re.compile(r"(?:^|\n)\s*(?:[-*]|\d+\.)\s*(?:TODO|To do|Action|Next step)[:\s]+(.+)", re.I)
MODALITY_LINE = re.compile(r"^[-*]\s*(.+?):\s*(.+)$", re.M)


def _clean(text: str) -> str:
    text = re.sub(r"\[\[([^\]]+)\]\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\{[^}]+\}", "", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = text.replace("**", "")
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r">\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip(" *:,")
    return text


def _classify_file(rel_path: str) -> str:
    p = rel_path.lower()
    if "readme" in p:
        return "overview"
    if "abstract" in p or "essb" in p or "aacr" in p or "eacr" in p or "manuscript" in p:
        return "dissemination"
    if "meeting" in p or "log" in p or "logbook" in p:
        return "activity"
    if "method" in p or "protocol" in p or "experiment" in p:
        return "protocol"
    if p.endswith((".py", ".r", ".sh")) or "pipeline" in p:
        return "pipeline"
    if "writing" in p:
        return "dissemination"
    return "document"


def _scan_folder(folder: Path) -> list[dict[str, Any]]:
    files = []
    if not folder.exists():
        return files
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.suffix.lower() not in {".xlsx", ".docx"}:
            continue
        rel = str(path.relative_to(folder))
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        files.append({
            "path": rel,
            "name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": size,
            "category": _classify_file(rel),
            "folder": str(path.parent.relative_to(folder)) if path.parent != folder else ".",
        })
    return sorted(files, key=lambda f: f["path"])


def _parse_timeline_from_log(content: str, source_file: str) -> list[dict[str, Any]]:
    entries = []
    lines = content.splitlines()
    current_date = None
    current_title = None
    buffer: list[str] = []

    def flush():
        nonlocal buffer
        if not current_date and not buffer:
            return
        body = _clean("\n".join(buffer))
        if not body and not current_title:
            return
        category = "update"
        title = current_title or "Project update"
        tl = title.lower()
        if "meeting" in tl:
            category = "meeting"
        elif "todo" in tl or "to-do" in tl or "to do" in tl:
            category = "action"
        elif "protocol" in tl or "experiment" in tl:
            category = "experiment"
        elif any(k in tl for k in ("kassandra", "spacestat", "deconvolution", "analysis", "pipeline")):
            category = "analysis"
        entries.append({
            "date": current_date or "Undated",
            "title": _clean(title),
            "category": category,
            "summary": body[:500] if body else title,
            "source_file": source_file,
        })
        buffer = []

    for line in lines:
        stripped = line.strip()
        dm = DATE_HEADER.match(stripped)
        if dm:
            flush()
            current_date = dm.group(1).replace("/", ".")
            current_title = None
            continue
        sm = SECTION_HEADER.match(stripped)
        if sm and len(sm.group(1)) >= 2:
            level = len(sm.group(1))
            title = _clean(sm.group(2))
            if level == 2 and DATE_HEADER.match(f"## {title}"):
                continue
            if level >= 3 and current_date:
                if current_title:
                    flush()
                current_title = title
                continue
        if stripped and not stripped.startswith("!["):
            buffer.append(stripped)
    flush()
    return entries


NON_PERSON_NAME_RE = re.compile(
    r"\b(pathway|pathways|inhibitor|inhibitors|levels|samples|panck|p21|p27|cdk|pi3k|"
    r"akt|mtor|fgfr|treatment|resistant|tumou?r|protein|marker|magenta|yellow|green)\b",
    re.I,
)


def _is_valid_person_name(name: str) -> bool:
    name = _clean(name).strip(" :,")
    if not name or len(name) < 4 or len(name) > 72:
        return False
    if INVALID_PERSON_RE.match(name):
        return False
    if URL_LIKE.search(name) or "http" in name.lower():
        return False
    if NON_PERSON_NAME_RE.search(name):
        return False
    if re.match(r"^\.{0,2}/?\d", name):
        return False
    low = name.lower()
    if low.startswith("personnel") or low in ("responsible personnel", "role / focus", ":"):
        return False
    core = name.split(",")[0].strip()
    parts = core.split()
    if len(parts) < 2 or len(parts) > 4:
        return False
    for part in parts:
        token = part.replace("-", "").replace("'", "")
        if not token or not token.isalpha():
            return False
        if not part[0].isupper():
            return False
    return True


def _parse_responsible_raw(raw: str) -> tuple[str, list[str]]:
    """Parse 'Lead (a, b)' or 'Lead1, Lead2 (a, b)' from master file or README."""
    if not raw:
        return "", []
    text = _clean(raw.replace("**", "")).strip(" :")
    if not text or INVALID_PERSON_RE.match(text):
        return "", []

    collaborators: list[str] = []
    lead_part = text
    paren = re.search(r"\(([^)]+)\)", text)
    if paren:
        inner = paren.group(1).strip()
        if inner and not INVALID_PERSON_RE.match(inner):
            for part in re.split(r",|;", inner):
                part = _clean(part)
                if _is_valid_person_name(part):
                    collaborators.append(part)
        lead_part = text[: paren.start()].strip()

    leads: list[str] = []
    for segment in re.split(r",|\band\b", lead_part):
        segment = _clean(segment)
        if _is_valid_person_name(segment):
            leads.append(segment)

    lead = leads[0] if leads else ""
    for extra in leads[1:]:
        if extra.lower() not in {c.lower() for c in collaborators}:
            collaborators.append(extra)
    return lead, collaborators


def _responsible_display(lead: str, collaborators: list[str]) -> str:
    if not lead:
        return ", ".join(collaborators) if collaborators else ""
    if collaborators:
        return f"{lead} ({', '.join(collaborators)})"
    return lead


def _extract_responsible_from_text(text: str) -> tuple[str, list[str], str]:
    best_lead, best_collabs = "", []

    for pattern in (RESPONSIBLE_LINE, RESPONSIBLE):
        for m in pattern.finditer(text[:80000]):
            lead, collabs = _parse_responsible_raw(m.group(1))
            score = (1 if lead else 0) + len(collabs)
            prev = (1 if best_lead else 0) + len(best_collabs)
            if score > prev:
                best_lead, best_collabs = lead, collabs

    return best_lead, best_collabs, _responsible_display(best_lead, best_collabs)


def _personnel_from_catalog(catalog: dict) -> tuple[str, list[str], list[dict]]:
    lead = (catalog.get("project_lead") or "").strip()
    if lead.upper() == "TBD":
        lead = ""
    collaborators = [
        _clean(c) for c in (catalog.get("collaborators") or []) if _is_valid_person_name(_clean(c))
    ]
    members: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(name: str, role: str) -> None:
        name = _clean(name)
        if not _is_valid_person_name(name):
            return
        key = name.lower()
        if key in seen:
            return
        seen.add(key)
        members.append({"name": name, "role": role, "focus": role})

    if lead:
        add(lead, "Project lead")
    for c in collaborators:
        add(c, "Collaborator")
    for m in catalog.get("members") or []:
        name = (m.get("name") or "").strip()
        role = (m.get("role") or "team member").replace("_", " ")
        if role == "project lead":
            role = "Project lead"
        elif role == "collaborator":
            role = "Collaborator"
        add(name, role)

    if not lead and members:
        lead = members[0]["name"]
    return lead, collaborators, members


def _role_is_person_name(role: str) -> bool:
    """True when role field mistakenly contains another person's name."""
    role = (role or "").strip()
    if not role or role.lower() in ("team member", "collaborator", "project lead"):
        return False
    return _is_valid_person_name(role)


def _merge_personnel(
    base: list[dict[str, Any]], extra: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    out = list(base)
    seen = {p["name"].lower() for p in out}
    for p in extra:
        name = (p.get("name") or "").strip()
        if not _is_valid_person_name(name):
            continue
        role = (p.get("role") or "Team member").strip()
        if role.lower() in ("role / focus", "role", "focus") or _role_is_person_name(role):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"name": name, "role": role, "focus": p.get("focus") or role})
    return out[:30]


def _priority_doc_text(file_inventory: list[dict], folder: Path | None) -> str:
    if not folder:
        return ""
    priority_names = ("readme", "overview", "project_info", "project_log", "_log", "log_file")
    chunks: list[str] = []
    for f in sorted(file_inventory, key=lambda x: x["path"]):
        path_low = f["path"].lower()
        if f["extension"] not in {".md", ".txt"}:
            continue
        if not any(h in path_low for h in priority_names):
            continue
        try:
            chunks.append((folder / f["path"]).read_text(encoding="utf-8", errors="ignore")[:12000])
        except OSError:
            continue
    return "\n".join(chunks)


def _parse_cohorts(text: str) -> list[dict[str, Any]]:
    cohorts = []
    seen = set()
    for m in BATCH_PATTERN.finditer(text):
        batch_num = (m.group(1) or m.group(2) or "?").replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
        count = int(m.group(3))
        if count > 500:
            continue
        key = f"batch_{batch_num}"
        if key in seen:
            continue
        seen.add(key)
        start = max(0, m.start() - 10)
        end = min(len(text), m.end() + 200)
        context = _clean(text[start:end])
        cohorts.append({
            "batch_id": f"Batch {batch_num}",
            "sample_count": count,
            "description": context[:220],
            "exclusions": [],
        })
    for block in re.split(r"(?i)(Batch\s+\d+)", text):
        excl = re.findall(r"⚠️?\s*Exclusion[s]?:?\s*(.+?)(?:\n|$)", block, re.I)
        if excl and cohorts:
            cohorts[-1]["exclusions"].extend([_clean(e) for e in excl[:3]])
    return cohorts[:8]


def _role_from_hint(hint: str) -> str:
    hint = _clean(hint.replace(">", " "))
    if not hint or DATE_ONLY_ROLE.match(hint):
        return "Team member"
    if _is_valid_person_name(hint):
        return "Team member"
    return hint[:120]


def _clean_multiline(text: str) -> str:
    text = re.sub(r"\[\[([^\]]+)\]\]\([^)]+\)", r"\1", text or "")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("!["):
            continue
        lines.append(line)
    return "\n\n".join(lines).strip()


def _person_name_token(raw: str) -> str:
    raw = _clean((raw or "").replace("**", ""))
    if not raw:
        return ""
    base = raw.split("(")[0].split(",")[0].strip()
    return _clean(base)


_README_SECTION_STOP = (
    r"(?:\n\s*(?:\*{0,2})?(?:Project\s+(?:lead|members?|leader)|External\s+collaborators?|Members\s+of\s+the\s+project)"
    r"|\n\s*(?:\*{0,2})?(?:Project\s+Log|Logbook|Changelog|Updates?|Meeting\s+(?:notes?|log))"
    r"|\n#{1,3}\s|\Z)"
)

_README_LOG_START = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s*)?\*{0,2}(?:Project\s+Log|Logbook|Changelog|Updates?|Meeting\s+(?:notes?|log))\*{0,2}\s*:?\s*(?:\n|$)",
    re.I,
)

_PERSONNEL_LINE = re.compile(
    r"^\s*(?:\*{0,2})?(?:Project\s+(?:lead|members?|leader)|Principal\s+investigator|PI|Members\s+of\s+the\s+project|External\s+collaborators?)\b",
    re.I,
)


def _format_intro_prose(text: str) -> str:
    """Collapse soft line wraps into paragraphs; keep intentional blank-line breaks."""
    paragraphs: list[str] = []
    current: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("!["):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        line = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        if _PERSONNEL_LINE.match(line):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    if not paragraphs:
        return ""
    if len(paragraphs) > 2 and (sum(len(p) for p in paragraphs) / len(paragraphs)) < 110:
        return " ".join(paragraphs).strip()
    return "\n\n".join(p for p in paragraphs if p).strip()


def _dedupe_description_blocks(text: str) -> str:
    """Drop repeated **Description:** tails that duplicate the opening narrative."""
    if not text:
        return ""
    parts = re.split(r"\s*\*{0,2}Description\s*:\s*\*{0,2}\s*", text, flags=re.I)
    if len(parts) <= 1:
        return text.strip()
    head = parts[0].strip()
    for tail in parts[1:]:
        tail = tail.strip()
        if not tail:
            continue
        if head and tail.lower().startswith(head[: min(len(head), 120)].lower()):
            continue
        if len(tail) > len(head) + 40:
            return head
    return head


def _strip_cover_tail_sections(text: str) -> str:
    """Remove log, team, and heading blocks that belong outside the cover narrative."""
    if not text:
        return ""
    cut = _README_LOG_START.search(text)
    if cut:
        text = text[: cut.start()].strip()
    for marker in (
        r"\n\s*(?:\*{0,2})?Project\s+(?:lead|members?|leader)\b",
        r"\n\s*(?:\*{0,2})?Members\s+of\s+the\s+project\b",
        r"\n\s*(?:\*{0,2})?External\s+collaborators?\b",
        r"\n#{1,3}\s",
    ):
        m = re.search(marker, text, re.I)
        if m:
            text = text[: m.start()].strip()
    return text


def _sanitize_cover_summary(text: str) -> str:
    text = _strip_cover_tail_sections(text)
    text = _dedupe_description_blocks(text)
    text = _format_intro_prose(text)
    return text.strip()


def _format_log_body(text: str) -> str:
    lines: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("!["):
            continue
        line = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", line)
        lines.append(line)
    return "\n".join(lines).strip()


def _extract_readme_log(text: str) -> str:
    if not text:
        return ""
    patterns = (
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}Project\s+Log\*{0,2}[^\n]*\n+(.*?)(?:\n#{1,3}\s|\Z)",
        r"(?:^|\n)\s*\*{0,2}Project\s+Log\*{0,2}\s*:?\s*\n+(.*?)(?:\n\s*(?:\*{0,2})?(?:Project\s+(?:lead|members?)|#{1,3}\s)|\Z)",
        r"(?:^|\n)\s*#{1,3}\s*\*{0,2}(?:Logbook|Changelog|Updates?)\*{0,2}[^\n]*\n+(.*?)(?:\n#{1,3}\s|\Z)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if not match:
            continue
        body = _format_log_body(match.group(1))
        if len(body) >= 20:
            return body[:12000]
    return ""


def _extract_readme_intro(text: str) -> str:
    if not text:
        return ""
    patterns = (
        r"\*{0,2}Project\s+introduction\*{0,2}\s*:?\s*\n+(.*?)" + _README_SECTION_STOP,
        r"(\*{0,2}Welcome to[^\n*]+?\*{0,2}\s*\n+.*?)" + _README_SECTION_STOP,
        r"((?:The objective|The aim|This project|We aim)[^\n]{20,}.*?)" + _README_SECTION_STOP,
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if not match:
            continue
        intro = _sanitize_cover_summary(match.group(1))
        if len(intro) >= 80:
            return intro[:2200]
    return ""


def _catalog_summary_is_stub(summary: str) -> bool:
    summary = (summary or "").strip()
    if not summary or len(summary) < 60:
        return True
    low = summary.lower()
    if low.startswith(("aim is to", "the aim is", "the aim of")) and len(summary) < 180:
        return True
    return False


def _resolve_project_summary(
    catalog: dict[str, Any],
    priority_text: str,
    combined_text: str,
) -> tuple[str, str]:
    catalog_summary = (catalog.get("project_summary") or "").strip()
    catalog_rq = (catalog.get("research_question") or "").strip()
    readme_intro = _extract_readme_intro(priority_text)
    guessed = de._guess_project_summary(priority_text or combined_text)

    summary = catalog_summary
    if readme_intro and (
        _catalog_summary_is_stub(catalog_summary) or len(readme_intro) > len(catalog_summary) + 40
    ):
        summary = readme_intro
    elif not summary:
        summary = _sanitize_cover_summary(guessed)
    else:
        summary = _sanitize_cover_summary(summary)

    research_question = catalog_rq
    if research_question and summary and research_question.lower() == summary.lower():
        research_question = ""
    elif research_question and len(research_question) < 24 and summary:
        research_question = ""
    return summary, research_question


def _append_person(
    personnel: list[dict[str, Any]],
    name: str,
    role: str,
) -> None:
    name = _person_name_token(name)
    if not _is_valid_person_name(name):
        return
    role = _role_from_hint(role) if role else "Team member"
    personnel.append({"name": name, "role": role, "focus": role})


def _parse_comma_member_list(segment: str, default_role: str = "Team member") -> list[dict[str, Any]]:
    personnel: list[dict[str, Any]] = []
    for part in re.split(r",|\band\b", segment):
        _append_person(personnel, part, default_role)
    return personnel


def _parse_project_lead_lines(text: str) -> list[dict[str, Any]]:
    personnel: list[dict[str, Any]] = []
    for match in re.finditer(
        r"(?:^|\n)\s*\*{0,2}Project\s+lead(?:er)?\*{0,2}\s*:?\s*(.+?)\s*(?:\n|$)",
        text,
        re.I,
    ):
        raw = match.group(1).strip()
        name = _person_name_token(raw)
        role = "Project lead"
        paren = re.search(r"\(([^)]+)\)", raw)
        if paren:
            role = _role_from_hint(paren.group(1)) or role
        if _is_valid_person_name(name):
            personnel.insert(0, {"name": name, "role": role, "focus": role})
    return personnel


def _parse_project_members_section(text: str) -> list[dict[str, Any]]:
    personnel: list[dict[str, Any]] = []
    inline = re.search(
        r"(?:\*{0,2})?Project\s+members?\s*(?:\([^)]*\))?\s*:?\s*\*{0,2}\s*([^\n]+)",
        text,
        re.I,
    )
    if inline:
        tail = inline.group(1).strip()
        if tail and not tail.endswith(":"):
            personnel.extend(_parse_comma_member_list(tail))

    block = re.search(
        r"(?:\*{0,2})?Project\s+members?\s*(?:\([^)]*\))?\s*:?\s*\*{0,2}\s*\n(.*?)"
        + _README_SECTION_STOP,
        text,
        re.I | re.S,
    )
    if not block:
        return personnel

    for line in block.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        bullet = re.match(r"^[-*]\s+\*?(.+?)\*?\s*$", line)
        if bullet:
            inner = bullet.group(1).strip()
            name_m = re.match(r"^([^(]+?)(?:\s*\(([^)]+)\))?\s*$", inner)
            if name_m:
                _append_person(personnel, name_m.group(1), name_m.group(2) or "Team member")
            continue
        if ":" in line:
            left, right = line.split(":", 1)
            if _is_valid_person_name(_person_name_token(left)):
                _append_person(personnel, left, right)
    return personnel


def _parse_members_of_project(text: str) -> list[dict[str, Any]]:
    personnel: list[dict[str, Any]] = []
    block = re.search(
        r"Members of the project\s*\n(.*?)(?:\n#\s*\*?\*?Project Log|\n##\s+Project Log|\n#\s+Project Log|\Z)",
        text,
        re.I | re.S,
    )
    if not block:
        return personnel

    body = re.sub(r">\s*\n\s*", " ", block.group(1))
    for line in body.splitlines():
        line = _clean(line.replace(">", " "))
        if not line:
            continue
        lead_m = re.match(r"Project leader:?\s*(.+)$", line, re.I)
        if lead_m:
            name = _clean(lead_m.group(1))
            if _is_valid_person_name(name):
                personnel.insert(0, {"name": name, "role": "Project lead", "focus": "Project lead"})
            continue
        if ":" not in line:
            continue
        names_part, role_part = line.split(":", 1)
        role = _clean(role_part)[:120]
        if not role:
            continue
        for segment in re.split(r",|\band\b", names_part):
            segment = _clean(segment)
            if _is_valid_person_name(segment):
                personnel.append({"name": segment, "role": role, "focus": role})
            elif len(segment) >= 3 and segment[0].isupper() and segment.replace(" ", "").isalpha():
                personnel.append({"name": segment, "role": role, "focus": role})
    return personnel


def _parse_personnel(text: str) -> list[dict[str, Any]]:
    personnel: list[dict[str, Any]] = []

    personnel.extend(_parse_project_lead_lines(text))
    personnel.extend(_parse_project_members_section(text))
    personnel.extend(_parse_members_of_project(text))

    personnel_section = re.search(
        r"Responsible\s+personnel[^\n]*\n(.*?)(?:\n\*\*|\nInput files|\n# |\Z)",
        text,
        re.I | re.S,
    )
    if personnel_section:
        section_text = re.sub(r">\s*\n\s*", " ", personnel_section.group(1))
        for line in section_text.splitlines():
            line = line.strip()
            if not line.startswith("-") and not line.startswith("*"):
                continue
            inner_m = re.match(r"^[-*]\s+\*?(.+?)\*?\s*$", line)
            if not inner_m:
                continue
            inner = inner_m.group(1).strip()
            name_m = re.match(
                r"^([A-Z][a-zäöåÄÖÅ]+(?:\s+[A-Z][a-zäöåÄÖÅ][a-zäöåÄÖÅ\-']*)+)",
                inner,
            )
            if not name_m:
                continue
            name = _clean(name_m.group(1))
            rest = inner[len(name_m.group(0)) :]
            role_hints = re.findall(r"\(([^)]+)\)", rest)
            role_hint = ""
            for hint in role_hints:
                hint = _clean(hint)
                if hint and not DATE_ONLY_ROLE.match(hint):
                    role_hint = hint
                    break
            if not role_hint and role_hints:
                role_hint = role_hints[0]
            if _is_valid_person_name(name):
                role = _role_from_hint(role_hint)
                personnel.append({"name": name, "role": role, "focus": role})

    table_section = re.search(
        r"(?:Name\s*\n(?:Role[^\n]*\n)?)(.*?)(?:\nTimeline|\nData Architecture|\nSoftware|\n#|\Z)",
        text,
        re.I | re.S,
    )
    if table_section:
        lines = [line.strip() for line in table_section.group(1).splitlines() if line.strip()]
        i = 0
        while i < len(lines) - 1:
            name = _clean(lines[i])
            role = _clean(lines[i + 1]) if i + 1 < len(lines) else ""
            if _is_valid_person_name(name) and role and not _is_valid_person_name(role):
                personnel.append({"name": name, "role": role, "focus": role})
                i += 2
            else:
                i += 1

    members_block = re.search(
        r"Members of the project[^\n]*\n(.*?)(?:\n#|\nData |\Z)",
        text,
        re.I | re.S,
    )
    if members_block:
        for line in members_block.group(1).splitlines():
            line = line.strip()
            if not line or line.lower().startswith("project leader"):
                continue
            m = re.match(r"^([A-Z][a-zA-ZäöåÄÖÅ, \-'.]+?):\s*(.+)$", line)
            if m:
                name = _clean(m.group(1))
                role = _clean(m.group(2))
                if _is_valid_person_name(name) and len(role) < 120 and not _is_valid_person_name(role):
                    personnel.append({"name": name, "role": role, "focus": role})

    for m in re.finditer(r"Owner Name\(s\):\s*([^\n]+)", text, re.I):
        segment = m.group(1)
        for part in re.split(r",|\band\b", segment):
            part = _clean(part)
            if _is_valid_person_name(part):
                personnel.append({"name": part, "role": "Owner", "focus": "Owner"})

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in personnel:
        key = p["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return deduped[:25]


def _parse_modalities(text: str) -> list[dict[str, Any]]:
    modalities = []
    section = re.search(r"(?:Core Data Modalities|Data Modalities)(.*?)(?:\n[A-Z#]|\Z)", text, re.I | re.S)
    source = section.group(1) if section else text
    for m in MODALITY_LINE.finditer(source):
        name = _clean(m.group(1))
        desc = _clean(m.group(2))
        if len(name) < 40:
            modalities.append({"name": name, "type": name.split()[0] if name else "assay", "description": desc})
    known = ["tCycIF", "t-CycIF", "GeoMx", "WES", "RNA-seq", "scRNA-seq", "CosMx", "Xenium", "CycIF"]
    if section:
        existing = {m["name"].lower() for m in modalities}
        for k in known:
            if k.lower() in source.lower() and k.lower() not in existing:
                modalities.append({"name": k, "type": "assay", "description": "Referenced in modality section"})
    return modalities[:15]


def _parse_data_assets(text: str, file_inventory: list[dict]) -> dict[str, Any]:
    raw_paths = WIN_PATH.findall(text)
    paths = sorted(set(_clean(p.rstrip(".,;*")) for p in raw_paths if not URL_LIKE.search(p)))
    repos = sorted(set(GITHUB_URL.findall(text)))
    folders: dict[str, dict] = {}
    for f in file_inventory:
        folder = f["folder"]
        if folder not in folders:
            folders[folder] = {"path": folder, "file_count": 0, "categories": set()}
        folders[folder]["file_count"] += 1
        folders[folder]["categories"].add(f["category"])
    folder_tree = [
        {"path": v["path"], "file_count": v["file_count"], "categories": sorted(v["categories"])}
        for v in sorted(folders.values(), key=lambda x: x["path"])
    ]
    return {
        "storage_paths": paths[:25],
        "repositories": repos,
        "folder_tree": folder_tree,
    }


def _parse_dissemination(files: list[dict], folder: Path) -> list[dict[str, Any]]:
    items = []
    for f in files:
        if f["category"] != "dissemination":
            continue
        path = folder / f["path"]
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:3000]
        except OSError:
            continue
        title = f["name"].replace("_", " ").rsplit(".", 1)[0]
        author = ""
        am = re.search(r"by[_\s]+([A-Za-z_ ]+)|([A-Z][a-z]+ [A-Z][a-z]+)", f["name"])
        if am:
            author = _clean(am.group(1) or am.group(2) or "")
        conference = ""
        for conf in ("AACR", "EACR", "EMBO", "ESSB", "SCSO"):
            if conf.lower() in f["path"].lower():
                conference = conf
        year_m = re.search(r"20\d{2}", f["path"])
        dois = DOI_PATTERN.findall(content)
        items.append({
            "title": _clean(title),
            "author": author,
            "conference": conference,
            "year": int(year_m.group()) if year_m else None,
            "doi": dois[0] if dois else None,
            "type": "abstract" if "abstract" in f["path"].lower() else "manuscript",
            "source_file": f["path"],
        })
    return items


def _parse_protocols(files: list[dict], folder: Path) -> list[dict[str, Any]]:
    protocols = []
    for f in files:
        if f["category"] != "protocol":
            continue
        path = folder / f["path"]
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        steps = []
        for line in content.splitlines():
            line = line.strip()
            if re.match(r"^\d+[\.)]\s+", line) or line.startswith("- "):
                step = _clean(re.sub(r"^\d+[\.)]\s+|^-\s+", "", line))
                if 10 < len(step) < 300:
                    steps.append(step)
        key_points = [_clean(s) for s in re.findall(r"^[-*]\s+(.+)$", content, re.M) if 15 < len(s) < 200][:8]
        protocols.append({
            "title": f["name"].rsplit(".", 1)[0].replace("_", " "),
            "category": f["folder"],
            "steps": steps[:12] or key_points,
            "source_file": f["path"],
        })
    return protocols


def _parse_meetings(timeline: list[dict]) -> list[dict[str, Any]]:
    return [
        {
            "date": e["date"],
            "title": e["title"],
            "summary": e["summary"],
            "source_file": e["source_file"],
        }
        for e in timeline if e["category"] == "meeting"
    ]


def _load_catalog() -> dict[str, dict]:
    if not CATALOG_PATH.exists():
        return {}
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {p["project_code"]: p for p in data}


DRIVE_STUB = re.compile(r"-\d{8}T\d{6}Z-\d+-?\d*$")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def resolve_content_root(folder: Path, project_code: str = "") -> Path:
    """Descend into inner folder when wrapper is a Google Drive export stub."""
    if not folder.is_dir():
        return folder
    subdirs = [d for d in folder.iterdir() if d.is_dir() and not d.name.startswith(".")]
    root_files = [f for f in folder.iterdir() if f.is_file()]

    if DRIVE_STUB.search(folder.name) and len(subdirs) == 1 and not root_files:
        return subdirs[0]

    if len(subdirs) == 1 and not root_files:
        inner = subdirs[0]
        inner_files = sum(1 for _ in inner.rglob("*") if _.is_file())
        outer_files = sum(1 for _ in folder.rglob("*") if _.is_file())
        if inner_files >= max(outer_files - 2, 1):
            return inner

    if project_code:
        code = _norm(project_code)
        for d in subdirs:
            if code and code in _norm(d.name):
                return d
    return folder


def _classify_lifecycle_section(rel_path: str) -> str:
    parts = Path(rel_path).parts
    probe = " ".join(parts[:3]).lower() if parts else ""
    if len(parts) <= 1 and (not parts or not parts[0].startswith(("1", "2", "3", "4", "5", "6"))):
        return "root"
    for sec_id, _label, pattern in LIFECYCLE_RULES:
        if sec_id == "root":
            continue
        if re.search(pattern, probe, re.I):
            return sec_id
    return "root"


def _classify_asset_type(ext: str, rel_path: str, name: str) -> str:
    p = rel_path.lower()
    n = name.lower()
    if ext in IMAGE_EXTENSIONS:
        if FIGURE_PATH_HINTS.search(p) or FIGURE_NAME_HINTS.search(n) or "figure" in p:
            return "figure"
        return "image"
    if ext in DOCUMENT_EXTENSIONS:
        if "fig" in n and ext == ".pdf":
            return "figure"
        return "document"
    if ext in PRESENTATION_EXTENSIONS:
        return "presentation"
    if ext in DATA_EXTENSIONS:
        return "data"
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "other"


def _figure_priority(rel_path: str, name: str) -> int:
    p, n = rel_path.lower(), name.lower()
    score = 0
    if re.match(r"^figures?/", p) or p.startswith("figures/"):
        score += 12
    if "final_manuscript" in p:
        score += 10
    if re.search(r"fig[\d_\-.]", n):
        score += 9
    if FIGURE_PATH_HINTS.search(p):
        score += 5
    if "screenshot" in p or "snapshot" in p or "spatial_count" in p:
        score -= 4
    if "archive" in p:
        score += 2
    depth = len(Path(rel_path).parts)
    if depth > 7:
        score -= min(depth - 7, 8)
    if n.endswith((".svg",)):
        score += 1
    return score


def _scan_all_assets(folder: Path) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    if not folder.exists():
        return assets
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        ext = path.suffix.lower()
        if ext not in SCANNABLE_EXTENSIONS:
            continue
        rel = str(path.relative_to(folder))
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        name = path.name
        asset_type = _classify_asset_type(ext, rel, name)
        lifecycle = _classify_lifecycle_section(rel)
        priority = _figure_priority(rel, name) if asset_type in ("figure", "image") else 0
        previewable = ext in IMAGE_EXTENSIONS or ext == ".pdf"
        excerpt = ""
        if ext in {".md", ".txt"} and size < 500_000:
            try:
                excerpt = path.read_text(encoding="utf-8", errors="ignore")[:400].strip()
            except OSError:
                pass
        assets.append({
            "path": rel,
            "name": name,
            "extension": ext,
            "size_bytes": size,
            "asset_type": asset_type,
            "lifecycle_section": lifecycle,
            "category": _classify_file(rel),
            "folder": str(path.parent.relative_to(folder)) if path.parent != folder else ".",
            "priority": priority,
            "previewable": previewable,
            "excerpt": excerpt,
        })
    return sorted(assets, key=lambda a: a["path"])


def _cap(items: list, limit: int) -> list:
    return items[:limit] if len(items) > limit else items


def _build_content_library(assets: list[dict[str, Any]]) -> dict[str, Any]:
    section_defs = {r[0]: {"id": r[0], "label": r[1], "figures": [], "documents": [], "presentations": [], "data_files": [], "text_files": [], "videos": [], "counts": {}} for r in LIFECYCLE_RULES}
    figures_pool: list[dict] = []
    totals: dict[str, int] = {}

    for a in assets:
        sec_id = a.get("lifecycle_section", "root")
        sec = section_defs.get(sec_id, section_defs["root"])
        atype = a["asset_type"]
        totals[atype] = totals.get(atype, 0) + 1
        totals["all"] = totals.get("all", 0) + 1
        item = {
            "path": a["path"],
            "name": a["name"],
            "extension": a["extension"],
            "size_bytes": a["size_bytes"],
            "asset_type": atype,
            "previewable": a.get("previewable", False),
            "excerpt": a.get("excerpt", ""),
        }
        bucket_key = {
            "figure": "figures", "image": "figures",
            "document": "documents", "presentation": "presentations",
            "data": "data_files", "text": "text_files", "video": "videos",
        }.get(atype, "documents")
        sec["counts"][atype] = sec["counts"].get(atype, 0) + 1
        if atype in ("figure", "image"):
            figures_pool.append({**item, "section": sec_id, "section_label": sec["label"], "priority": a.get("priority", 0)})
        lst = sec[bucket_key]
        if len(lst) < 40:
            lst.append(item)

    figures_gallery = sorted(figures_pool, key=lambda x: (-x["priority"], x["path"]))[:72]
    sections = []
    order = [r[0] for r in LIFECYCLE_RULES]
    for sid in order:
        sec = section_defs[sid]
        if not sec["counts"]:
            continue
        sections.append({
            "id": sec["id"],
            "label": sec["label"],
            "figures": sec["figures"],
            "documents": sec["documents"],
            "presentations": sec["presentations"],
            "data_files": sec["data_files"],
            "text_files": sec["text_files"],
            "videos": sec["videos"],
            "counts": sec["counts"],
            "total_files": sum(sec["counts"].values()),
        })

    return {
        "sections": sections,
        "figures_gallery": figures_gallery,
        "totals": totals,
        "figure_count": totals.get("figure", 0) + totals.get("image", 0),
    }


def get_content_root(project_code: str) -> Path | None:
    folder = find_project_folder(project_code)
    if not folder:
        return None
    catalog = _load_catalog().get(project_code, {})
    return resolve_content_root(folder, project_code or catalog.get("project_code", ""))


def _content_root_relative(folder: Path | None) -> str | None:
    if not folder:
        return None
    try:
        return str(folder.relative_to(PROJECTS_ROOT))
    except ValueError:
        return folder.name


def _folder_file_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for _ in path.rglob("*") if _.is_file())


def _folder_search_hints(catalog: dict[str, Any], project_code: str) -> list[str]:
    """Relative path hints for locating a project folder across scan roots."""
    hints: list[str] = []
    seen: set[str] = set()

    def add_hint(value: str) -> None:
        text = (value or "").strip().strip("/\\")
        if not text or text in seen:
            return
        seen.add(text)
        hints.append(text)

    add_hint(catalog.get("folder_path") or "")
    for alias in catalog.get("folder_aliases") or []:
        add_hint(str(alias))

    idx = catalog.get("project_index")
    code = (project_code or catalog.get("project_code") or "").strip()
    if idx and code:
        add_hint(f"{idx}_{code}")
        add_hint(f"{idx}-{code}")
        add_hint(f"{idx}_{code.replace('-', '_')}")
        add_hint(f"{idx}-{code.replace('_', '-')}")

    for part in catalog.get("folder_structure") or []:
        add_hint(str(part))

    return hints


def _collect_folder_candidates(root: Path, rel_hint: str) -> list[Path]:
    """Try a catalog hint at common lab-storage subpaths."""
    found: list[Path] = []
    rel = rel_hint.strip().strip("/\\")
    if not rel:
        return found
    for sub in _LAB_STORAGE_SUBPATHS:
        candidate = (root / sub / rel) if sub else (root / rel)
        if candidate.is_dir():
            found.append(candidate)
    return found


def find_project_folder(project_code: str) -> Path | None:
    catalog = _load_catalog().get(project_code, {})
    roots = projects_roots_for_scan()
    if not roots:
        return None

    matches: list[tuple[int, Path]] = []
    seen_paths: set[str] = set()

    def consider(path: Path | None) -> None:
        if not path or not path.is_dir():
            return
        key = str(path.resolve())
        if key in seen_paths:
            return
        seen_paths.add(key)
        matches.append((_folder_file_count(path), path))

    for hint in _folder_search_hints(catalog, project_code):
        for root in roots:
            for candidate in _collect_folder_candidates(root, hint):
                consider(candidate)

    code_clean = _norm(project_code)
    project_index = catalog.get("project_index")
    for root in roots:
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for folder in children:
            if not folder.is_dir() or folder.name in ("compiled_scripts", "project_scripts"):
                continue
            name_clean = _norm(folder.name)
            if code_clean and (
                code_clean in name_clean
                or name_clean.startswith(code_clean)
                or name_clean.endswith(code_clean)
            ):
                consider(folder)
                continue
            if project_index and folder.name.startswith(f"{project_index}"):
                tail = folder.name[len(str(project_index)) :]
                if tail[:1] in ("_", "-", ".") and code_clean in _norm(folder.name):
                    consider(folder)

    if not matches:
        return None
    matches.sort(key=lambda x: (-x[0], str(x[1])))
    return matches[0][1]


def process_project(project_code: str, catalog_entry: dict | None = None) -> dict[str, Any]:
    catalog = catalog_entry or _load_catalog().get(project_code, {})
    wrapper = find_project_folder(project_code)
    folder = resolve_content_root(wrapper, project_code) if wrapper else None
    file_inventory = de._scan_folder(folder) if folder else []
    all_assets = de._scan_all_assets(folder) if folder else []
    content_library = de._build_content_library(all_assets) if all_assets else {
        "sections": [], "figures_gallery": [], "totals": {}, "figure_count": 0
    }

    document_records: list[de.ExtractionResult] = []
    vector_chunks: list[dict[str, Any]] = []
    extraction_summary: dict[str, Any] = {
        "total_scannable_assets": 0,
        "extracted_records": 0,
        "chunk_count": 0,
        "status_counts": {},
        "extractor_counts": {},
        "extension_counts": {},
        "errors": [],
    }
    if folder and all_assets:
        document_records, vector_chunks, extraction_summary = de._extract_project_documents(folder, all_assets)

    combined_text = de._combine_text_records(document_records)
    timeline: list[dict] = []
    for r in document_records:
        if r.status != "extracted" or not r.text:
            continue
        if r.extension in {".md", ".txt", ".rtf", ".docx", ".pdf"} and (
            r.document_kind in {"markdown", "plain_text", "word_document", "pdf", "rich_text"}
            or any(k in r.path.lower() for k in ("log", "meeting", "update", "readme", "overview"))
        ):
            timeline.extend(_parse_timeline_from_log(r.text, r.path))
    for action in de._extract_action_items(combined_text):
        timeline.append({
            "date": "Undated",
            "title": action["title"],
            "category": "action",
            "summary": action["summary"],
            "source_file": action["source_file"],
        })

    timeline.sort(key=lambda e: e.get("date", ""), reverse=True)
    seen_tl = set()
    unique_timeline = []
    for e in timeline:
        key = (e.get("date"), e.get("title"), e.get("source_file"))
        if key not in seen_tl:
            seen_tl.add(key)
            unique_timeline.append(e)

    catalog_lead, catalog_collabs, catalog_personnel = _personnel_from_catalog(catalog)
    priority_text = _priority_doc_text(file_inventory, folder)
    doc_lead, doc_collabs, doc_responsible = _extract_responsible_from_text(priority_text or "")
    if not doc_lead and not doc_collabs:
        doc_lead, doc_collabs, doc_responsible = _extract_responsible_from_text(combined_text[:25000])
    parsed_personnel = _parse_personnel(priority_text)
    if len(parsed_personnel) < 2:
        parsed_personnel = _merge_personnel(parsed_personnel, _parse_personnel(combined_text[:40000]))

    lead = doc_lead or catalog_lead
    collaborators = list(dict.fromkeys(
        [c for c in catalog_collabs + doc_collabs if _is_valid_person_name(c)]
    ))
    personnel = _merge_personnel(catalog_personnel, parsed_personnel)
    if lead:
        personnel = _merge_personnel(
            [{"name": lead, "role": "Project lead", "focus": "Project lead"}],
            personnel,
        )
    for c in collaborators:
        personnel = _merge_personnel(
            [{"name": c, "role": "Collaborator", "focus": "Collaborator"}],
            personnel,
        )

    cohorts = _parse_cohorts(combined_text)
    if not cohorts and catalog.get("cohort_size"):
        cohorts = [{"batch_id": "Primary", "sample_count": None, "description": catalog["cohort_size"], "exclusions": []}]

    modalities = [{"name": m, "type": "assay", "description": ""} for m in catalog.get("modalities", [])]
    if not modalities:
        modalities = _parse_modalities(combined_text)

    data_assets = _parse_data_assets(combined_text, file_inventory)
    if catalog.get("repository") and catalog["repository"] not in data_assets["repositories"]:
        data_assets["repositories"].insert(0, catalog["repository"])

    if document_records:
        dissemination = de._parse_dissemination_from_records(document_records)
        protocols = de._parse_protocols_from_records(document_records)
    else:
        dissemination = _parse_dissemination(file_inventory, folder) if folder else []
        protocols = _parse_protocols(file_inventory, folder) if folder else []
    meetings = _parse_meetings(unique_timeline)
    dois = sorted(set(DOI_PATTERN.findall(combined_text)))
    publications = []
    if catalog.get("publication"):
        publications.append({"title": catalog["publication"], "doi": dois[0] if dois else None, "source": "catalog"})
    for doi in dois:
        if not any(p.get("doi") == doi for p in publications):
            publications.append({"title": f"DOI {doi}", "doi": doi, "source": "document"})

    timeline_range = TIMELINE_RANGE.search(priority_text or combined_text)
    if personnel and not collaborators:
        collaborators = [
            p["name"]
            for p in personnel
            if p["name"].lower() != (lead or "").lower()
            and p.get("role") != "Project lead"
        ][:20]
    if doc_responsible and NON_PERSON_NAME_RE.search(doc_responsible):
        doc_responsible = ""
    if doc_responsible and "(" not in doc_responsible and collaborators:
        responsible_display = _responsible_display(lead, collaborators)
    else:
        responsible_display = doc_responsible or _responsible_display(lead, collaborators)
    if not responsible_display and personnel:
        responsible_display = _responsible_display(lead, collaborators) or personnel[0]["name"]

    pi = (catalog.get("principal_investigator") or "").strip() or LAB_PI
    project_lead = lead or (personnel[0]["name"] if personnel else "")
    if project_lead.upper() == "TBD":
        project_lead = ""

    project_summary, research_question = _resolve_project_summary(catalog, priority_text, combined_text)

    identity = {
        "project_code": project_code,
        "project_name": catalog.get("project_name", project_code),
        "project_index": catalog.get("project_index"),
        "project_lead": project_lead,
        "principal_investigator": pi,
        "disease_focus": catalog.get("disease_focus", ""),
        "status": catalog.get("status", "active"),
        "category": catalog.get("category", ""),
        "category_label": catalog.get("category_label", ""),
        "priority": catalog.get("priority", "medium"),
        "research_question": research_question,
        "project_summary": project_summary,
        "timeline": (catalog.get("timeline") or "").strip() or (timeline_range.group(0) if timeline_range else ""),
        "responsible": responsible_display,
    }

    total_samples = sum(c["sample_count"] for c in cohorts if c.get("sample_count"))
    derived = de._parse_methods_and_findings(priority_text or combined_text)
    document_index_json = [
        r.as_json(include_text=False, include_chunks=False)
        for r in document_records[: de.DEFAULT_MAX_DOCS_IN_JSON]
    ]
    vector_chunks_json = vector_chunks[: de.DEFAULT_MAX_CHUNKS_IN_JSON]

    return {
        "project_code": project_code,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "folder_path": wrapper.name if wrapper else None,
        "content_root": _content_root_relative(folder),
        "source_files_count": len(file_inventory),
        "total_assets_count": len(all_assets),
        "content_library": content_library,
        "identity": identity,
        "personnel": personnel,
        "modalities": modalities,
        "cohorts": cohorts,
        "data_assets": data_assets,
        "timeline": unique_timeline[:100],
        "meetings": meetings[:40],
        "protocols": protocols[:20],
        "dissemination": dissemination[:30],
        "publications": publications,
        "derived_knowledge": derived,
        "document_index": document_index_json,
        "vector_chunks": vector_chunks_json,
        "extraction": extraction_summary,
        "metrics": {
            "document_count": len(file_inventory),
            "total_assets": len(all_assets),
            "figure_count": content_library.get("figure_count", 0),
            "timeline_entries": len(unique_timeline),
            "meeting_count": len(meetings),
            "protocol_count": len(protocols),
            "cohort_count": len(cohorts),
            "estimated_sample_count": total_samples or None,
            "repository_count": len(data_assets["repositories"]),
            "storage_path_count": len(data_assets["storage_paths"]),
            "presentation_count": content_library.get("totals", {}).get("presentation", 0),
            "data_file_count": content_library.get("totals", {}).get("data", 0),
            "extracted_document_count": extraction_summary.get("status_counts", {}).get("extracted", 0),
            "knowledge_chunk_count": len(vector_chunks),
            "extraction_error_count": len(extraction_summary.get("errors", [])),
        },
    }


def normalize_twin(data: dict[str, Any]) -> dict[str, Any]:
    """Merge duplicates and group related fields for presentation."""
    out = dict(data)
    identity = dict(out.get("identity") or {})

    rq = (identity.get("research_question") or "").strip()
    summary = (identity.get("project_summary") or "").strip()
    if rq and summary and rq.lower() == summary.lower():
        identity["research_question"] = ""
    elif rq and len(rq) < 20 and summary:
        identity["research_question"] = ""

    lead = (identity.get("project_lead") or "").strip()
    responsible = (identity.get("responsible") or "").strip()
    if responsible.lower() in ("personnel:", "personnel", ":", "tbd"):
        responsible = _responsible_display(lead, [])
    if responsible and lead and responsible.lower().startswith(lead.lower()[:4]) and "(" not in responsible:
        identity["responsible"] = _responsible_display(lead, [])
    elif responsible:
        identity["responsible"] = responsible
    else:
        identity["responsible"] = lead
    if identity.get("project_lead", "").upper() == "TBD":
        identity["project_lead"] = lead
    out["identity"] = identity

    seen_names: set[str] = set()
    personnel: list[dict[str, Any]] = []
    for p in out.get("personnel") or []:
        name = (p.get("name") or "").strip()
        if not _is_valid_person_name(name) or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        role = (p.get("role") or "").strip()
        focus = (p.get("focus") or "").strip()
        if not role or role.lower() in ("role / focus", "role", "focus") or _role_is_person_name(role):
            role = "Team member"
        if focus.lower() == role.lower() or focus.lower() in ("role / focus", "focus") or _is_valid_person_name(focus):
            focus = role
        personnel.append({"name": name, "role": role, "focus": focus})
    out["personnel"] = personnel

    seen_mod: set[str] = set()
    modalities: list[dict[str, Any]] = []
    for m in out.get("modalities") or []:
        name = (m.get("name") if isinstance(m, dict) else str(m)).strip()
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        if not name or key in seen_mod:
            continue
        seen_mod.add(key)
        if isinstance(m, dict):
            modalities.append(m)
        else:
            modalities.append({"name": name, "type": "assay", "description": ""})
    out["modalities"] = modalities

    seen_batches: dict[str, dict] = {}
    for c in out.get("cohorts") or []:
        batch_id = (c.get("batch_id") or "Primary").strip()
        key = re.sub(r"[^a-z0-9]", "", batch_id.lower())
        if key in seen_batches:
            existing = seen_batches[key]
            if c.get("sample_count") and not existing.get("sample_count"):
                existing["sample_count"] = c["sample_count"]
            ex = set(existing.get("exclusions") or [])
            ex.update(c.get("exclusions") or [])
            existing["exclusions"] = list(ex)
        else:
            seen_batches[key] = dict(c)
    out["cohorts"] = list(seen_batches.values())

    assets = dict(out.get("data_assets") or {})
    paths: list[str] = []
    seen_paths: set[str] = set()
    for p in assets.get("storage_paths") or []:
        p = p.strip().rstrip("/")
        if not p or URL_LIKE.search(p):
            continue
        key = p.lower()
        if key not in seen_paths:
            seen_paths.add(key)
            paths.append(p)
    repos: list[str] = []
    seen_repos: set[str] = set()
    for r in assets.get("repositories") or []:
        r = r.strip().rstrip("/")
        key = r.lower()
        if r and key not in seen_repos:
            seen_repos.add(key)
            repos.append(r)
    tree: dict[str, dict] = {}
    for f in assets.get("folder_tree") or []:
        path = f.get("path", ".")
        if path in tree:
            tree[path]["file_count"] = max(tree[path]["file_count"], f.get("file_count", 0))
            cats = set(tree[path].get("categories") or [])
            cats.update(f.get("categories") or [])
            tree[path]["categories"] = sorted(cats)
        else:
            tree[path] = dict(f)
    assets["storage_paths"] = paths
    assets["repositories"] = repos
    assets["folder_tree"] = sorted(tree.values(), key=lambda x: x.get("path", ""))
    out["data_assets"] = assets

    outputs: list[dict] = []
    seen_outputs: set[str] = set()
    for item in (out.get("dissemination") or []) + (out.get("publications") or []):
        key = (item.get("source_file") or item.get("doi") or item.get("title") or "").lower()
        if not key or key in seen_outputs:
            continue
        seen_outputs.add(key)
        outputs.append({
            "title": item.get("title") or "Untitled",
            "author": item.get("author") or "",
            "conference": item.get("conference") or item.get("source") or "",
            "year": item.get("year"),
            "doi": item.get("doi"),
            "type": item.get("type") or ("publication" if item.get("doi") else "abstract"),
            "source_file": item.get("source_file") or "",
        })
    out["outputs"] = outputs
    out["dissemination"] = [o for o in outputs if o["type"] == "abstract"]
    out["publications"] = [o for o in outputs if o["type"] == "publication" or o.get("doi")]

    seen_tl: set[tuple] = set()
    timeline: list[dict] = []
    for e in out.get("timeline") or []:
        title = (e.get("title") or "").strip()
        date = (e.get("date") or "").strip()
        summary = (e.get("summary") or "").strip()
        if date.lower() == "undated" and len(summary) > 500:
            continue
        key = (date, title)
        if key in seen_tl:
            continue
        seen_tl.add(key)
        timeline.append(e)
    out["timeline"] = timeline

    seen_meetings: set[tuple] = set()
    meetings: list[dict] = []
    for m in out.get("meetings") or []:
        key = (m.get("date"), m.get("title"))
        if key in seen_meetings or key in seen_tl:
            continue
        seen_meetings.add(key)
        meetings.append(m)
    out["meetings"] = meetings[:20]

    cohorts = out.get("cohorts") or []
    total_samples = sum(c["sample_count"] for c in cohorts if c.get("sample_count"))
    metrics = dict(out.get("metrics") or {})
    metrics.update({
        "timeline_entries": len(timeline),
        "meeting_count": len([e for e in timeline if e.get("category") == "meeting"]),
        "cohort_count": len(cohorts),
        "estimated_sample_count": total_samples or metrics.get("estimated_sample_count"),
        "repository_count": len(repos),
        "storage_path_count": len(paths),
        "output_count": len(outputs),
        "total_assets": out.get("total_assets_count") or metrics.get("total_assets"),
        "figure_count": (out.get("content_library") or {}).get("figure_count") or metrics.get("figure_count"),
    })
    out["metrics"] = metrics
    return out


def sync_public_processed(project_code: str | None = None) -> int:
    """Copy processed JSON twins to React public/processed for offline fallback."""
    from app_skeleton.api.data_layout import iter_lab_processed_files

    PUBLIC_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    if project_code:
        sources = [PROCESSED_DIR / f"{project_code}.json"]
    else:
        sources = list(iter_lab_processed_files()) + [
            p for p in sorted(PROCESSED_DIR.glob("*.json"))
            if not p.name.startswith("lab__")
        ]
    for src in sources:
        if not src.exists():
            continue
        dest = PUBLIC_PROCESSED_DIR / src.name
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        count += 1
    return count


_PROJECT_LOG_RE = re.compile(r"project[_\s-]?log", re.I)


def _find_project_log_rel_path(project_code: str, twin: dict[str, Any] | None = None) -> str | None:
    twin = twin or load_processed(project_code)
    candidates: list[tuple[int, str]] = []

    def score(path: str) -> int:
        ext = Path(path).suffix.lower()
        if ext == ".md":
            return 0
        if ext == ".txt":
            return 1
        if ext in {".html", ".rtf"}:
            return 2
        return 3

    def consider(path: str | None) -> None:
        if not path:
            return
        norm = str(path).replace("\\", "/").lstrip("./")
        base = norm.split("/")[-1]
        if _PROJECT_LOG_RE.search(base):
            candidates.append((score(norm), norm))

    if twin:
        for entry in twin.get("document_index") or []:
            consider(entry.get("path") or entry.get("relative_path"))
        for row in (twin.get("data_assets") or {}).get("folder_tree") or []:
            consider(row.get("path") or row.get("relative_path") or row.get("name"))
        for section in (twin.get("content_library") or {}).get("sections") or []:
            for key in ("documents", "text_files", "data_files"):
                for item in section.get(key) or []:
                    consider(item.get("path"))

    root = get_content_root(project_code)
    if root and root.is_dir():
        for hit in root.rglob("*"):
            if not hit.is_file():
                continue
            if _PROJECT_LOG_RE.search(hit.name):
                try:
                    consider(str(hit.relative_to(root)).replace("\\", "/"))
                except ValueError:
                    continue

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], len(item[1])))
    return candidates[0][1]


def sync_readme_log_to_file(project_code: str, readme_text: str, *, twin: dict[str, Any] | None = None) -> str | None:
    """Move README log sections into the project log file; returns relative log path if written."""
    log_body = _extract_readme_log(readme_text)
    if not log_body:
        return None
    twin = twin or load_processed(project_code)
    rel = _find_project_log_rel_path(project_code, twin)
    root = get_content_root(project_code)
    if not root or not root.is_dir():
        return None
    if not rel:
        rel = "Project_log.md"
    try:
        abs_path = safe_relative_path(root, rel)
    except ValueError:
        return None
    if abs_path.suffix.lower() not in TEXT_EXTENSIONS:
        rel = "Project_log.md"
        abs_path = safe_relative_path(root, rel)
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"# Project Log\n\n{log_body.rstrip()}\n"
    abs_path.write_text(content, encoding="utf-8")
    return rel


def sync_readme_identity_from_text(project_code: str, readme_text: str) -> dict[str, Any]:
    """Refresh cover-board identity and team roster from README without a full reprocess."""
    twin = load_processed(project_code)
    if not twin:
        twin = normalize_twin(process_project(project_code))
    sync_readme_log_to_file(project_code, readme_text, twin=twin)
    catalog = _load_catalog().get(project_code, {})
    summary, research_question = _resolve_project_summary(catalog, readme_text, "")
    parsed_personnel = _parse_personnel(readme_text)
    doc_lead, doc_collabs, _doc_responsible = _extract_responsible_from_text(readme_text)
    lead = doc_lead or (
        (parsed_personnel[0]["name"] if parsed_personnel and parsed_personnel[0].get("role") == "Project lead" else "")
    )
    catalog_lead, catalog_collabs, catalog_personnel = _personnel_from_catalog(catalog)
    if not lead:
        lead = catalog_lead
    collaborators = list(dict.fromkeys(
        [c for c in catalog_collabs + doc_collabs if _is_valid_person_name(c)]
    ))
    personnel = _merge_personnel(catalog_personnel, parsed_personnel)
    if lead:
        personnel = _merge_personnel(
            [{"name": lead, "role": "Project lead", "focus": "Project lead"}],
            personnel,
        )
    for c in collaborators:
        personnel = _merge_personnel(
            [{"name": c, "role": "Collaborator", "focus": "Collaborator"}],
            personnel,
        )

    identity = dict(twin.get("identity") or {})
    identity["project_summary"] = summary
    identity["research_question"] = research_question
    if lead:
        identity["project_lead"] = lead
    identity["responsible"] = _responsible_display(lead, collaborators) or lead or identity.get("responsible", "")

    twin["identity"] = identity
    twin["personnel"] = personnel
    twin["readme_synced_at"] = datetime.now(timezone.utc).isoformat()
    normalized = normalize_twin(twin)
    save_processed(project_code, normalized)
    return normalized


def save_processed(project_code: str, data: dict | None = None) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    payload = normalize_twin(data or process_project(project_code))
    out = PROCESSED_DIR / f"{project_code}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    chunks = payload.get("vector_chunks") or []
    chunks_out = PROCESSED_DIR / f"{project_code}.chunks.jsonl"
    with chunks_out.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    sync_public_processed(project_code)
    return out


def load_processed(project_code: str) -> dict | None:
    path = PROCESSED_DIR / f"{project_code}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    public_path = PUBLIC_PROCESSED_DIR / f"{project_code}.json"
    if public_path.exists():
        return json.loads(public_path.read_text(encoding="utf-8"))
    return None


def get_digital_twin(project_code: str, refresh: bool = False) -> dict[str, Any]:
    cached = load_processed(project_code)
    if not refresh:
        if cached:
            return normalize_twin(cached)
    data = normalize_twin(process_project(project_code))
    if cached and refresh:
        old_assets = int(cached.get("total_assets_count") or cached.get("metrics", {}).get("total_assets") or 0)
        new_assets = int(data.get("total_assets_count") or data.get("metrics", {}).get("total_assets") or 0)
        if old_assets > 0 and new_assets < old_assets:
            return normalize_twin(cached)
    save_processed(project_code, data)
    return data


README_DEFAULT_CONTENT = "Welcome to the project, start your readme file here."


def _readme_template(catalog: dict[str, Any]) -> str:
    name = compact_text(
        catalog.get("project_name") or catalog.get("project_code") or "Project",
        "Project",
    )
    lead = compact_text(catalog.get("project_lead"), "—")
    pi = compact_text(catalog.get("principal_investigator"), "—")
    summary = compact_text(catalog.get("project_summary") or catalog.get("research_question"), "")
    status = compact_text(catalog.get("status"), "active")
    disease = compact_text(catalog.get("disease_focus"), "")
    lines = [
        f"# {name}",
        "",
        "## Summary",
        summary or "Describe the project goals, cohort, and current scope.",
        "",
        "## People",
        f"- **Lead:** {lead}",
        f"- **PI:** {pi}",
    ]
    if disease:
        lines.extend(["", "## Disease focus", disease])
    lines.extend(
        [
            "",
            "## Data & storage",
            "Document where raw data, analysis outputs, and key folders live.",
            "",
            "## Status",
            f"{status.title()} — note milestones, blockers, and next steps here.",
            "",
            "---",
            "*Edit this README to keep the lab informed about this project.*",
        ]
    )
    return "\n".join(lines) + "\n"


def compact_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _readme_exists_on_disk(root: Path) -> str | None:
    for name in ("README.md", "readme.md", "README.txt", "readme.txt"):
        if (root / name).is_file():
            return name
    return None


def _twin_has_readme(twin: dict[str, Any] | None) -> bool:
    paths: list[str] = []
    for entry in (twin or {}).get("document_index") or []:
        path = (entry.get("path") or entry.get("relative_path") or "").strip()
        if path:
            paths.append(path)
    for section in (twin or {}).get("content_library", {}).get("sections") or []:
        for key in ("documents", "text_files", "presentations", "data_files"):
            for item in section.get(key) or []:
                path = (item.get("path") or "").strip()
                if path:
                    paths.append(path)
    for path in paths:
        base = path.split("/")[-1].lower()
        if base.startswith("readme."):
            return True
    return False


def ensure_project_readme(project_code: str) -> dict[str, Any]:
    """Create README.md at the project content root when no readme is indexed."""
    catalog = _load_catalog().get(project_code, {})
    root = get_content_root(project_code)
    if not root or not root.is_dir():
        raise FileNotFoundError("Project folder not found on disk.")

    twin = load_processed(project_code)
    existing = _readme_exists_on_disk(root)
    if existing:
        if not _twin_has_readme(twin):
            refreshed = get_digital_twin(project_code, refresh=True)
            return {
                "created": False,
                "project_code": project_code,
                "relative_path": existing,
                "reason": "rescanned",
                "twin": refreshed,
            }
        return {
            "created": False,
            "project_code": project_code,
            "relative_path": existing,
            "reason": "exists_on_disk",
        }

    if _twin_has_readme(twin):
        return {
            "created": False,
            "project_code": project_code,
            "reason": "exists_in_index",
        }

    rel = "README.md"
    content = _readme_template(catalog)
    abs_path = root / rel
    abs_path.write_text(content, encoding="utf-8")
    refreshed = get_digital_twin(project_code, refresh=True)
    return {
        "created": True,
        "project_code": project_code,
        "relative_path": rel,
        "content": content,
        "twin": refreshed,
    }


def update_digital_twin(project_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("project_code") and payload["project_code"] != project_code:
        raise ValueError("project_code mismatch")
    payload = dict(payload)
    payload["project_code"] = project_code
    payload["edited_at"] = datetime.now(timezone.utc).isoformat()
    payload["user_edited"] = True
    normalized = normalize_twin(payload)
    save_processed(project_code, normalized)
    return normalized


PROJECT_EXTRACTABLE_EXTENSIONS = {
    ".pdf", ".docx", ".dotx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".odt", ".csv", ".tsv", ".rtf",
}
PROJECT_ASSET_PREVIEW_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".tif", ".tiff",
}


def _normalize_project_rel_path(relative_path: str) -> str:
    return relative_path.strip().lstrip("/").replace("\\", "/")


def _chunks_text_from_twin(twin: dict[str, Any], norm_path: str) -> str | None:
    parts: list[tuple[int, str]] = []
    for chunk in twin.get("vector_chunks") or []:
        src = (chunk.get("source_file") or "").replace("\\", "/")
        if src == norm_path:
            parts.append((chunk.get("chunk_index") or 0, chunk.get("text") or ""))
    if not parts:
        return None
    parts.sort(key=lambda x: x[0])
    text = "\n\n".join(t for _, t in parts if t).strip()
    return text or None


def _chunks_text_from_jsonl(project_code: str, norm_path: str) -> str | None:
    chunks_path = PROCESSED_DIR / f"{project_code}.chunks.jsonl"
    if not chunks_path.is_file():
        return None
    parts: list[tuple[int, str]] = []
    with chunks_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            src = (chunk.get("source_file") or "").replace("\\", "/")
            if src == norm_path:
                parts.append((chunk.get("chunk_index") or 0, chunk.get("text") or ""))
    if not parts:
        return None
    parts.sort(key=lambda x: x[0])
    text = "\n\n".join(t for _, t in parts if t).strip()
    return text or None


def _document_index_entry(twin: dict[str, Any], norm_path: str) -> dict[str, Any] | None:
    for doc in twin.get("document_index") or []:
        if (doc.get("path") or "").replace("\\", "/") == norm_path:
            return doc
    return None


def get_project_file_preview_text(
    project_code: str,
    relative_path: str,
    *,
    max_chars: int = 2_000_000,
    live_extract: bool = True,
) -> dict[str, Any]:
    """Resolved preview text: processed chunks → document index → live extraction."""
    norm = _normalize_project_rel_path(relative_path)
    twin = load_processed(project_code) or {}

    chunk_text = _chunks_text_from_twin(twin, norm) or _chunks_text_from_jsonl(project_code, norm)
    if chunk_text:
        if len(chunk_text) > max_chars:
            chunk_text = chunk_text[:max_chars] + "\n… [truncated]"
        return {
            "content": chunk_text,
            "path": norm,
            "source": "processed_chunks",
            "project_code": project_code,
        }

    doc = _document_index_entry(twin, norm)
    if doc:
        excerpt = (doc.get("excerpt") or "").strip()
        title = (doc.get("title") or "").strip()
        body = excerpt
        if title and title not in excerpt[:200]:
            body = f"{title}\n\n{excerpt}" if excerpt else title
        if body:
            if len(body) > max_chars:
                body = body[:max_chars] + "\n… [truncated]"
            return {
                "content": body,
                "path": norm,
                "source": "document_index",
                "extractor": doc.get("extractor"),
                "status": doc.get("status"),
                "project_code": project_code,
            }

    root = get_content_root(project_code)
    if not root:
        raise FileNotFoundError(f"Project folder not found for {project_code}")
    try:
        abs_path = safe_relative_path(root, norm)
    except ValueError as exc:
        raise FileNotFoundError(f"Invalid path: {norm}") from exc
    if not abs_path.is_file():
        raise FileNotFoundError(f"File not found: {norm}")

    ext = abs_path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + "\n… [truncated]"
        return {"content": content, "path": norm, "source": "disk_text", "project_code": project_code}

    if live_extract and ext in PROJECT_EXTRACTABLE_EXTENSIONS:
        result = de._extract_file(abs_path, root)
        text = (result.text or "").strip() or (result.excerpt or "").strip()
        if not text:
            raise ValueError("No text could be extracted from this file.")
        if len(text) > max_chars:
            text = text[:max_chars] + "\n… [truncated]"
        return {
            "content": text,
            "path": norm,
            "source": "live_extract",
            "extractor": result.extractor,
            "status": result.status,
            "warnings": (result.warnings or [])[:8],
            "project_code": project_code,
        }

    raise ValueError(f"Preview not available for file type {ext or 'unknown'}")


def export_document_text(project_code: str, *, refresh: bool = False) -> Path:
    """Export extracted text chunks as Markdown for human review."""
    twin = get_digital_twin(project_code, refresh=refresh)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / f"{project_code}.extracted_text.md"
    lines = [f"# Extracted text for {project_code}", ""]
    for chunk in twin.get("vector_chunks") or []:
        lines.append(f"## {chunk.get('source_file')} — chunk {chunk.get('chunk_index')}")
        lines.append(chunk.get("text", ""))
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_vector_manifest(project_code: str, *, refresh: bool = False) -> dict[str, Any]:
    """Return a manifest for vector-ingestion workers."""
    twin = get_digital_twin(project_code, refresh=refresh)
    identity = twin.get("identity") or {}
    return {
        "project_code": project_code,
        "project_name": identity.get("project_name"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(twin.get("vector_chunks") or []),
        "metadata_fields": [
            "project_code", "project_name", "source_file", "chunk_index", "document_kind",
            "modality", "lifecycle_section", "sha256", "modified_at",
        ],
        "chunks_jsonl": str((PROCESSED_DIR / f"{project_code}.chunks.jsonl").resolve()),
    }


def _load_all_catalog_entries() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []
    try:
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Build extraction-rich project digital twins.")
    parser.add_argument("project_code", nargs="?", help="Project code, e.g. SPACE or 12-SPACE")
    parser.add_argument("--all", action="store_true", help="Process every project in projects_catalog.json")
    parser.add_argument("--refresh", action="store_true", help="Force refresh instead of cache")
    parser.add_argument("--export-text", action="store_true", help="Export extracted chunks to Markdown")
    parser.add_argument("--manifest", action="store_true", help="Print vector-ingestion manifest")
    args = parser.parse_args()

    if args.all:
        entries = _load_all_catalog_entries()
        if not entries:
            raise SystemExit(f"No catalog entries found at {CATALOG_PATH}")
        for entry in entries:
            code = entry.get("project_code") or entry.get("code") or entry.get("project_name")
            if not code:
                continue
            twin = get_digital_twin(str(code), refresh=args.refresh)
            out = save_processed(str(code), twin)
            print(f"wrote {out}")
            if args.export_text:
                print(f"wrote {export_document_text(str(code), refresh=False)}")
        return 0

    if not args.project_code:
        parser.error("provide project_code or --all")
    twin = get_digital_twin(args.project_code, refresh=args.refresh)
    out = save_processed(args.project_code, twin)
    print(f"wrote {out}")
    print(json.dumps({
        "project_code": args.project_code,
        "metrics": twin.get("metrics"),
        "extraction": (twin.get("extraction") or {}).get("status_counts"),
        "chunks_jsonl": str((PROCESSED_DIR / f"{args.project_code}.chunks.jsonl").resolve()),
    }, indent=2, ensure_ascii=False))
    if args.export_text:
        print(f"wrote {export_document_text(args.project_code, refresh=False)}")
    if args.manifest:
        print(json.dumps(build_vector_manifest(args.project_code, refresh=False), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
