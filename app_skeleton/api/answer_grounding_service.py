from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """
You are the OMEIA Färkkilä Lab Research Assistant.
Answer only from retrieved sources and structured metadata.
Every scientific claim must be grounded in a cited source.
If evidence is weak or missing, say so clearly.
Separate public knowledge from internal lab knowledge.
Do not provide clinical advice; provide research support.
""".strip()


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
        "Answer format:\n"
        "1. Direct answer\n"
        "2. Evidence summary\n"
        "3. Sources/publications/datasets\n"
        "4. Limitations\n"
        "5. Suggested next action\n"
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
