"""Central config. Loads .env, exposes typed settings, picks demo vs prod stack."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_mode: str = "demo"  # "demo" | "prod"

    # demo providers — up to 5 Groq keys rotated to spread free-tier rate limits
    groq_api_key: str = ""
    groq_api_key_1: str = ""
    groq_api_key_2: str = ""
    groq_api_key_3: str = ""
    groq_api_key_4: str = ""
    groq_api_key_5: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    firecrawl_api_key: str = ""

    # prod providers (documented)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    pinecone_api_key: str = ""
    pinecone_index: str = "seo-content-workflow"

    trace_file: str = "traces/trace.jsonl"

    @property
    def trace_path(self) -> Path:
        p = Path(self.trace_file)
        return p if p.is_absolute() else ROOT / p

    @property
    def groq_keys(self) -> list[str]:
        keys = [self.groq_api_key, self.groq_api_key_1, self.groq_api_key_2,
                self.groq_api_key_3, self.groq_api_key_4, self.groq_api_key_5]
        return [k.strip() for k in keys if k.strip()]

    @property
    def has_groq(self) -> bool:
        return len(self.groq_keys) > 0

    @property
    def has_firecrawl(self) -> bool:
        return bool(self.firecrawl_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
