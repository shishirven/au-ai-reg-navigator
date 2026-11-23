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
        hybrid: Retriever = HybridRetriever(
            [dense, BM25Retriever(load_chunk_rows(cfg))], r.candidate_k, r.rrf_k
        )
        if r.rerank:  # re-rank the fused candidates (inside each tier when stratified)
            from regnav.retrieve.rerank import CrossEncoderScorer, RerankRetriever

            hybrid = RerankRetriever(hybrid, CrossEncoderScorer(r.rerank_model), r.rerank_pool_k)
        if r.mode == "hybrid":
            retriever, top_k = hybrid, r.top_k
        else:
            retriever, top_k = (
                StratifiedRetriever(
                    hybrid, r.per_tier_k, per_doc_cap=r.per_doc_cap, depth=r.tier_depth
                ),
                r.per_tier_k * 3,
            )
    planned = r.mode == "stratified" and (
        r.strip_instructions or r.stage_queries or r.per_doc_cap is not None
    )
    if planned:
        from regnav.retrieve.plan import PlannedRetriever

        assert isinstance(retriever, StratifiedRetriever)
        retriever = PlannedRetriever(
            retriever, r.strip_instructions, r.stage_queries, r.query_expansion, r.max_stages
        )
    elif r.query_expansion:
        from regnav.retrieve.rerank import ExpandingRetriever

        retriever = ExpandingRetriever(retriever)
    return RetrievalSystem(
        retriever,
        top_k,
        manifest["index_version"],
        r.include_superseded,
        r.sector_filter,
        instruments,
    )


__all__ = ["Filters", "RetrievalSystem", "RetrievedChunk", "build_retrieval"]
