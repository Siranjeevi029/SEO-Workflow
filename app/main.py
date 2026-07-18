"""FastAPI surface for the SEO content workflow.

Endpoints:
  GET  /            -> minimal demo UI
  GET  /health      -> active demo stack (llm/search/mode)
  POST /generate    -> run the full pipeline, returns article + seo + meta + run_id
  GET  /trace/{id}  -> replay all trace events for a run
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agents.graph import run_pipeline
from app.config import get_settings
from app.llm.registry import get_llm
from app.search.registry import get_search
from app.trace import read_run

app = FastAPI(title="SEO Content Workflow", version="0.1.0")


class GenerateRequest(BaseModel):
    topic: str
    target_keyword: str = ""
    audience: str = "general"
    tone: str = "professional"


@app.get("/health")
def health():
    s = get_settings()
    return {
        "mode": s.app_mode,
        "llm": get_llm(s).name,
        "search": get_search(s).name,
        "note": "mock/ddg used when keys absent — pipeline still runs free.",
    }


@app.post("/generate")
def generate(req: GenerateRequest):
    result = run_pipeline(
        topic=req.topic, target_keyword=req.target_keyword,
        audience=req.audience, tone=req.tone,
    )
    return JSONResponse({
        "run_id": result.get("run_id"),
        "brief": result.get("brief"),
        "outline": result.get("outline"),
        "article": result.get("article"),
        "seo": result.get("seo"),
        "meta": result.get("meta"),
        "serp_insights": result.get("serp_insights"),
    })


@app.get("/trace/{run_id}")
def trace(run_id: str):
    return {"run_id": run_id, "events": read_run(run_id)}


@app.get("/")
def index():
    from pathlib import Path
    idx = Path(__file__).resolve().parent.parent / "static" / "index.html"
    return FileResponse(str(idx))


# serve static assets
from pathlib import Path as _P  # noqa: E402

_static = _P(__file__).resolve().parent.parent / "static"
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")
