import json

import pytest

from regnav.generate.validate import uses_mandatory_language, validate_answer

RETRIEVED = {
    "cps:p52": {"tier": "binding", "modality": "must"},
    "cps:p1": {"tier": "binding", "modality": "info"},
    "cpg:p50": {"tier": "expectation", "modality": "should"},
    "ai6:s006": {"tier": "voluntary", "modality": "should"},
}


def _ans(**sections) -> str:
    base = {
        "mandatory": [],
        "regulator_expects": [],
        "recommended": [],
        "abstained": False,
        "abstain_reason": "",
    }
    base.update(sections)
    return json.dumps(base)


def test_valid_answer_passes() -> None:
    raw = _ans(
        mandatory=[{"claim": "Entities must undertake due diligence.", "citation_id": "cps:p52"}],
        regulator_expects=[
            {"claim": "Entities should manage key risks.", "citation_id": "cpg:p50"}
        ],
        recommended=[{"claim": "Assign an accountable AI owner.", "citation_id": "ai6:s006"}],
    )
    res = validate_answer(raw, RETRIEVED)
    assert res.ok, res.errors
    assert len(res.answer.claims()) == 3


def test_rejects_missing_citation() -> None:
    res = validate_answer(_ans(mandatory=[{"claim": "x must y", "citation_id": ""}]), RETRIEVED)
    assert not res.ok and res.error_types == ["schema"]
    res = validate_answer(_ans(mandatory=[{"claim": "x must y"}]), RETRIEVED)
    assert not res.ok and res.error_types == ["schema"]


def test_rejects_citation_not_in_retrieved_set() -> None:
    res = validate_answer(_ans(mandatory=[{"claim": "x", "citation_id": "cps:p999"}]), RETRIEVED)
    assert res.error_types == ["citation_invalid"]


def test_rejects_should_chunk_under_mandatory() -> None:
    res = validate_answer(
        _ans(mandatory=[{"claim": "Manage key risks.", "citation_id": "cpg:p50"}]), RETRIEVED
    )
    assert set(res.error_types) == {"tier_mismatch", "modality"}


def test_rejects_must_language_on_should_source() -> None:
    raw = _ans(recommended=[{"claim": "You must assign an AI owner.", "citation_id": "ai6:s006"}])
    res = validate_answer(raw, RETRIEVED)
    assert res.error_types == ["modality"]


def test_negated_mandatory_language_is_allowed() -> None:
    raw = _ans(
        recommended=[
            {
                "claim": "Adoption is not mandatory; organisations should assign an owner.",
                "citation_id": "ai6:s006",
            }
        ]
    )
    assert validate_answer(raw, RETRIEVED).ok


def test_rejects_tier_mismatch() -> None:
    raw = _ans(recommended=[{"claim": "Due diligence.", "citation_id": "cps:p52"}])
    assert validate_answer(raw, RETRIEVED).error_types == ["tier_mismatch"]


@pytest.mark.parametrize(
    "raw,kind",
    [
        ("not json at all", "parse"),
        ('{"mandatory": "oops"}', "schema"),
        (_ans(), "abstain"),  # no claims, not abstained
        (_ans(abstained=True, mandatory=[{"claim": "x", "citation_id": "cps:p52"}]), "abstain"),
        (json.dumps({"mandatory": [], "extra": 1}), "schema"),
    ],
)
def test_structural_failures(raw: str, kind: str) -> None:
    res = validate_answer(raw, RETRIEVED)
    assert not res.ok and kind in res.error_types


def test_abstention_is_valid() -> None:
    assert validate_answer(_ans(abstained=True, abstain_reason="not covered"), RETRIEVED).ok


def test_accepts_fenced_or_wrapped_json() -> None:
    inner = _ans(mandatory=[{"claim": "Entities must do due diligence.", "citation_id": "cps:p52"}])
    assert validate_answer(f"```json\n{inner}\n```", RETRIEVED).ok
    assert validate_answer(f"Here you go: {inner} thanks", RETRIEVED).ok


@pytest.mark.parametrize(
    "claim,expected",
    [
        ("You must do X", True),
        ("X is required", True),
        ("X is not required", False),
        ("Consider X", False),
    ],
)
def test_uses_mandatory_language(claim: str, expected: bool) -> None:
    assert uses_mandatory_language(claim) is expected
