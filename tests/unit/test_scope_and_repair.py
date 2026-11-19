import pytest

from regnav.generate.schema import Claim, StructuredAnswer
from regnav.generate.scope import check_scope, corpus_instruments
from regnav.generate.validate import repair_answer
from regnav.retrieve.base import RetrievedChunk

KNOWN = corpus_instruments(["CPS 230", "CPS 234", "CPG 235", "APRA AI letter", "AI6 Foundations"])
CH = [RetrievedChunk("a", "t", {}, 0.1, 1, {"dense": 0.8})]


def test_corpus_instruments() -> None:
    assert {"CPS230", "CPS234", "CPG235"} == KNOWN


@pytest.mark.parametrize(
    "question,blocked",
    [
        ("What does CPS 230 require for service providers?", False),
        ("What does CPS230 para 52 say?", False),
        ("Penalties under the EU AI Act?", True),
        ("Does GDPR apply to our AI model?", True),
        ("What does APS 115 require for operational risk capital?", True),
        ("What are ASIC's requirements under RG 255?", True),
        ("How should we monitor AI drift?", False),
        ("Is the US approach different?", True),
        ("How do we use AI in our business?", False),  # 'us' lower-case is not the US
    ],
)
def test_scope_gate_questions(question: str, blocked: bool) -> None:
    assert (check_scope(question, CH, KNOWN, 0.62) is not None) is blocked


def test_scope_gate_similarity_floor() -> None:
    weak = [RetrievedChunk("a", "t", {}, 0.1, 1, {"dense": 0.5})]
    assert "similarity" in check_scope("How should we monitor AI drift?", weak, KNOWN, 0.62)
    assert (
        check_scope("x", [RetrievedChunk("a", "t", {}, 0.1, 1, {"bm25": 3.0})], KNOWN, 0.62) is None
    )


RET = {
    "cps:p52": {"tier": "binding", "modality": "must"},
    "cpg:p50": {"tier": "expectation", "modality": "should"},
    "ai6:s1": {"tier": "voluntary", "modality": "should"},
}


def test_repair_moves_drops_dedupes_and_caps() -> None:
    ans = StructuredAnswer(
        mandatory=[
            Claim(
                claim="Manage key risks.", citation_id="cpg:p50"
            ),  # should-source in mandatory -> dropped
            Claim(claim="Do due diligence.", citation_id="cps:p52"),
            Claim(claim="Do due diligence.", citation_id="cps:p52"),  # duplicate
            Claim(claim="Made up.", citation_id="zzz:1"),  # unknown
        ],
        recommended=[
            Claim(claim="Assign an owner.", citation_id="ai6:s1"),
            Claim(claim="Owner must exist.", citation_id="ai6:s1"),
        ],
        regulator_expects=[
            Claim(claim="Diligence again.", citation_id="cps:p52")
        ],  # misfiled -> mandatory
    )
    fixed, log = repair_answer(ans, RET, max_per_section=1)
    assert [c.citation_id for c in fixed.mandatory] == ["cps:p52"]  # moved + deduped + capped
    assert [c.claim for c in fixed.recommended] == ["Assign an owner."]
    # a 'should' claim misfiled under mandatory is moved to its own tier's section (no must-wording)
    assert [c.citation_id for c in fixed.regulator_expects] == ["cpg:p50"]
    assert not fixed.abstained
    joined = "\n".join(log)
    for fragment in (
        "unknown citation",
        "duplicate",
        "mandatory wording",
        "moved claim",
        "trimmed mandatory",
    ):
        assert fragment in joined


def test_repair_of_all_bad_claims_leaves_empty_answer() -> None:
    fixed, log = repair_answer(
        StructuredAnswer(mandatory=[Claim(claim="x", citation_id="nope")]), RET
    )
    assert fixed.claims() == [] and log
