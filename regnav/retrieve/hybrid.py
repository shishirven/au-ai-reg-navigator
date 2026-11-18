"""Hybrid retrieval: dense + BM25 fused with Reciprocal Rank Fusion (RRF).

RRF(d) = sum over rankers r of 1 / (k + rank_r(d)), k = 60 (Cormack, Clarke & Buettcher 2009).
Rank-based, so the incomparable score scales of cosine similarity and BM25 do not matter.
"""

from __future__ import annotations

from regnav.retrieve.base import Filters, RetrievedChunk, Retriever, rerank


def rrf_fuse(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fuse ranked id lists. Ties are broken by first appearance (deterministic)."""
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    pos = 0
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in first_seen:
                first_seen[doc_id] = pos
                pos += 1
    return sorted(scores.items(), key=lambda kv: (-kv[1], first_seen[kv[0]]))


class HybridRetriever:
    name = "hybrid"

    def __init__(self, retrievers: list[Retriever], candidate_k: int = 40, rrf_k: int = 60) -> None:
        self.retrievers = retrievers
        self.candidate_k = candidate_k
        self.rrf_k = rrf_k

    def search(self, query: str, k: int, filters: Filters) -> list[RetrievedChunk]:
        by_id: dict[str, RetrievedChunk] = {}
        rankings: list[list[str]] = []
        for r in self.retrievers:
            results = r.search(query, self.candidate_k, filters)
            rankings.append([c.chunk_id for c in results])
            for c in results:
                if c.chunk_id in by_id:
                    by_id[c.chunk_id].scores.update(c.scores)
                else:
                    by_id[c.chunk_id] = c
        out = []
        for cid, score in rrf_fuse(rankings, self.rrf_k)[:k]:
            c = by_id[cid]
            c.score = score
            c.scores["rrf"] = score
            out.append(c)
        return rerank(out)
