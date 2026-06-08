from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

ChatIntent = Literal[
    "smalltalk",
    "general_chat",
    "app_help",
    "research_question",
    "protocol_question",
    "search_request",
    "coding_request",
    "document_ingestion_help",
    "people_question",
    "sensitive_private",
]

@dataclass(frozen=True)
class IntentDecision:
    intent: ChatIntent
    use_rag: bool
    show_sources: bool
    require_citations: bool
    answer_style: str
    reason: str
    intent_category: str = "GENERAL_CHAT"
    confidence: float = 0.7

SMALLTALK_PATTERNS = [
    r"^\s*(hi|hello|hey|yo|hiya|howdy)(?:\s+there)?\s*[!.,]*\s*$",
    r"^\s*good\s+(morning|afternoon|evening|day)\s*[!.,]*\s*$",
    r"^\s*(morning|afternoon|evening)\s*[!.,]*\s*$",
    r"^\s*(thanks|thank you|thx|ok|okay|great|nice|cool|good)\s*[!.]*\s*$",
    r"^\s*(how are you|who are you|what can you do|what do you do)\s*[?!.]*\s*$",
]

RESEARCH_TERMS = {
    "hgsc", "hgsoc", "ovarian", "cancer", "tumor", "tumour", "spatial",
    "spatial transcriptomics", "spatial biology", "single-cell", "single cell",
    "scrna", "rna-seq", "visium", "geomx", "cycif", "tcycif", "mhc",
    "mhc class ii", "mhc class 2", "tls", "tertiary lymphoid",
    "tertiary lymphoid structures", "immune", "microenvironment", "stroma",
    "marker", "biomarker", "publication", "paper", "dataset", "geo", "ega",
    "tcga", "cptac", "hrd", "brca", "tp53", "chemotherapy", "immunotherapy",
    "färkkilä", "farkkila", "farkkila lab", "färkkilä lab",
    "lab study", "what does the lab study", "what does this lab study",
    "space", "eyemt", "hgsc immunology", "ovarian cancer immunology",
    "immunotherapy", "stromal", "imc", "proteomics", "humanized", "xenograft",
    "finprove", "precision oncology", "translational",
}

PEOPLE_TERMS = {
    "who is", "who are", "lab member", "lab manager", "team member",
    "principal investigator", "doctoral researcher", "research coordinator",
    "anniina", "anastasia", "joonas", "maija", "saundarya", "debashish",
    "färkkilä lab team", "farkkila lab team",
}

FINNISH_RESEARCH_PATTERNS = [
    re.compile(r"mitä\s+f[äa]rkkil[äa]n\s+lab", re.I),
    re.compile(r"mikä\s+on\s+mhc", re.I),
    re.compile(r"miten\s+teen\s+ashlar", re.I),
]

# Short tokens must match whole words — avoids "app" matching inside "project"/"FastAPI".
_WORD_BOUNDARY_TERMS = frozenset({"app", "api", "env", "css", "jsx", "bug"})

LAB_OVERVIEW_PATTERNS = [
    r"what does (?:the )?(?:f[äa]rkkil[äa]|farkkila)\s*lab\s*study",
    r"what (?:does|do)\s*(?:the )?lab\s*(?:study|research|work on)",
    r"what is (?:the )?(?:f[äa]rkkil[äa]|farkkila)\s*lab",
    r"research focus of (?:the )?(?:f[äa]rkkil[äa]|farkkila)\s*lab",
]

PROTOCOL_TERMS = {
    "protocol", "sop", "staining", "segmentation", "ashlar", "basic",
    "illumination", "mesmer", "stardist", "pipeline",
    "ome-tiff", "tiff", "mask", "quantification", "cylinter",
}

APP_HELP_TERMS = {
    "app", "screen", "button", "upload", "login", "auth", "search",
    "chatbot", "assistant", "gemini", "api", "setup", "install",
    "configuration", "configure", "env", "environment",
}

CODING_TERMS = {
    "code", "script", "react", "fastapi", "python", "javascript",
    "jsx", "css", "bug", "error", "traceback", "compile", "npm",
}

SENSITIVE_PATTERNS = [
    r"\b\d{6}[-+A][0-9A-Z]{3,4}\b",
    r"\bMRN[:\s#-]*[A-Z0-9-]{4,}\b",
    r"\b(?:patient|pt|subject)\s*#?\s*[A-Z0-9-]{3,}\b",
    r"\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[^'\"\s]{8,}",
]

SCIENTIFIC_ACCESSION_PATTERNS = [
    re.compile(r"\bGSE\d+\b", re.I),
    re.compile(r"\bGSM\d+\b", re.I),
    re.compile(r"\bGPL\d+\b", re.I),
    re.compile(r"\bPRJNA\d+\b", re.I),
    re.compile(r"\bSRR\d+\b", re.I),
    re.compile(r"\bSRX\d+\b", re.I),
    re.compile(r"\bEGAS\d+\b", re.I),
    re.compile(r"\bEGAD\d+\b", re.I),
    re.compile(r"\bphs\d+(?:\.v\d+)?\b", re.I),
    re.compile(r"\bTCGA-[A-Z0-9-]+\b", re.I),
    re.compile(r"\b10\.\d{4,}/[^\s]+", re.I),
    re.compile(r"\bPMID:?\s*\d+\b", re.I),
]

RESEARCH_PROTOCOL_SHORT_TERMS = RESEARCH_TERMS | PROTOCOL_TERMS | {
    "gse", "gsm", "ega", "tcga", "doi", "pmid", "accession", "dataset",
}


def _contains_scientific_identifier(text: str) -> bool:
    return any(pattern.search(text) for pattern in SCIENTIFIC_ACCESSION_PATTERNS)


def _term_matches(text: str, term: str) -> bool:
    lower = text.lower()
    if term in _WORD_BOUNDARY_TERMS or len(term) <= 3:
        return bool(re.search(rf"\b{re.escape(term)}\b", lower, re.I))
    return term in lower


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(_term_matches(text, term) for term in terms)


def _is_lab_overview_question(text: str) -> bool:
    lower = text.lower()
    return any(re.search(pattern, lower, re.I) for pattern in LAB_OVERVIEW_PATTERNS)


def classify_chat_intent(message: str) -> IntentDecision:
    """Classify user intent — specific intents win before generic matches."""
    text = (message or "").strip()
    lower = text.lower()

    if not text:
        return IntentDecision(
            intent="smalltalk",
            use_rag=False,
            show_sources=False,
            require_citations=False,
            answer_style="brief_conversational",
            reason="empty message",
        )

    # 1. sensitive_private
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text, re.I):
            return IntentDecision(
                intent="sensitive_private",
                use_rag=False,
                show_sources=False,
                require_citations=False,
                answer_style="safety",
                reason="sensitive pattern detected",
            )

    # 2. accession / identifier search
    if _contains_scientific_identifier(text):
        return IntentDecision(
            intent="search_request",
            use_rag=True,
            show_sources=True,
            require_citations=True,
            answer_style="search_summary",
            reason="scientific accession or identifier detected",
        )

    # 3. document_ingestion_help (RAG/indexing only — not generic file upload)
    if any(
        phrase in lower
        for phrase in (
            "ingest document",
            "index document",
            "chunk and embed",
            "vector index",
            "rag ingest",
            "add to qdrant",
            "ingest documents into rag",
            "ingest into rag",
            "ingest into qdrant",
        )
    ) or (
        _contains_any(lower, {"ingest", "indexing", "chunking", "embedding"})
        and _contains_any(lower, {"document", "protocol", "sop", "rag", "qdrant", "vector"})
    ):
        return IntentDecision(
            intent="document_ingestion_help",
            use_rag=False,
            show_sources=False,
            require_citations=False,
            answer_style="helpful_steps",
            reason="document ingestion help",
        )

    # 4. coding_request (before app_help — use word boundaries; skip when research terms dominate)
    if _contains_any(lower, CODING_TERMS) and not _contains_any(lower, RESEARCH_TERMS):
        return IntentDecision(
            intent="coding_request",
            use_rag=False,
            show_sources=False,
            require_citations=False,
            answer_style="technical",
            reason="coding term detected",
        )

    # 5. search_request (explicit lookup — word boundaries; "research" must not match "search")
    if re.search(r"\b(find|search|look up|where is|show me|locate)\b", lower):
        return IntentDecision(
            intent="search_request",
            use_rag=True,
            show_sources=True,
            require_citations=True,
            answer_style="search_summary",
            reason="explicit search request",
        )

    # 6. Finnish research/protocol cues
    for pattern in FINNISH_RESEARCH_PATTERNS:
        if pattern.search(text):
            intent = "protocol_question" if "ashlar" in lower or "protokoll" in lower else "research_question"
            return IntentDecision(
                intent=intent,
                use_rag=True,
                show_sources=True,
                require_citations=True,
                answer_style="scientific_with_sources" if intent == "research_question" else "practical_with_sources",
                reason="Finnish research/protocol pattern",
            )

    # 7. people_question
    if any(term in lower for term in PEOPLE_TERMS) or re.search(r"\bwho\s+is\b", lower):
        return IntentDecision(
            intent="people_question",
            use_rag=True,
            show_sources=True,
            require_citations=True,
            answer_style="search_summary",
            reason="lab member / people lookup",
        )

    # 8. protocol how-to (before research — tCyCIF/CycIF must not override "how do I run")
    if re.search(r"\b(how do i|how to|workflow|steps|overview)\b", lower) and _contains_any(lower, PROTOCOL_TERMS):
        return IntentDecision(
            intent="protocol_question",
            use_rag=True,
            show_sources=True,
            require_citations=True,
            answer_style="practical_with_sources",
            reason="protocol how-to detected",
        )

    # 9. research_question (before app_help so "project research focus" is not misclassified)
    if _is_lab_overview_question(text) or _contains_any(lower, RESEARCH_TERMS) or "research focus" in lower or "lab research" in lower:
        return IntentDecision(
            intent="research_question",
            use_rag=True,
            show_sources=True,
            require_citations=True,
            answer_style="scientific_with_sources",
            reason="research term or lab overview detected",
        )

    # 9. generic upload/login UI help (before protocol — upload protocol doc is app help, not SOP)
    if re.search(r"\bupload\b", lower) and _contains_any(lower, {"document", "protocol", "file"}):
        return IntentDecision(
            intent="app_help",
            use_rag=False,
            show_sources=False,
            require_citations=False,
            answer_style="helpful_steps",
            reason="document upload UI help",
        )

    # 10. app_help (skip when research/protocol terms dominate)
    if _contains_any(lower, APP_HELP_TERMS) and not (
        _contains_any(lower, RESEARCH_TERMS)
        or _contains_any(lower, PROTOCOL_TERMS)
        or "research on" in lower
        or "lab research" in lower
        or "research focus" in lower
    ):
        return IntentDecision(
            intent="app_help",
            use_rag=False,
            show_sources=False,
            require_citations=False,
            answer_style="helpful_steps",
            reason="app-help term detected",
        )

    # 11. protocol_question
    if _contains_any(lower, PROTOCOL_TERMS) or "workflow" in lower or "normalization" in lower:
        return IntentDecision(
            intent="protocol_question",
            use_rag=True,
            show_sources=True,
            require_citations=True,
            answer_style="practical_with_sources",
            reason="protocol/workflow term detected",
        )

    # 12. smalltalk (before short generic trap so "thanks"/"hi" stay conversational)
    for pattern in SMALLTALK_PATTERNS:
        if re.match(pattern, lower, re.I):
            return IntentDecision(
                intent="smalltalk",
                use_rag=False,
                show_sources=False,
                require_citations=False,
                answer_style="brief_conversational",
                reason="smalltalk/greeting",
            )

    # Very short generic messages should not trigger RAG.
    if len(text.split()) <= 2 and not _contains_any(lower, RESEARCH_PROTOCOL_SHORT_TERMS):
        return IntentDecision(
            intent="general_chat",
            use_rag=False,
            show_sources=False,
            require_citations=False,
            answer_style="natural",
            reason="short generic message",
        )

    return IntentDecision(
        intent="general_chat",
        use_rag=False,
        show_sources=False,
        require_citations=False,
        answer_style="natural",
        reason="default general chat",
    )
