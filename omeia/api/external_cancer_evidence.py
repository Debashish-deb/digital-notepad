"""External cancer evidence connectors — retrieval sources only (Layer 1 + 3)."""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from omeia.api.platform_flags import external_cancer_evidence_enabled
from omeia.api.search_models import SearchHit, SearchNavAction

LOGGER = logging.getLogger(__name__)

_EUROPE_PMC = re.compile(r"https://www\.ebi\.ac\.uk/europepmc/webservices/rest/search")


def search_europe_pmc(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Metadata-only Europe PMC search (no full-text storage)."""
    if not query.strip():
        return []
    try:
        import httpx

        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        params = {"query": query, "format": "json", "pageSize": min(limit, 10), "resultType": "core"}
        with httpx.Client(timeout=12.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        results = []
        for row in (data.get("resultList") or {}).get("result") or []:
            results.append({
                "title": row.get("title") or "Publication",
                "source_type": "external_literature",
                "pmid": row.get("pmid"),
                "doi": row.get("doi"),
                "journal": row.get("journalTitle"),
                "year": row.get("pubYear"),
                "snippet": (row.get("abstractText") or "")[:500],
                "url": f"https://europepmc.org/article/MED/{row.get('pmid')}" if row.get("pmid") else None,
                "connector": "europe_pmc",
            })
        return results
    except Exception as exc:
        LOGGER.warning("Europe PMC connector failed: %s", exc)
        return []


def external_hits_for_query(query: str, *, limit: int = 4) -> list[SearchHit]:
    if not external_cancer_evidence_enabled():
        return []

    enabled = (os.getenv("OMEIA_EXTERNAL_CONNECTORS", "europe_pmc") or "europe_pmc").split(",")
    hits: list[SearchHit] = []
    if "europe_pmc" in [c.strip() for c in enabled]:
        for idx, row in enumerate(search_europe_pmc(query, limit=limit)):
            hits.append(SearchHit(
                id=f"external:europe_pmc:{row.get('pmid') or row.get('doi') or idx}",
                bucket="research",
                title=row.get("title") or "External publication",
                snippet=row.get("snippet") or "",
                score=0.55 - idx * 0.03,
                rank=idx + 1,
                source="external_cancer_evidence",
                source_type="external_literature",
                metadata={
                    **row,
                    "evidence_tier": "external",
                    "connector": row.get("connector"),
                },
                nav=SearchNavAction(
                    action="open_external_url",
                    label="Open publication",
                    payload={"url": row.get("url")},
                ) if row.get("url") else None,
            ))
    return hits[:limit]


def merge_external_into_hits(query: str, base_hits: list[SearchHit], *, limit: int = 3) -> list[SearchHit]:
    """Append external metadata hits after internal evidence."""
    external = external_hits_for_query(query, limit=limit)
    if not external:
        return base_hits
    seen = {h.id for h in base_hits}
    merged = list(base_hits)
    for hit in external:
        if hit.id in seen:
            continue
        merged.append(hit)
        seen.add(hit.id)
    for idx, hit in enumerate(merged):
        hit.rank = idx + 1
    return merged
