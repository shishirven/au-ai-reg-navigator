"""Sourced commencement dates (D-056): registry, relevance, and the answer flow."""

from __future__ import annotations

import json
from datetime import date

import pytest

from regnav.commencement import by_id, load_commencements, pending_for
from regnav.config import AppConfig
from regnav.generate import answer as answer_mod
from regnav.generate.answer import answer_question
from regnav.generate.llm import StubClient
from regnav.retrieve import RetrievalSystem
from regnav.retrieve.base import Filters, RetrievedChunk

BEFORE = date(2026, 11, 24)
AFTER = date(2027, 1, 5)
SRC_ID = "oaic_app1_adm_2026:s001"
QUOTE = "Changes to privacy obligations for APP entities come into effect on 10 December 2026."


# --- registry -------------------------------------------------------------------------------


def test_registry_entry_is_sourced() -> None:
    c = by_id("app_1_7_9")
    assert c is not None and c.commences == date(2026, 12, 10) and c.long_date == "10 December 2026"
    assert c.live_source is not None and c.live_source.chunk == SRC_ID
    assert c.live_source.quote == QUOTE
    assert any(not s.live and "commencement table" in s.cite for s in c.sources)
    assert all(s.quote for s in c.sources)
    ids = [x.id for x in load_commencements()]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(
    "text,stated",
    [
        ("It commences on 10 December 2026.", True),
        ("from 10 Dec 2026", True),
        ("from 10th December, 2026", True),
        ("starting December 10, 2026", True),
        ("effective 2026-12-10", True),
        ("on 10/12/2026", True),
        ("in December 2026", False),
        ("on 10 December 2025", False),
    ],
)
def test_date_recognised_in_common_formats(text: str, stated: bool) -> None:
    c = by_id("app_1_7_9")
    assert c is not None and c.stated_in(text) is stated


def _chunk(cid: str, doc: str, text: str, tier: str = "expectation") -> RetrievedChunk:
    return RetrievedChunk(
        cid, text, {"tier": tier, "modality": "should", "doc_id": doc, "short_name": doc}, 1.0, 1
    )


def test_pending_only_before_the_date_and_only_when_relevant() -> None:
    adm = _chunk("oaic_app1_adm_2026:s005", "oaic_app1_adm_2026", "APP entities should...")
    other = _chunk("apra_cps234:p16", "apra_cps234", "16. Where information assets...", "binding")
    mention = _chunk(
        "oaic_ai_products_2025:s1", "oaic_ai_products_2025", "See APP 1.8 for details."
    )
    assert [c.id for c in pending_for([adm], BEFORE)] == ["app_1_7_9"]
    assert pending_for([adm], AFTER) == []
    assert pending_for([other], BEFORE) == []
    assert [c.id for c in pending_for([mention], BEFORE)] == ["app_1_7_9"]


# --- answer flow ------------------------------------------------------------------------------


class _Static:
    name = "static"

    def __init__(self, chunks):
        self.chunks = chunks

    def search(self, query, k, filters: Filters):
        return self.chunks[:k]


ADM = _chunk(
    "oaic_app1_adm_2026:s005",
    "oaic_app1_adm_2026",
    "[OAIC]\nAPP entities should explain decisions.",
)


def _answer(claims: list[tuple[str, str]]) -> str:
    return json.dumps(
        {
            "mandatory": [],
            "regulator_expects": [{"claim": c, "citation_id": cid} for c, cid in claims],
            "recommended": [],
            "abstained": False,
            "abstain_reason": "",
        }
    )


SILENT = _answer([("Privacy policies should explain automated decisions.", ADM.chunk_id)])
DATED = _answer(
    [
        ("Privacy policies should explain automated decisions.", ADM.chunk_id),
        ("The obligation commences on 10 December 2026.", SRC_ID),
    ]
)
BROKEN = _answer([("x", "nope:1")])


@pytest.fixture(autouse=True)
def _source_row(monkeypatch):
    row = {
        "chunk_id": SRC_ID,
        "text": f"[OAIC APP 1.7-1.9 fact sheet]\nThis fact sheet... {QUOTE}",
        "tier": "expectation",
        "modality": "should",
        "doc_id": "oaic_app1_adm_2026",
        "short_name": "OAIC APP 1.7-1.9 fact sheet",
    }
    monkeypatch.setattr(answer_mod, "_chunk_row", lambda cfg, cid: row if cid == SRC_ID else None)


def _cfg(check: bool = True) -> AppConfig:
    cfg = AppConfig(name="t")
    cfg.generation.scope_gate = False
    cfg.generation.commencement_check = check
    return cfg


def _run(responses, check=True, today=BEFORE):
    system = RetrievalSystem(_Static([ADM]), 9, "idx-test", False, True)
    return answer_question("q", _cfg(check), system, StubClient(responses=responses), today=today)


def test_source_stating_the_date_is_added_to_the_context() -> None:
    r = _run([DATED])
    assert SRC_ID in r.retrieved_ids and r.retrieved[-1].scores.get("commencement_source") == 1.0
    assert QUOTE in json.dumps([c.text for c in r.retrieved])


def test_model_states_date_first_time() -> None:
    r = _run([DATED])
    assert r.valid and len(r.attempts) == 1
    assert r.commencements == [
        {"id": "app_1_7_9", "commences": "2026-12-10", "source_chunk": SRC_ID, "how": "model"}
    ]


def test_silent_answer_gets_one_targeted_retry() -> None:
    seen = []

    def second(system, messages):
        seen.append(messages[-1]["content"])
        return DATED

    r = _run([SILENT, second])
    assert r.valid and len(r.attempts) == 2 and r.commencements[0]["how"] == "retry"
    assert "10 December 2026" in seen[0] and SRC_ID in seen[0] and QUOTE in seen[0]


def test_still_silent_gets_a_verbatim_cited_quote_never_a_bare_date() -> None:
    r = _run([SILENT, SILENT])
    assert r.valid and r.commencements[0]["how"] == "quoted"
    added = [c for s, c in r.answer.claims() if c.citation_id == SRC_ID]
    assert len(added) == 1 and added[0].claim == QUOTE
    assert ("regulator_expects", QUOTE, SRC_ID) in r.cited()  # section follows the source's tier


def test_failed_retry_keeps_the_valid_answer_and_quotes() -> None:
    r = _run([SILENT, BROKEN])
    assert r.valid and not r.fallback and r.commencements[0]["how"] == "quoted"
    assert any(c.citation_id == ADM.chunk_id for _, c in r.answer.claims())


def test_off_by_default_and_after_commencement() -> None:
    r = _run([SILENT], check=False)
    assert r.commencements == [] and SRC_ID not in r.retrieved_ids and len(r.attempts) == 1
    r = _run([SILENT], today=AFTER)
    assert r.commencements == [] and len(r.attempts) == 1
