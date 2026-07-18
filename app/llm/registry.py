"""LLM selection — the single place prod-vs-demo model routing lives.

DEMO  -> Groq (free) or Mock (no key).
PROD  -> per-agent model routing (documented, not run in the prototype):
         reasoning-heavy agents  -> Claude Sonnet 5   (best long-form + brief quality)
         high-volume cheap agents -> GPT-4o-mini       (cost-optimized bulk steps)
See docs/01-research-evaluation.md for the full justification table.
"""
from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.base import LLMClient

# Documented prod routing: agent-role -> (provider, model, reason).
# This is intentionally data, not wiring — the prototype never calls paid APIs,
# but the mapping is asserted by tests and rendered into the docs.
PROD_ROUTING: dict[str, dict[str, str]] = {
    "keyword_research": {"provider": "openai", "model": "gpt-4o-mini",
                          "reason": "cheap, structured, high call volume"},
    "serp_analysis":    {"provider": "openai", "model": "gpt-4o-mini",
                          "reason": "summarization of scraped text; cost-sensitive"},
    "brief":            {"provider": "anthropic", "model": "claude-sonnet-5",
                          "reason": "reasoning + instruction-following quality"},
    "outline":          {"provider": "anthropic", "model": "claude-sonnet-5",
                          "reason": "structure/coherence matters most here"},
    "writer":           {"provider": "anthropic", "model": "claude-sonnet-5",
                          "reason": "long-form prose quality; brand voice"},
    "editor":           {"provider": "anthropic", "model": "claude-sonnet-5",
                          "reason": "critique + factual/consistency checks"},
    "seo_optimizer":    {"provider": "openai", "model": "gpt-4o-mini",
                          "reason": "rule-based scoring; cheap and deterministic"},
    "meta_schema":      {"provider": "openai", "model": "gpt-4o-mini",
                          "reason": "short structured output; low cost"},
}


def get_llm(settings: Settings | None = None) -> LLMClient:
    """Return the active demo LLM (Groq if keyed, else deterministic Mock)."""
    s = settings or get_settings()
    if s.has_groq:
        from app.llm.groq_client import GroqClient
        return GroqClient(api_keys=s.groq_keys, model=s.groq_model)
    from app.llm.mock_client import MockClient
    return MockClient()
