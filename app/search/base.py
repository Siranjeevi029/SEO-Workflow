"""Search/scrape abstraction. Pipeline depends on this, not on a vendor."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str = ""
    position: int = 0


@dataclass
class ScrapedPage:
    url: str
    title: str = ""
    markdown: str = ""
    word_count: int = 0
    headings: list[str] = field(default_factory=list)


class SearchClient(ABC):
    name: str = "base"

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        ...

    @abstractmethod
    def scrape(self, url: str) -> ScrapedPage:
        ...
