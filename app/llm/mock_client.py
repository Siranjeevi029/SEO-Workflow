"""Deterministic mock LLM — lets the whole pipeline run with ZERO keys.

Used automatically when no GROQ_API_KEY is set, so `python scripts/run_demo.py`
never hard-fails during evaluation. Output is templated per agent role so the
end-to-end trace and artifact shapes are still realistic.
"""
from __future__ import annotations

from app.llm.base import LLMClient, LLMResult


class MockClient(LLMClient):
    name = "mock"
    model = "mock-deterministic"

    def complete(self, system: str, user: str, temperature: float = 0.4,
                 max_tokens: int = 1500) -> LLMResult:
        role = system.lower()
        head = user.strip().splitlines()[0][:80] if user.strip() else ""
        if "json" in role or "json" in user.lower():
            text = '{"note": "mock output — set GROQ_API_KEY for real generation"}'
        elif "outline" in role:
            text = ("## H1: Mock Title\n- H2: Introduction\n- H2: Key Points\n"
                    "- H2: Best Practices\n- H2: Conclusion")
        elif "writer" in role or "draft" in role:
            text = (f"# Mock Article\n\n(Mock draft for: {head})\n\n"
                    "This is placeholder prose generated without an LLM key. "
                    "Set GROQ_API_KEY to produce a real SEO-optimized draft.")
        else:
            text = f"[mock:{role[:24]}] {head}"
        return LLMResult(text=text, model=self.model,
                         prompt_tokens=len(user) // 4,
                         completion_tokens=len(text) // 4)
