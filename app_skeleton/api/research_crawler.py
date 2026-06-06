from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

PLAYWRIGHT_ENABLED = os.getenv("RESEARCH_KB_ENABLE_PLAYWRIGHT", "false").lower() in {"1", "true", "yes"}
MIN_USEFUL_TEXT_CHARS = 50

ALLOWED_HOSTS = {"www.farkkilab.org", "farkkilab.org"}
DEFAULT_HEADERS = {
    "User-Agent": "OMEIAResearchKnowledgeBot/0.1 (+research knowledge indexing; contact lab admin)"
}

@dataclass
class CrawledPage:
    url: str
    canonical_url: str
    title: str
    text: str
    links: list[str]
    checksum: str
    status_code: int


def canonicalize_url(url: str) -> str:
    url, _frag = urldefrag(url.strip())
    parsed = urlparse(url)
    return parsed._replace(query="").geturl().rstrip("/")


def is_allowed_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in ALLOWED_HOSTS


def _meta_content(soup: BeautifulSoup, *names: str) -> str:
    for name in names:
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        content = (tag.get("content") or "").strip() if tag else ""
        if content:
            return content
    return ""


def clean_html_to_text(html: str) -> tuple[str, str, list[str]]:
    soup = BeautifulSoup(html or "", "html.parser")

    noscript_chunks: list[str] = []
    for node in soup.find_all("noscript"):
        text = " ".join(node.get_text(" ", strip=True).split())
        if text:
            noscript_chunks.append(text)

    for tag in soup(["script", "style", "svg"]):
        tag.decompose()

    title = (soup.title.string if soup.title and soup.title.string else "").strip()
    og_title = _meta_content(soup, "og:title", "twitter:title")
    if not title and og_title:
        title = og_title

    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        links.append(href.strip())

    chunks: list[str] = []
    meta_desc = _meta_content(soup, "description", "og:description", "twitter:description")
    if meta_desc:
        chunks.append(meta_desc)
    for node in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = " ".join(node.get_text(" ", strip=True).split())
        if text:
            chunks.append(text)
    chunks.extend(noscript_chunks)

    body_text = "\n".join(chunks).strip()
    if not body_text and title:
        body_text = title
    return title, body_text, links


def _fetch_with_playwright(url: str, timeout: float = 15.0) -> str | None:
    if not PLAYWRIGHT_ENABLED:
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        LOGGER.warning("Playwright not installed; skipping JS render for %s", url)
        return None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            html = page.content()
            browser.close()
            return html
    except Exception as exc:
        LOGGER.warning("Playwright fetch failed for %s: %s", url, exc)
        return None


def fetch_page(url: str, timeout: float = 15.0) -> CrawledPage:
    if not is_allowed_url(url):
        raise ValueError(f"URL is not on allowlist: {url}")
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    title, text, links = clean_html_to_text(response.text)
    if len(text.strip()) < MIN_USEFUL_TEXT_CHARS:
        rendered = _fetch_with_playwright(url, timeout=timeout)
        if rendered:
            title2, text2, links2 = clean_html_to_text(rendered)
            if len(text2.strip()) > len(text.strip()):
                title, text, links = title2, text2, links2
    canonical = canonicalize_url(response.url or url)
    checksum = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    abs_links = []
    for href in links:
        abs_url = canonicalize_url(urljoin(canonical, href))
        if is_allowed_url(abs_url):
            abs_links.append(abs_url)
    return CrawledPage(
        url=url,
        canonical_url=canonical,
        title=title or canonical,
        text=text,
        links=sorted(set(abs_links)),
        checksum=checksum,
        status_code=response.status_code,
    )


def crawl_seed_urls(seed_urls: list[str], max_pages: int = 50, delay_seconds: float = 1.0) -> list[CrawledPage]:
    seen: set[str] = set()
    queue = [canonicalize_url(u) for u in seed_urls]
    pages: list[CrawledPage] = []

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in seen or not is_allowed_url(url):
            continue
        seen.add(url)
        try:
            page = fetch_page(url)
            pages.append(page)
            LOGGER.info("Crawled %s (%d chars)", url, len(page.text))
            for link in page.links:
                if link not in seen and len(pages) + len(queue) < max_pages * 2:
                    queue.append(link)
        except Exception as exc:
            LOGGER.warning("Failed to crawl %s: %s", url, exc)
        time.sleep(delay_seconds)
    return pages
