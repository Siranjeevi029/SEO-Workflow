"""DuckDuckGo + httpx — FULLY FREE fallback search/scrape (no key at all).

Used automatically when FIRECRAWL_API_KEY is empty, so the prototype runs with
zero paid services. Lower quality than Firecrawl (no JS render, rough markdown)
but proves the pipeline end-to-end for free.
"""
from __future__ import annotations

import re

import httpx

from app.search.base import ScrapedPage, SearchClient, SearchHit

_UA = "Mozilla/5.0 (compatible; seo-content-workflow-bot/0.1)"


def _html_to_text(html: str) -> tuple[str, list[str]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])][:30]
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))
    return text, headings


class DDGClient(SearchClient):
    name = "duckduckgo"

    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        from duckduckgo_search import DDGS

        hits: list[SearchHit] = []
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=limit)):
                hits.append(SearchHit(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    position=i + 1,
                ))
        return hits

    def scrape(self, url: str) -> ScrapedPage:
        try:
            resp = httpx.get(url, headers={"User-Agent": _UA},
                             timeout=20, follow_redirects=True)
            text, headings = _html_to_text(resp.text)
        except Exception:
            text, headings = "", []
        title = headings[0] if headings else url
        return ScrapedPage(url=url, title=title, markdown=text,
                           word_count=len(text.split()), headings=headings)
