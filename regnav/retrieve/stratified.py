"""Tier-stratified retrieval: run the base retriever once per authority tier with a quota,
then merge. Guarantees binding standards (which never say "AI") get a seat at the table
even when voluntary guidance (which says "AI" everywhere) dominates pooled similarity.

Merge order: by within-tier score, ties broken by tier authority (binding first). With RRF
scores this interleaves tiers rank-by-rank: [B1, E1, V1, B2, E2, V2, ...].
"""

from __future__ import annotations

from regnav.config import TIERS
from regnav.retrieve.base import Filters, RetrievedChunk, Retriever, rerank


def stratified_merge(per_tier: dict[str, list[RetrievedChunk]]) -> list[RetrievedChunk]:
    order: dict[str, int] = {t: i for i, t in enumerate(TIERS)}
    merged = [c for chunks in per_tier.values() for c in chunks]
    merged.sort(key=lambda c: (c.rank, -c.score, order.get(c.tier, 99)))
    return rerank(merged)


class StratifiedRetriever:
    name = "stratified"

    def __init__(
        self, base: Retriever, per_tier_k: int = 3, tiers: tuple[str, ...] = TIERS
    ) -> None:
        self.base = base
        self.per_tier_k = per_tier_k
        self.tiers = tiers

    def search(self, query: str, k: int, filters: Filters) -> list[RetrievedChunk]:
        allowed = [t for t in self.tiers if not filters.tiers or t in filters.tiers]
        per_tier = {
            t: self.base.search(query, self.per_tier_k, filters.with_tier(t)) for t in allowed
        }
        return stratified_merge(per_tier)[:k] if k else stratified_merge(per_tier)
