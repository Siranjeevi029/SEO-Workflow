"""Groq LLM client — DEMO provider (free tier) with multi-key rotation.

Why Groq for the demo: free API key, very fast inference (LPU), and it serves
open models (Llama 3.3 70B) with an OpenAI-compatible chat API. Good enough to
prove the workflow end-to-end at zero cost. Prod swaps to Claude/GPT — see
docs/01-research-evaluation.md for the justification.

Free tier is rate-limited, so we rotate across up to 5 keys: on a 429 we advance
to the next key and retry. This is a demo-only trick to keep the pipeline moving;
prod uses a single paid key with proper concurrency limits.
"""
from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

from app.llm.base import LLMClient, LLMResult


class GroqClient(LLMClient):
    name = "groq"

    def __init__(self, api_keys: list[str], model: str):
        from groq import Groq  # lazy import so keyless envs still load

        if not api_keys:
            raise ValueError("GroqClient needs at least one API key")
        self.model = model
        self._keys = api_keys
        self._idx = 0
        self._clients = [Groq(api_key=k) for k in api_keys]

    def _rotate(self) -> None:
        self._idx = (self._idx + 1) % len(self._clients)

    @retry(stop=stop_after_attempt(4),
           wait=wait_exponential(multiplier=1, min=1, max=8))
    def complete(self, system: str, user: str, temperature: float = 0.4,
                 max_tokens: int = 1500) -> LLMResult:
        try:
            from groq import RateLimitError
        except Exception:  # pragma: no cover
            RateLimitError = Exception  # type: ignore

        try:
            client = self._clients[self._idx]
            resp = client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except RateLimitError:
            self._rotate()  # advance key, let tenacity retry
            raise

        choice = resp.choices[0].message.content or ""
        usage = resp.usage
        return LLMResult(
            text=choice.strip(),
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
        )
