"""Primary-API -> local-model fallback (D-041)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from regnav.config import AppConfig, LLMConfig, load_config
from regnav.generate.answer import answer_question
from regnav.generate.llm import (
    FallbackClient,
    LLMError,
    LLMResponse,
    OpenAICompatClient,
    StubClient,
    make_llm,
)
from regnav.retrieve import RetrievalSystem
from regnav.retrieve.base import RetrievedChunk

GOOD = json.dumps(
    {
        "mandatory": [{"claim": "Entities must do due diligence.", "citation_id": "cps:p52"}],
        "regulator_expects": [],
        "recommended": [],
        "abstained": False,
        "abstain_reason": "",
    }
)


class _Failing:
    def __init__(self, kind: str, retry_after: float | None = None, provider: str = "groq") -> None:
        self.cfg = LLMConfig(provider=provider, model="qwen/qwen3.8-27b")  # type: ignore[arg-type]
        self.kind, self.retry_after, self.calls = kind, retry_after, 0

    def complete(self, system, messages, schema=None) -> LLMResponse:
        self.calls += 1
        raise LLMError(f"boom ({self.kind})", self.kind, self.retry_after)


def _local(responses=None) -> StubClient:
    return StubClient(
        LLMConfig(provider="ollama", model="qwen3:4b"), responses=responses or [GOOD] * 10
    )


class _Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


def test_quota_opens_circuit_until_reset_then_retries_primary() -> None:
    clock, primary, local = _Clock(), _Failing("quota", retry_after=600), _local()
    fb = FallbackClient(primary, local, clock=clock)
    r1 = fb.complete("s", [{"role": "user", "content": "q"}])
    assert r1.provider == "ollama" and "usage limit reached" in r1.fallback_reason
    assert fb.status()["fallback_active"] and "Groq retried in ~10 min" in fb.status()["reason"]
    assert "using the local model" in r1.fallback_reason
    fb.complete("s", [{"role": "user", "content": "q"}])
    assert primary.calls == 1  # circuit open: primary not called again
    clock.t += 601
    fb.complete("s", [{"role": "user", "content": "q"}])
    assert primary.calls == 2  # window passed: primary retried
    assert not fb.status()["fallback_active"] or fb.status()["until"] > clock.t


@pytest.mark.parametrize("retry_after,expected", [(None, 900), (5, 60), (99999, 3600)])
def test_circuit_window_is_clamped(retry_after, expected) -> None:
    clock = _Clock()
    fb = FallbackClient(_Failing("quota", retry_after), _local(), clock=clock)
    fb.complete("s", [{"role": "user", "content": "q"}])
    assert fb.blocked_until - clock.t == pytest.approx(expected)


def test_transient_error_falls_back_for_that_call_only() -> None:
    primary = _Failing("unavailable")
    fb = FallbackClient(primary, _local())
    r = fb.complete("s", [{"role": "user", "content": "q"}])
    assert r.fallback_reason == "Groq unavailable" and not fb.status()["fallback_active"]
    fb.complete("s", [{"role": "user", "content": "q"}])
    assert primary.calls == 2


def test_primary_success_is_labelled_api() -> None:
    primary = StubClient(LLMConfig(provider="groq", model="qwen/qwen3.8-27b"), responses=[GOOD])
    r = FallbackClient(primary, _local()).complete("s", [{"role": "user", "content": "q"}])
    assert r.fallback_reason is None and r.provider == "groq"


def test_both_failing_raises_combined_error() -> None:
    local = _Failing("unavailable", provider="ollama")
    with pytest.raises(LLMError, match="local fallback also failed"):
        FallbackClient(_Failing("quota", 60), local).complete(
            "s", [{"role": "user", "content": "q"}]
        )


def test_answer_records_which_model_answered() -> None:
    class _R:
        name = "r"

        def search(self, q, k, f):
            return [
                RetrievedChunk(
                    "cps:p52", "t", {"tier": "binding", "modality": "must"}, 0.1, 1, {"dense": 0.9}
                )
            ]

    cfg = AppConfig()
    cfg.generation.fallback = LLMConfig(
        provider="ollama", model="qwen3:4b", price_input_per_mtok=0.0
    )
    cfg.generation.price_input_per_mtok = 99.0
    r = answer_question(
        "q",
        cfg,
        RetrievalSystem(_R(), 9, "idx", False, True),
        FallbackClient(_Failing("quota", 60), _local()),
    )
    assert r.valid and r.llm_provider == "ollama" and r.llm_model == "stub"
    assert "usage limit" in r.llm_fallback_reason
    assert r.cost_usd == 0.0  # priced at the local model's (zero) rate, not the API's
    assert r.attempts[0].provider == "ollama"


def test_make_llm_wraps_only_when_allowed() -> None:
    cfg = load_config("configs/hybrid_stratified.yaml")
    assert isinstance(make_llm(cfg.generation), FallbackClient)
    assert not isinstance(make_llm(cfg.generation, use_fallback=False), FallbackClient)
    assert (
        make_llm(cfg.generation).primary.cfg.max_rate_limit_retries <= 2
    )  # don't keep users waiting
    assert not isinstance(make_llm(cfg.judge), FallbackClient)  # judge has no fallback


def test_ollama_base_url_env_override(monkeypatch) -> None:
    from regnav.generate.llm import OllamaClient

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    assert (
        OllamaClient(LLMConfig(provider="ollama")).base_url == "http://host.docker.internal:11434"
    )


class _QuotaHandler(BaseHTTPRequestHandler):
    calls: ClassVar[int] = 0

    def do_POST(self):
        _QuotaHandler.calls += 1
        self.rfile.read(int(self.headers["Content-Length"]))
        body = json.dumps(
            {
                "error": {
                    "message": "Rate limit reached for model `m` on tokens per day (TPD): "
                    "Limit 200000, Used 199000. Please try again in 12m9.216s. Need more?"
                }
            }
        )
        data = body.encode()
        self.send_response(429)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def test_daily_quota_429_fails_fast_with_reset_hint() -> None:
    httpd = HTTPServer(("127.0.0.1", 0), _QuotaHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        client = OpenAICompatClient(
            LLMConfig(
                provider="openai_compat",
                model="m",
                base_url=f"http://127.0.0.1:{httpd.server_port}/v1",
            )
        )
        client.sleep = lambda s: pytest.fail("must not back off on a daily quota")
        with pytest.raises(LLMError) as ei:
            client.complete("s", [{"role": "user", "content": "x"}])
        assert ei.value.kind == "quota" and ei.value.retry_after_s == pytest.approx(729.216)
        assert _QuotaHandler.calls == 1
    finally:
        httpd.shutdown()
