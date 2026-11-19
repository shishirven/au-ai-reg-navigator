"""Query expansion and cross-encoder re-ranking (D-042). Fake scorer: no model download."""

from __future__ import annotations

import pytest

from regnav.config import AppConfig
from regnav.retrieve.base import Filters, RetrievedChunk
from regnav.retrieve.expand import expand_query
from regnav.retrieve.rerank import ExpandingRetriever, RerankRetriever


@pytest.mark.parametrize(
    "question,must_add,must_not_add",
    [
        (
            "What must we do before engaging a third-party AI vendor?",
            ["service", "provider", "arrangement"],
            [],
        ),
        ("Who is accountable for AI systems?", ["information", "asset"], ["arrangement"]),
        ("Our AI claims triage had an outage", ["incident", "disruption", "critical"], []),
        ("Do we need an inventory of models?", ["register", "classify"], ["service"]),
        ("What does CPS 230 para 52 say?", [], ["service", "asset"]),  # no AI wording -> unchanged
    ],
)
def test_expand_query(question, must_add, must_not_add) -> None:
    out = expand_query(question)
    assert out.startswith(question)
    added = out[len(question) :].lower().split()
    for w in must_add:
        assert w in added
    for w in must_not_add:
        assert w not in added
    if not must_add:
        assert out == question
    assert len(added) == len(set(added))  # deduplicated


def _c(cid: str, text: str, rank: int) -> RetrievedChunk:
    return RetrievedChunk(cid, text, {"tier": "binding", "status": "current"}, 1.0 / rank, rank)


class _Base:
    name = "base"

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def search(self, query, k, filters):
        self.calls.append((query, k))
        pool = [
            _c("a", "about cats", 1),
            _c("b", "service provider due diligence", 2),
            _c("c", "about dogs", 3),
        ]
        return pool[:k]


class _KeywordScorer:
    def score(self, query: str, texts: list[str]) -> list[float]:
        return [float(sum(w in t for w in query.lower().split())) for t in texts]


def test_rerank_reorders_pool_and_records_scores() -> None:
    base = _Base()
    out = RerankRetriever(base, _KeywordScorer(), pool_k=3).search("service provider", 2, Filters())
    assert [c.chunk_id for c in out] == [
        "b",
        "a",
    ]  # b promoted from rank 2 to 1; ties keep original order
    assert base.calls == [("service provider", 3)]  # pool_k candidates requested
    assert (
        out[0].rank == 1
        and out[0].scores["pre_rerank_rank"] == 2.0
        and out[0].scores["rerank"] == 2.0
    )


def test_expanding_retriever_passes_expanded_query() -> None:
    base = _Base()
    ExpandingRetriever(base).search("AI vendor checks", 1, Filters())
    assert "service provider" in base.calls[0][0]


def test_build_retrieval_wires_rerank_inside_tiers(fixture_cfg: AppConfig, monkeypatch) -> None:
    from regnav.ingest.index import ingest
    from regnav.retrieve import build_retrieval
    from regnav.retrieve import rerank as rerank_mod
    from regnav.retrieve.stratified import StratifiedRetriever

    monkeypatch.setattr(rerank_mod, "CrossEncoderScorer", lambda model: _KeywordScorer())
    ingest(fixture_cfg)
    fixture_cfg.retrieval = fixture_cfg.retrieval.model_copy(
        update={"mode": "stratified", "rerank": True, "query_expansion": True, "per_tier_k": 2}
    )
    rs = build_retrieval(fixture_cfg)
    assert isinstance(rs.retriever, ExpandingRetriever)
    assert isinstance(rs.retriever.base, StratifiedRetriever)
    assert isinstance(rs.retriever.base.base, RerankRetriever)
    chunks = rs.search(
        "What do we need to do before engaging a third-party AI vendor?", sector="bank"
    )
    assert len(chunks) == 6 and {c.tier for c in chunks} == {"binding", "expectation", "voluntary"}
    assert all("rerank" in c.scores for c in chunks)
