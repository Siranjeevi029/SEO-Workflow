"""Vector store abstraction for the (optional) RAG grounding step.

DEMO: local Chroma (embedded, free, no server) with a hash-based fallback
embedder so it runs with zero keys.
PROD: Pinecone (serverless) — same interface, documented in docs/02-architecture.md.

Purpose in the workflow: index the scraped competitor pages so the writer/editor
can retrieve grounded facts instead of hallucinating. Kept optional so the core
demo runs even if chromadb is not installed.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Doc:
    id: str
    text: str
    meta: dict


def _hash_embed(text: str, dim: int = 256) -> list[float]:
    """Deterministic keyless embedding (bag-of-hashed-tokens). Demo-only."""
    vec = [0.0] * dim
    for tok in text.lower().split():
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


class VectorStore(ABC):
    @abstractmethod
    def add(self, docs: list[Doc]) -> None: ...

    @abstractmethod
    def query(self, text: str, k: int = 3) -> list[Doc]: ...


class ChromaStore(VectorStore):
    """Local embedded Chroma. Falls back to in-memory cosine if chroma missing."""

    def __init__(self, collection: str = "seo-content-workflow"):
        self._docs: list[Doc] = []
        self._vecs: list[list[float]] = []
        try:
            import chromadb
            self._client = chromadb.Client()
            self._col = self._client.get_or_create_collection(collection)
            self._backend = "chroma"
        except Exception:
            self._backend = "memory"

    def add(self, docs: list[Doc]) -> None:
        if self._backend == "chroma":
            self._col.add(
                ids=[d.id for d in docs],
                documents=[d.text for d in docs],
                embeddings=[_hash_embed(d.text) for d in docs],
                metadatas=[d.meta for d in docs],
            )
        else:
            for d in docs:
                self._docs.append(d)
                self._vecs.append(_hash_embed(d.text))

    def query(self, text: str, k: int = 3) -> list[Doc]:
        q = _hash_embed(text)
        if self._backend == "chroma":
            res = self._col.query(query_embeddings=[q], n_results=k)
            out = []
            for i, doc in enumerate(res.get("documents", [[]])[0]):
                meta = res.get("metadatas", [[]])[0][i] if res.get("metadatas") else {}
                out.append(Doc(id=str(i), text=doc, meta=meta or {}))
            return out
        scored = sorted(
            zip(self._docs, self._vecs),
            key=lambda dv: -sum(a * b for a, b in zip(q, dv[1])),
        )
        return [d for d, _ in scored[:k]]
