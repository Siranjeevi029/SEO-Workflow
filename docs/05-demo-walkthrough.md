# Demo Walkthrough

This is the script for the demo video / live walkthrough. Every step below was
verified against a real run (Groq LLM + Firecrawl search/scrape).

## 0. Setup (once)

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # add GROQ_API_KEY_1..5 + FIRECRAWL_API_KEY
```

Keyless is fine too — it falls back to a mock LLM + DuckDuckGo and still runs.

## 1. Show the stack is live

```bash
curl http://127.0.0.1:8000/health
# {"mode":"demo","llm":"groq","search":"firecrawl", ...}
```

Talking point: the app reports which providers are active. Swap to prod = flip
keys / `APP_MODE`, no code change.

## 2. Run the pipeline (CLI)

```bash
python scripts/run_demo.py "how to compost at home" "home composting"
```

What to point at while it runs:
- 8 agents fire in order (keyword → serp → brief → outline → writer → editor →
  seo → meta).
- `serp_analysis` really searches Google via Firecrawl and scrapes the top 5
  competitor pages (watch the per-scrape timings).
- Output: `out/article.md` (real 800+ word article), `out/result.json`.

Verified result (run `run_312251c4ed92`):
- **SEO score: 90/100**
- **Title tag:** "Home Composting Guide"
- **Article length:** 814 words
- **Brief title:** "A Beginner's Guide to Home Composting: Tips, Methods, and Benefits"

## 3. Show the trace — the "black box recorder"

```bash
python -c "import json; [print(json.loads(l)['seq'], json.loads(l)['agent'], json.loads(l)['action'], json.loads(l).get('duration_ms','')) for l in open('traces/trace.jsonl',encoding='utf-8')]"
```

38 events per run: every agent's `start`/`ok`/`done` with millisecond timing.
Talking point: this is how you debug and audit an agent system in production —
"where did it go wrong / how long did each step take."

## 4. Run it from the UI

```bash
uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

Fill topic + keyword → **Generate** → the page shows:
- SEO score (big green number)
- generated title tag + meta description
- the brief (JSON), the full article, the SEO checks
- the **live trace** at the bottom (every agent step)

> 📸 Capture screenshots here for the deliverable:
> - the filled form
> - the result card (SEO score + title)
> - the trace panel
> Save them into `docs/diagrams/`.

## 5. The API (for integration story)

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic":"best budget mechanical keyboards","target_keyword":"budget mechanical keyboards"}'

curl http://127.0.0.1:8000/trace/<run_id>
```

Talking point: `/generate` is the automation surface — an n8n node, a CMS hook,
or a scheduled job calls this. `/trace/{id}` gives full observability per run.

## 6. Close on prod story (hold up the docs)

- `01-research-evaluation.md` — why Claude/GPT-4o-mini/Firecrawl/Pinecone for prod.
- `04-cost-analysis.md` — ~$0.10/article, mixed routing saves 27%.
- `02-architecture.md` — the diagram + prod enhancements (quality loop, RAG, n8n).

**One-line pitch:** "The demo runs free on Groq + Firecrawl; production is the same
pipeline with better models swapped in behind an interface — proven, traced, and
costed."
