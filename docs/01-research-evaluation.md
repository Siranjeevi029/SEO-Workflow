# Part 1 — AI Research & Evaluation

**Use case:** SEO Content Workflow — an automated multi-agent pipeline that turns a
topic + target keyword into a SERP-informed, on-page-optimized article with
metadata and schema, fully traced.

The workflow touches four tool categories. For each we compare ≥3 options across
**capabilities, pricing, scalability, ease of integration, limitations, best use
cases**, then state the **prod pick** (justified) and the **demo pick** (free, to
make the prototype run). Pricing figures are early-2026 list prices — verify at
the vendor before committing.

---

## 1. LLM / reasoning model (the agents' brains)

This is the most important choice: 8 agents each make ≥1 LLM call. Quality of the
brief, draft, and edit dominates the final output.

| | **Claude (Sonnet 5 / Opus 4.8)** | **OpenAI (GPT-4o / 4o-mini)** | **Google Gemini (2.0 Flash/Pro)** | **Groq (Llama 3.3 70B)** — *demo* |
|---|---|---|---|---|
| Capabilities | Best-in-class long-form writing, instruction following, editorial critique; 200K ctx | Strong all-round, huge tool/ecosystem, structured outputs, 128K ctx | Very long ctx (1M+), strong multimodal, competitive quality | Open models on fast LPU HW; good, not frontier quality |
| Pricing (per 1M tok, in/out) | Sonnet ~$3 / $15; Opus higher | 4o ~$2.5 / $10; **4o-mini ~$0.15 / $0.60** | Flash ~$0.10 / $0.40; Pro higher | **Free tier** (rate-limited); paid usage cheap |
| Scalability | High; enterprise SLAs, prompt caching | Highest; mature autoscale, batch API | High; GCP-backed | Free tier rate-limited — not for prod volume |
| Ease of integration | Clean SDK, OpenAI-compat via proxies | OpenAI-compatible = de-facto standard | Google SDK; slightly different API shape | **OpenAI-compatible API** — trivial swap |
| Limitations | Priciest for bulk cheap steps | Writing slightly behind Claude for long-form | Occasional format drift; ecosystem smaller | Rate limits; open models weaker at nuanced editing |
| Best use cases | Brief, outline, writer, editor (reasoning-heavy) | Bulk/structured steps, tool use | Long-context RAG, multimodal, cheap bulk | **Prototyping / demo at $0** |

**Prod decision — per-agent model routing (not one model for all):**
- **Claude Sonnet 5** → `brief`, `outline`, `writer`, `editor`. These are
  reasoning- and prose-quality-bound; Claude's long-form writing and editorial
  critique are measurably stronger, and this is where content ROI is made.
- **GPT-4o-mini** → `keyword_research`, `serp_analysis`, `seo_optimizer`,
  `meta_schema`. These are high-volume, structured, low-nuance steps where
  4o-mini is ~20× cheaper than Sonnet and quality is indistinguishable.

This split is encoded as data in `app/llm/registry.py::PROD_ROUTING` and asserted
by tests — the docs and the code cannot drift.

**Why not one model everywhere?** Using Sonnet for the cheap structured steps
would ~3–4× the per-article LLM cost for no quality gain; using 4o-mini for the
writer would visibly hurt the deliverable. Mixed routing is the cost-optimization
lever (see `04-cost-analysis.md`).

**Demo decision — Groq (Llama 3.3 70B):** free API key, OpenAI-compatible (so the
prod swap is a one-line registry change), and LPU inference is fast enough that
the 8-step pipeline finishes in ~30s. We rotate 5 free keys to absorb rate limits.
Groq proves the *workflow*; it is explicitly not the prod quality bar.

---

## 2. Agent orchestration (wiring the 8 steps)

| | **LangGraph** — *prod + demo* | **CrewAI** | **n8n / Make** |
|---|---|---|---|
| Model | Explicit stateful graph (nodes/edges), typed state | Role/goal "crew" of agents, higher-level | Visual no-code nodes + code steps |
| Capabilities | Branching, loops, checkpoints, resumability, human-in-loop | Fast to stand up multi-agent collabs | Great for glue/integrations, non-devs |
| Pricing | OSS (free); pay only for LLM calls | OSS (free) | Free self-host / paid cloud tiers |
| Scalability | High — deterministic, testable, ships as a service | Medium — less control over control-flow | Medium — good for I/O glue, weaker for complex agent logic |
| Integration | Python-native, LangChain ecosystem | Python-native | Webhooks/HTTP; code nodes limited |
| Limitations | Steeper learning curve | Control-flow less explicit → harder to debug at scale | Not ideal as the core reasoning engine |
| Best use | **Production agent pipelines needing traces + control** | Quick multi-agent PoCs | Business automations, connectors |

**Decision (prod & demo): LangGraph.** The workflow is a well-defined DAG whose
control flow we want explicit, testable, and resumable. LangGraph gives typed
state, per-node tracing hooks (which feed our `trace.jsonl`), and a trivial path
to add prod branches (e.g. loop `editor → seo_optimizer` until score ≥ 80).
n8n is documented as the **business-user front door** in prod (trigger the
pipeline from a visual workflow) but not as the reasoning core.

---

## 3. Web search + scrape (SERP & competitor analysis)

| | **Firecrawl** — *demo + prod* | **Serper** | **Bright Data** | **DuckDuckGo + httpx** — *free fallback* |
|---|---|---|---|---|
| Capabilities | Search **+** JS-rendered scrape → clean markdown, one key | Fast Google SERP JSON (search only) | Industrial proxy/scrape at scale | Basic search + raw HTML |
| Pricing | Free tier; paid from ~$16/mo | ~$50 / 100k queries | Usage-based, premium | Free |
| Scalability | High (managed) | High (search only) | Highest | Low — rate-limited, brittle |
| Integration | One SDK for search+scrape | Simple, search only | Heavier setup | Trivial but fragile |
| Limitations | Some sites unsupported (reddit/paywalls) | No scraping — need a second tool | Cost + complexity | No JS render, easily blocked |
| Best use | **SEO pipelines needing SERP + page content** | Pure SERP lookups | Massive scraping ops | Zero-budget fallback |

**Decision:** **Firecrawl for both demo and prod.** One key covers SERP search
*and* clean markdown extraction of competitor pages — exactly what
`serp_analysis` needs. **Serper was rejected**: the free key returned `403` in
our environment (see `notes.txt`) and it does not scrape, so we'd need a second
vendor. Prod keeps Firecrawl (paid plan) and adds **Bright Data** only if scrape
volume outgrows Firecrawl's limits. A free **DuckDuckGo + httpx** adapter is
built in and auto-activates when no Firecrawl key is present, so the repo runs at
truly $0.

---

## 4. Vector store (optional RAG grounding of the draft)

| | **Pinecone** — *prod* | **Weaviate** | **Chroma** — *demo* |
|---|---|---|---|
| Capabilities | Managed serverless ANN, metadata filters, hybrid | OSS + cloud, hybrid search, modules | Embedded/local, dead-simple |
| Pricing | Serverless pay-per-use; free starter | OSS free / paid cloud | Free (embedded) |
| Scalability | Very high, zero-ops | High (self-host or cloud) | Low — single-node dev tool |
| Integration | Clean SDK | More config | Trivial |
| Limitations | Vendor lock-in, cost at scale | You run infra (self-host) | Not for prod scale/HA |
| Best use | **Prod RAG at scale, minimal ops** | Full control / OSS mandate | Local dev & demos |

**Decision:** **Pinecone in prod** (zero-ops serverless, scales with content
library; a real key is present but unused by the core demo path), **Chroma in
demo** (embedded, no server). RAG is optional in this pipeline — it grounds the
writer in scraped competitor facts to cut hallucination. The `VectorStore`
interface (`app/rag/store.py`) makes the swap one line, and a keyless hash-embed
fallback keeps even the RAG path runnable at $0.

---

## Summary — prod vs demo, and why

| Layer | Demo (free, runs now) | Prod (recommended) | Primary reason for prod pick |
|---|---|---|---|
| LLM (reasoning) | Groq Llama-3.3-70B | Claude Sonnet 5 | Best long-form + editorial quality |
| LLM (bulk/structured) | Groq Llama-3.3-70B | GPT-4o-mini | ~20× cheaper, quality parity on simple steps |
| Orchestration | LangGraph | LangGraph | Explicit, testable, resumable DAG |
| Search + scrape | Firecrawl (free tier) | Firecrawl (paid) + Bright Data | SERP+scrape in one; scale headroom |
| Vector store | Chroma (embedded) | Pinecone (serverless) | Zero-ops scale for content library |
| Business front-door | CLI / FastAPI | n8n visual trigger | Non-dev operability |

Every demo→prod swap is a **registry/config change**, never a rewrite — see
`app/llm/registry.py`, `app/search/registry.py`, `app/rag/store.py`.
