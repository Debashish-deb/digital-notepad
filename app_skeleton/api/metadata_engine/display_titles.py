"""Display title generation — never replaces original filenames on disk."""
from __future__ import annotations

import re
from typing import Any

_DATE_RE = re.compile(r"\b(20\d{2})(\d{2})(\d{2})\b")
_YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
_SEP_RE = re.compile(r"[_\-.]+")
_CAMEL_RE = re.compile(r"([a-z])([A-Z])")
_MULTI_SPACE = re.compile(r"\s+")


def _humanize_stem(stem: str) -> str:
    s = stem.strip()
    s = _SEP_RE.sub(" ", s)
    s = _CAMEL_RE.sub(r"\1 \2", s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    if not s:
        return stem
    # Title case but keep acronyms
    words = []
    for w in s.split():
        if w.isupper() and len(w) <= 6:
            words.append(w)
        elif w.lower() in ("and", "or", "of", "the", "a", "an", "for", "to", "in", "on", "with"):
            words.append(w.lower() if words else w.capitalize())
        else:
            words.append(w.capitalize())
    return " ".join(words)


def _extract_date_label(filename: str) -> str | None:
    m = _DATE_RE.search(filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _YEAR_RE.search(filename)
    if m:
        return m.group(1)
    return None


def _project_display_name(project_id: str) -> str:
    name = project_id.replace("_", " ").strip()
    # 4_CellCycle -> CellCycle
    m = re.match(r"^\d+[_\s-]*(.+)$", name)
    if m:
        return _humanize_stem(m.group(1))
    return _humanize_stem(name)


def _infer_document_role_short(role: str) -> str:
    mapping = {
        "presentation": "Presentation",
        "manuscript": "Manuscript",
        "project_plan": "Project Plan",
        "project_log": "Project Log",
        "protocol": "Protocol",
        "SOP": "SOP",
        "instruction": "Instruction",
        "spreadsheet": "Spreadsheet",
        "figure": "Figure",
        "analysis_notebook": "Notebook",
        "lab_notebook": "Lab Notebook",
        "inventory": "Inventory",
        "order_form": "Order Form",
        "administrative_document": "Administrative",
        "personnel_document": "Personnel",
        "social_event_document": "Social Event",
        "system_artifact": "System File",
        "unknown": "Document",
    }
    return mapping.get(role, _humanize_stem(role.replace("_", " ")))


def build_display_titles(
    *,
    filename: str,
    logical_path: str,
    is_project_file: bool,
    project_id: str | None,
    project_category: str | None,
    document_role: str,
    processed_title: str | None = None,
    metadata_excerpt: str | None = None,
) -> dict[str, Any]:
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    human_stem = _humanize_stem(stem)
    date_label = _extract_date_label(filename)
    role_short = _infer_document_role_short(document_role)

    display_title = human_stem
    subtitle = None
    rename_needed = False
    rename_confidence = 0.0
    rename_reason = ""
    search_aliases = [filename, stem, human_stem]

    if processed_title and len(processed_title.strip()) > 3:
        search_aliases.append(processed_title.strip())

    if is_project_file and project_id:
        proj = _project_display_name(project_id)
        cat = project_category or "Files"
        topic = human_stem
        # Remove redundant project prefix from stem
        for prefix in (project_id, proj.replace(" ", ""), proj.replace(" ", "_")):
            if topic.lower().startswith(prefix.lower()):
                topic = topic[len(prefix) :].strip(" -_")
                topic = _humanize_stem(topic) if topic else human_stem

        parts = [proj, cat, topic]
        if role_short and role_short.lower() not in topic.lower():
            parts.append(role_short)
        if date_label:
            parts.append(date_label)
        display_title = " — ".join(p for p in parts if p)
        subtitle = f"Original: {filename}"
        search_aliases.extend([proj, cat, project_id])

        # Good name check
        if human_stem.lower() == stem.lower() and len(stem) > 8 and " " not in stem:
            rename_needed = False
            rename_reason = "Existing name is clear enough after display formatting"
        else:
            suggested = f"{proj}_{cat.replace(' & ', '_')}_{topic.replace(' ', '_')}"
            if date_label:
                suggested += f"_{date_label.replace('-', '')}"
            suggested += filename[filename.rfind(".") :] if "." in filename else ""
            rename_needed = suggested.lower() != filename.lower()
            rename_confidence = 0.55 if rename_needed else 0.0
            rename_reason = "Suggested cleaner project filename for later review" if rename_needed else "Existing name is clear enough"

    elif (logical_path or "").lower().startswith("wet_lab") or "protocol" in logical_path.lower():
        assay = ""
        lower = logical_path.lower()
        for kw in ("cycif", "tcycif", "xenium", "geomx", "scrna", "ihc", "if "):
            if kw in lower or kw in filename.lower():
                assay = kw.upper().replace(" ", "")
                break
        parts = [p for p in (assay, role_short, human_stem, date_label) if p]
        display_title = " — ".join(parts) if parts else human_stem
        subtitle = filename if display_title.lower() != human_stem.lower() else None

    elif "order" in logical_path.lower() or "billing" in logical_path.lower():
        display_title = f"{role_short} — {human_stem}" if role_short else human_stem
        subtitle = filename

    elif "overview" in logical_path.lower() or "onboarding" in filename.lower():
        display_title = human_stem
        if "onboarding" in filename.lower():
            display_title = "Färkkilä Lab Onboarding Guide" if "färkkilä" in filename.lower() or "farkkila" in filename.lower() else human_stem
        if "phone" in filename.lower() and "email" in filename.lower():
            display_title = "Important Phone Numbers, Links, and Emails"
        subtitle = filename

    else:
        display_title = processed_title.strip() if processed_title and len(processed_title) > 4 else human_stem
        subtitle = filename if display_title != human_stem else None

    # If display is nearly identical to original stem, mark rename not needed
    if not rename_reason:
        if _humanize_stem(stem).lower() == display_title.lower() or stem.lower() == display_title.lower():
            rename_needed = False
            rename_reason = "Existing name is clear enough"
            rename_confidence = 0.0
        elif abs(len(display_title) - len(stem)) < 4:
            rename_needed = False
            rename_reason = "Existing name is clear enough"
        else:
            rename_needed = True
            rename_confidence = 0.45
            rename_reason = "Display title improves clarity; physical rename deferred for review"

    short_title = display_title if len(display_title) <= 48 else f"{display_title[:45]}…"
    professional_title = display_title

    return {
        "display_title": display_title,
        "short_title": short_title,
        "subtitle": subtitle,
        "professional_title": professional_title,
        "original_name_visible": display_title.lower() != filename.lower(),
        "suggested_filename_for_later": (
            f"{_humanize_stem(stem).replace(' ', '_')}{filename[filename.rfind('.'):]}"
            if rename_needed and "." in filename
            else None
        ),
        "rename_needed": rename_needed,
        "rename_confidence": round(rename_confidence, 2),
        "rename_reason": rename_reason or "Existing name is clear enough",
        "legacy_aliases": [filename, stem],
        "search_aliases": list(dict.fromkeys(a for a in search_aliases if a)),
    }
