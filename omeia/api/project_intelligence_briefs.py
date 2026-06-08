"""Project Intelligence Briefs — structured dossiers from internal lab evidence (Layer 1)."""
from __future__ import annotations

import logging
from typing import Any

from omeia.api.evidence_orchestrator import package_evidence, understand_query
from omeia.api.chat_conversation import classify_and_enrich
from omeia.api.platform_flags import project_intelligence_briefs_enabled
from omeia.api.search_service import SearchService

LOGGER = logging.getLogger(__name__)

BRIEF_SECTIONS = (
    "Project Summary",
    "Internal Evidence",
    "Relevant Publications",
    "Marker/Method Summary",
    "Dataset Summary",
    "Research Gaps",
    "Recommended Directions",
    "Risks",
    "Validation Plan",
    "References",
)


def generate_project_brief(
    *,
    project_code: str,
    focus_question: str,
    search_svc: SearchService,
    llm: Any,
    user_role: str | None = None,
) -> dict[str, Any]:
    if not project_intelligence_briefs_enabled():
        return {"ok": False, "error": "disabled", "flag": "OMEIA_PROJECT_INTELLIGENCE_BRIEFS"}

    intent = classify_and_enrich(focus_question or f"Summarize project {project_code}")
    understanding = understand_query(focus_question, intent)
    hits = search_svc.hits_for_copilot(
        focus_question or f"project {project_code} evidence markers protocols publications",
        intent="project_question",
        project_codes=[project_code],
        limit=16,
        prioritize_buckets=understanding.search_plan.prioritize_buckets,
        user_role=user_role,
    )
    evidence = package_evidence(hits, [], entities=understanding.entities, limit=16)

    if not evidence.items:
        return {
            "ok": True,
            "project_code": project_code,
            "markdown": (
                f"# Project Intelligence Brief — {project_code}\n\n"
                "## Project Summary\nInsufficient indexed evidence for this project. "
                "Ingest vault documents, twin JSON, or Research KB sources first.\n"
            ),
            "sections": {s: "" for s in BRIEF_SECTIONS},
            "confidence": "insufficient",
            "sources": [],
        }

    context_lines = []
    for idx, item in enumerate(evidence.items[:12], start=1):
        context_lines.append(f"[{idx}] {item.title}: {item.snippet[:400]}")

    system_prompt = (
        "You are generating a Project Intelligence Brief for the Färkkilä Lab. "
        "Use ONLY the numbered internal evidence. Cite as [1], [2]. "
        "Separate facts from hypotheses. Mark gaps explicitly."
    )
    user_prompt = (
        f"Project: {project_code}\nFocus: {focus_question}\n\n"
        "Internal evidence:\n" + "\n".join(context_lines) + "\n\n"
        "Produce Markdown with sections: "
        + ", ".join(BRIEF_SECTIONS)
    )
    markdown = llm.generate(user_prompt, system_prompt)
    return {
        "ok": True,
        "project_code": project_code,
        "markdown": markdown,
        "confidence": evidence.confidence,
        "sources": [
            {
                "index": item.index,
                "title": item.title,
                "bucket": item.bucket,
                "snippet": item.snippet[:400],
                "score": item.score,
            }
            for item in evidence.items[:12]
        ],
        "sections": _parse_sections(markdown),
    }


def _parse_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, str] = {name: "" for name in BRIEF_SECTIONS}
    current = None
    buf: list[str] = []
    for line in (markdown or "").splitlines():
        if line.startswith("## "):
            if current and current in sections:
                sections[current] = "\n".join(buf).strip()
            heading = line[3:].strip()
            current = heading if heading in sections else None
            buf = []
        elif current:
            buf.append(line)
    if current and current in sections:
        sections[current] = "\n".join(buf).strip()
    return sections
