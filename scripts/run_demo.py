"""CLI demo runner — end-to-end pipeline without the API server.

    python scripts/run_demo.py "best running shoes for flat feet"

Runs all 8 agents, prints the article + SEO score, and writes artifacts to
out/. Every agent action is appended to traces/trace.jsonl.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.graph import run_pipeline  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.llm.registry import get_llm  # noqa: E402
from app.search.registry import get_search  # noqa: E402


def main() -> None:
    topic = sys.argv[1] if len(sys.argv) > 1 else "how to start a vegetable garden"
    keyword = sys.argv[2] if len(sys.argv) > 2 else topic
    s = get_settings()
    print(f"[stack] mode={s.app_mode} llm={get_llm(s).name} search={get_search(s).name}")
    print(f"[run] topic={topic!r}\n")

    result = run_pipeline(topic=topic, target_keyword=keyword)
    # run_pipeline() already writes out/article.md + out/result.json (write_output)

    print("=" * 60)
    print("ARTICLE (out/article.md):\n")
    print((result.get("article") or "")[:1200], "...\n")
    print("=" * 60)
    print("SEO:", json.dumps(result.get("seo", {}), indent=2)[:600])
    print("META title_tag:", result.get("meta", {}).get("title_tag"))
    print("RUN ID:", result.get("run_id"), "-> traces/trace.jsonl")


if __name__ == "__main__":
    main()
