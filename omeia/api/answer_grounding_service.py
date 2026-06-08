from __future__ import annotations

import re
from typing import Any

SYSTEM_PROMPT = """
You are the OMEIA Färkkilä Lab Research Assistant.
Answer only from retrieved sources and structured metadata.
Every scientific claim must be grounded in a cited source.
If evidence is weak or missing, say so clearly.
Separate public knowledge from internal lab knowledge.
Do not provide clinical advice; provide research support.
""".strip()

OFF_TOPIC_PATTERNS = [
    re.compile(r"quantum\s+(?:chromodynamics|physics|mechanics|field)", re.I),
    re.compile(r"quark[- ]gluon", re.I),
    re.compile(r"string theory", re.I),
    re.compile(r"black hole thermodynamics", re.I),
    re.compile(r"\b\d+\s*dimensions?\b.*(?:physics|quantum|space)", re.I),
]

CONVERSATIONAL_ANSWER_STYLES = frozenset({
    "brief_conversational",
    "natural",
    "helpful_steps",
    "technical",
    "safety",
})


def is_off_topic_query(question: str) -> bool:
    text = (question or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in OFF_TOPIC_PATTERNS)


def build_grounded_prompt(question: str, hits: list[dict[str, Any]]) -> str:
    context_lines = []
    for i, hit in enumerate(hits[:12], 1):
        context_lines.append(
            f"[{i}] {hit.get('title')}\n"
            f"Type: {hit.get('source_type')}\n"
            f"URL: {hit.get('source_url') or ''}\n"
            f"DOI: {hit.get('doi') or ''}\n"
            f"PMID: {hit.get('pmid') or ''}\n"
            f"Excerpt: {hit.get('snippet') or ''}\n"
        )
    return (
        "Use the following retrieved sources only. Cite sources as [1], [2], etc.\n\n"
        + "\n".join(context_lines)
        + f"\n\nQuestion: {question}\n\n"
        "Write a colleague-style scientific summary. Be specific — no generic filler.\n"
        "Cover:\n"
        "1. Key findings (what was shown, in what context)\n"
        "2. Methods (assays, cohorts, platforms, analysis approach)\n"
        "3. Limitations (sample size, bias, missing data, caveats)\n"
        "4. Implications (for HGSC, spatial biology, immunology, or the user's question)\n"
        "5. Future directions / sensible next experiments or analyses\n"
        "Do not introduce yourself or list assistant capabilities.\n"
    )


def validate_answer_sources(answer: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    cited = []
    for i in range(1, len(hits) + 1):
        if f"[{i}]" in answer:
            cited.append(i)
    return {
        "has_citations": bool(cited),
        "cited_indices": cited,
        "retrieved_count": len(hits),
        "warning": None if cited else "Answer contains no source citations.",
    }


def append_sources_block(answer: str, hits: list[dict[str, Any]]) -> str:
    """Append a validated sources list when inline citations are missing."""
    if not hits:
        return answer
    lines = ["\n\n**Sources used:**"]
    for i, hit in enumerate(hits[:8], 1):
        title = hit.get("title") or f"Source {i}"
        lines.append(f"[{i}] {title}")
    return answer.rstrip() + "\n".join(lines)


def enforce_citations(
    answer: str,
    hits: list[dict[str, Any]],
    *,
    generate_fn,
    user_content: str,
    system_prompt: str,
) -> tuple[str, list[str]]:
    """Ensure [n] markers when citations are required — re-prompt once, then append sources."""
    notes: list[str] = []
    if not hits:
        return answer, notes

    validation = validate_answer_sources(answer, hits)
    if validation.get("has_citations"):
        return answer, notes

    retry_content = (
        user_content
        + "\n\nIMPORTANT: You MUST cite every factual claim using inline markers [1], [2], etc. "
        "that map to the numbered sources above. Do not omit citations."
    )
    retry_answer = generate_fn(retry_content, system_prompt)
    validation2 = validate_answer_sources(retry_answer, hits)
    if validation2.get("has_citations"):
        return retry_answer, notes

    patched = append_sources_block(retry_answer or answer, hits)
    notes.append("Citations were appended automatically because the model omitted inline [n] markers.")
    return patched, notes


def empty_corpus_answer(question: str, *, intent: str = "research_question") -> str:
    return (
        "I don't have indexed evidence on this in the current knowledge base. "
        f"Try unified search (⌘K) for “{question.strip()[:80]}”, or ask an admin to ingest "
        "relevant publications, protocols, or datasets into the research KB."
    )


def off_topic_refusal() -> str:
    return (
        "I'm the OMEIA Färkkilä Lab research copilot — I focus on lab research, protocols, "
        "datasets, and platform help. Your question looks outside that scope. "
        "The following is general knowledge, not lab-grounded: I can't provide a reliable "
        "answer from our indexed sources. Please ask about spatial biology, HGSC immunology, "
        "lab protocols, or dataset lookup instead."
    )
