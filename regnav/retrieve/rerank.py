"""Cross-encoder re-ranking of a retriever's candidate pool (D-042).

Diagnostics showed 97% of gold paragraphs are in the top-40 hybrid candidates per tier but only
61% reach the 9-chunk context: a *ranking* problem. A cross-encoder reads (question, paragraph)
together and re-scores the pool; used inside each tier quota so tier guarantees are kept.
"""

from __future__ import annotations

from functools import lru_cache

from regnav.retrieve.base import Filters, RetrievedChunk, Retriever, rerank


@lru_cache(maxsize=2)
def _cross_encoder(model_name: str, device: str = "cpu"):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device=device, max_length=512)


class CrossEncoderScorer:
    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        model = _cross_encoder(self.model_name, self.device)
        return [
            float(s)
            for s in model.predict(
                [(query, t) for t in texts], batch_size=32, show_progress_bar=False
            )
        ]


class RerankRetriever:
    """Wraps a retriever: fetch ``pool_k`` candidates, re-score with ``scorer``, return top ``k``.
    ``rerank_query`` lets the reranker see the original question while retrieval used an
    expanded one (or vice versa)."""

    name = "rerank"

    def __init__(self, base: Retriever, scorer, pool_k: int = 20) -> None:
        self.base = base
        self.scorer = scorer
        self.pool_k = pool_k

    def search(self, query: str, k: int, filters: Filters) -> list[RetrievedChunk]:
        pool = self.base.search(query, max(k, self.pool_k), filters)
        scores = self.scorer.score(query, [c.text for c in pool])
        for c, s in zip(pool, scores, strict=True):
            c.scores["rerank"] = s
            c.scores.setdefault("pre_rerank_rank", float(c.rank))
            c.score = s
        pool.sort(key=lambda c: (-c.score, c.rank))
        return rerank(pool[:k])


class ExpandingRetriever:
    """Applies deterministic query expansion before delegating."""

    name = "expand"

    def __init__(self, base: Retriever) -> None:
        self.base = base

    def search(self, query: str, k: int, filters: Filters) -> list[RetrievedChunk]:
        from regnav.retrieve.expand import expand_query

        return self.base.search(expand_query(query), k, filters)
