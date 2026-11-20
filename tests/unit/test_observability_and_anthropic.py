"""Langfuse tracer and Anthropic client logic with fake SDK objects (no network)."""

from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from regnav.config import AppConfig, LLMConfig
from regnav.generate.answer import answer_question
from regnav.generate.llm import AnthropicClient, LLMError, StubClient
from regnav.observability.langfuse import LangfuseTracer, trace_tags
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


class _Static:
    name = "s"

    def search(self, q, k, f):
        return [
            RetrievedChunk(
                "cps:p52", "t", {"tier": "binding", "modality": "must"}, 0.1, 1, {"dense": 0.9}
            )
        ]


class _FakeObs:
    def __init__(self, log, name):
        self.log, self.name = log, name

    def update(self, **kw):
        self.log.append((self.name, kw))


class _FakeLangfuse:
    def __init__(self):
        self.log: list = []

    @contextmanager
    def start_as_current_observation(self, *, name, as_type="span", **kw):
        self.log.append(("start", name, as_type))
        yield _FakeObs(self.log, name)

    def get_current_trace_id(self):
        return "trace123"

    def get_trace_url(self, trace_id):
        return f"https://lf.example/trace/{trace_id}"

    def flush(self):
        self.log.append(("flush",))


def test_langfuse_tracer_records_retrieval_generation_and_metadata(monkeypatch) -> None:
    tracer = LangfuseTracer.__new__(LangfuseTracer)
    tracer.client = _FakeLangfuse()
    seen = {}

    @contextmanager
    def fake_propagate(**kw):
        seen.update(kw)
        yield

    import langfuse

    monkeypatch.setattr(langfuse, "propagate_attributes", fake_propagate)
    system = RetrievalSystem(_Static(), 9, "idx-abc", False, True)
    r = answer_question(
        "q?", AppConfig(name="cfgX"), system, StubClient(responses=[GOOD]), tracer=tracer
    )
    assert r.trace_url == "https://lf.example/trace/trace123"
    assert ("start", "retrieve", "retriever") in tracer.client.log
    assert ("start", "generate-attempt-1", "generation") in tracer.client.log
    gen = next(
        kw
        for name, kw in (e for e in tracer.client.log if len(e) == 2)
        if name == "generate-attempt-1"
    )
    assert gen["usage_details"]["input"] > 0 and "cost_details" in gen
    ret = next(
        kw for name, kw in (e for e in tracer.client.log if len(e) == 2) if name == "retrieve"
    )
    assert ret["output"][0]["chunk_id"] == "cps:p52"
    assert (
        seen["metadata"]["config_name"] == "cfgX" and seen["metadata"]["index_version"] == "idx-abc"
    )
    assert seen["tags"] == trace_tags("cfgX", "idx-abc", "stub")
    tracer.flush()
    assert tracer.client.log[-1] == ("flush",)


def test_trace_tags_add_env_prod_only_for_the_public_demo(monkeypatch) -> None:
    monkeypatch.delenv("REGNAV_PUBLIC_DEMO", raising=False)
    assert trace_tags("prod", "idx-1", "qwen/qwen3.8-27b") == [
        "prod",
        "idx-1",
        "qwen/qwen3.8-27b",
    ]
    monkeypatch.setenv("REGNAV_PUBLIC_DEMO", "1")
    assert trace_tags("prod", "idx-1", "qwen/qwen3.8-27b") == [
        "env:prod",
        "prod",
        "idx-1",
        "qwen/qwen3.8-27b",
    ]


class _FakeMessages:
    def __init__(self, resp):
        self.resp, self.kwargs = resp, None

    def create(self, **kw):
        self.kwargs = kw
        return self.resp


def _resp(stop="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=GOOD)],
        model="claude-x",
        usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
        stop_reason=stop,
    )


def _client(resp, **cfg_kw) -> tuple[AnthropicClient, _FakeMessages]:
    c = AnthropicClient.__new__(AnthropicClient)
    c.cfg = LLMConfig(provider="anthropic", model="claude-x", **cfg_kw)
    msgs = _FakeMessages(resp)
    c.client = SimpleNamespace(messages=msgs)
    return c, msgs


def test_anthropic_client_request_shape_and_usage() -> None:
    c, msgs = _client(_resp(), effort="low", temperature=0.0)
    out = c.complete("SYS", [{"role": "user", "content": "x"}], schema={"type": "object"})
    assert out.text == GOOD and (out.input_tokens, out.output_tokens) == (1000, 200)
    kw = msgs.kwargs
    assert kw["system"] == "SYS" and kw["model"] == "claude-x"
    assert kw["output_config"] == {
        "effort": "low",
        "format": {"type": "json_schema", "schema": {"type": "object"}},
    }
    assert "temperature" not in kw  # current Claude models reject sampling params (D-004)


def test_anthropic_refusal_raises() -> None:
    c, _ = _client(_resp("refusal"))
    with pytest.raises(LLMError, match="refusal"):
        c.complete("s", [{"role": "user", "content": "x"}])
