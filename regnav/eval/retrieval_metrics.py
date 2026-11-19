"""Deterministic retrieval metrics (no LLM)."""

from __future__ import annotations

from collections.abc import Sequence


def recall_at_k(retrieved: Sequence[str], gold: Sequence[str], k: int = 5) -> float | None:
    """Share of gold chunks found in the top-k. None when there is no gold (unanswerable)."""
    if not gold:
        return None
    top = set(retrieved[:k])
    return len(top & set(gold)) / len(set(gold))


def reciprocal_rank(retrieved: Sequence[str], gold: Sequence[str]) -> float | None:
    if not gold:
        return None
    gold_set = set(gold)
    for i, cid in enumerate(retrieved, start=1):
        if cid in gold_set:
            return 1.0 / i
    return 0.0


def binding_coverage(retrieved_tiers: Sequence[str], gold_tiers: Sequence[str]) -> float | None:
    """1 if the question has a binding gold chunk and >=1 binding chunk was retrieved, 0 if
    it has one and none was retrieved, None if the question has no binding gold chunk."""
    if "binding" not in gold_tiers:
        return None
    return 1.0 if "binding" in retrieved_tiers else 0.0


def binding_gold_hit(
    retrieved: Sequence[str], gold: Sequence[str], tier_of: dict[str, str]
) -> float | None:
    """Stricter: a *gold* binding chunk itself was retrieved."""
    binding_gold = {g for g in gold if tier_of.get(g) == "binding"}
    if not binding_gold:
        return None
    return 1.0 if binding_gold & set(retrieved) else 0.0
