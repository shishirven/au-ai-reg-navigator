"""Statement-level authority (D-044): statements, references, tagger, applicability, scoring."""

from datetime import date

import pytest

from regnav.legal.applicability import Profile, app_entity_status, assess
from regnav.legal.evaluate import score
from regnav.legal.references import Reference, Resolver, extract_references
from regnav.legal.statements import split_statements
from regnav.legal.tagger import classify


def test_split_statements_keeps_lead_in_for_items() -> None:
    text = "[CPS 230 · Binding · S · para 52]\n52. Before entering into an arrangement, an entity must:\n(a) do due diligence; and\n(b) assess risks."
    sts = split_statements("c:p52", text)
    assert [s.text for s in sts] == [
        "52. Before entering into an arrangement, an entity must:",
        "do due diligence; and",
        "assess risks.",
    ]
    assert sts[1].context.endswith("must:") and sts[1].full.startswith("52. Before")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("as set out in paragraph 60(a) of CPS 230", [("CPS 230", "60(a)")]),
        (
            "paragraphs 53, 54 and 55 of CPS 230",
            [("CPS 230", "53"), ("CPS 230", "54"), ("CPS 230", "55")],
        ),
        ("CPS 230 paragraph 35 sets out", [("CPS 230", "35")]),
        ("must comply with APP 3 and APP 5", [("APP 3", ""), ("APP 5", "")]),
        ("Australian Privacy Principle 1.7", [("APP 1.7", "")]),
        ("APP 1.7-1.9", [("APP 1.7", ""), ("APP 1.8", ""), ("APP 1.9", "")]),
        ("section 6D of the Privacy Act", [("Privacy Act s 6D", "")]),
        ("see CPS 234 for more", [("CPS 234", "")]),
    ],
)
def test_extract_references(text, expected) -> None:
    assert [(r.instrument, r.provision) for r in extract_references(text)] == expected


ROWS = [
    {
        "chunk_id": "apra_cps230_2026:p60",
        "doc_id": "apra_cps230_2026",
        "para": "60",
        "section": "Monitoring",
        "text": "60. must notify",
    },
    {
        "chunk_id": "apra_cps230_2026:p50-51",
        "doc_id": "apra_cps230_2026",
        "para": "50-51",
        "section": "x",
        "text": "50.",
    },
    {
        "chunk_id": "privacy_act_apps:s007.1",
        "doc_id": "privacy_act_apps",
        "para": "",
        "section": "Part 3 › APP 6 - use or disclosure",
        "text": "x\n6.1 If an APP entity",
    },
    {
        "chunk_id": "privacy_act_apps:s007.2",
        "doc_id": "privacy_act_apps",
        "para": "",
        "section": "Part 3 › APP 6 - use or disclosure",
        "text": "x\n6.2 Exceptions",
    },
    {
        "chunk_id": "privacy_act_apps:s070",
        "doc_id": "privacy_act_apps",
        "para": "",
        "section": "APP 10 - quality",
        "text": "10.1",
    },
    {
        "chunk_id": "privacy_act_app1_7_9:s002",
        "doc_id": "privacy_act_app1_7_9",
        "para": "",
        "section": "APP 1.7 - When",
        "text": "1.7",
    },
]
REG = {
    "instruments": {
        "CPS 230": {"doc_id": "apra_cps230_2026"},
        "APP 1.7": {"doc_id": "privacy_act_app1_7_9", "heading": "APP 1.7"},
        "APP *": {"doc_id": "privacy_act_apps", "heading": "APP {n}"},
        "SPS 220": {"doc_id": "not_indexed"},
    },
    "documents": {"privacy_act_apps": {"regime": "privacy"}},
}


def test_resolver() -> None:
    r = Resolver(ROWS, REG)
    assert r.resolve(Reference("CPS 230", "60(a)")).chunk_ids == ["apra_cps230_2026:p60"]
    assert r.resolve(Reference("CPS 230", "51")).chunk_ids == [
        "apra_cps230_2026:p50-51"
    ]  # merged paragraphs
    assert r.resolve(Reference("APP 6")).chunk_ids == [
        "privacy_act_apps:s007.1",
        "privacy_act_apps:s007.2",
    ]
    assert r.resolve(Reference("APP 6.2")).chunk_ids == ["privacy_act_apps:s007.2"]  # subclause
    assert r.resolve(Reference("APP 1")).chunk_ids == []  # "APP 1" must not match "APP 10"
    assert r.resolve(Reference("APP 1.7")).chunk_ids == [
        "privacy_act_app1_7_9:s002"
    ]  # explicit entry wins
    res = r.resolve(Reference("SPS 220"))
    assert res.doc_id == "not_indexed" and not res.in_corpus and not res.resolved
    assert not r.resolve(Reference("GPS 001")).resolved
    assert r.regime("privacy_act_apps") == "privacy"


@pytest.mark.parametrize(
    "text,tier,expected",
    [
        ("An APRA-regulated entity must maintain a register.", "binding", "binding_requirement"),
        (
            "APRA may require an entity to review its tolerance levels.",
            "binding",
            "binding_context",
        ),
        (
            "An entity need not comply with paragraph 53 if the arrangement is exempt.",
            "binding",
            "binding_context",
        ),
        (
            "This collection must comply with APP 3 and APP 5 requirements.",
            "expectation",
            "restates_law",
        ),
        (
            "APP 6 provides that personal information can only be used for the primary purpose.",
            "expectation",
            "restates_law",
        ),
        (
            "The Privacy Act applies to all uses of AI involving personal information.",
            "expectation",
            "restates_law",
        ),
        (
            "The OAIC considers that ML outputs would generally fall within scope.",
            "expectation",
            "regulator_interpretation",
        ),
        (
            "APRA expects that information provided to the Board is targeted.",
            "expectation",
            "regulator_expectation",
        ),
        (
            "APRA envisages that an entity would adopt high-level principles.",
            "expectation",
            "regulator_expectation",
        ),
        (
            "Organisations should consider a privacy impact assessment.",
            "expectation",
            "regulator_expectation",
        ),
        (
            "Entities must ensure generation of personal information is reasonably necessary.",
            "expectation",
            "unclear",
        ),
        ("AI adoption is accelerating across industries.", "expectation", "information"),
        (
            "[7] DISR, Proposals paper for introducing mandatory guardrails for AI, 2024.",
            "expectation",
            "information",
        ),
        (
            "Organisations should assign an accountable AI owner.",
            "voluntary",
            "voluntary_recommendation",
        ),
    ],
)
def test_tagger(text, tier, expected) -> None:
    assert classify(text, tier).label == expected


def test_tagger_uses_lead_in_for_items() -> None:
    assert (
        classify("undertake due diligence;", "binding", context="An entity must:").label
        == "binding_requirement"
    )
    assert classify("undertake due diligence;", "binding").label == "binding_context"


TODAY = date(2026, 11, 19)


@pytest.mark.parametrize(
    "profile,status",
    [
        (Profile(sector="bank"), "yes"),
        (Profile(sector="any_business", turnover_over_3m=True), "yes"),
        (Profile(sector="any_business", turnover_over_3m=False), "no"),
        (
            Profile(sector="any_business", turnover_over_3m=False, exceptions={"health_service"}),
            "yes",
        ),
        (Profile(sector="any_business", turnover_over_3m=False, exceptions={"opted_in"}), "yes"),
        (Profile(sector="any_business"), "unknown"),
    ],
)
def test_app_entity_status(profile, status) -> None:
    assert app_entity_status(profile)[0] == status


def test_assess_dates_regimes_and_exemption() -> None:
    kw = dict(
        regime="privacy", doc_tier="binding", status="current", applies_to_sector=True, today=TODAY
    )
    a = assess(effective_from="2026-12-10", profile=Profile(sector="bank"), **kw)
    assert a.status == "applies_from" and a.from_date == "2026-12-10"
    assert (
        assess(
            effective_from="2026-12-10",
            profile=Profile(sector="any_business", turnover_over_3m=False),
            **kw,
        ).status
        == "likely_exempt"
    )
    assert (
        assess(effective_from="2026-01-01", profile=Profile(sector="bank"), **kw).status
        == "applies"
    )
    assert assess(effective_from="", profile=Profile(sector="any_business"), **kw).status == "check"
    pru = dict(
        regime="prudential",
        doc_tier="binding",
        effective_from="2026-07-01",
        today=TODAY,
        profile=Profile(sector="super"),
    )
    assert assess(status="current", applies_to_sector=True, **pru).status == "applies"
    assert assess(status="current", applies_to_sector=False, **pru).status == "not_applicable"
    assert assess(status="superseded", applies_to_sector=True, **pru).status == "historical"
    guide = assess(
        regime="prudential",
        doc_tier="expectation",
        status="current",
        effective_from="",
        applies_to_sector=True,
        profile=Profile(sector="bank"),
        today=TODAY,
    )
    assert guide.status == "check" and "not itself binding" in guide.reason


def test_score_hand_computed() -> None:
    pairs = [
        ("binding_requirement", "binding_requirement"),
        ("restates_law", "unclear"),
        ("information", "information"),
        ("regulator_expectation", "information"),
    ]
    s = score(pairs)
    assert s["accuracy"] == 0.5 and s["n"] == 4
    assert s["per_label"]["information"] == {"precision": 0.5, "recall": 1.0, "support": 1}
    assert ("restates_law -> unclear", 1) in s["confusion"]
    assert -1.0 <= s["kappa_binding_vs_not"] <= 1.0
