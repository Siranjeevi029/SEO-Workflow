"""LLM provider abstraction.

The whole pipeline talks to this interface, never to a vendor SDK directly.
Swapping demo (Groq) for prod (Claude / GPT-4o) is a one-line registry change.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMClient(ABC):
    name: str = "base"
    model: str = "unknown"

    @abstractmethod
    def complete(self, system: str, user: str, temperature: float = 0.4,
                 max_tokens: int = 1500) -> LLMResult:
        ...
