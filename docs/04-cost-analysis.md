# Cost Analysis & Optimization

All figures are early-2026 list prices. Token estimates are per article, measured
against real runs of this pipeline (see `traces/trace.jsonl` for actual call
counts and timings).

## Per-article token budget (8 agents)

| Agent | ~In tok | ~Out tok | Prod model |
|---|---|---|---|
| keyword_research | 500 | 400 | GPT-4o-mini |
| serp_analysis (synth) | 1,500 | 500 | GPT-4o-mini |
| brief | 1,500 | 500 | Claude Sonnet 5 |
| outline | 800 | 400 | Claude Sonnet 5 |
| writer | 1,200 | 1,500 | Claude Sonnet 5 |
| editor | 1,800 | 1,600 | Claude Sonnet 5 |
| seo_optimizer | 300 | 300 | GPT-4o-mini |
| meta_schema | 200 | 300 | GPT-4o-mini |

Rates used: Sonnet 5 = **$3 / $15** per 1M in/out; GPT-4o-mini = **$0.15 / $0.60**.

## Cost per article

| Line item | Cost |
|---|---|
| Claude Sonnet 5 (brief+outline+writer+editor) | ~$0.076 |
| GPT-4o-mini (4 structured steps) | ~$0.0013 |
| **LLM subtotal (mixed routing)** | **~$0.077** |
| Firecrawl (1 search + ~5 scrapes) | ~$0.01–0.02 |
| **Total per article (prod)** | **~$0.09–0.10** |

**Demo cost: $0** — Groq free tier (5 rotated keys) + Firecrawl free tier.

## Cost-optimization lever: mixed routing

| Strategy | LLM $/article | Δ |
|---|---|---|
| All Claude Sonnet 5 | ~$0.106 | baseline |
| **Mixed routing (ours)** | **~$0.077** | **−27% LLM cost, no quality loss** |
| All GPT-4o-mini | ~$0.005 | −95% but visibly worse writer/editor output |

The 4 structured steps (keyword/serp/seo/meta) are 20× cheaper on 4o-mini with no
measurable quality drop; the 4 prose steps stay on Sonnet where quality = ROI.
This is why routing is **per-agent data** (`PROD_ROUTING`), not a global setting.

Further levers (documented, easy to add):
- **Prompt caching** on Claude for the repeated system prompts → ~10–20% off input cost.
- **Batch API** for non-realtime bulk generation → ~50% off.
- **Cache SERP scrapes** per keyword (Redis, 24h TTL) → cuts Firecrawl calls on re-runs.
- **Skip RAG** unless the topic is fact-heavy → avoids embedding + vector costs.

## Monthly infrastructure cost (prod)

Assume a content team producing **1,000 articles/month**.

| Component | Model | Monthly |
|---|---|---|
| LLM (mixed) | Claude + GPT-4o-mini | ~$77 |
| Search/scrape | Firecrawl paid | ~$16–50 |
| Vector store | Pinecone serverless (light) | ~$0–25 |
| Compute (API) | 1× small container (Railway/Fly/Cloud Run) | ~$5–20 |
| Observability | Langfuse (self-host/free tier) | ~$0 |
| **Total** | | **~$100–170 / mo** = **~$0.10–0.17 / article** |

At 10,000 articles/month, LLM ≈ $770 and Firecrawl scales to a higher tier, but
per-article cost stays flat (~$0.10) — the architecture is **linear in volume**,
no step-function infra jumps until you self-host models.

## Break-even framing

A freelance SEO writer costs ~$50–200 per article. At ~$0.10 of compute + review
time, the automation's marginal cost is negligible; the real cost is human review
of the output. The business case is **throughput and consistency**, not shaving
cents — but the routing optimization keeps compute from being a line item anyone
notices.
