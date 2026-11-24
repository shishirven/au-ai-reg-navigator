"""Model-use check (D-053): intake, playbook selection, checklist building, rendering, coverage.
Hermetic: a fake tier retriever stands in for the index and cross-encoder."""

from __future__ import annotations

import csv
import io
from datetime import date

import pytest

from regnav.assess import checklist as ck
from regnav.assess.checklist import applicability_notes, build_checklist, selected_playbooks
from regnav.assess.render import CSV_FIELDS, to_csv, to_markdown
from regnav.assess.usecase import UseCase
from regnav.config import AppConfig
from regnav.coverage import conditions_met, gaps_for_question, gaps_for_use_case
from regnav.retrieve.base import RetrievedChunk
from regnav.retrieve.stratified import StratifiedRetriever

TODAY = date(2026, 11, 23)


def _uc(**kw) -> UseCase:
    base = dict(
        name="Pricing GBM",
        description="Prices motor policies",
        sector="insurer",
        team="actuarial",
        personal_information="yes",
        decisions_about_individuals="yes",
        third_party="no",
        offshore="no",
        critical_operation="no",
        generative_ai="no",
        sensitive_information="no",
    )
    return UseCase(**{**base, **kw})


# --- intake and selection -------------------------------------------------------------------


def test_unsure_counts_as_yes_and_is_reported() -> None:
    uc = _uc(third_party="unsure", offshore="unsure")
    f = uc.facts()
    assert f["third_party"] and f["offshore"] and not f["critical_operation"]
    assert uc.unsure_fields() == ["third_party", "offshore"]


def test_playbook_selection_follows_intake() -> None:
    ids = [pb.id for pb in selected_playbooks(_uc())]
    assert ids[0] == "model_lifecycle"  # analytics teams see their own lifecycle first
    assert {"personal_info", "automated_decisions", "governance"} <= set(ids)
    assert "vendor" not in ids and "resilience" not in ids
    ids = [pb.id for pb in selected_playbooks(_uc(third_party="yes", critical_operation="unsure"))]
    assert {"vendor", "resilience"} <= set(ids)


# --- applicability notes ------------------------------------------------------------------------


def test_notes_cite_cps230_para60_for_vendor_and_offshore() -> None:
    notes = " ".join(
        applicability_notes(
            _uc(third_party="yes", critical_operation="yes", offshore="unsure"), TODAY
        )
    )
    assert "para 60(a)" in notes and "20 business days" in notes
    assert "para 60(b)" in notes and "unsure" in notes


def test_adm_note_counts_down_then_switches_tense() -> None:
    before = " ".join(applicability_notes(_uc(), TODAY))
    assert "commences on 10 December 2026 (17 days from today)" in before
    after = " ".join(applicability_notes(_uc(), date(2027, 1, 5)))
    assert "has applied since 10 December 2026" in after
    none = " ".join(applicability_notes(_uc(decisions_about_individuals="no"), TODAY))
    assert "APP 1.7" not in none


# --- checklist building with a fake retriever -----------------------------------------------------


class _FakeTierRetriever:
    """Returns, per tier, chunks whose rerank score depends on the stage query."""

    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def search(self, query, k, filters):
        self.calls += 1
        tier = filters.tiers[0]
        shared = RetrievedChunk(
            "cps230:p52",
            "[CPS 230 · Binding]\n52. An entity must undertake due diligence.",
            {
                "tier": "binding",
                "doc_id": "apra_cps230_2026",
                "short_name": "CPS 230",
                "para": "52",
                "modality": "must",
                "effective_from": "2025-07-01",
            },
            9.0,
            1,
            {"rerank": 9.0},
        )
        offtopic = RetrievedChunk(
            "cps234:p12",
            "[CPS 234]\n12. Definitions.",
            {"tier": "binding", "doc_id": "apra_cps234", "short_name": "CPS 234", "para": "12"},
            -6.0,
            2,
            {"rerank": -6.0},
        )
        future = RetrievedChunk(
            f"adm:{abs(hash(query)) % 1000}",
            "[OAIC fact sheet]\nAPP entities should explain decisions.",
            {
                "tier": "expectation",
                "doc_id": "oaic_app1_adm_2026",
                "short_name": "OAIC APP 1.7-1.9 fact sheet",
                "section": "Fact Sheet › When does it apply?",
                "modality": "should",
                "effective_from": "2026-12-10",
            },
            2.0,
            1,
            {"rerank": 2.0},
        )
        weak_vol = RetrievedChunk(
            f"ai6:{abs(hash(query)) % 1000}",
            "[AI6]\nTest and monitor.",
            {
                "tier": "voluntary",
                "doc_id": "naic_ai6_foundations",
                "short_name": "AI6 Foundations",
                "section": "5. Test and monitor",
                "modality": "should",
            },
            -5.0,
            1,
            {"rerank": -5.0},
        )
        return {"binding": [shared, offtopic], "expectation": [future], "voluntary": [weak_vol]}[
            tier
        ][:k]


@pytest.fixture(autouse=True)
def _no_disk_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(ck, "CACHE_DIR", tmp_path / "stage_cache")
    ck._STAGE_CACHE.clear()


def _build(uc: UseCase) -> tuple[ck.Checklist, _FakeTierRetriever]:
    base = _FakeTierRetriever()
    strat = StratifiedRetriever(base, per_tier_k=4, per_doc_cap=2)
    cfg = AppConfig.model_validate({"name": "test"})
    return build_checklist(uc, cfg, strat, "idx-test", today=TODAY), base


def test_checklist_dedupes_drops_offtopic_and_flags() -> None:
    cl, _ = _build(_uc())
    ids = [i.chunk_id for i in cl.items]
    assert ids.count("cps230:p52") == 1  # found by every stage, listed once
    assert "cps234:p12" not in ids  # below the binding drop floor
    first = next(i for i in cl.items if i.chunk_id == "cps230:p52")
    assert first.also_in  # other stages point back to it
    assert any((s.see_also and not s.items) or s.see_also for s in cl.stages[1:])
    fut = [i for i in cl.items if i.tier == "expectation"]
    assert fut and all(i.not_yet_in_force for i in fut)
    vol = [i for i in cl.items if i.tier == "voluntary"]
    assert vol and all(i.weak for i in vol)  # -5.0: kept (above -7) but flagged


def test_stage_results_are_cached_in_memory_and_on_disk(tmp_path) -> None:
    _, base1 = _build(_uc())
    assert base1.calls > 0
    ck._STAGE_CACHE.clear()  # simulate a restart: only the disk cache remains
    _, base2 = _build(_uc())
    assert base2.calls == 0


# --- rendering ------------------------------------------------------------------------------


def test_markdown_and_csv_render() -> None:
    cl, _ = _build(_uc(third_party="yes"))
    md = to_markdown(cl)
    assert md.startswith("# Model-use check: Pricing GBM")
    assert "- [ ] **🔴 Mandatory** · CPS 230 para 52" in md
    assert "⏳ APP 1.7-1.9 commences 2026-12-10" in md and "not a compliance verdict" in md
    assert "no language model used" in md
    rows = list(csv.DictReader(io.StringIO(to_csv(cl))))
    assert rows and list(rows[0]) == CSV_FIELDS
    assert {r["status"] for r in rows} == {""}  # left for the team to fill in
    assert len(rows) == len(cl.items)


# --- coverage ("not covered by this library") ----------------------------------------------------


def test_coverage_conditions() -> None:
    assert conditions_met({"always": True}, {})
    assert conditions_met(
        {"sector": "insurer", "decisions_about_individuals": True},
        {"sector": "insurer", "decisions_about_individuals": True},
    )
    assert not conditions_met({"sector": "bank"}, {"sector": "insurer"})
    assert not conditions_met({}, {"anything": True})


def test_coverage_gaps_for_use_case_and_question() -> None:
    gaps = {g.id for g in gaps_for_use_case(_uc().facts(), "motor pricing")}
    assert {
        "far",
        "privacy_act_text",
        "insurance_law",
        "anti_discrimination",
        "actuarial_standards",
    } <= gaps
    assert "credit_law" not in gaps  # insurer, not a lender
    assert "super_standards" not in gaps
    q = {
        g.id
        for g in gaps_for_question(
            "Who is the accountable executive under FAR for our credit model?"
        )
    }
    assert {"far", "credit_law"} <= q
    assert gaps_for_question("What does CPS 230 para 52 require?") == []


def test_exports_carry_the_teams_tracking() -> None:
    cl, _ = _build(_uc())
    first = cl.items[0].chunk_id
    track = {first: {"status": "Met", "owner": "Priya", "evidence": "https://wiki/val-report"}}
    rows = list(csv.DictReader(io.StringIO(to_csv(cl, track))))
    row = next(r for r in rows if r["chunk_id"] == first)
    assert (row["status"], row["owner"], row["evidence_link"]) == (
        "Met",
        "Priya",
        "https://wiki/val-report",
    )
    assert all(r["status"] == "" for r in rows if r["chunk_id"] != first)
    md = to_markdown(cl, track)
    assert "- [x] **" in md and "owner: Priya" in md
