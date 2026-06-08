"""Natural, context-aware conversational layer for the research copilot."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from app_skeleton.api.chat_intent import IntentDecision, classify_chat_intent

# User-facing intent taxonomy (metadata for routing + analytics)
INTENT_GREETING = "GREETING"
INTENT_QUESTION = "QUESTION"
INTENT_PROJECT = "PROJECT_DISCUSSION"
INTENT_LITERATURE = "LITERATURE"
INTENT_IMAGE_ANALYSIS = "IMAGE_ANALYSIS"
INTENT_TROUBLESHOOTING = "TROUBLESHOOTING"
INTENT_CLINICAL = "CLINICAL_ANALYSIS"
INTENT_CODING = "CODING"
INTENT_GENERAL = "GENERAL_CHAT"

PURE_GREETING_PATTERNS = [
    re.compile(r"^\s*(hi|hello|hey|yo|hiya|howdy)(?:\s+there)?\s*[!.,]*\s*$", re.I),
    re.compile(r"^\s*good\s+(morning|afternoon|evening|day)\s*[!.,]*\s*$", re.I),
    re.compile(r"^\s*(morning|afternoon|evening)\s*[!.,]*\s*$", re.I),
    re.compile(r"^\s*(thanks|thank you|thx)\s*[!.,]*\s*$", re.I),
    re.compile(r"^\s*(ok|okay|great|nice|cool|good)\s*[!.,]*\s*$", re.I),
]

GREETING_PATTERNS = PURE_GREETING_PATTERNS + [
    re.compile(r"^\s*how\s+are\s+you\s*[?!.]*\s*$", re.I),
]

CAPABILITY_ASK_PATTERNS = [
    re.compile(r"^\s*(who\s+are\s+you|what\s+can\s+you\s+do|what\s+do\s+you\s+do)\s*[?!.]*\s*$", re.I),
]

IMAGE_ANALYSIS_TERMS = {
    "image analysis", "segmentation", "stardist", "napari", "ashlar", "stitching",
    "cycif", "tcycif", "illumination", "mask", "pipeline", "ome-tiff", "quantification",
    "spatial deconvolution", "cell2location",
}

LITERATURE_TERMS = {
    "literature", "publication", "paper", "pubmed", "doi", "review", "meta-analysis",
    "citation", "manuscript", "journal",
}

PROJECT_TERMS = {
    "project", "portfolio", "eyemt", "space", "kras", "notebook", "workspace",
}

CLINICAL_TERMS = {
    "patient", "clinical", "cohort", "survival", "hrd", "treatment", "chemotherapy",
    "immunotherapy", "prognosis",
}

COLLEAGUE_CONVERSATIONAL_PROMPT = (
    "You are a senior research colleague in the Färkkilä Lab (HGSC, spatial biology, immunology). "
    "Sound like a helpful scientist in the lab — not a product, chatbot manual, or marketing page. "
    "Never open with 'Hello! I'm OMEIA' or list capabilities unless the user explicitly asks who you are. "
    "Do not say: 'I can help with…', 'I am designed to…', 'My capabilities include…', 'As an AI assistant…'. "
    "Prefer short, direct replies: ask what they want to investigate, offer to look at data or papers, "
    "or answer the question immediately. "
    "No headings, bullet lists, or citation blocks unless the user asked for a structured summary."
)

COLLEAGUE_RESEARCH_PROMPT = (
    "You are a senior research colleague in the Färkkilä Lab. "
    "Answer the scientific question directly — do not introduce yourself or list assistant features. "
    "Ground claims in retrieved sources with [1], [2] markers. "
    "If evidence is thin, say so plainly. No clinical treatment advice."
)

COLLEAGUE_SUMMARY_PROMPT = (
    "Summarize retrieved sources like a colleague briefing the lab. "
    "Extract and state clearly: (1) key findings, (2) methods, (3) limitations, "
    "(4) implications for HGSC/spatial/immuno-oncology work, (5) sensible next steps. "
    "Avoid generic filler. Be specific and actionable. Cite as [1], [2], etc."
)


@dataclass(frozen=True)
class UserChatContext:
    user_name: str = ""
    project_codes: tuple[str, ...] = ()
    project_labels: tuple[str, ...] = ()


def enrich_intent_decision(decision: IntentDecision, message: str) -> IntentDecision:
    """Attach user-facing intent category and confidence score."""
    category, confidence = _intent_category_and_confidence(decision, message)
    return replace(decision, intent_category=category, confidence=confidence)


def is_greeting_message(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return True
    return any(pattern.match(text) for pattern in GREETING_PATTERNS)


def is_pure_greeting(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return True
    return any(pattern.match(text) for pattern in PURE_GREETING_PATTERNS)


def is_capability_question(message: str) -> bool:
    text = (message or "").strip()
    return any(pattern.match(text) for pattern in CAPABILITY_ASK_PATTERNS)


def should_use_instant_greeting(decision: IntentDecision, message: str) -> bool:
    """Template greetings — no RAG, no expensive LLM pipeline."""
    if decision.intent != "smalltalk":
        return False
    return is_pure_greeting(message) or is_capability_question(message)


def _time_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def _project_hint(ctx: UserChatContext) -> str:
    labels = [p for p in ctx.project_labels if p]
    codes = [c for c in ctx.project_codes if c]
    names = labels or codes
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} or {names[1]}"
    return ", ".join(names[:-1]) + f", or {names[-1]}"


def instant_greeting_response(message: str, ctx: UserChatContext) -> str:
    """Sub-second contextual greeting — no capability brochure."""
    text = (message or "").strip().lower()
    name = ctx.user_name.split()[0] if ctx.user_name else ""
    name_bit = f", {name}" if name else ""
    projects = _project_hint(ctx)

    if re.match(r"^\s*(thanks|thank you|thx)\s*", text):
        return "You're welcome. What should we look at next?"

    if is_capability_question(message):
        if projects:
            return (
                f"I'm here to think through lab work with you — literature, {projects}, "
                "pipelines, or image analysis. What are you working on today?"
            )
        return (
            "I'm here to think through lab work with you — literature, projects, "
            "pipelines, or image analysis. What are you working on today?"
        )

    if re.match(r"^\s*how\s+are\s+you", text):
        return f"Doing well{name_bit} — thanks. What are you working on today?"

    if projects:
        lead = _time_greeting() if re.search(r"good\s+(morning|afternoon|evening)|^(morning|afternoon|evening)\b", text) else "Welcome back"
        return (
            f"{lead}{name_bit}. Would you like to continue with {projects}, "
            "or start something new?"
        )

    if re.search(r"good\s+morning|^(morning)\b", text):
        return f"Good morning{name_bit}. What are you working on today?"
    if re.search(r"good\s+afternoon|^(afternoon)\b", text):
        return f"Good afternoon{name_bit}. What can I help you investigate?"
    if re.search(r"good\s+evening|^(evening)\b", text):
        return f"Good evening{name_bit}. What would you like to explore?"

    return (
        f"Hi{name_bit}. Are you looking at a project, a paper, image-analysis results, "
        "or something else?"
    )


def conversational_system_prompt(
    decision: IntentDecision,
    *,
    user_name: str = "",
    lang: str | None = None,
) -> str:
    """Colleague-style system prompts — intent-aware, no robotic intros."""
    name_hint = f" The researcher's name is {user_name}." if user_name else ""
    lang_hint = ""
    if lang == "fi":
        lang_hint = " Reply in Finnish; keep DOIs and accession IDs unchanged."

    if decision.answer_style == "safety":
        return (
            "Decline to process patient identifiers, credentials, or secrets. "
            "Ask the user to remove sensitive details and try again."
        )

    if decision.intent == "smalltalk" or decision.answer_style in {"brief_conversational", "natural"}:
        return COLLEAGUE_CONVERSATIONAL_PROMPT + name_hint + lang_hint

    if decision.answer_style == "helpful_steps":
        return (
            COLLEAGUE_CONVERSATIONAL_PROMPT
            + name_hint
            + lang_hint
            + " Give practical steps for using the platform. Stay conversational."
        )

    if decision.answer_style == "technical":
        return (
            COLLEAGUE_CONVERSATIONAL_PROMPT
            + name_hint
            + lang_hint
            + " Focus on code and debugging. Use code blocks when useful."
        )

    if decision.answer_style == "search_summary":
        return COLLEAGUE_SUMMARY_PROMPT + name_hint + lang_hint

    if decision.answer_style in {"scientific_with_sources", "practical_with_sources"}:
        return COLLEAGUE_RESEARCH_PROMPT + name_hint + lang_hint

    return COLLEAGUE_RESEARCH_PROMPT + name_hint + lang_hint


def resolve_route_model(decision: IntentDecision) -> tuple[str | None, str | None]:
    """
    Return (provider, model) override for fast/local routing.
    None means keep the request default.
    """
    if decision.intent == "smalltalk":
        return "ollama", os.getenv("CHAT_GREETING_MODEL", "qwen3:8b").strip() or "qwen2.5:3b"
    if decision.intent == "general_chat" and not decision.use_rag:
        return "ollama", os.getenv("CHAT_CONVERSATION_MODEL", "qwen3:14b").strip() or "qwen2.5:7b-instruct"
    if decision.answer_style == "search_summary":
        return "ollama", os.getenv("CHAT_SUMMARY_MODEL", "qwen3:14b").strip() or "qwen2.5:7b-instruct"
    if decision.intent in {"coding_request", "app_help", "document_ingestion_help"}:
        return "ollama", os.getenv("CHAT_CONVERSATION_MODEL", "qwen3:14b").strip() or "qwen2.5:7b-instruct"
    # research / protocol / search with citations — keep configured primary (gemini etc.)
    return None, None


def _user_display_name(user: dict[str, Any] | None) -> str:
    if not user:
        return ""
    for key in ("display_name", "full_name", "name"):
        val = (user.get(key) or "").strip()
        if val:
            return val.split(",")[0].strip()
    email = (user.get("email") or "").strip()
    if email and "@" in email:
        local = email.split("@", 1)[0]
        return local.replace(".", " ").replace("_", " ").title()
    return ""


def build_user_context(
    message: str,
    *,
    user: dict[str, Any] | None,
    project_codes: list[str] | None,
    db_data: dict[str, Any] | None = None,
) -> UserChatContext:
    codes = tuple(c for c in (project_codes or []) if c)
    labels: list[str] = list(codes[:4])
    return UserChatContext(
        user_name=_user_display_name(user),
        project_codes=codes,
        project_labels=tuple(labels),
    )


def _intent_category_and_confidence(decision: IntentDecision, message: str) -> tuple[str, float]:
    lower = (message or "").lower()

    if decision.intent == "smalltalk":
        return INTENT_GREETING, 0.95
    if decision.intent == "sensitive_private":
        return INTENT_TROUBLESHOOTING, 0.99
    if decision.intent == "coding_request":
        return INTENT_CODING, 0.88
    if decision.intent == "document_ingestion_help" or decision.intent == "app_help":
        return INTENT_TROUBLESHOOTING, 0.82
    if decision.intent == "people_question" or any(t in lower for t in PROJECT_TERMS):
        return INTENT_PROJECT, 0.8
    if decision.intent == "search_request" or any(t in lower for t in LITERATURE_TERMS):
        return INTENT_LITERATURE, 0.86
    if decision.intent == "protocol_question" or any(t in lower for t in IMAGE_ANALYSIS_TERMS):
        return INTENT_IMAGE_ANALYSIS, 0.84
    if any(t in lower for t in CLINICAL_TERMS) and decision.use_rag:
        return INTENT_CLINICAL, 0.78
    if decision.intent == "research_question":
        return INTENT_QUESTION, 0.9
    if decision.intent == "general_chat":
        return INTENT_GENERAL, 0.65
    return INTENT_GENERAL, 0.7


def classify_and_enrich(message: str) -> IntentDecision:
    return enrich_intent_decision(classify_chat_intent(message), message)
