"""Firecrawl search/scrape — DEMO provider.

Why Firecrawl for the demo: has a free tier, returns clean LLM-ready markdown
(handles JS-rendered SPAs), and one key covers both SERP search and page scrape.
Serper was rejected (403 on the free key + no scrape). Prod keeps Firecrawl but
on a paid plan, or swaps to Bright Data for very high volume — see docs.
"""
from __future__ import annotations

import re

from app.search.base import ScrapedPage, SearchClient, SearchHit


def _headings(md: str) -> list[str]:
    return [h.strip() for h in re.findall(r"^#{1,3}\s+(.+)$", md, flags=re.M)][:30]


class FirecrawlClient(SearchClient):
    name = "firecrawl"

    def __init__(self, api_key: str):
        from firecrawl import FirecrawlApp  # lazy import

        self._app = FirecrawlApp(api_key=api_key)

    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        # firecrawl-py v4: returns SearchData(web=[SearchResultWeb(...)])
        res = self._app.search(query, limit=limit)
        web = getattr(res, "web", None) or []
        hits: list[SearchHit] = []
        for i, item in enumerate(web):
            hits.append(SearchHit(
                title=getattr(item, "title", "") or "",
                url=getattr(item, "url", "") or "",
                snippet=getattr(item, "description", "") or "",
                position=i + 1,
            ))
        return hits

    def scrape(self, url: str) -> ScrapedPage:
        # firecrawl-py v4: returns Document(markdown=..., metadata=DocumentMetadata)
        # Some sites (reddit, paywalls) are unsupported — degrade gracefully so
        # one bad SERP result never kills the pipeline.
        try:
            doc = self._app.scrape(url, formats=["markdown"])
        except Exception:
            return ScrapedPage(url=url, title="", markdown="", word_count=0,
                               headings=[])
        md = getattr(doc, "markdown", "") or ""
        meta = getattr(doc, "metadata", None)
        title = getattr(meta, "title", "") if meta else ""
        return ScrapedPage(
            url=url,
            title=title or "",
            markdown=md,
            word_count=len(md.split()),
            headings=_headings(md),
        )
