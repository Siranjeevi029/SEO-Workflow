# Part 3 — Recommendation Report

## Executive summary

For an SEO Content Workflow, we recommend a **LangGraph multi-agent pipeline**
with **per-agent LLM routing** (Claude Sonnet 5 for prose, GPT-4o-mini for
structured steps), **Firecrawl** for SERP search + competitor scraping, and
**Pinecone** for optional RAG grounding. The prototype in this repo proves the
full workflow end-to-end at **$0** using Groq + Firecrawl free tiers, with every
demo→prod component swap already isolated behind an interface.

## Recommended architecture

```
topic + keyword
   → keyword_research → serp_analysis (search+scrape top 5)
   → brief → outline → writer → editor
   → seo_optimizer (deterministic score) → meta_schema (title/desc/JSON-LD)
   → article + SEO report + metadata
   (every step appended to trace.jsonl)
```

- **Orchestration:** LangGraph — explicit, typed, testable, resumable DAG.
- **Reasoning steps** (brief/outline/writer/editor): **Claude Sonnet 5**.
- **Structured steps** (keyword/serp/seo/meta): **GPT-4o-mini**.
- **Search + scrape:** Firecrawl (paid), Bright Data as an overflow scraper.
- **Vector store:** Pinecone serverless (optional RAG grounding).
- **Business front-door:** n8n visual trigger → FastAPI `/generate`.
- **Observability:** ship `trace.jsonl` events to Langfuse.

See `02-architecture.md` for the full diagram and `01-research-evaluation.md` for
the option-by-option comparison behind each pick.

## Why these tools/models

| Choice | Reason |
|---|---|
| **LangGraph** (not CrewAI/n8n as core) | Control flow must be explicit, testable, and resumable; native hooks feed our trace. |
| **Claude Sonnet 5** for prose | Strongest long-form writing + editorial critique; this is where content ROI is made. |
| **GPT-4o-mini** for structured steps | ~20× cheaper than Sonnet with no quality loss on simple structured output → −27% LLM cost. |
| **Firecrawl** (not Serper) | One key does SERP search **and** clean markdown scrape; Serper 403'd on the free key and can't scrape. |
| **Pinecone** for prod RAG | Serverless, zero-ops, scales with the content library. |
| **Groq + Chroma + DDG** for demo | Free, so the prototype runs at $0; each swaps to the prod pick via one registry line. |

## Estimated infrastructure cost

- **Demo:** $0 (free tiers).
- **Prod:** ~**$0.09–0.10 per article**; ~**$100–170/month** at 1,000
  articles/month. Cost is linear in volume — no infra step-functions.
  Full breakdown in `04-cost-analysis.md`.

## Risks & limitations

| Risk | Mitigation |
|---|---|
| **LLM hallucination / factual errors** | RAG grounding on scraped competitor pages; mandatory human review before publish. |
| **Scrape gaps** (reddit/paywalls unsupported) | Degrade gracefully (skip page); add Bright Data for hard targets. |
| **Free-tier rate limits (demo)** | 5-key Groq rotation + tenacity backoff; prod uses paid keys. |
| **Google SERP volatility** | Treat SERP insights as directional, not deterministic; re-run and cache. |
| **Prompt injection via scraped pages** | Sanitize/limit scraped text fed to the LLM; never execute retrieved content. |
| **SEO ≠ ranking guarantee** | On-page score is a quality proxy, not a ranking promise; pair with off-page strategy. |
| **Cost creep at scale** | Prompt caching + batch API + SERP cache; monitor via trace + Langfuse. |
| **Vendor lock-in** | Every vendor sits behind an interface; swaps are one-line. |

## How it scales in production

1. **Throughput:** async fan-out on SERP scraping; run multiple articles
   concurrently (stateless pipeline, horizontally scalable API containers).
2. **Quality loop:** LangGraph conditional edge `editor → seo_optimizer` until
   `score ≥ 80`; human-in-the-loop approval gate after `brief`.
3. **Grounding:** persistent Pinecone index of scraped pages + published content
   for internal-link suggestions and factual grounding.
4. **Operability:** n8n front-door for non-technical operators; scheduled bulk
   runs; CMS publish integration (WordPress/Webflow/Shopify).
5. **Observability & eval:** stream `trace.jsonl` to Langfuse; score outputs;
   A/B model routing; detect regressions.
6. **Cost control:** prompt caching, batch API, SERP/scrape caching — all additive
   to the current design, no rewrite.

## Conclusion

The prototype demonstrates the complete workflow with real API integrations
(Groq LLM + Firecrawl search/scrape), a multi-agent LangGraph orchestration, full
action tracing, deterministic SEO scoring, and structured metadata/schema output.
The path to production is a set of **config swaps**, not a re-architecture — which
is the point of the interface-first design.
