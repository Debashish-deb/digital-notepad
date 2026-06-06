from __future__ import annotations

import logging
import os
import time
from typing import Any
from urllib.parse import quote_plus

import requests

LOGGER = logging.getLogger(__name__)

PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
CROSSREF_WORKS = "https://api.crossref.org/works"

PUBMED_DELAY_SECONDS = float(os.getenv("RESEARCH_KB_PUBMED_DELAY_SECONDS", "0.4"))
PUBMED_MAX_RETRIES = int(os.getenv("RESEARCH_KB_PUBMED_MAX_RETRIES", "4"))


def _request_with_retry(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 20.0,
    max_retries: int = PUBMED_MAX_RETRIES,
) -> requests.Response:
    last_response: requests.Response | None = None
    for attempt in range(max_retries):
        response = requests.get(url, params=params, timeout=timeout)
        last_response = response
        if response.status_code == 429:
            wait = min(2 ** attempt, 30.0)
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = max(wait, float(retry_after))
                except ValueError:
                    pass
            LOGGER.warning(
                "Rate limited on %s; sleeping %.1fs (attempt %d/%d)",
                url,
                wait,
                attempt + 1,
                max_retries,
            )
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response
    if last_response is not None:
        last_response.raise_for_status()
    raise RuntimeError(f"Request failed for {url}")


def search_pubmed(query: str, retmax: int = 20) -> list[str]:
    params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax}
    response = _request_with_retry(PUBMED_ESEARCH, params=params)
    return response.json().get("esearchresult", {}).get("idlist", [])


def summarize_pubmed(pmids: list[str]) -> list[dict[str, Any]]:
    if not pmids:
        return []
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
    response = _request_with_retry(PUBMED_ESUMMARY, params=params)
    data = response.json().get("result", {})
    results = []
    for pmid in pmids:
        record = data.get(str(pmid))
        if not isinstance(record, dict):
            continue
        article_ids = record.get("articleids") or []
        doi = None
        for aid in article_ids:
            if aid.get("idtype") == "doi":
                doi = aid.get("value")
        results.append({
            "pmid": str(pmid),
            "title": record.get("title") or "",
            "journal": record.get("fulljournalname") or record.get("source"),
            "publication_year": int(str(record.get("pubdate") or "")[:4] or 0) or None,
            "authors": record.get("authors") or [],
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "metadata": record,
        })
    return results


def search_crossref(query: str, rows: int = 20) -> list[dict[str, Any]]:
    params = {"query.bibliographic": query, "rows": rows, "select": "DOI,title,author,container-title,published-print,published-online,URL,abstract"}
    response = requests.get(CROSSREF_WORKS, params=params, timeout=20)
    response.raise_for_status()
    items = response.json().get("message", {}).get("items", [])
    out = []
    for item in items:
        title = " ".join(item.get("title") or [])
        journal = " ".join(item.get("container-title") or [])
        year = None
        for key in ("published-print", "published-online"):
            parts = item.get(key, {}).get("date-parts") or []
            if parts and parts[0]:
                year = parts[0][0]
                break
        out.append({
            "doi": item.get("DOI"),
            "title": title,
            "journal": journal,
            "publication_year": year,
            "authors": item.get("author") or [],
            "abstract": item.get("abstract"),
            "url": item.get("URL"),
            "metadata": item,
        })
    return out


def discover_priority_publications() -> list[dict[str, Any]]:
    queries = [
        "Anniina Färkkilä ovarian cancer spatial biology",
        "Färkkilä MHC class II high-grade serous ovarian cancer",
        "Färkkilä tertiary lymphoid structures ovarian cancer",
        "Färkkilä CyCIF ovarian cancer",
    ]
    seen = set()
    records: list[dict[str, Any]] = []
    for index, query in enumerate(queries):
        if index:
            time.sleep(PUBMED_DELAY_SECONDS)
        try:
            pmids = search_pubmed(query, retmax=10)
            if pmids:
                time.sleep(PUBMED_DELAY_SECONDS)
            for rec in summarize_pubmed(pmids):
                key = rec.get("doi") or rec.get("pmid") or rec.get("title")
                if key and key not in seen:
                    seen.add(key)
                    rec["discovery_query"] = query
                    records.append(rec)
        except Exception as exc:
            LOGGER.warning("PubMed query failed for %s: %s", query, exc)
    return records
