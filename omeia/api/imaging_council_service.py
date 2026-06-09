"""Multi-agent imaging council — literature, biomarker, spatial, critic roles."""
from __future__ import annotations

from typing import Any

COUNCIL_ROLES = ("literature", "biomarker", "spatial", "critic")

ROLE_PROMPTS: dict[str, str] = {
    "literature": (
        "You are a literature analyst for multiplex immunofluorescence. "
        "Cite peer-reviewed sources when discussing markers. Disclose uncertainty."
    ),
    "biomarker": (
        "You are a biomarker specialist. Interpret channel intensities and phenotypes. "
        "Never override quantitative measurements from the instrument. Cite sources."
    ),
    "spatial": (
        "You are a spatial biology analyst. Discuss neighborhood context and distances. "
        "Use µm units when calibration is provided. Disclose limitations."
    ),
    "critic": (
        "You are a scientific critic. Challenge assumptions, flag confounders, "
        "require uncertainty disclosure, and ensure cited sources. "
        "Never claim measurements were re-run — only interpret reported values."
    ),
}

GUARDRAIL_SUFFIX = (
    "\n\nGuardrails: cite sources where possible; disclose uncertainty; "
    "do not override or contradict instrument measurements."
)


def _mock_council_response(
    *,
    asset_id: str,
    markers: list[str],
    question: str,
) -> dict[str, Any]:
    marker_txt = ", ".join(markers[:6]) if markers else "unspecified markers"
    opinions = []
    for role in COUNCIL_ROLES:
        opinions.append(
            {
                "role": role,
                "summary": (
                    f"[{role}] For asset {asset_id} ({marker_txt}): "
                    f"interpretation of '{question[:120]}' requires validation against "
                    "raw probe values and literature (stub council — configure LLM for live synthesis)."
                ),
                "citations": [
                    {"title": "Multiplex IF best practices", "source": "methodology_stub", "confidence": "low"}
                ],
                "uncertainty": "medium",
                "measurement_override": False,
            }
        )
    return {
        "asset_id": asset_id,
        "question": question,
        "markers": markers,
        "opinions": opinions,
        "consensus": (
            "Council recommends cross-checking display windows with raw pixel probe "
            "and validating against Napari/QuPath on the same OME-TIFF."
        ),
        "guardrails_applied": True,
        "provider": "mock",
    }


def run_imaging_council(
    *,
    asset_id: str,
    question: str,
    markers: list[str] | None = None,
    imaging_context: dict[str, Any] | None = None,
    llm: Any = None,
) -> dict[str, Any]:
    """Run lightweight multi-role council; falls back to structured mock."""
    markers = list(markers or [])
    ctx = imaging_context or {}
    provider = getattr(llm, "provider", None) if llm else None

    if not llm or provider in (None, "mock"):
        return _mock_council_response(asset_id=asset_id, markers=markers, question=question)

    opinions: list[dict[str, Any]] = []
    context_block = (
        f"Asset: {asset_id}. Markers: {', '.join(markers) or 'none'}. "
        f"Dtype: {ctx.get('dtype', 'unknown')}. "
        f"Pixel size µm: {ctx.get('pixel_size_um', 'uncalibrated')}."
    )
    for role in COUNCIL_ROLES:
        prompt = (
            f"{ROLE_PROMPTS[role]}{GUARDRAIL_SUFFIX}\n\n"
            f"Context: {context_block}\n\nQuestion: {question}"
        )
        try:
            answer = llm.generate(prompt) if hasattr(llm, "generate") else str(llm)
            text = answer if isinstance(answer, str) else getattr(answer, "text", str(answer))
        except Exception as exc:
            text = f"Council role {role} unavailable: {exc}"
        opinions.append(
            {
                "role": role,
                "summary": text[:2000],
                "citations": [],
                "uncertainty": "medium",
                "measurement_override": False,
            }
        )

    return {
        "asset_id": asset_id,
        "question": question,
        "markers": markers,
        "opinions": opinions,
        "consensus": opinions[-1]["summary"][:500] if opinions else "",
        "guardrails_applied": True,
        "provider": provider or "unknown",
    }
