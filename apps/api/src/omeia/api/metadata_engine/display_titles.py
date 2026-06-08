"""Display title generation — never replaces original filenames on disk."""
from __future__ import annotations

import re
from typing import Any

_DATE_RE = re.compile(r"\b(20\d{2})(\d{2})(\d{2})\b")
_YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
_SEP_RE = re.compile(r"[_\-.]+")
_CAMEL_RE = re.compile(r"([a-z])([A-Z])")
_MULTI_SPACE = re.compile(r"\s+")
_COPY_OF_RE = re.compile(r"^copy\s+of\s+", re.I)
_REVISION_PREFIX_RE = re.compile(
    r"^(?:UPD|UPDATE|REV(?:ISED)?|DRAFT)\s+[\d./-]+(?:\s+[A-Z]{1,3})?\s+",
    re.I,
)
_MARKDOWN_NOISE_RE = re.compile(r"\{[^}]*\}")
_TITLE_STOPWORDS = frozenset(
    {"a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with", "at", "by", "from", "as"}
)
_PRESERVE_ACRONYMS = frozenset(
    {
        "SOP", "BSL", "RNA", "DNA", "IHC", "IF", "QC", "PI", "GSK", "UPS", "PDF", "CSV", "XLSX",
        "HTML", "API", "IT", "LUMI", "CSC", "EMEA", "USDA", "BSL-2", "GEO", "DSP", "OME", "XML",
        "SCRNA", "TCYCIF", "CYCIF", "XENIUM",
    }
)
_KNOWN_TYPOS = (
    (re.compile(r"\bBIlling\b", re.I), "Billing"),
    (re.compile(r"\bIlmoitis\b", re.I), "Ilmoitus"),
    (re.compile(r"\bluovotuspyyntö\b", re.I), "luovutuspyyntö"),
    (re.compile(r"\briskiarviounti\b", re.I), "riskiarviointi"),
    (re.compile(r"\bTayttoohje\b", re.I), "Täyttöohje"),
    (re.compile(r"\bRiskinarviointipohja\b", re.I), "Riskinarviointipohja"),
    (re.compile(r"\bCellcycle\b", re.I), "Cell Cycle"),
    (re.compile(r"\bCellcycleproject\b", re.I), "Cell Cycle Project"),
    (re.compile(r"\bfarkkila\b", re.I), "Färkkilä"),
    (re.compile(r"\bfärkkilä\b", re.I), "Färkkilä"),
)
_LEADING_DATE_RE = re.compile(
    r"^\s*(?:\d{1,2}[._]\d{1,2}[._]\d{4}|\d{4}-\d{2}-\d{2})\s*",
)
_TRAILING_DATE_TITLE_RE = re.compile(
    r"\s*(?:—|–|-)\s*(?:\d{4}-\d{2}-\d{2}|\d{1,2}[._]\d{1,2}[._]\d{4})\s*$",
)
_DOTTED_DATE_RE = re.compile(r"(?:^|[\s_])(\d{1,2})[._](\d{1,2})[._](\d{4})(?=[\s_.-]|$)")
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_PROJECT_PREFIX_RE = re.compile(r"^(\d+)[_\s-]+([A-Za-z][A-Za-z0-9]*)")


def _strip_markdown_noise(text: str) -> str:
    s = _MARKDOWN_NOISE_RE.sub("", text or "")
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return s.strip()


def _smart_title_case(text: str) -> str:
    words = text.split()
    out: list[str] = []
    for i, word in enumerate(words):
        core = re.sub(r"^[^A-Za-zÀ-ÿ0-9]+|[^A-Za-zÀ-ÿ0-9]+$", "", word)
        upper = core.upper()
        if upper in _PRESERVE_ACRONYMS:
            out.append(word.replace(core, upper))
        elif len(core) <= 6 and core.isupper() and any(c.isalpha() for c in core):
            out.append(word)
        elif i > 0 and core.lower() in _TITLE_STOPWORDS:
            out.append(word.replace(core, core.lower()))
        else:
            cased = core[:1].upper() + core[1:].lower() if core else core
            out.append(word.replace(core, cased) if core else word)
    return " ".join(out)


def _looks_mostly_uppercase(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 4:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters) >= 0.82


def _polish_display_title(title: str, *, heading: bool = False) -> str:
    s = _strip_markdown_noise(title)
    if not s:
        return title.strip() if title else ""
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    s = _COPY_OF_RE.sub("", s)
    if heading:
        s = _REVISION_PREFIX_RE.sub("", s)
    for pattern, repl in _KNOWN_TYPOS:
        s = pattern.sub(repl, s)
    s = re.sub(r"\s*_{2,}\s*", " ", s)
    s = re.sub(r"\s*[-–—]\s*[-–—]+\s*", " — ", s)
    s = re.sub(r"\s*_\s*", " ", s)
    s = re.sub(r"\s*&\s*", " & ", s)
    s = re.sub(r"\s*/\s*", " / ", s)
    s = _CAMEL_RE.sub(r"\1 \2", s)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"([,.;:!?])([^\s\d)])", r"\1 \2", s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    if _looks_mostly_uppercase(s) or (heading and re.search(r"\b[A-Z]{2,}\b", s)):
        s = _smart_title_case(s)
    elif " — " not in s and ("_" in title or "-" in title or s.isupper()):
        s = _smart_title_case(s)
    for pattern, repl in _KNOWN_TYPOS:
        s = pattern.sub(repl, s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    return s or title.strip()


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


def _normalize_date_token(token: str) -> str:
    m = _DOTTED_DATE_RE.search(token)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = _ISO_DATE_RE.search(token)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _DATE_RE.search(token)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return token


def _extract_date_label(filename: str) -> str | None:
    m = _DOTTED_DATE_RE.search(filename)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = _ISO_DATE_RE.search(filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _DATE_RE.search(filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _YEAR_RE.search(filename)
    if m:
        return m.group(1)
    return None


def _strip_leading_date(stem: str) -> tuple[str, str | None]:
    s = stem.strip()
    m = _LEADING_DATE_RE.match(s)
    if not m:
        return s, None
    date_label = _normalize_date_token(m.group(0).strip())
    remainder = s[m.end() :].lstrip(" _-.")
    return remainder or s, date_label


def _strip_trailing_date(title: str) -> str:
    return _TRAILING_DATE_TITLE_RE.sub("", title).strip()


def _parse_project_prefix(stem: str) -> tuple[str | None, str]:
    m = _PROJECT_PREFIX_RE.match(stem.strip())
    if not m:
        return None, stem
    prefix = f"{m.group(1)}-{m.group(2)}"
    remainder = stem[m.end() :].lstrip(" _-.")
    return prefix, remainder or stem


def _topic_from_stem(stem: str) -> tuple[str, str | None]:
    """Return humanized topic and optional project prefix (e.g. 4-Cellcycleproject)."""
    cleaned, _ = _strip_leading_date(stem.strip())
    prefix, remainder = _parse_project_prefix(cleaned)
    topic = _humanize_stem(remainder.rstrip(" _-."))
    return topic, prefix


def _professional_role_label(document_role: str) -> str:
    mapping = {
        "order_record": "Order / Procurement Record",
        "order_form": "Order / Procurement Record",
        "protocol": "Protocol",
        "SOP": "SOP",
        "instruction": "Instruction / Handbook",
        "presentation": "Presentation",
        "manuscript": "Manuscript",
        "project_plan": "Project Plan",
        "project_log": "Project Log",
        "spreadsheet": "Spreadsheet",
        "figure": "Figure",
        "analysis_notebook": "Notebook",
        "lab_notebook": "Lab Notebook",
        "inventory": "Inventory / Registry",
        "administrative_document": "Administrative",
        "personnel_document": "Personnel",
        "social_event_document": "Social Event",
        "system_artifact": "System File",
        "unknown": "Document",
    }
    return mapping.get(document_role, _humanize_stem(document_role.replace("_", " ")))


def _infer_document_role_short(role: str) -> str:
    return _professional_role_label(role)


def _role_topic_title(topic: str, project_prefix: str | None, document_role: str) -> str:
    role_label = _professional_role_label(document_role)
    if project_prefix:
        return f"{project_prefix} {topic} — {role_label}"
    return f"{topic} — {role_label}"


def _project_display_name(project_id: str) -> str:
    name = project_id.replace("_", " ").strip()
    # 4_CellCycle -> CellCycle
    m = re.match(r"^\d+[_\s-]*(.+)$", name)
    if m:
        return _humanize_stem(m.group(1))
    return _humanize_stem(name)


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
    stem = (filename.rsplit(".", 1)[0] if "." in filename else filename).strip()
    date_label = _extract_date_label(filename.strip())
    role_short = _infer_document_role_short(document_role)
    professional_role_label = _professional_role_label(document_role)

    topic, project_prefix = _topic_from_stem(stem)
    human_stem = _humanize_stem(_strip_leading_date(stem)[0])

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
        topic_part = topic
        # Remove redundant project prefix from stem
        for prefix in (project_id, proj.replace(" ", ""), proj.replace(" ", "_")):
            if topic_part.lower().startswith(prefix.lower()):
                topic_part = topic_part[len(prefix) :].strip(" -_")
                topic_part = _humanize_stem(topic_part) if topic_part else topic

        parts = [proj, cat, topic_part]
        if role_short and role_short.lower() not in topic_part.lower():
            parts.append(role_short)
        display_title = " — ".join(p for p in parts if p)
        subtitle = f"Original: {filename}"
        search_aliases.extend([proj, cat, project_id])

        # Good name check
        if human_stem.lower() == stem.lower() and len(stem) > 8 and " " not in stem:
            rename_needed = False
            rename_reason = "Existing name is clear enough after display formatting"
        else:
            suggested = f"{proj}_{cat.replace(' & ', '_')}_{topic_part.replace(' ', '_')}"
            if date_label:
                suggested += f"_{date_label.replace('-', '')}"
            suggested += filename[filename.rfind(".") :] if "." in filename else ""
            rename_needed = suggested.lower() != filename.lower()
            rename_confidence = 0.55 if rename_needed else 0.0
            rename_reason = "Suggested cleaner project filename for later review" if rename_needed else "Existing name is clear enough"

    elif "order" in logical_path.lower() or "billing" in logical_path.lower():
        display_title = _role_topic_title(topic, project_prefix, document_role)
        subtitle = filename

    elif (logical_path or "").lower().startswith("wet_lab") or "protocol" in logical_path.lower():
        assay = ""
        lower = logical_path.lower()
        for kw in ("cycif", "tcycif", "xenium", "geomx", "scrna", "ihc", "if "):
            if kw in lower or kw in filename.lower():
                assay = kw.upper().replace(" ", "")
                break
        if document_role in ("protocol", "SOP", "instruction", "order_form", "order_record"):
            display_title = _role_topic_title(topic, project_prefix, document_role)
            if assay and assay.lower() not in display_title.lower():
                display_title = f"{assay} {display_title}"
        else:
            parts = [p for p in (assay, topic) if p]
            display_title = " — ".join(parts) if parts else topic
        subtitle = filename if display_title.lower() != human_stem.lower() else None

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

    display_title = _strip_trailing_date(display_title)
    display_title = _polish_display_title(display_title)
    short_title = display_title if len(display_title) <= 48 else f"{display_title[:45]}…"
    professional_title = display_title

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

    return {
        "display_title": display_title,
        "short_title": short_title,
        "subtitle": subtitle,
        "professional_title": professional_title,
        "date_label": date_label,
        "professional_role_label": professional_role_label,
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
