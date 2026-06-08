from __future__ import annotations

import json
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)

PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CROSSREF_WORKS = "https://api.crossref.org/works"

PUBMED_DELAY_SECONDS = float(os.getenv("RESEARCH_KB_PUBMED_DELAY_SECONDS", "0.4"))
PUBMED_MAX_RETRIES = int(os.getenv("RESEARCH_KB_PUBMED_MAX_RETRIES", "4"))
PUBMED_RETMAX = int(os.getenv("RESEARCH_KB_PUBMED_RETMAX", "25"))
MAX_PUBLICATION_QUERIES = int(os.getenv("RESEARCH_KB_MAX_PUBLICATION_QUERIES", "25"))
ENABLE_PUBMED = os.getenv("RESEARCH_KB_ENABLE_PUBMED", "true").lower() in {"1", "true", "yes"}
ENABLE_CROSSREF = os.getenv("RESEARCH_KB_ENABLE_CROSSREF", "true").lower() in {"1", "true", "yes"}

CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs" / "research_knowledge"

LAB_QUERIES = [
    "Anniina Färkkilä ovarian cancer spatial biology",
    "Färkkilä MHC class II high-grade serous ovarian cancer",
    "Färkkilä tertiary lymphoid structures ovarian cancer",
    "Färkkilä CyCIF ovarian cancer",
    "Farkkila HGSC spatial transcriptomics",
    "Farkkila ONCOSYS ovarian cancer",
]


def _ncbi_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = dict(extra or {})
    tool = os.getenv("RESEARCH_KB_NCBI_TOOL", "OMEIAResearchKB").strip()
    email = (
        os.getenv("RESEARCH_KB_NCBI_EMAIL")
        or os.getenv("NCBI_EMAIL")
        or os.getenv("PUBMED_EMAIL")
        or ""
    ).strip()
    if tool:
        params.setdefault("tool", tool)
    if email:
        params.setdefault("email", email)
    return params


def _crossref_mailto() -> str:
    return (
        os.getenv("RESEARCH_KB_CROSSREF_MAILTO")
        or os.getenv("RESEARCH_KB_NCBI_EMAIL")
        or os.getenv("NCBI_EMAIL")
        or "research-kb@omeia.local"
    ).strip()


def _request_with_retry(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 20.0,
    max_retries: int = PUBMED_MAX_RETRIES,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    last_response: requests.Response | None = None
    for attempt in range(max_retries):
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
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


def search_pubmed(query: str, retmax: int = PUBMED_RETMAX) -> list[str]:
    params = _ncbi_params({"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax})
    response = _request_with_retry(PUBMED_ESEARCH, params=params)
    return response.json().get("esearchresult", {}).get("idlist", [])


def fetch_pubmed_abstracts(pmids: list[str]) -> dict[str, str]:
    """Fetch abstracts via PubMed efetch (metadata only; respects copyright policy)."""
    abstracts: dict[str, str] = {}
    if not pmids:
        return abstracts
    batch_size = 80
    for offset in range(0, len(pmids), batch_size):
        batch = pmids[offset : offset + batch_size]
        params = _ncbi_params(
            {"db": "pubmed", "id": ",".join(batch), "retmode": "xml", "rettype": "abstract"}
        )
        response = _request_with_retry(PUBMED_EFETCH, params=params, timeout=45.0)
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            LOGGER.warning("PubMed efetch XML parse failed: %s", exc)
            continue
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            if pmid_el is None or not pmid_el.text:
                continue
            pmid = pmid_el.text.strip()
            parts: list[str] = []
            for abs_text in article.findall(".//AbstractText"):
                label = abs_text.get("Label")
                text = " ".join("".join(abs_text.itertext()).split())
                if not text:
                    continue
                parts.append(f"{label}: {text}" if label else text)
            if parts:
                abstracts[pmid] = " ".join(parts)
        if offset + batch_size < len(pmids):
            time.sleep(PUBMED_DELAY_SECONDS)
    return abstracts


def summarize_pubmed(pmids: list[str]) -> list[dict[str, Any]]:
    if not pmids:
        return []
    params = _ncbi_params({"db": "pubmed", "id": ",".join(pmids), "retmode": "json"})
    response = _request_with_retry(PUBMED_ESUMMARY, params=params)
    data = response.json().get("result", {})
    abstract_map = fetch_pubmed_abstracts(pmids)
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
            "abstract": abstract_map.get(str(pmid)),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "metadata": record,
        })
    return results


def search_crossref(query: str, rows: int = 20) -> list[dict[str, Any]]:
    mailto = _crossref_mailto()
    params = {
        "query.bibliographic": query,
        "rows": rows,
        "select": "DOI,title,author,container-title,published-print,published-online,URL,abstract",
        "mailto": mailto,
    }
    headers = {"User-Agent": f"OMEIAResearchKB/0.1 (mailto:{mailto})"}
    response = _request_with_retry(CROSSREF_WORKS, params=params, headers=headers)
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


def _record_key(rec: dict[str, Any]) -> str | None:
    doi = (rec.get("doi") or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    pmid = (rec.get("pmid") or "").strip()
    if pmid:
        return f"pmid:{pmid}"
    title = (rec.get("title") or "").strip().lower()
    return f"title:{title}" if title else None


def _load_discovery_queries() -> list[str]:
    queries: list[str] = list(LAB_QUERIES)
    seed_path = CONFIG_DIR / "seed_sources.json"
    if seed_path.is_file():
        try:
            data = json.loads(seed_path.read_text(encoding="utf-8"))
            for query in data.get("worldwide_research_queries") or []:
                q = str(query).strip()
                if q and q not in queries:
                    queries.append(q)
        except Exception as exc:
            LOGGER.warning("Failed to load seed_sources queries: %s", exc)
    return queries[:MAX_PUBLICATION_QUERIES]


def _seed_priority_pmids() -> list[str]:
    seed_path = CONFIG_DIR / "seed_sources.json"
    if not seed_path.is_file():
        return []
    pmids: list[str] = []
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        for item in data.get("priority_publications_and_datasets") or []:
            if (item.get("type") or "").startswith("publication"):
                url = str(item.get("url") or "")
                match = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url, re.I)
                if match:
                    pmids.append(match.group(1))
    except Exception as exc:
        LOGGER.warning("Failed to load seed PMIDs: %s", exc)
    return pmids


def discover_priority_publications() -> list[dict[str, Any]]:
    seen: set[str] = set()
    records: list[dict[str, Any]] = []

    def add_record(rec: dict[str, Any], *, discovery_query: str) -> None:
        key = _record_key(rec)
        if not key or key in seen:
            return
        seen.add(key)
        rec["discovery_query"] = discovery_query
        records.append(rec)

    if ENABLE_PUBMED:
        priority_pmids = _seed_priority_pmids()
        if priority_pmids:
            try:
                time.sleep(PUBMED_DELAY_SECONDS)
                for rec in summarize_pubmed(priority_pmids):
                    add_record(rec, discovery_query="seed_priority_pmids")
            except Exception as exc:
                LOGGER.warning("Seed PMID ingest failed: %s", exc)

        for index, query in enumerate(_load_discovery_queries()):
            if index:
                time.sleep(PUBMED_DELAY_SECONDS)
            try:
                pmids = search_pubmed(query, retmax=PUBMED_RETMAX)
                if pmids:
                    time.sleep(PUBMED_DELAY_SECONDS)
                for rec in summarize_pubmed(pmids):
                    add_record(rec, discovery_query=query)
            except Exception as exc:
                LOGGER.warning("PubMed query failed for %s: %s", query, exc)

    if ENABLE_CROSSREF:
        crossref_rows = min(PUBMED_RETMAX, 15)
        for index, query in enumerate(_load_discovery_queries()[:8]):
            if index:
                time.sleep(PUBMED_DELAY_SECONDS)
            try:
                for rec in search_crossref(query, rows=crossref_rows):
                    if not rec.get("title"):
                        continue
                    if not rec.get("url") and rec.get("doi"):
                        rec["url"] = f"https://doi.org/{rec['doi']}"
                    add_record(rec, discovery_query=f"crossref:{query}")
            except Exception as exc:
                LOGGER.warning("Crossref query failed for %s: %s", query, exc)

    LOGGER.info("Discovered %d priority publication records", len(records))
    return records
