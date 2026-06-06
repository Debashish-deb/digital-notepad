from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

@dataclass
class ParsedDocument:
    title: str
    clean_text: str
    abstract: str = ""
    sections: dict[str, str] | None = None
    metadata: dict[str, Any] | None = None


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def clean_scientific_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_sections(text: str) -> dict[str, str]:
    clean = clean_scientific_text(text)
    headings = ["Abstract", "Introduction", "Methods", "Materials and methods", "Results", "Discussion", "Data availability", "References"]
    pattern = re.compile(r"(?im)^\s*(" + "|".join(re.escape(h) for h in headings) + r")\s*$")
    matches = list(pattern.finditer(clean))
    if not matches:
        return {"Body": clean}
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(clean)
        name = match.group(1).strip()
        sections[name] = clean[start:end].strip()
    return sections


def chunk_document(text: str, target_chars: int = 4200, overlap_chars: int = 650) -> list[dict[str, Any]]:
    clean = clean_scientific_text(text)
    sections = extract_sections(clean)
    chunks: list[dict[str, Any]] = []
    idx = 0
    for section_title, section_text in sections.items():
        if not section_text.strip():
            continue
        start = 0
        while start < len(section_text):
            chunk = section_text[start:start + target_chars].strip()
            if chunk:
                chunks.append({
                    "chunk_index": idx,
                    "section_title": section_title,
                    "text": chunk,
                    "text_hash": sha256_text(chunk),
                    "token_count": max(1, len(chunk.split())),
                })
                idx += 1
            if start + target_chars >= len(section_text):
                break
            start += max(1, target_chars - overlap_chars)
    return chunks
