"""OMEIA Research Evidence Orchestrator — query understanding, evidence packaging, synthesis prompts."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from app_skeleton.api.chat_intent import IntentDecision, SCIENTIFIC_ACCESSION_PATTERNS
from app_skeleton.api.research_search_service import normalize_query, tokenize_query

ConfidenceLevel = Literal["high", "medium", "low", "insufficient"]
ClaimStatus = Literal["corroborated", "single_source", "conflicting", "uncertain"]

ORCHESTRATOR_SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("executive_summary", r"executive\s+summary"),
    ("evidence", r"evidence|key\s+findings"),
    ("methods", r"methods?(?:\s*&\s*context)?|context(?:\s*&\s*methods)?"),
    ("limitations", r"limitations?(?:\s*&\s*confidence)?|confidence(?:\s*assessment)?"),
    ("references", r"references?|supporting\s+literature|citations?"),
)

SECTION_HEADER_RE = re.compile(
    r"^(?:#{1,3}\s*|\d+\.\s*)?\*{0,2}(" + "|".join(pat for _, pat in ORCHESTRATOR_SECTION_ORDER) + r")\*{0,2}\s*:?\s*$",
    re.I,
)

POSITIVE_CLAIM_RE = re.compile(
    r"\b(increase[ds]?|elevated|high|associated with|predicts|promotes|enhances|correlates|improves|sensitive|response|benefit)\b",
    re.I,
)
NEGATIVE_CLAIM_RE = re.compile(
    r"\b(decrease[ds]?|reduced|low|lack(?:s|ing)?|inhibits|suppresses|resistant|no association|not associated|worse|poor)\b",
    re.I,
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# --- Master orchestrator principles (11) encoded as prompt sections ---

ORCHESTRATOR_IDENTITY = (
    "You are the OMEIA Research Evidence Orchestrator for the Färkkilä Lab "
    "(HGSC, spatial biology, immunology). You synthesize answers from retrieved evidence only."
)

PRINCIPLE_UNDERSTAND = (
    "Understand the question before searching: classify intent, identify domain and entities, "
    "and plan which source classes (internal lab, protocols, publications, datasets) matter."
)

PRINCIPLE_MULTI_SOURCE = (
    "Retrieve across multiple source classes: internal lab knowledge, protocols/SOPs, "
    "publications/preprints, datasets, and project metadata. Prefer lab-indexed evidence "
    "over general knowledge when both exist."
)

PRINCIPLE_HYBRID_SEARCH = (
    "Evidence was retrieved via hybrid search (semantic + keyword/BM25 + metadata filters). "
    "Treat higher-scored, multi-bucket corroboration as stronger support."
)

PRINCIPLE_RANKING = (
    "Rank evidence by relevance score, source type priority (lab protocols > publications > files), "
    "and cross-source agreement on key entities or claims."
)

PRINCIPLE_CROSS_VALIDATE = (
    "Cross-validate claims across sources. When sources agree, state confidence as higher. "
    "When they conflict or only one source supports a claim, say so explicitly."
)

PRINCIPLE_STRUCTURED_PACKAGE = (
    "You receive a structured evidence package — not a raw document dump. "
    "Each numbered item maps to an indexed source with title, type, excerpt, and identifiers."
)

PRINCIPLE_RESEARCH_REASONING = (
    "Use research-grade reasoning: separate observed findings, methods, limitations, "
    "and hypotheses. Do not conflate correlation with causation. No clinical treatment advice."
)

PRINCIPLE_RESPONSE_STRUCTURE = (
    "Structure every evidence-grounded answer as:\n"
    "1. **Executive summary** — 2–4 sentences answering the question directly.\n"
    "2. **Evidence** — key findings with inline [1], [2] citations tied to the package.\n"
    "3. **Methods & context** — assays, cohorts, platforms where relevant.\n"
    "4. **Limitations & confidence** — gaps, conflicts, sample-size caveats; state confidence "
    "(high / medium / low) and why.\n"
    "5. **References** — numbered list matching [n] markers (title + DOI/PMID/accession when available)."
)

PRINCIPLE_HALLUCINATION_CONTROL = (
    "Hallucination control: NEVER invent citations, DOIs, PMIDs, accession IDs, p-values, "
    "hazard ratios, or patient counts. If evidence is missing, say 'not found in indexed sources'. "
    "Do not cite a source index that was not provided in the evidence package."
)

PRINCIPLE_PREMIUM_UX = (
    "Premium UX: sound like a senior lab colleague — natural, direct, audience-adapted. "
    "No robotic intros ('Hello! I'm OMEIA'), no capability brochures, no generic filler. "
    "Use headings only when they aid scanning; keep prose tight."
)

ORCHESTRATOR_CORE_PROMPT = "\n".join(
    [
        ORCHESTRATOR_IDENTITY,
        PRINCIPLE_UNDERSTAND,
        PRINCIPLE_MULTI_SOURCE,
        PRINCIPLE_HYBRID_SEARCH,
        PRINCIPLE_RANKING,
        PRINCIPLE_CROSS_VALIDATE,
        PRINCIPLE_STRUCTURED_PACKAGE,
        PRINCIPLE_RESEARCH_REASONING,
        PRINCIPLE_RESPONSE_STRUCTURE,
        PRINCIPLE_HALLUCINATION_CONTROL,
        PRINCIPLE_PREMIUM_UX,
    ]
)

# Domain buckets for query understanding
DOMAIN_PATTERNS: dict[str, re.Pattern[str]] = {
    "hgsc_immunology": re.compile(
        r"\b(hgsc|hgsoc|ovarian|immunotherapy|tls|tertiary lymphoid|mhc|tim-?3|pd-?1|pd-?l1)\b",
        re.I,
    ),
    "spatial_biology": re.compile(
        r"\b(spatial|visium|geomx|cycif|tcycif|imc|multiplex|deconvolution|cell2location)\b",
        re.I,
    ),
    "clinical_translational": re.compile(
        r"\b(patient|cohort|survival|hrd|chemotherapy|prognosis|clinical|finprove)\b",
        re.I,
    ),
    "protocols_pipelines": re.compile(
        r"\b(protocol|sop|ashlar|stardist|pipeline|segmentation|staining|illumination)\b",
        re.I,
    ),
    "literature_datasets": re.compile(
        r"\b(publication|paper|doi|pmid|dataset|geo|ega|tcga|gse\d+|accession)\b",
        re.I,
    ),
}

GENE_ENTITY_PATTERN = re.compile(
    r"\b(?:BRCA[12]?|TP53|KRAS|PIK3CA|PTEN|CD8|CD4|FOXP3|PD-?L1|TIM-?3|LAG-?3)\b",
    re.I,
)

BUCKET_PRIORITY: dict[str, float] = {
    "lab": 1.0,
    "research": 0.95,
    "document_library": 0.88,
    "vault": 0.82,
    "file": 0.78,
    "notebook": 0.75,
    "wiki": 0.72,
    "project": 0.70,
    "people": 0.68,
}

INTENT_SCOPE_MAP: dict[str, tuple[str, ...]] = {
    "research_question": ("research", "lab", "file", "vault", "document_library", "notebook", "wiki"),
    "project_question": ("project", "file", "lab", "vault", "document_library", "notebook", "wiki", "research"),
    "protocol_question": ("lab", "vault", "file", "document_library", "notebook", "wiki"),
    "search_request": ("research", "lab", "file", "vault", "document_library", "notebook", "wiki"),
    "people_question": ("people", "lab", "wiki"),
}


@dataclass(frozen=True)
class SearchPlan:
    scopes: tuple[str, ...]
    prioritize_buckets: tuple[str, ...]
    retrieval_mode: str
    require_citations: bool
    rationale: str


@dataclass(frozen=True)
class QueryUnderstanding:
    raw_query: str
    normalized_query: str
    intent_decision: IntentDecision
    domains: tuple[str, ...]
    entities: tuple[str, ...]
    query_terms: tuple[str, ...]
    search_plan: SearchPlan


@dataclass(frozen=True)
class EvidenceItem:
    index: int
    title: str
    source_type: str
    bucket: str
    snippet: str
    score: float
    doi: str | None = None
    pmid: str | None = None
    source_url: str | None = None
    chunk_id: str | None = None
    corroboration_count: int = 0


@dataclass(frozen=True)
class ClaimValidation:
    claim: str
    status: ClaimStatus
    supporting_indices: tuple[int, ...]
    conflicting_indices: tuple[int, ...] = ()
    note: str = ""


@dataclass
class EvidencePackage:
    items: list[EvidenceItem] = field(default_factory=list)
    by_bucket: dict[str, int] = field(default_factory=dict)
    confidence: ConfidenceLevel = "insufficient"
    validation_notes: list[str] = field(default_factory=list)
    cross_source_summary: str = ""
    claim_validations: list[ClaimValidation] = field(default_factory=list)


def extract_domains(message: str) -> tuple[str, ...]:
    text = message or ""
    return tuple(domain for domain, pattern in DOMAIN_PATTERNS.items() if pattern.search(text))


def extract_entities(message: str) -> tuple[str, ...]:
    text = message or ""
    entities: list[str] = []
    for pattern in SCIENTIFIC_ACCESSION_PATTERNS:
        entities.extend(m.group(0) for m in pattern.finditer(text))
    entities.extend(m.group(0) for m in GENE_ENTITY_PATTERN.finditer(text))
    seen: set[str] = set()
    unique: list[str] = []
    for ent in entities:
        key = ent.upper()
        if key not in seen:
            seen.add(key)
            unique.append(ent)
    return tuple(unique)


def build_search_plan(intent_decision: IntentDecision, domains: tuple[str, ...], entities: tuple[str, ...]) -> SearchPlan:
    intent = intent_decision.intent
    default_scopes = INTENT_SCOPE_MAP.get(intent, ("lab", "file", "vault", "notebook", "wiki", "research", "people"))

    prioritize: list[str] = []
    if "literature_datasets" in domains or intent == "search_request":
        prioritize.extend(["research", "lab"])
    if "protocols_pipelines" in domains or intent == "protocol_question":
        prioritize.extend(["lab", "document_library", "vault"])
    if intent == "project_question":
        prioritize.extend(["project", "file", "lab", "research"])
    if "hgsc_immunology" in domains or "clinical_translational" in domains:
        prioritize.extend(["research", "lab", "project"])
    if intent == "people_question":
        prioritize.append("people")
    if not prioritize:
        prioritize = list(default_scopes[:3])

    rationale_parts = [f"intent={intent}"]
    if domains:
        rationale_parts.append(f"domains={','.join(domains)}")
    if entities:
        rationale_parts.append(f"entities={','.join(entities[:5])}")

    return SearchPlan(
        scopes=default_scopes,
        prioritize_buckets=tuple(dict.fromkeys(prioritize)),
        retrieval_mode="hybrid",
        require_citations=intent_decision.require_citations,
        rationale="; ".join(rationale_parts),
    )


def understand_query(message: str, intent_decision: IntentDecision) -> QueryUnderstanding:
    normalized = normalize_query(message)
    domains = extract_domains(message)
    entities = extract_entities(message)
    terms = tuple(tokenize_query(normalized))
    plan = build_search_plan(intent_decision, domains, entities)
    return QueryUnderstanding(
        raw_query=message,
        normalized_query=normalized,
        intent_decision=intent_decision,
        domains=domains,
        entities=entities,
        query_terms=terms,
        search_plan=plan,
    )


def _hit_to_dict(hit: Any) -> dict[str, Any]:
    if hasattr(hit, "model_dump"):
        return hit.model_dump()
    if isinstance(hit, dict):
        return hit
    return {
        "title": getattr(hit, "title", "Untitled"),
        "source_type": getattr(hit, "source_type", None) or getattr(hit, "bucket", "unknown"),
        "bucket": getattr(hit, "bucket", "unknown"),
        "snippet": getattr(hit, "snippet", "") or getattr(hit, "text_preview", ""),
        "score": float(getattr(hit, "score", 0.0) or 0.0),
        "id": getattr(hit, "id", None),
        "metadata": getattr(hit, "metadata", None) or {},
    }


def _entity_overlap(snippet: str, entities: tuple[str, ...]) -> int:
    if not entities:
        return 0
    lower = (snippet or "").lower()
    return sum(1 for ent in entities if ent.lower() in lower)


def rank_evidence_items(items: list[EvidenceItem], *, entities: tuple[str, ...] = ()) -> list[EvidenceItem]:
    """Re-rank by bucket priority, base score, and entity corroboration."""
    scored: list[tuple[float, EvidenceItem]] = []
    for item in items:
        bucket_boost = BUCKET_PRIORITY.get(item.bucket, 0.65)
        entity_boost = _entity_overlap(item.snippet, entities) * 0.05
        composite = item.score * bucket_boost + entity_boost + (item.corroboration_count * 0.02)
        scored.append((composite, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    reranked: list[EvidenceItem] = []
    for new_index, (_, item) in enumerate(scored, start=1):
        reranked.append(
            EvidenceItem(
                index=new_index,
                title=item.title,
                source_type=item.source_type,
                bucket=item.bucket,
                snippet=item.snippet,
                score=item.score,
                doi=item.doi,
                pmid=item.pmid,
                source_url=item.source_url,
                chunk_id=item.chunk_id,
                corroboration_count=item.corroboration_count,
            )
        )
    return reranked


def _corroboration_counts(items: list[EvidenceItem], entities: tuple[str, ...]) -> list[EvidenceItem]:
    if not entities:
        return items
    updated: list[EvidenceItem] = []
    for item in items:
        count = sum(
            1
            for other in items
            if other.index != item.index
            and _entity_overlap(other.snippet, entities) > 0
            and _entity_overlap(item.snippet, entities) > 0
        )
        updated.append(
            EvidenceItem(
                index=item.index,
                title=item.title,
                source_type=item.source_type,
                bucket=item.bucket,
                snippet=item.snippet,
                score=item.score,
                doi=item.doi,
                pmid=item.pmid,
                source_url=item.source_url,
                chunk_id=item.chunk_id,
                corroboration_count=count,
            )
        )
    return updated


def _sentence_polarity(sentence: str) -> str:
    text = sentence or ""
    if re.search(r"\bnot\s+associated\b|\bno\s+association\b", text, re.I):
        return "negative"
    pos = bool(POSITIVE_CLAIM_RE.search(text))
    neg = bool(NEGATIVE_CLAIM_RE.search(text))
    if pos and neg:
        return "mixed"
    if pos:
        return "positive"
    if neg:
        return "negative"
    return "neutral"


def _extract_claim_sentences(snippet: str, entities: tuple[str, ...]) -> list[str]:
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(snippet or "") if s.strip()]
    if not entities:
        return [s for s in sentences if len(s) >= 40][:2]
    matched = [s for s in sentences if any(ent.lower() in s.lower() for ent in entities)]
    return matched[:3] if matched else sentences[:2]


def validate_claims_across_sources(
    items: list[EvidenceItem],
    entities: tuple[str, ...],
    *,
    max_claims: int = 8,
) -> list[ClaimValidation]:
    """Cross-source claim validation via entity overlap and polarity heuristics."""
    if not items:
        return []

    claim_map: dict[str, dict[str, Any]] = {}

    for item in items:
        for sentence in _extract_claim_sentences(item.snippet, entities):
            key_entities = tuple(
                ent for ent in entities if ent.lower() in sentence.lower()
            ) or (sentence[:48].lower(),)
            key = "|".join(sorted(e.lower() for e in key_entities))
            entry = claim_map.setdefault(
                key,
                {
                    "claim": sentence[:220],
                    "by_index": {},
                    "polarities": {},
                    "buckets": set(),
                },
            )
            entry["by_index"][item.index] = item.bucket
            entry["polarities"][item.index] = _sentence_polarity(sentence)
            entry["buckets"].add(item.bucket)

    validations: list[ClaimValidation] = []
    for entry in claim_map.values():
        indices = tuple(sorted(entry["by_index"].keys()))
        polarities = {entry["polarities"][idx] for idx in indices}
        buckets = entry["buckets"]
        claim = entry["claim"]

        per_index = {idx: entry["polarities"][idx] for idx in indices}
        has_positive = any(p == "positive" for p in per_index.values())
        has_negative = any(p == "negative" for p in per_index.values())

        if len(indices) >= 2 and len(buckets) >= 2:
            if has_positive and has_negative:
                validations.append(
                    ClaimValidation(
                        claim=claim,
                        status="conflicting",
                        supporting_indices=indices,
                        conflicting_indices=indices,
                        note="Sources disagree on directionality or association for this claim.",
                    )
                )
                continue
            if "mixed" in polarities:
                validations.append(
                    ClaimValidation(
                        claim=claim,
                        status="uncertain",
                        supporting_indices=indices,
                        note="Mixed polarity language across sources — interpret cautiously.",
                    )
                )
                continue
            validations.append(
                ClaimValidation(
                    claim=claim,
                    status="corroborated",
                    supporting_indices=indices,
                    note=f"Corroborated across {len(buckets)} source classes.",
                )
            )
        elif len(indices) == 1:
            validations.append(
                ClaimValidation(
                    claim=claim,
                    status="single_source",
                    supporting_indices=indices,
                    note="Supported by a single retrieved source only.",
                )
            )
        else:
            validations.append(
                ClaimValidation(
                    claim=claim,
                    status="uncertain",
                    supporting_indices=indices,
                    note="Weak or ambiguous support in retrieved excerpts.",
                )
            )

    status_rank = {"conflicting": 0, "uncertain": 1, "single_source": 2, "corroborated": 3}
    validations.sort(key=lambda row: (status_rank.get(row.status, 9), -len(row.supporting_indices)))
    return validations[:max_claims]


def parse_orchestrator_sections(answer: str) -> list[dict[str, str]]:
    """Parse orchestrator-formatted answers into UI sections."""
    text = (answer or "").strip()
    if not text:
        return []

    lines = text.splitlines()
    sections: list[dict[str, str]] = []
    current_id = "preamble"
    current_label = "Overview"
    buffer: list[str] = []

    def _flush() -> None:
        body = "\n".join(buffer).strip()
        if body or current_id != "preamble":
            sections.append({"id": current_id, "label": current_label, "body": body})

    def _match_section(line: str) -> tuple[str, str] | None:
        trimmed = line.strip()
        if not trimmed:
            return None
        header_match = SECTION_HEADER_RE.match(trimmed)
        if not header_match:
            return None
        header_text = re.sub(r"^\d+\.\s*", "", header_match.group(1)).strip("* ").strip(" :")
        for section_id, pattern in ORCHESTRATOR_SECTION_ORDER:
            if re.search(pattern, header_text, re.I):
                return section_id, header_text or section_id.replace("_", " ").title()
        return None

    for line in lines:
        matched = _match_section(line)
        if matched:
            _flush()
            buffer = []
            current_id, current_label = matched
            continue
        buffer.append(line)

    _flush()
    if len(sections) == 1 and sections[0]["id"] == "preamble":
        return []
    return [s for s in sections if s.get("body")]


def _assess_confidence(
    items: list[EvidenceItem],
    entities: tuple[str, ...],
    claim_validations: list[ClaimValidation] | None = None,
) -> tuple[ConfidenceLevel, list[str], str]:
    notes: list[str] = []
    if not items:
        return "insufficient", ["No evidence items retrieved."], "No cross-source validation possible."

    buckets = {item.bucket for item in items}
    high_score = sum(1 for item in items if item.score >= 0.5)
    corroborated = sum(1 for item in items if item.corroboration_count > 0)

    if len(buckets) >= 2 and high_score >= 2:
        confidence: ConfidenceLevel = "high"
        notes.append(f"Evidence spans {len(buckets)} source classes with {high_score} high-relevance hits.")
    elif len(items) >= 2 and (high_score >= 1 or corroborated >= 1):
        confidence = "medium"
        notes.append("Moderate evidence — multiple sources but limited corroboration or score spread.")
    elif len(items) >= 1:
        confidence = "low"
        notes.append("Thin evidence — single or low-scoring sources; treat claims cautiously.")
    else:
        confidence = "insufficient"

    if entities and corroborated == 0:
        notes.append(f"Query entities ({', '.join(entities[:3])}) not corroborated across multiple sources.")

    conflicts = [v for v in (claim_validations or []) if v.status == "conflicting"]
    if conflicts:
        notes.append(f"{len(conflicts)} cross-source claim conflict(s) detected — see claim validation.")
        if confidence == "high":
            confidence = "medium"
        elif confidence == "medium":
            confidence = "low"

    cross_summary = (
        f"{len(items)} sources across {len(buckets)} buckets "
        f"({', '.join(sorted(buckets))}); {corroborated} with entity corroboration."
    )
    return confidence, notes, cross_summary


def package_evidence(
    unified_hits: list[Any],
    rag_sources: list[dict[str, Any]],
    *,
    entities: tuple[str, ...] = (),
    limit: int = 12,
) -> EvidencePackage:
    """Build structured evidence package from retrieval hits."""
    raw_items: list[EvidenceItem] = []
    seen_ids: set[str] = set()

    for hit in unified_hits:
        data = _hit_to_dict(hit)
        cid = str(data.get("id") or data.get("chunk_id") or "")
        if cid and cid in seen_ids:
            continue
        if cid:
            seen_ids.add(cid)
        meta = data.get("metadata") or {}
        raw_items.append(
            EvidenceItem(
                index=0,
                title=data.get("title") or "Untitled",
                source_type=data.get("source_type") or data.get("bucket") or "unknown",
                bucket=data.get("bucket") or "unknown",
                snippet=(data.get("snippet") or "")[:600],
                score=float(data.get("score") or 0.0),
                doi=meta.get("doi"),
                pmid=meta.get("pmid"),
                source_url=meta.get("source_url"),
                chunk_id=cid or None,
            )
        )

    for src in rag_sources:
        cid = str(src.get("chunk_id") or "")
        if cid and cid in seen_ids:
            continue
        if cid:
            seen_ids.add(cid)
        raw_items.append(
            EvidenceItem(
                index=0,
                title=src.get("title") or "Untitled",
                source_type=src.get("source_type") or "lab",
                bucket=src.get("bucket") or "lab",
                snippet=(src.get("text_preview") or "")[:600],
                score=float(src.get("score") or 0.0),
                chunk_id=cid or None,
            )
        )

    raw_items = raw_items[:limit]
    corroborated = _corroboration_counts(raw_items, entities)
    ranked = rank_evidence_items(corroborated, entities=entities)

    by_bucket: dict[str, int] = {}
    for item in ranked:
        by_bucket[item.bucket] = by_bucket.get(item.bucket, 0) + 1

    claim_validations = validate_claims_across_sources(ranked, entities)
    confidence, notes, cross_summary = _assess_confidence(ranked, entities, claim_validations)
    return EvidencePackage(
        items=ranked,
        by_bucket=by_bucket,
        confidence=confidence,
        validation_notes=notes,
        cross_source_summary=cross_summary,
        claim_validations=claim_validations,
    )


def evidence_items_to_grounding_hits(package: EvidencePackage) -> list[dict[str, Any]]:
    return [
        {
            "title": item.title,
            "source_type": item.source_type,
            "source_url": item.source_url,
            "doi": item.doi,
            "pmid": item.pmid,
            "snippet": item.snippet,
        }
        for item in package.items
    ]


def format_evidence_package_block(package: EvidencePackage) -> str:
    lines = [
        "=== STRUCTURED EVIDENCE PACKAGE ===",
        f"Confidence assessment: {package.confidence}",
        f"Cross-source: {package.cross_source_summary}",
    ]
    if package.validation_notes:
        lines.append("Validation notes: " + "; ".join(package.validation_notes))
    if package.claim_validations:
        lines.append("Claim validation:")
        for claim in package.claim_validations[:6]:
            refs = ", ".join(f"[{idx}]" for idx in claim.supporting_indices)
            conflict = (
                f" vs conflict {', '.join(f'[{i}]' for i in claim.conflicting_indices)}"
                if claim.conflicting_indices
                else ""
            )
            lines.append(f"  - ({claim.status}) {claim.claim[:160]} — {refs}{conflict}")
    lines.append("")
    for item in package.items:
        id_bits = []
        if item.doi:
            id_bits.append(f"DOI: {item.doi}")
        if item.pmid:
            id_bits.append(f"PMID: {item.pmid}")
        if item.source_url:
            id_bits.append(f"URL: {item.source_url}")
        id_line = " | ".join(id_bits)
        lines.append(
            f"[{item.index}] {item.title}\n"
            f"  Type: {item.source_type} | Bucket: {item.bucket} | Score: {item.score:.3f}"
            + (f" | Corroboration: {item.corroboration_count}" if item.corroboration_count else "")
            + (f"\n  {id_line}" if id_line else "")
            + f"\n  Excerpt: {item.snippet}\n"
        )
    return "\n".join(lines)


def build_orchestrator_system_prompt(
    understanding: QueryUnderstanding,
    package: EvidencePackage | None = None,
    *,
    user_name: str = "",
    lang: str | None = None,
    answer_style: str | None = None,
) -> str:
    """Compose system prompt from master orchestrator principles + intent context."""
    parts = [ORCHESTRATOR_CORE_PROMPT]

    if user_name:
        parts.append(f"The researcher's name is {user_name}.")
    if lang == "fi":
        parts.append("Reply in Finnish; keep DOIs, PMIDs, and accession IDs in original form.")

    parts.append(
        f"Query understanding: intent={understanding.intent_decision.intent}, "
        f"domains={','.join(understanding.domains) or 'general'}, "
        f"entities={','.join(understanding.entities) or 'none'}."
    )
    parts.append(f"Search plan: {understanding.search_plan.rationale}")

    style = answer_style or understanding.intent_decision.answer_style
    if style == "search_summary":
        parts.append("Prioritize a concise evidence synthesis over step-by-step protocol detail.")
    elif style == "practical_with_sources":
        parts.append("Focus on actionable protocol steps grounded in cited sources.")
    elif style in {"brief_conversational", "natural", "helpful_steps", "technical"}:
        parts.append("Keep the structured sections compact — this is a lighter conversational turn.")

    if package and package.confidence in {"low", "insufficient"}:
        parts.append(
            "Evidence is thin — lead with uncertainty, avoid strong claims, and suggest what to search or ingest next."
        )

    return "\n\n".join(parts)


def build_orchestrator_user_prompt(
    question: str,
    package: EvidencePackage,
    *,
    db_block: str = "",
    clinical_block: str = "",
) -> str:
    """User message with structured evidence package and synthesis instructions."""
    sections = []
    if db_block:
        sections.append(db_block.rstrip())
    if clinical_block:
        sections.append(clinical_block.rstrip())
    sections.append(format_evidence_package_block(package))
    sections.append(
        f"Question: {question}\n\n"
        "Synthesize an answer using ONLY the evidence package above. "
        "Follow the response structure (executive summary, evidence, methods, limitations & confidence, references). "
        "Use [n] citation markers matching package indices. "
        "Do not invent sources or identifiers."
    )
    return "\n\n".join(sections)


def orchestrator_metadata(
    understanding: QueryUnderstanding,
    package: EvidencePackage | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "evidence_orchestrator": True,
        "query_domains": list(understanding.domains),
        "query_entities": list(understanding.entities),
        "search_plan": {
            "scopes": list(understanding.search_plan.scopes),
            "prioritize_buckets": list(understanding.search_plan.prioritize_buckets),
            "retrieval_mode": understanding.search_plan.retrieval_mode,
            "rationale": understanding.search_plan.rationale,
        },
    }
    if package:
        meta["evidence_confidence"] = package.confidence
        meta["evidence_buckets"] = package.by_bucket
        meta["evidence_count"] = len(package.items)
        meta["cross_source_summary"] = package.cross_source_summary
        if package.validation_notes:
            meta["evidence_validation_notes"] = package.validation_notes
        if package.claim_validations:
            meta["claim_validations"] = [
                {
                    "claim": row.claim,
                    "status": row.status,
                    "supporting_indices": list(row.supporting_indices),
                    "conflicting_indices": list(row.conflicting_indices),
                    "note": row.note,
                }
                for row in package.claim_validations
            ]
    return meta


def orchestrator_answer_metadata(answer: str) -> dict[str, Any]:
    """Structured section parse for chat UI rendering."""
    sections = parse_orchestrator_sections(answer)
    if not sections:
        return {}
    return {"response_sections": sections}


def should_use_orchestrator(intent_decision: IntentDecision) -> bool:
    """Use evidence orchestrator prompts for RAG-grounded synthesis."""
    return intent_decision.use_rag and intent_decision.answer_style not in {
        "safety",
        "brief_conversational",
        "natural",
    }
