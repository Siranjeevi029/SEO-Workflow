"""Search provider selection — Firecrawl if keyed, else free DuckDuckGo."""
from __future__ import annotations

from app.config import Settings, get_settings
from app.search.base import SearchClient


def get_search(settings: Settings | None = None) -> SearchClient:
    s = settings or get_settings()
    if s.has_firecrawl:
        from app.search.firecrawl_client import FirecrawlClient
        return FirecrawlClient(api_key=s.firecrawl_api_key)
    from app.search.ddg_client import DDGClient
    return DDGClient()
