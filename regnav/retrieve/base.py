"""Shared retrieval types and metadata filters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from regnav.config import TIERS


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    score: float
    rank: int = 0
    # per-retriever evidence, e.g. {"dense": 0.71, "bm25": 12.3, "rrf": 0.032}
    scores: dict[str, float] = field(default_factory=dict)

    @property
    def tier(self) -> str:
        return str(self.metadata.get("tier", ""))

    @property
    def modality(self) -> str:
        return str(self.metadata.get("modality", "info"))


@dataclass(frozen=True)
class Filters:
    """Metadata filters applied identically to dense (Chroma ``where``) and BM25."""

    sector: str | None = None  # bank | insurer | super | any_business
    tiers: tuple[str, ...] | None = None
    include_superseded: bool = False

    def with_tier(self, tier: str) -> Filters:
        return Filters(self.sector, (tier,), self.include_superseded)

    def to_where(self) -> dict[str, Any] | None:
        clauses: list[dict[str, Any]] = []
        if self.sector and self.sector != "any_business":
            clauses.append(
                {"$or": [{f"applies_{self.sector}": True}, {"applies_any_business": True}]}
            )
        if self.tiers and set(self.tiers) != set(TIERS):
            clauses.append(
                {"tier": self.tiers[0]}
                if len(self.tiers) == 1
                else {"tier": {"$in": list(self.tiers)}}
            )
        if not self.include_superseded:
            clauses.append({"status": "current"})
        if not clauses:
            return None
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}

    def matches(self, meta: dict[str, Any]) -> bool:
        if (
            self.sector
            and self.sector != "any_business"
            and not (meta.get(f"applies_{self.sector}") or meta.get("applies_any_business"))
        ):
            return False
        if self.tiers and meta.get("tier") not in self.tiers:
            return False
        return self.include_superseded or meta.get("status") == "current"


class Retriever(Protocol):
    name: str

    def search(self, query: str, k: int, filters: Filters) -> list[RetrievedChunk]: ...


def rerank(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    for i, c in enumerate(chunks, start=1):
        c.rank = i
    return chunks
