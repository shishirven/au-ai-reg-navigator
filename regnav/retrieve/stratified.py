"""Tier-stratified retrieval: run the base retriever once per authority tier with a quota,
then merge. Guarantees binding standards (which never say "AI") get a seat at the table
even when voluntary guidance (which says "AI" everywhere) dominates pooled similarity.

Merge order: by within-tier score, ties broken by tier authority (binding first). With RRF
scores this interleaves tiers rank-by-rank: [B1, E1, V1, B2, E2, V2, ...].

Two opt-in extensions (D-052), both off by default so earlier configs are unchanged:

* ``per_doc_cap``: prefer at most N chunks from one document per tier. Without it a long
  document can take every slot in its tier (F-12: the OAIC AI-products guidance crowded out the
  APP 1.7-1.9 fact sheet; CPS 230 crowded out CPS 234). The cap is *soft*: if a tier has no other
  documents (voluntary: only AI6 is current), remaining slots are refilled from capped chunks.
* ``search_multi``: several queries (the question plus stage sub-queries). Each tier's slots
  are filled round-robin from the per-query rankings, the question first, each query adding its
  best chunk not already picked.
"""

from __future__ import annotations

from collections import Counter

from regnav.config import TIERS
from regnav.retrieve.base import Filters, RetrievedChunk, Retriever, rerank


def stratified_merge(per_tier: dict[str, list[RetrievedChunk]]) -> list[RetrievedChunk]:
    order: dict[str, int] = {t: i for i, t in enumerate(TIERS)}
    merged = [c for chunks in per_tier.values() for c in chunks]
    merged.sort(key=lambda c: (c.rank, -c.score, order.get(c.tier, 99)))
    return rerank(merged)


def select(
    rankings: list[list[RetrievedChunk]],
    k: int,
    per_doc_cap: int | None = None,
    labels: list[str] | None = None,
) -> list[RetrievedChunk]:
    """Pick ``k`` chunks from one or more rankings of the same tier.

    Round-robin over the rankings (the question first): in each round every ranking contributes
    its best *eligible* chunk, i.e. the highest-ranked one not already picked and whose document
    is under ``per_doc_cap``. So each stage gets a seat with its own best match, instead of
    re-offering a document that already has its share. The cap is soft: if the tier is still
    short when the rankings are exhausted, capped chunks fill the remaining slots in order.
    ``labels[i]`` is recorded on chunks found by ranking ``i`` (``metadata["matched"]``).
    """
    picked: list[RetrievedChunk] = []
    seen: set[str] = set()
    per_doc: Counter[str] = Counter()
    deferred: list[tuple[int, RetrievedChunk]] = []
    pointers = [0] * len(rankings)

    def doc(c: RetrievedChunk) -> str:
        return str(c.metadata.get("doc_id", ""))

    def take(i: int, c: RetrievedChunk) -> None:
        seen.add(c.chunk_id)
        per_doc[doc(c)] += 1
        if labels is not None:
            c.metadata = {**c.metadata, "matched": labels[i]}
        picked.append(c)

    def next_eligible(i: int) -> RetrievedChunk | None:
        r = rankings[i]
        while pointers[i] < len(r):
            c = r[pointers[i]]
            pointers[i] += 1
            if c.chunk_id in seen:
                continue
            if per_doc_cap is not None and per_doc[doc(c)] >= per_doc_cap:
                deferred.append((i, c))
                continue
            return c
        return None

    while len(picked) < k and any(p < len(r) for p, r in zip(pointers, rankings, strict=True)):
        for i in range(len(rankings)):
            if len(picked) == k:
                break
            c = next_eligible(i)
            if c is not None:
                take(i, c)
    for i, c in deferred:  # soft cap: refill a short tier
        if len(picked) == k:
            break
        if c.chunk_id not in seen:
            take(i, c)
    return rerank(picked)


class StratifiedRetriever:
    name = "stratified"

    def __init__(
        self,
        base: Retriever,
        per_tier_k: int = 3,
        tiers: tuple[str, ...] = TIERS,
        per_doc_cap: int | None = None,
        depth: int = 40,
        cap_tiers: tuple[str, ...] | None = None,
    ) -> None:
        self.base = base
        self.per_tier_k = per_tier_k
        self.tiers = tiers
        self.per_doc_cap = per_doc_cap
        self.depth = depth  # candidates considered per tier when capping or merging queries
        self.cap_tiers = cap_tiers  # tiers the per-document cap applies to (None = all)

    def _allowed(self, filters: Filters) -> list[str]:
        return [t for t in self.tiers if not filters.tiers or t in filters.tiers]

    def search(self, query: str, k: int, filters: Filters) -> list[RetrievedChunk]:
        if self.per_doc_cap is None:  # original behaviour, exactly
            per_tier = {
                t: self.base.search(query, self.per_tier_k, filters.with_tier(t))
                for t in self._allowed(filters)
            }
            return stratified_merge(per_tier)[:k] if k else stratified_merge(per_tier)
        return self.search_multi([query], k, filters)

    def search_multi(
        self,
        queries: list[str],
        k: int,
        filters: Filters,
        labels: list[str] | None = None,
        per_tier_k: int | None = None,
    ) -> list[RetrievedChunk]:
        quota = per_tier_k or self.per_tier_k
        depth = max(self.depth, quota)
        per_tier = {}
        for t in self._allowed(filters):
            cap = self.per_doc_cap if self.cap_tiers is None or t in self.cap_tiers else None
            # An uncapped tier searched with one query behaves exactly like the original
            # retriever (top `quota`); only capped or multi-query tiers look deeper.
            n = depth if (cap is not None or len(queries) > 1) else quota
            rankings = [self.base.search(q, n, filters.with_tier(t)) for q in queries]
            per_tier[t] = select(rankings, quota, cap, labels)
        merged = stratified_merge(per_tier)
        return merged[:k] if k else merged
