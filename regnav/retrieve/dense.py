"""Dense retrieval: Chroma cosine search over BGE embeddings."""

from __future__ import annotations

from regnav.ingest.embed import Embedder
from regnav.retrieve.base import Filters, RetrievedChunk, rerank


class DenseRetriever:
    name = "dense"

    def __init__(self, collection, embedder: Embedder) -> None:
        self.collection = collection
        self.embedder = embedder

    def search(self, query: str, k: int, filters: Filters) -> list[RetrievedChunk]:
        n = self.collection.count()
        if n == 0 or k <= 0:
            return []
        res = self.collection.query(
            query_embeddings=[self.embedder.embed_query(query).tolist()],
            n_results=min(k, n),
            where=filters.to_where(),
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for cid, doc, meta, dist in zip(
            res["ids"][0],
            res["documents"][0],
            res["metadatas"][0],
            res["distances"][0],
            strict=True,
        ):
            sim = 1.0 - float(dist)  # cosine distance -> similarity
            out.append(RetrievedChunk(cid, doc, dict(meta), sim, scores={"dense": sim}))
        return rerank(out)
