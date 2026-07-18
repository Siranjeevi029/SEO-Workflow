"""Append-only JSONL tracer for every agent action.

One event per line in traces/trace.jsonl. Groups events by run_id so a full
pipeline can be replayed / inspected. This is the single source of truth for
"what did each agent do" — used by both humans and the /trace API endpoint.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.config import get_settings

_LOCK = threading.Lock()


def new_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


def _now_ms() -> int:
    return int(time.time() * 1000)


class Tracer:
    """Per-run tracer. Writes structured events; never raises on logging."""

    def __init__(self, run_id: str | None = None, path: Path | None = None,
                 fresh: bool = True):
        self.run_id = run_id or new_run_id()
        self.path = path or get_settings().trace_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        if fresh:
            # each new run starts a clean trace file — no cross-run buildup
            self.path.write_text("", encoding="utf-8")

    def _write(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _LOCK:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def event(
        self,
        agent: str,
        action: str,
        status: str = "ok",
        data: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        self._seq += 1
        rec = {
            "run_id": self.run_id,
            "seq": self._seq,
            "ts_ms": _now_ms(),
            "agent": agent,
            "action": action,
            "status": status,
        }
        if duration_ms is not None:
            rec["duration_ms"] = duration_ms
        if error:
            rec["error"] = error
        if data is not None:
            rec["data"] = data
        self._write(rec)

    def step(self, agent: str, action: str, data: dict[str, Any] | None = None):
        """Context manager: auto-times a step and logs start/finish/error."""
        return _Step(self, agent, action, data)


class _Step:
    def __init__(self, tracer: Tracer, agent: str, action: str, data):
        self.t = tracer
        self.agent = agent
        self.action = action
        self.data = data or {}
        self.start = 0.0

    def __enter__(self):
        self.start = time.time()
        self.t.event(self.agent, self.action, status="start", data=self.data)
        return self

    def __exit__(self, exc_type, exc, tb):
        dur = int((time.time() - self.start) * 1000)
        if exc:
            self.t.event(
                self.agent, self.action, status="error",
                duration_ms=dur, error=f"{exc_type.__name__}: {exc}",
            )
        else:
            self.t.event(self.agent, self.action, status="ok", duration_ms=dur)
        return False  # never swallow exceptions


def read_run(run_id: str, path: Path | None = None) -> list[dict[str, Any]]:
    """Read all events for a run_id (for the /trace endpoint & inspection)."""
    p = path or get_settings().trace_path
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("run_id") == run_id:
                out.append(rec)
    return out
