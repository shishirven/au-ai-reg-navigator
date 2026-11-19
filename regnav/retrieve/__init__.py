"""Retrieval: dense, BM25, hybrid (RRF) and tier-stratified, behind one factory."""

from __future__ import annotations

from dataclasses import dataclass, field

from regnav.config import AppConfig
from regnav.retrieve.base import Filters, RetrievedChunk, Retriever


@dataclass
class RetrievalSystem:
    retriever: Retriever
    top_k: int
    index_version: str
    include_superseded: bool
    sector_filter: bool
    known_instruments: set[str] = field(default_factory=set)

    def search(self, query: str, sector: str | None = None) -> list[RetrievedChunk]:
        filters = Filters(
            sector=sector if self.sector_filter else None,
            include_superseded=self.include_superseded,
        )
        return self.retriever.search(query, self.top_k, filters)


def build_retrieval(cfg: AppConfig) -> RetrievalSystem:
    from regnav.ingest.embed import get_embedder
    from regnav.ingest.index import get_collection, load_chunk_rows, load_manifest
    from regnav.retrieve.bm25 import BM25Retriever
    from regnav.retrieve.dense import DenseRetriever
    from regnav.retrieve.hybrid import HybridRetriever
    from regnav.retrieve.stratified import StratifiedRetriever

    manifest = load_manifest(cfg)
    if manifest is None:
        raise FileNotFoundError("no index found - run `make ingest` first")
    rows = load_chunk_rows(cfg)
    instruments = {str(r.get("short_name", "")) for r in rows}
    r = cfg.retrieval
    dense = DenseRetriever(get_collection(cfg), get_embedder(cfg.embedding))
    retriever: Retriever
    if r.mode == "dense":
        retriever = dense
        top_k = r.top_k
    else:
        hybrid = HybridRetriever(
            [dense, BM25Retriever(load_chunk_rows(cfg))], r.candidate_k, r.rrf_k
        )
        if r.mode == "hybrid":
            retriever, top_k = hybrid, r.top_k
        else:
            retriever, top_k = StratifiedRetriever(hybrid, r.per_tier_k), r.per_tier_k * 3
    return RetrievalSystem(
        retriever,
        top_k,
        manifest["index_version"],
        r.include_superseded,
        r.sector_filter,
        instruments,
    )


__all__ = ["Filters", "RetrievalSystem", "RetrievedChunk", "build_retrieval"]
