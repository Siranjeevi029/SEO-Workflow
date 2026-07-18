"""LangGraph wiring of the SEO content pipeline.

Linear DAG (each step feeds the next); the graph makes the flow explicit,
resumable, and easy to visualize. Swapping to conditional branches (e.g. loop
editor->seo until score>=80) is a one-edge change — noted in docs as a prod
enhancement.
"""
from __future__ import annotations

import json
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from app.agents import nodes
from app.agents.nodes import Deps
from app.agents.state import PipelineState
from app.llm.registry import get_llm
from app.search.registry import get_search
from app.trace import Tracer


def build_graph(deps: Deps):
    g = StateGraph(PipelineState)
    g.add_node("keyword_research", nodes.keyword_research(deps))
    g.add_node("serp_analysis", nodes.serp_analysis(deps))
    g.add_node("brief", nodes.brief(deps))
    g.add_node("outline", nodes.outline(deps))
    g.add_node("writer", nodes.writer(deps))
    g.add_node("editor", nodes.editor(deps))
    g.add_node("seo_optimizer", nodes.seo_optimizer(deps))
    g.add_node("meta_schema", nodes.meta_schema(deps))

    g.add_edge(START, "keyword_research")
    g.add_edge("keyword_research", "serp_analysis")
    g.add_edge("serp_analysis", "brief")
    g.add_edge("brief", "outline")
    g.add_edge("outline", "writer")
    g.add_edge("writer", "editor")
    g.add_edge("editor", "seo_optimizer")
    g.add_edge("seo_optimizer", "meta_schema")
    g.add_edge("meta_schema", END)
    return g.compile()


def run_pipeline(topic: str, target_keyword: str = "", audience: str = "general",
                 tone: str = "professional", run_id: str | None = None) -> dict:
    tracer = Tracer(run_id=run_id)
    deps = Deps(llm=get_llm(), search=get_search(), tracer=tracer)
    tracer.event("orchestrator", "run_start",
                 data={"topic": topic, "llm": deps.llm.name, "search": deps.search.name})
    app = build_graph(deps)
    init: PipelineState = {
        "topic": topic, "target_keyword": target_keyword,
        "audience": audience, "tone": tone, "run_id": tracer.run_id, "errors": [],
    }
    final = app.invoke(init)
    tracer.event("orchestrator", "run_end", data={"seo_score":
                 final.get("seo", {}).get("score")})
    final["run_id"] = tracer.run_id
    write_output(final)
    return final


def write_output(result: dict, out_dir: Path | None = None) -> None:
    """Replace out/article.md and out/result.json with the latest run.

    Called by both the CLI (scripts/run_demo.py) and the API (/generate) so
    out/ always reflects only the most recent generation, never a stale one.
    """
    out = out_dir or (Path(__file__).resolve().parent.parent.parent / "out")
    out.mkdir(exist_ok=True)
    (out / "article.md").write_text(result.get("article", ""), encoding="utf-8")
    (out / "result.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "article"},
                   indent=2, ensure_ascii=False), encoding="utf-8")
