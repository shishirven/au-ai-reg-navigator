"""Retrieval fixes (D-052): instruction stripping, stage sub-queries, per-document cap."""

from __future__ import annotations

import pytest

from regnav.retrieve.base import Filters, RetrievedChunk
from regnav.retrieve.plan import PlannedRetriever, make_plan
from regnav.retrieve.query import strip_instructions
from regnav.retrieve.stages import is_broad, load_playbooks, stages_for_question
from regnav.retrieve.stratified import StratifiedRetriever, select

OPUS_QUESTION = (
    "from an australian regulations standpoint, What do we need to do before engaging a "
    "third-party AI vendor ? consider APRA and CPS standards at a minimum, and highight which are "
    "mandatory (binding by law), which are what regulatry expects, and what is reccommneded but "
    "by voluntary guidance"
)


# --- instruction stripping -------------------------------------------------------------------


def test_strips_authority_instruction_keeps_topic_and_scope() -> None:
    r = strip_instructions(OPUS_QUESTION)
    assert r.changed
    assert "consider APRA and CPS standards at a minimum" in r.search
    assert "third-party AI vendor" in r.search
    for w in ["mandatory", "voluntary", "reccommneded", "highight"]:
        assert w not in r.search


@pytest.mark.parametrize(
    "question,removed_fragment",
    [
        (
            "What does APRA expect for model monitoring? Please show which items are mandatory "
            "and which are recommended.",
            "mandatory",
        ),
        ("List the contract terms CPS 230 requires. Use a table.", "Use a table."),
    ],
)
def test_strips_format_requests(question: str, removed_fragment: str) -> None:
    r = strip_instructions(question)
    assert any(removed_fragment in x for x in r.removed)
    assert r.search.endswith(("?", "."))


@pytest.mark.parametrize(
    "question",
    [
        "Which requirements are mandatory for AI vendors under CPS 230?",  # authority IS the topic
        "Is AI6 voluntary or binding?",
        "What is the difference between binding standards and guidance?",
        "Show me what CPS 234 says about third parties",
        "What do we need to do before engaging a third-party AI vendor?",
    ],
)
def test_leaves_real_questions_alone(question: str) -> None:
    r = strip_instructions(question)
    assert not r.changed and r.search == question


def test_never_returns_empty_search() -> None:
    q = "Highlight what is binding and what is voluntary"
    assert strip_instructions(q).search == q


# --- playbooks and stage planning -------------------------------------------------------------


def test_playbooks_load_and_are_well_formed() -> None:
    pbs = load_playbooks()
    ids = [s.id for pb in pbs for s in pb.stages]
    assert len(ids) == len(set(ids)) >= 15
    for pb in pbs:
        assert pb.stages and pb.when
        for s in pb.stages:
            assert s.query and s.evidence and s.involve


@pytest.mark.parametrize(
    "question,broad",
    [
        ("What do we need to do before engaging a third-party AI vendor?", True),
        ("What are the requirements for monitoring a pricing model?", True),
        ("What does CPS 230 para 52 say?", False),  # names a provision
        ("Who is accountable for AI risk?", False),  # focused, not a checklist question
    ],
)
def test_is_broad(question: str, broad: bool) -> None:
    assert is_broad(question) is broad


def test_vendor_question_gets_vendor_stages_only_when_broad() -> None:
    stages = stages_for_question("What do we need to do before engaging a third-party AI vendor?")
    assert [s.playbook for s in stages][:5] == ["vendor"] * 5 or "vendor" in {
        s.playbook for s in stages
    }
    assert {"vendor_notify", "vendor_security"} <= {s.id for s in stages}
    assert stages_for_question("What does CPS 230 para 52 say about vendors?") == []


def test_stages_round_robin_across_playbooks_and_respect_budget() -> None:
    q = "What do we need to do before using a vendor model on customer personal information for pricing?"
    stages = stages_for_question(q, max_stages=4)
    assert len(stages) == 4
    assert len({s.playbook for s in stages}) >= 3  # not all from the first playbook


def test_make_plan_strips_then_stages() -> None:
    plan = make_plan(OPUS_QUESTION, strip=True, stages=True)
    assert plan.removed and plan.stages
    assert plan.labels()[0] == "question" and len(plan.labels()) == len(plan.queries(expand=False))
    qs = plan.queries(expand=True)
    assert "service" in qs[0]  # AI -> tech-neutral expansion applied to every query


# --- selection with per-document cap ------------------------------------------------------------


def _c(cid: str, doc: str, rank: int = 1) -> RetrievedChunk:
    return RetrievedChunk(
        cid, cid, {"tier": "expectation", "doc_id": doc, "status": "current"}, 1.0 / rank, rank
    )


def test_select_without_cap_single_ranking_is_top_k() -> None:
    r = [_c(f"a{i}", "A", i) for i in range(1, 6)]
    assert [c.chunk_id for c in select([r], 3)] == ["a1", "a2", "a3"]


def test_cap_stops_one_document_taking_every_slot() -> None:
    """F-12 shape: document A dominates the ranking; B sits deeper."""
    r = [_c("a1", "A"), _c("a2", "A"), _c("a3", "A"), _c("a4", "A"), _c("b1", "B"), _c("b2", "B")]
    out = [c.chunk_id for c in select([r], 4, per_doc_cap=2)]
    assert out == ["a1", "a2", "b1", "b2"]


def test_cap_is_soft_when_tier_has_one_document() -> None:
    r = [_c(f"a{i}", "A", i) for i in range(1, 6)]
    assert [c.chunk_id for c in select([r], 4, per_doc_cap=2)] == ["a1", "a2", "a3", "a4"]


def test_multi_query_round_robin_best_eligible_and_labels() -> None:
    question = [_c("a1", "A"), _c("a2", "A"), _c("a3", "A")]
    stage1 = [_c("a1", "A"), _c("b1", "B")]  # top hit duplicates the question's
    stage2 = [_c("a2", "A"), _c("c1", "C")]
    out = select([question, stage1, stage2], 4, per_doc_cap=2, labels=["question", "s1", "s2"])
    # round 1: a1 (question), b1 (stage1 skips the duplicate a1), a2 (A now at its cap of 2);
    # round 2: question's a3 is capped -> deferred, stage2 adds c1.
    assert [c.chunk_id for c in out] == ["a1", "b1", "a2", "c1"]
    assert [c.metadata["matched"] for c in out] == ["question", "s1", "s2", "s2"]
    assert [c.rank for c in out] == [1, 2, 3, 4]


class _TierRetriever:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, tuple]] = []

    def search(self, query, k, filters):
        self.calls.append((query, k, filters.tiers))
        tier = filters.tiers[0]
        return [
            RetrievedChunk(
                f"{tier}-{query}-{i}", "t", {"tier": tier, "doc_id": f"{tier}{i % 2}"}, 1.0, i
            )
            for i in range(1, k + 1)
        ]


def test_stratified_unchanged_without_cap() -> None:
    base = _TierRetriever()
    out = StratifiedRetriever(base, per_tier_k=2).search("q", 6, Filters())
    assert len(out) == 6 and all(k == 2 for _, k, _ in base.calls)  # no deeper fetch


def test_planned_retriever_searches_each_stage_per_tier() -> None:
    base = _TierRetriever()
    pr = PlannedRetriever(
        StratifiedRetriever(base, per_tier_k=3, per_doc_cap=2, depth=5), expand=False
    )
    out = pr.search("What do we need to do before engaging a third-party AI vendor?", 9, Filters())
    n_queries = 1 + len(pr.last_plan.stages)
    assert n_queries > 1 and len(base.calls) == 3 * n_queries
    assert all(k == 5 for _, k, _ in base.calls)
    assert len(out) == 9 and {c.metadata["matched"] for c in out} - {"question"}


def test_cap_can_be_limited_to_guidance_tiers_and_binding_is_unchanged() -> None:
    base = _TierRetriever()
    strat = StratifiedRetriever(
        base, per_tier_k=2, per_doc_cap=1, depth=6, cap_tiers=("expectation", "voluntary")
    )
    out = strat.search_multi(["q"], 0, Filters())
    by_tier = {t: [c for c in out if c.tier == t] for t in ("binding", "expectation", "voluntary")}
    # binding: uncapped, single query -> fetched exactly like the original retriever (k = quota)
    assert [k for _, k, tiers in base.calls if tiers == ("binding",)] == [2]
    assert [c.chunk_id for c in by_tier["binding"]] == ["binding-q-1", "binding-q-2"]
    # guidance tiers: capped (docs alternate expectation1, expectation0 ...) -> deeper fetch
    assert [k for _, k, tiers in base.calls if tiers == ("expectation",)] == [6]
    docs = [c.metadata["doc_id"] for c in by_tier["expectation"]]
    assert len(set(docs)) == len(docs) == 2
