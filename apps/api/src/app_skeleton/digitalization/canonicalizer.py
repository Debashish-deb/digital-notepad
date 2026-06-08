"""Canonicalizer — convert ExtractedDocument into canonical JSON."""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from app_skeleton.digitalization.models import (
    CanonicalDocument,
    CanonicalSection,
    ExtractedDocument,
    SourceFileManifest,
)
from app_skeleton.digitalization.secret_detector import scan_for_secrets

LOGGER = logging.getLogger(__name__)

# ── Document type classification rules ────────────────────────
_DOC_TYPE_RULES: list[tuple[str, re.Pattern]] = [
    ("order", re.compile(r"order|tilaus|bestall|invoice|lasku|quotation|tarjous|offer", re.I)),
    ("protocol", re.compile(r"protocol|sop|standard.?operating|procedure", re.I)),
    ("guideline", re.compile(r"guideline|instruction|how.?to|ohje", re.I)),
    ("datasheet", re.compile(r"datasheet|data.?sheet|product.?info|msds|safety.?data", re.I)),
    ("meeting_notes", re.compile(r"meeting|agenda|minutes|kokous", re.I)),
    ("onboarding", re.compile(r"onboarding|outboarding|orientation|perehdytys", re.I)),
    ("cleaning_record", re.compile(r"cleaning|siivous|puhdistus", re.I)),
    ("form", re.compile(r"form|lomake|application|hakemus", re.I)),
    ("permit", re.compile(r"permit|license|lupa|valvira", re.I)),
    ("thesis", re.compile(r"thesis|dissertation|gradu|väitös", re.I)),
    ("presentation", re.compile(r"presentation|slide|poster|esitys", re.I)),
    ("report", re.compile(r"report|raportti|summary|yhteenveto", re.I)),
    ("spreadsheet_data", re.compile(r"\.xlsx?$|\.csv$|\.tsv$|spreadsheet", re.I)),
    ("script", re.compile(r"\.py$|\.r$|\.sh$|\.sql$|script", re.I)),
]

_DOMAIN_RULES: list[tuple[str, re.Pattern]] = [
    ("orders", re.compile(r"order|billing|invoice|offer|quote|tarjous|tilaus|procurement", re.I)),
    ("lab_management", re.compile(r"onboarding|outboarding|guideline|cleaning|personnel|lab.?coat", re.I)),
    ("research", re.compile(r"protocol|experiment|method|cycif|geomx|xenium|sequencing|staining", re.I)),
    ("meetings", re.compile(r"meeting|agenda|minutes", re.I)),
    ("permits_compliance", re.compile(r"permit|valvira|ethanol|safety|msds|gsk", re.I)),
    ("it_computational", re.compile(r"conda|python|lumi|docker|install|server|computational", re.I)),
    ("data_analysis", re.compile(r"analysis|pipeline|figure|plot|data|spreadsheet", re.I)),
]

# ── Entity extraction patterns ────────────────────────────────
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I)
URL_RE = re.compile(r"https?://[^\s\])\">]+", re.I)
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}")
ORDER_NUM_RE = re.compile(r"(?:order|tilaus|po)[\s#:]*(\w{4,20})", re.I)


def _classify_document_type(filename: str, text: str) -> tuple[str, float]:
    probe = f"{filename} {text[:2000]}"
    for dtype, pattern in _DOC_TYPE_RULES:
        if pattern.search(probe):
            return dtype, 0.7
    return "unknown", 0.2


def _classify_domain(logical_path: str, text: str) -> tuple[str, float]:
    probe = f"{logical_path} {text[:2000]}"
    for domain, pattern in _DOMAIN_RULES:
        if pattern.search(probe):
            return domain, 0.65
    return "unknown", 0.2


def _detect_language(text: str) -> str:
    """Very rough language detection from common words."""
    sample = text[:3000].lower()
    fi_words = sum(1 for w in ("ja", "on", "ei", "tai", "että", "kanssa", "tämä", "kaikki") if f" {w} " in sample)
    sv_words = sum(1 for w in ("och", "att", "det", "som", "för", "med", "har", "kan") if f" {w} " in sample)
    en_words = sum(1 for w in ("the", "and", "is", "are", "was", "for", "that", "with") if f" {w} " in sample)
    if fi_words > en_words and fi_words > sv_words:
        return "fi"
    if sv_words > en_words and sv_words > fi_words:
        return "sv"
    return "en"


def _extract_entities(text: str) -> dict[str, list[str]]:
    """Extract named entities via regex (deterministic, no AI)."""
    sample = text[:50000]
    emails = list(set(EMAIL_RE.findall(sample)))[:20]
    urls = list(set(URL_RE.findall(sample)))[:20]
    phones = list(set(PHONE_RE.findall(sample)))[:10]
    order_nums = list(set(m.group(1) for m in ORDER_NUM_RE.finditer(sample)))[:10]
    return {
        "emails": emails,
        "urls": urls,
        "phone_numbers": phones,
        "order_numbers": order_nums,
    }


def _infer_title(filename: str, text: str) -> str:
    """Infer document title from filename and first heading."""
    # Try to find a markdown heading
    for line in text[:2000].split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title and len(title) > 3:
                return title[:200]
    # Fall back to filename
    name = filename.rsplit(".", 1)[0] if "." in filename else filename
    return name.replace("_", " ").replace("-", " ").strip()[:200]


def _build_sections(text: str) -> list[dict[str, Any]]:
    """Split text into sections by headings."""
    sections: list[dict[str, Any]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            if current_lines:
                sections.append({
                    "heading": current_heading,
                    "text": "\n".join(current_lines).strip(),
                })
            current_heading = stripped.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "heading": current_heading,
            "text": "\n".join(current_lines).strip(),
        })

    return sections


def _short_summary(text: str, max_len: int = 300) -> str:
    """Generate a short summary from the first meaningful paragraph."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and len(stripped) > 20 and not stripped.startswith("#"):
            return stripped[:max_len]
    return text[:max_len].strip()


def canonicalize(
    manifest: SourceFileManifest,
    extracted: ExtractedDocument,
) -> CanonicalDocument:
    """Convert ExtractedDocument into a canonical document with structured JSON."""
    raw_text = extracted.raw_text or ""

    # Secret redaction
    secret_result = scan_for_secrets(raw_text)
    canonical_text = secret_result.redacted_text
    secret_warnings = []
    if secret_result.has_secrets:
        secret_warnings = [f"Secret detected: {m.secret_type}" for m in secret_result.matches[:5]]

    # Classification
    doc_type, type_conf = _classify_document_type(manifest.file_name, canonical_text)
    domain, domain_conf = _classify_domain(manifest.logical_path, canonical_text)
    language = _detect_language(canonical_text)
    title = _infer_title(manifest.file_name, canonical_text)
    summary = _short_summary(canonical_text)
    entities = _extract_entities(canonical_text)
    sections = _build_sections(canonical_text)

    # Document ID
    doc_id_source = f"{manifest.provider}:{manifest.logical_path}:{manifest.checksum_sha256 or ''}"
    document_id = f"doc_{hashlib.sha256(doc_id_source.encode()).hexdigest()[:16]}"

    needs_review = bool(secret_result.has_secrets) or len(canonical_text.strip()) < 50

    # Build canonical JSON
    canonical_json: dict[str, Any] = {
        "schema_version": "1.0",
        "document_id": document_id,
        "source": {
            "file_name": manifest.file_name,
            "file_type": manifest.file_ext,
            "provider": manifest.provider,
            "logical_path": manifest.logical_path,
            "checksum_sha256": manifest.checksum_sha256,
            "source_system": manifest.provider,
        },
        "classification": {
            "document_type": doc_type,
            "domain": domain,
            "project": None,
            "confidence": round((type_conf + domain_conf) / 2, 3),
        },
        "language": {
            "original": language,
            "canonical": "en",
            "translation_policy": (
                "ordinary text to English; preserve official names, company names, "
                "IDs, emails, URLs, phone numbers, account numbers, file names, "
                "project names exactly"
            ),
        },
        "content": {
            "title": title,
            "short_summary": summary,
            "canonical_text": canonical_text,
            "original_text_length": len(raw_text),
            "sections": sections[:50],
        },
        "entities": {
            "people": [],
            "organizations": [],
            "companies": [],
            **entities,
            "addresses": [],
            "account_numbers": [],
            "product_names": [],
            "software_tools": [],
        },
        "structured_data": {
            "dates": [],
            "prices": [],
            "tables": extracted.raw_tables[:20] if extracted.raw_tables else [],
            "instructions": [],
            "form_fields": [],
            "credentials_or_secrets": secret_result.vault_references,
        },
        "rag": {
            "should_index": not secret_result.has_secrets and len(canonical_text.strip()) > 20,
            "chunking_strategy": "section_then_tokens",
            "recommended_chunk_size_tokens": 700,
            "recommended_overlap_tokens": 100,
            "embedding_status": "not_started",
        },
        "quality": {
            "extraction_confidence": round(extracted.extraction_confidence, 4),
            "translation_confidence": 0.0,
            "ai_canonicalization": False,
            "needs_human_review": needs_review,
            "warnings": extracted.warnings[:10] + secret_warnings,
        },
    }

    all_warnings = extracted.warnings[:10] + secret_warnings

    return CanonicalDocument(
        manifest_id=manifest.id or "",
        extracted_document_id=extracted.id or "",
        document_id=document_id,
        title=title,
        document_type=doc_type,
        domain=domain,
        language_original=language,
        language_canonical="en",
        canonical_json=canonical_json,
        canonical_text=canonical_text,
        short_summary=summary,
        should_index=canonical_json["rag"]["should_index"],
        needs_review=needs_review,
        validation_status="not_validated",
        warnings=all_warnings,
    )
