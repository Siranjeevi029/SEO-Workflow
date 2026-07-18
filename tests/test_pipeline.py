"""Fast, keyless tests — validate scoring, routing, trace, JSON parsing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.nodes import _json_from, _seo_checks
from app.llm.registry import PROD_ROUTING
from app.trace import Tracer, read_run


def test_seo_scoring_good_article():
    art = ("# Budget Keyboards\n\nBudget mechanical keyboards are great.\n"
           "## Why\n text [link](/x)\n## How\n more\n## When\n more\n" + "word " * 800)
    checks = _seo_checks(art, "budget mechanical keyboards")
    assert checks["has_single_h1"] is True
    assert checks["h2_count"] >= 3
    assert checks["keyword_in_first_100"] is True
    assert 0 <= checks["score"] <= 100
    assert checks["score"] >= 70


def test_seo_scoring_penalizes_thin_content():
    weak = _seo_checks("no heading here just text", "keyword")
    good_len = _seo_checks("# H1\n## H2\n## H3\n## H4\n" + "keyword " * 900, "keyword")
    assert good_len["score"] > weak["score"]


def test_json_extraction_from_fenced_block():
    assert _json_from('```json\n{"a": 1}\n```') == {"a": 1}
    assert _json_from('noise before [1,2,3] noise') == [1, 2, 3]
    assert _json_from("not json at all") is None


def test_prod_routing_covers_all_agents():
    expected = {"keyword_research", "serp_analysis", "brief", "outline",
                "writer", "editor", "seo_optimizer", "meta_schema"}
    assert set(PROD_ROUTING) == expected
    for role, cfg in PROD_ROUTING.items():
        assert cfg["provider"] in {"openai", "anthropic"}
        assert cfg["model"] and cfg["reason"]


def test_tracer_writes_and_reads(tmp_path):
    t = Tracer(path=tmp_path / "t.jsonl")
    t.event("a", "act", data={"x": 1})
    with t.step("b", "work"):
        pass
    events = read_run(t.run_id, path=tmp_path / "t.jsonl")
    assert len(events) == 3  # event + step start + step ok
    assert events[0]["agent"] == "a"
    assert any(e["status"] == "ok" and e["agent"] == "b" for e in events)
