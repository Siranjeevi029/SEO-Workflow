"""Shared pipeline state passed between LangGraph nodes."""
from __future__ import annotations

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    # inputs
    topic: str
    target_keyword: str
    audience: str
    tone: str

    # runtime
    run_id: str

    # keyword_research
    keywords: list[dict[str, Any]]        # [{keyword, intent, note}]

    # serp_analysis
    serp: list[dict[str, Any]]            # top hits w/ scraped stats
    serp_insights: dict[str, Any]         # avg word count, common headings, gaps

    # brief
    brief: dict[str, Any]

    # outline
    outline: str

    # writer / editor
    draft: str
    edited: str

    # seo_optimizer
    seo: dict[str, Any]                   # score, checks, suggestions

    # meta_schema
    meta: dict[str, Any]                  # title tag, meta desc, JSON-LD

    # final
    article: str
    errors: list[str]
