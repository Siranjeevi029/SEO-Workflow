"""The 8 SEO agents as LangGraph nodes.

Each node: reads state -> does one job -> logs a trace event -> returns a
partial state update. Nodes never call vendor SDKs directly; they use the
injected LLM + Search clients (demo/prod swap handled by the registries).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from app.agents.state import PipelineState
from app.llm.base import LLMClient
from app.search.base import SearchClient
from app.trace import Tracer


@dataclass
class Deps:
    llm: LLMClient
    search: SearchClient
    tracer: Tracer


# ---------- helpers ----------

def _json_from(text: str) -> Any:
    """Best-effort JSON extraction from an LLM reply."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    if m:
        text = m.group(1).strip()
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start >= 0:
        text = text[start:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # tolerate trailing prose after the JSON value
        try:
            obj, _ = json.JSONDecoder().raw_decode(text)
            return obj
        except json.JSONDecodeError:
            return None


# ---------- nodes ----------

def keyword_research(d: Deps) -> Callable[[PipelineState], dict]:
    def node(s: PipelineState) -> dict:
        topic = s["topic"]
        with d.tracer.step("keyword_research", "expand_keywords", {"topic": topic}):
            sys = ("You are an SEO keyword strategist. Return ONLY JSON: a list of "
                   "8 objects with keys: keyword, intent (informational|commercial|"
                   "transactional|navigational), note.")
            usr = f"Seed topic: {topic}\nTarget keyword hint: {s.get('target_keyword','')}"
            res = d.llm.complete(sys, usr, temperature=0.5, max_tokens=800)
            kws = _json_from(res.text) or [
                {"keyword": topic, "intent": "informational", "note": "seed"}]
        d.tracer.event("keyword_research", "done", data={"count": len(kws),
                       "model": res.model, "tokens": res.completion_tokens})
        return {"keywords": kws}
    return node


def serp_analysis(d: Deps) -> Callable[[PipelineState], dict]:
    def node(s: PipelineState) -> dict:
        kw = s.get("target_keyword") or s["topic"]
        with d.tracer.step("serp_analysis", "search", {"query": kw}):
            hits = d.search.search(kw, limit=5)
        serp: list[dict[str, Any]] = []
        for h in hits[:5]:
            with d.tracer.step("serp_analysis", "scrape", {"url": h.url}):
                page = d.search.scrape(h.url)
            serp.append({"title": h.title or page.title, "url": h.url,
                         "position": h.position, "word_count": page.word_count,
                         "headings": page.headings[:12]})
        avg_wc = int(sum(p["word_count"] for p in serp) / max(len(serp), 1))
        all_heads = [h for p in serp for h in p["headings"]]
        sys = ("You are a SERP content-gap analyst. Given competitor headings, "
               "return ONLY JSON with keys: common_themes (list), content_gaps "
               "(list), recommended_word_count (int).")
        usr = (f"Keyword: {kw}\nAvg competitor word count: {avg_wc}\n"
               f"Competitor headings:\n{json.dumps(all_heads[:60])}")
        with d.tracer.step("serp_analysis", "synthesize_gaps", {"n": len(serp)}):
            res = d.llm.complete(sys, usr, temperature=0.4, max_tokens=700)
            insights = _json_from(res.text) or {}
        insights.setdefault("recommended_word_count", max(avg_wc, 800))
        insights["avg_competitor_word_count"] = avg_wc
        d.tracer.event("serp_analysis", "done",
                       data={"competitors": len(serp), "avg_wc": avg_wc})
        return {"serp": serp, "serp_insights": insights}
    return node


def brief(d: Deps) -> Callable[[PipelineState], dict]:
    def node(s: PipelineState) -> dict:
        with d.tracer.step("brief", "compose", {"topic": s["topic"]}):
            sys = ("You are an SEO content strategist. Return ONLY JSON with keys: "
                   "title, primary_keyword, secondary_keywords (list), search_intent, "
                   "target_audience, angle, key_points (list), word_count_target (int).")
            usr = (f"Topic: {s['topic']}\nAudience: {s.get('audience','general')}\n"
                   f"Keywords: {json.dumps(s.get('keywords', []))}\n"
                   f"SERP insights: {json.dumps(s.get('serp_insights', {}))}")
            res = d.llm.complete(sys, usr, temperature=0.5, max_tokens=900)
            b = _json_from(res.text) or {"title": s["topic"],
                "primary_keyword": s.get("target_keyword", s["topic"])}
        d.tracer.event("brief", "done", data={"title": b.get("title")})
        return {"brief": b}
    return node


def outline(d: Deps) -> Callable[[PipelineState], dict]:
    def node(s: PipelineState) -> dict:
        with d.tracer.step("outline", "generate", {}):
            sys = ("You are an SEO editor. Produce a markdown H1/H2/H3 outline that "
                   "beats the competitor structure and fills the content gaps. "
                   "Output markdown only, no prose.")
            usr = (f"Brief: {json.dumps(s.get('brief', {}))}\n"
                   f"Gaps to cover: {json.dumps(s.get('serp_insights', {}).get('content_gaps', []))}")
            res = d.llm.complete(sys, usr, temperature=0.5, max_tokens=800)
        d.tracer.event("outline", "done", data={"chars": len(res.text)})
        return {"outline": res.text}
    return node


def writer(d: Deps) -> Callable[[PipelineState], dict]:
    def node(s: PipelineState) -> dict:
        wc = s.get("serp_insights", {}).get("recommended_word_count", 900)
        with d.tracer.step("writer", "draft", {"target_wc": wc}):
            sys = (f"You are an expert SEO writer. Tone: {s.get('tone','professional')}. "
                   "Write a complete, well-structured article in markdown following the "
                   "outline. Use the primary keyword naturally in the intro, one H2, and "
                   "the conclusion. No keyword stuffing.")
            usr = (f"Brief: {json.dumps(s.get('brief', {}))}\n\nOutline:\n{s.get('outline','')}"
                   f"\n\nTarget length: ~{wc} words.")
            res = d.llm.complete(sys, usr, temperature=0.6, max_tokens=3000)
        d.tracer.event("writer", "done",
                       data={"words": len(res.text.split()), "model": res.model})
        return {"draft": res.text}
    return node


def editor(d: Deps) -> Callable[[PipelineState], dict]:
    def node(s: PipelineState) -> dict:
        with d.tracer.step("editor", "revise", {}):
            sys = ("You are a senior editor. Improve clarity, flow, and factual "
                   "consistency of the draft. Fix awkward phrasing and remove fluff. "
                   "Keep markdown structure. Output the revised article only.")
            usr = s.get("draft", "")
            res = d.llm.complete(sys, usr, temperature=0.4, max_tokens=3000)
        d.tracer.event("editor", "done", data={"words": len(res.text.split())})
        return {"edited": res.text}
    return node


_STOP = {"the", "a", "an", "and", "or", "to", "of", "in", "for", "on", "with", "is"}


def _seo_checks(article: str, primary: str) -> dict[str, Any]:
    """Deterministic on-page SEO scoring — no LLM needed, cheap + reproducible."""
    words = re.findall(r"[a-zA-Z]+", article.lower())
    wc = len(words)
    pk = (primary or "").lower().strip()
    density = (article.lower().count(pk) / max(wc, 1) * 100) if pk else 0.0
    h1 = len(re.findall(r"^#\s+", article, flags=re.M))
    h2 = len(re.findall(r"^##\s+", article, flags=re.M))
    checks = {
        "word_count": wc,
        "has_single_h1": h1 == 1,
        "h2_count": h2,
        "keyword_in_first_100": pk in " ".join(words[:100]) if pk else False,
        "keyword_density_pct": round(density, 2),
        "density_in_range": 0.5 <= density <= 2.5 if pk else False,
        "internal_link_placeholders": article.count("]("),
    }
    score = 0
    score += 20 if checks["word_count"] >= 700 else 10
    score += 15 if checks["has_single_h1"] else 0
    score += 15 if checks["h2_count"] >= 3 else 5
    score += 20 if checks["keyword_in_first_100"] else 0
    score += 20 if checks["density_in_range"] else 5
    score += 10 if checks["internal_link_placeholders"] >= 1 else 0
    checks["score"] = min(score, 100)
    return checks


def seo_optimizer(d: Deps) -> Callable[[PipelineState], dict]:
    def node(s: PipelineState) -> dict:
        article = s.get("edited") or s.get("draft", "")
        primary = s.get("brief", {}).get("primary_keyword", s.get("target_keyword", ""))
        with d.tracer.step("seo_optimizer", "score", {"primary": primary}):
            checks = _seo_checks(article, primary)
            sys = ("You are an on-page SEO auditor. Given these automated checks, return "
                   "ONLY JSON with keys: suggestions (list of short actionable strings).")
            usr = json.dumps(checks)
            res = d.llm.complete(sys, usr, temperature=0.3, max_tokens=500)
            sug = _json_from(res.text) or {}
        checks["suggestions"] = sug.get("suggestions", []) if isinstance(sug, dict) else []
        d.tracer.event("seo_optimizer", "done", data={"score": checks["score"]})
        return {"seo": checks}
    return node


def meta_schema(d: Deps) -> Callable[[PipelineState], dict]:
    def node(s: PipelineState) -> dict:
        b = s.get("brief", {})
        with d.tracer.step("meta_schema", "generate", {}):
            sys = ("You generate SEO metadata. Return ONLY JSON with keys: title_tag "
                   "(<=60 chars), meta_description (<=155 chars), slug, "
                   "faq (list of {q,a}).")
            usr = f"Title: {b.get('title')}\nKeyword: {b.get('primary_keyword')}"
            res = d.llm.complete(sys, usr, temperature=0.4, max_tokens=600)
            meta = _json_from(res.text) or {}
        # JSON-LD Article schema (deterministic assembly)
        meta["json_ld"] = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": meta.get("title_tag") or b.get("title", ""),
            "description": meta.get("meta_description", ""),
            "keywords": b.get("primary_keyword", ""),
        }
        article = s.get("edited") or s.get("draft", "")
        d.tracer.event("meta_schema", "done", data={"title_tag": meta.get("title_tag")})
        return {"meta": meta, "article": article}
    return node
