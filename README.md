# SEO Content Workflow

A multi-agent pipeline that turns a **topic + target keyword** into a
**SERP-informed, on-page-optimized article** with metadata and JSON-LD schema —
every agent action traced to `traces/trace.jsonl`.

Built for the "AI-powered business workflow automation" assignment (use case:
**SEO Content Workflow**). Production architecture is fully documented; the
prototype runs on **free tiers** (Groq + Firecrawl) at **$0**.

```
topic → keyword_research → serp_analysis → brief → outline
      → writer → editor → seo_optimizer → meta_schema → article + report
```

## Why this design (30-second version)

- **8 specialized agents** orchestrated by **LangGraph** (explicit, testable, resumable).
- **Vendor behind an interface** — demo→prod is a one-line registry swap:
  | Layer | Demo (free) | Prod (recommended) |
  |---|---|---|
  | LLM (prose) | Groq Llama-3.3-70B | Claude Sonnet 5 |
  | LLM (structured) | Groq Llama-3.3-70B | GPT-4o-mini |
  | Search + scrape | Firecrawl free / DDG | Firecrawl paid + Bright Data |
  | Vector store | Chroma (embedded) | Pinecone (serverless) |
- **Trace-first**: `traces/trace.jsonl` is the single source of truth for what each agent did.
- **Degrades, never crashes**: no keys → mock LLM + DuckDuckGo; unsupported scrape → skipped.
- **Cost-optimized**: per-agent model routing cuts prod LLM cost ~27% vs all-Sonnet.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on *nix)
pip install -r requirements.txt

cp .env.example .env              # then add keys (or leave empty to run keyless)
```

`.env` keys (all optional — pipeline runs keyless with mock LLM + DuckDuckGo):

```
GROQ_API_KEY_1=...      # up to _5, rotated to dodge free-tier rate limits
FIRECRAWL_API_KEY=...   # falls back to DuckDuckGo if empty
```

### Run — CLI

```bash
python scripts/run_demo.py "best budget mechanical keyboards" "budget mechanical keyboards"
# → out/article.md, out/result.json, traces/trace.jsonl
```

### Run — API + UI

```bash
uvicorn app.main:app --reload
# open http://127.0.0.1:8000   (form → article + SEO score + live trace)
```

| Endpoint | Purpose |
|---|---|
| `GET /` | Demo UI |
| `GET /health` | Active stack (mode / llm / search) |
| `POST /generate` | Run full pipeline → article + seo + meta + run_id |
| `GET /trace/{run_id}` | Replay all trace events for a run |

### Test

```bash
pytest -q          # 5 tests: SEO scoring, prod routing, trace, JSON parsing
```

## Repo layout

```
app/
  config.py            env settings, demo/prod mode, 5-key Groq rotation
  trace.py             append-only JSONL tracer (per-run, auto-timed steps)
  llm/                 base + groq (demo) + mock (keyless) + PROD_ROUTING
  search/              base + firecrawl (demo) + ddg (free fallback)
  rag/store.py         VectorStore: Chroma (demo) / Pinecone (prod)
  agents/nodes.py      the 8 agent node functions (each logs a trace event)
  agents/graph.py      LangGraph wiring + run_pipeline()
  main.py              FastAPI + endpoints
static/index.html      demo UI
scripts/run_demo.py    end-to-end CLI runner
tests/                 pytest
docs/                  research, architecture, recommendation, cost
traces/trace.jsonl     agent action log (generated)
```

## Documentation (the report)

| Doc | Covers |
|---|---|
| [`docs/01-research-evaluation.md`](docs/01-research-evaluation.md) | Part 1 — compare LLMs, orchestration, search, vector stores; prod vs demo justification |
| [`docs/02-architecture.md`](docs/02-architecture.md) | Part 2 — architecture, diagram, components, design principles |
| [`docs/03-recommendation-report.md`](docs/03-recommendation-report.md) | Part 3 — recommended stack, why, cost, risks, scaling |
| [`docs/04-cost-analysis.md`](docs/04-cost-analysis.md) | Per-article & monthly cost, mixed-routing optimization |

## Deliverables map

| Required | Where |
|---|---|
| GitHub repository | this repo |
| Documentation / report | `docs/` (4 files) |
| Working prototype / POC | `app/`, `scripts/run_demo.py`, FastAPI + UI |
| Workflow diagram | `docs/02-architecture.md` (Mermaid) |
| Screenshots | [`docs/diagrams/`](docs/diagrams/) — form, result, live trace |
| Demo walkthrough | `docs/05-demo-walkthrough.md` |
| Demo video | [Google Drive link](https://drive.google.com/file/d/1ibTp6nI6zyzoo744stro1A160lK-wvkY/view?usp=sharing) |

## Notes

- Demo tools (Groq, Chroma, DuckDuckGo) exist only to run the prototype free —
  they are **not** the production recommendation. Prod picks are justified in `docs/`.
