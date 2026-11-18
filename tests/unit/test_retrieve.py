import pytest

from regnav.retrieve.base import Filters, RetrievedChunk
from regnav.retrieve.bm25 import BM25Retriever, tokenize
from regnav.retrieve.hybrid import HybridRetriever, rrf_fuse
from regnav.retrieve.stratified import StratifiedRetriever, stratified_merge


def test_rrf_hand_computed() -> None:
    # k=60: a = 1/61 + 1/62, b = 1/62 + 1/61, c = 1/63, d = 1/63
    fused = dict(rrf_fuse([["a", "b", "c"], ["b", "a", "d"]], k=60))
    assert fused["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert fused["c"] == pytest.approx(1 / 63)
    assert fused["d"] == pytest.approx(1 / 63)


def test_rrf_ordering_and_deterministic_ties() -> None:
    order = [d for d, _ in rrf_fuse([["a", "b", "c"], ["b", "a", "d"]])]
    assert order == ["a", "b", "c", "d"]  # a/b tie -> first seen; c/d tie -> first seen
    assert next(d for d, _ in rrf_fuse([["x"], ["y", "x"]])) == "x"  # in both lists beats single
    assert rrf_fuse([]) == []


def _c(cid: str, tier: str, score: float, rank: int) -> RetrievedChunk:
    return RetrievedChunk(cid, cid, {"tier": tier, "status": "current"}, score, rank)


def test_stratified_merge_interleaves_and_keeps_every_tier() -> None:
    merged = stratified_merge(
        {
            "binding": [_c("b1", "binding", 0.02, 1), _c("b2", "binding", 0.01, 2)],
            "expectation": [_c("e1", "expectation", 0.03, 1)],
            "voluntary": [_c("v1", "voluntary", 0.05, 1), _c("v2", "voluntary", 0.04, 2)],
        }
    )
    ids = [c.chunk_id for c in merged]
    assert ids == ["v1", "e1", "b1", "v2", "b2"]
    assert [c.rank for c in merged] == [1, 2, 3, 4, 5]
    assert {c.tier for c in merged[:3]} == {"binding", "expectation", "voluntary"}


class _FakeRetriever:
    name = "fake"

    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks
        self.calls: list[Filters] = []

    def search(self, query, k, filters):
        self.calls.append(filters)
        return [c for c in self.chunks if filters.matches(c.metadata)][:k]


def test_stratified_returns_at_least_one_chunk_per_available_tier() -> None:
    pool = [_c(f"v{i}", "voluntary", 1 - i / 10, i) for i in range(1, 8)] + [
        _c("b1", "binding", 0.1, 1),
        _c("e1", "expectation", 0.2, 1),
    ]
    base = _FakeRetriever(pool)
    out = StratifiedRetriever(base, per_tier_k=2).search("q", 6, Filters())
    tiers = [c.tier for c in out]
    assert (
        tiers.count("binding") == 1
        and tiers.count("expectation") == 1
        and tiers.count("voluntary") == 2
    )
    assert [f.tiers for f in base.calls] == [("binding",), ("expectation",), ("voluntary",)]


def test_stratified_respects_tier_filter_and_missing_tiers() -> None:
    base = _FakeRetriever([_c("v1", "voluntary", 1, 1)])
    out = StratifiedRetriever(base, per_tier_k=3).search("q", 9, Filters(tiers=("voluntary",)))
    assert [c.chunk_id for c in out] == ["v1"]
    assert len(base.calls) == 1


def test_hybrid_merges_scores_from_both_retrievers() -> None:
    a = _FakeRetriever([_c("x", "binding", 0.9, 1), _c("y", "binding", 0.8, 2)])
    b = _FakeRetriever([_c("y", "binding", 5.0, 1)])
    for c in a.chunks:
        c.scores = {"dense": c.score}
    b.chunks[0].scores = {"bm25": 5.0}
    out = HybridRetriever([a, b], candidate_k=10).search("q", 2, Filters())
    assert out[0].chunk_id == "y"
    assert set(out[0].scores) >= {"rrf"}


@pytest.mark.parametrize(
    "filters,meta,expected",
    [
        (Filters(sector="bank"), {"applies_bank": True, "status": "current"}, True),
        (
            Filters(sector="super"),
            {"applies_bank": True, "applies_super": False, "status": "current"},
            False,
        ),
        (Filters(sector="super"), {"applies_any_business": True, "status": "current"}, True),
        (Filters(), {"status": "superseded"}, False),
        (Filters(include_superseded=True), {"status": "superseded"}, True),
        (Filters(tiers=("binding",)), {"tier": "voluntary", "status": "current"}, False),
    ],
)
def test_filter_matches(filters: Filters, meta: dict, expected: bool) -> None:
    assert filters.matches(meta) is expected


def test_filter_to_where() -> None:
    assert Filters(include_superseded=True).to_where() is None
    assert Filters().to_where() == {"status": "current"}
    where = Filters(sector="insurer", tiers=("binding",)).to_where()
    assert where == {
        "$and": [
            {"$or": [{"applies_insurer": True}, {"applies_any_business": True}]},
            {"tier": "binding"},
            {"status": "current"},
        ]
    }
    assert Filters(tiers=("binding", "voluntary")).to_where()["$and"][0] == {
        "tier": {"$in": ["binding", "voluntary"]}
    }


def test_bm25_tokenizer_and_search() -> None:
    assert tokenize("Service providers' AI-vendors and the policies") == [
        "service",
        "provider",
        "ai-vendor",
        "policy",
    ]
    rows = [
        {
            "chunk_id": "a",
            "text": "material service provider policy",
            "tier": "binding",
            "status": "current",
        },
        {
            "chunk_id": "b",
            "text": "artificial intelligence vendors",
            "tier": "voluntary",
            "status": "current",
        },
        {
            "chunk_id": "c",
            "text": "service provider old",
            "tier": "binding",
            "status": "superseded",
        },
    ]
    r = BM25Retriever(rows)
    out = r.search("service providers", 5, Filters())
    assert [c.chunk_id for c in out] == ["a"]  # c is superseded, b has no overlap
    assert out[0].rank == 1 and "bm25" in out[0].scores
    assert BM25Retriever([]).search("x", 3, Filters()) == []
