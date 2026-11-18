import json

from regnav.config import AppConfig, LLMConfig
from regnav.generate.answer import answer_question
from regnav.generate.llm import LLMError, StubClient, cost_usd, make_llm
from regnav.observability.langfuse import NoopTracer, get_tracer
from regnav.retrieve import RetrievalSystem
from regnav.retrieve.base import Filters, RetrievedChunk


class _StaticRetriever:
    name = "static"

    def __init__(self, chunks):
        self.chunks = chunks

    def search(self, query, k, filters: Filters):
        return self.chunks[:k]


CHUNKS = [
    RetrievedChunk(
        "cps:p52",
        "[CPS] 52. must do due diligence",
        {"tier": "binding", "modality": "must", "short_name": "CPS"},
        0.03,
        1,
    ),
    RetrievedChunk(
        "ai6:s1",
        "[AI6] should assign owner",
        {"tier": "voluntary", "modality": "should", "short_name": "AI6"},
        0.02,
        2,
    ),
]
GOOD = json.dumps(
    {
        "mandatory": [
            {"claim": "Entities must undertake due diligence.", "citation_id": "cps:p52"}
        ],
        "regulator_expects": [],
        "recommended": [{"claim": "Assign an AI owner.", "citation_id": "ai6:s1"}],
        "abstained": False,
        "abstain_reason": "",
    }
)
BAD = json.dumps({**json.loads(GOOD), "mandatory": [{"claim": "x", "citation_id": "nope:1"}]})


def _system(chunks=CHUNKS) -> RetrievalSystem:
    return RetrievalSystem(_StaticRetriever(chunks), 9, "idx-test", False, True)


def test_valid_first_time() -> None:
    llm = StubClient(responses=[GOOD])
    r = answer_question("q", AppConfig(name="t"), _system(), llm, sector="bank")
    assert r.valid and not r.fallback and len(r.attempts) == 1
    assert r.config_name == "t" and r.index_version == "idx-test"
    assert r.retrieved_ids == ["cps:p52", "ai6:s1"]
    assert "not legal advice" in r.disclaimer
    assert r.to_dict()["answer"]["mandatory"][0]["citation_id"] == "cps:p52"


def test_retry_once_then_success_includes_feedback() -> None:
    llm = StubClient(responses=[BAD, GOOD])
    r = answer_question("q", AppConfig(), _system(), llm)
    assert r.valid and len(r.attempts) == 2
    assert r.attempts[0].error_types == ["citation_invalid"]
    repair = llm.calls[1]["messages"][-1]["content"]
    assert "failed validation" in repair and "nope:1" in repair


def test_two_failures_give_safe_abstention() -> None:
    llm = StubClient(responses=[BAD, BAD])
    r = answer_question("q", AppConfig(), _system(), llm)
    assert r.fallback and not r.valid and r.answer.abstained
    assert r.answer.claims() == []


def test_llm_error_gives_safe_abstention() -> None:
    def boom(system, messages):
        raise LLMError("down")

    r = answer_question("q", AppConfig(), _system(), StubClient(responses=[boom]))
    assert r.fallback and r.answer.abstained and r.error == "down"


def test_no_chunks_abstains_without_calling_llm() -> None:
    llm = StubClient()
    r = answer_question("q", AppConfig(), _system([]), llm)
    assert r.answer.abstained and llm.calls == []


def test_default_stub_answer_is_valid() -> None:
    r = answer_question("q", AppConfig(), _system(), StubClient())
    assert r.valid
    assert [s for s, _, _ in r.cited()] == ["mandatory", "recommended"]


def test_cost_and_factory() -> None:
    cfg = LLMConfig(price_input_per_mtok=4.0, price_output_per_mtok=20.0)
    assert cost_usd(cfg, 1_000_000, 100_000) == 6.0
    assert isinstance(make_llm(LLMConfig(provider="stub")), StubClient)


def test_tracer_disabled_without_keys(monkeypatch) -> None:
    from regnav.config import Secrets

    tracer = get_tracer(Secrets(_env_file=None, langfuse_public_key=None, langfuse_secret_key=None))
    assert isinstance(tracer, NoopTracer)
    r = answer_question("q", AppConfig(), _system(), StubClient(responses=[GOOD]), tracer=tracer)
    assert r.trace_url is None


def test_tracing_failure_never_breaks_answering() -> None:
    class Broken:
        def log_answer(self, result, cfg):
            raise RuntimeError("langfuse down")

    r = answer_question("q", AppConfig(), _system(), StubClient(responses=[GOOD]), tracer=Broken())
    assert r.valid
