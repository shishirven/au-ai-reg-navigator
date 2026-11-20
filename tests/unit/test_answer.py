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
# Unrepairable: every claim cites an unknown id -> nothing survives repair.
BAD_ALL = json.dumps(
    {
        "mandatory": [{"claim": "x", "citation_id": "nope:1"}],
        "regulator_expects": [],
        "recommended": [],
        "abstained": False,
        "abstain_reason": "",
    }
)
MISFILED = json.dumps(
    {
        "mandatory": [],
        "regulator_expects": [],
        "recommended": [
            {"claim": "Entities must undertake due diligence.", "citation_id": "cps:p52"},
            {"claim": "Assign an AI owner.", "citation_id": "ai6:s1"},
        ],
        "abstained": False,
        "abstain_reason": "",
    }
)


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


def test_claim_level_repair_drops_bad_citation_without_llm_retry() -> None:
    llm = StubClient(responses=[BAD])
    r = answer_question("q", AppConfig(), _system(), llm)
    assert r.valid and r.repaired and len(llm.calls) == 1
    assert [cid for _, _, cid in r.cited()] == ["ai6:s1"]
    assert r.attempts[0].repairs == ["dropped claim with unknown citation 'nope:1'"]


def test_claim_level_repair_moves_misfiled_claim_to_tier_section() -> None:
    r = answer_question("q", AppConfig(), _system(), StubClient(responses=[MISFILED]))
    assert r.valid and r.repaired
    assert [(s, cid) for s, _, cid in r.cited()] == [
        ("mandatory", "cps:p52"),
        ("recommended", "ai6:s1"),
    ]


def test_repair_disabled_falls_back_to_llm_retry() -> None:
    cfg = AppConfig()
    cfg.generation.claim_repair = False
    llm = StubClient(responses=[BAD, GOOD])
    r = answer_question("q", cfg, _system(), llm)
    assert r.valid and not r.repaired and len(r.attempts) == 2


def test_retry_once_then_success_includes_feedback() -> None:
    llm = StubClient(responses=[BAD_ALL, GOOD])
    r = answer_question("q", AppConfig(), _system(), llm)
    assert r.valid and len(r.attempts) == 2
    assert r.attempts[0].error_types == ["citation_invalid"]
    repair = llm.calls[1]["messages"][-1]["content"]
    assert "failed validation" in repair and "nope:1" in repair


def test_two_failures_give_safe_abstention() -> None:
    llm = StubClient(responses=[BAD_ALL, BAD_ALL])
    r = answer_question("q", AppConfig(), _system(), llm)
    assert r.fallback and not r.valid and r.answer.abstained
    assert r.answer.claims() == []


def test_llm_error_gives_safe_abstention() -> None:
    def boom(system, messages):
        raise LLMError("down")

    r = answer_question("q", AppConfig(), _system(), StubClient(responses=[boom]))
    assert r.fallback and r.answer.abstained and r.error == "down"


def test_llm_failure_log_has_status_and_not_the_prompt(caplog) -> None:
    import logging

    caplog.set_level(logging.ERROR, logger="regnav.generate.answer")
    secret = "gsk_notarealkey"
    prompt = "FULL PROMPT " + ("paragraph " * 80)

    def boom(system, messages):
        raise LLMError(
            f"groq HTTP 429: Bearer {secret} {prompt}",
            "quota",
            http_status=429,
            error_type="rate_limit_exceeded",
            retry_after_header="7s",
            model="qwen/qwen3.8-27b",
            prompt_tokens=1200,
            completion_tokens=0,
            elapsed_s=1.25,
            safe_message="Rate limit reached",
        )

    r = answer_question("q", AppConfig(), _system(), StubClient(responses=[boom]))
    assert r.answer.abstained
    fields = caplog.records[-1].extra_fields
    assert fields["event"] == "llm_call_failed"
    assert fields["exception_class"] == "LLMError"
    assert fields["http_status"] == 429
    assert fields["error_type"] == "rate_limit_exceeded"
    assert fields["retry_after"] == "7s"
    assert fields["model"] == "qwen/qwen3.8-27b"
    assert fields["prompt_tokens"] == 1200
    assert fields["completion_tokens"] == 0
    assert fields["elapsed_s"] == 1.25
    dumped = str(fields)
    assert secret not in dumped and "FULL PROMPT" not in dumped and "Bearer" not in dumped


def test_scope_gate_abstains_without_calling_llm() -> None:
    llm = StubClient()
    r = answer_question("What does the EU AI Act require?", AppConfig(), _system(), llm)
    assert r.answer.abstained and r.gate_reason and "EU" in r.gate_reason and llm.calls == []
    weak = [
        RetrievedChunk("x:1", "t", {"tier": "binding", "modality": "info"}, 0.1, 1, {"dense": 0.3})
    ]
    r = answer_question("Some question", AppConfig(), _system(weak), llm)
    assert r.answer.abstained and "similarity" in r.gate_reason and llm.calls == []


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


def test_stub_quote_skips_paragraph_number() -> None:
    from regnav.generate.llm import default_stub_answer

    prompt = (
        '<source id="cps:p52" tier="binding" document="CPS" modality="must" effective_from="">\n'
        "[CPS · Binding · para 52]\n52. Before entering into a material arrangement, an entity must: (a) do x.\n</source>"
    )
    out = json.loads(default_stub_answer(prompt))
    assert out["mandatory"][0]["claim"].startswith("Before entering into a material arrangement")
