"""LLM clients behind one interface: Ollama (local, default), Anthropic (API), Stub (tests).

All return :class:`LLMResponse` with token usage, so cost/latency tracking is provider-agnostic.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from regnav.config import LLMConfig


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    cfg: LLMConfig

    def complete(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any] | None = None
    ) -> LLMResponse: ...


def cost_usd(cfg: LLMConfig, input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * cfg.price_input_per_mtok + output_tokens * cfg.price_output_per_mtok
    ) / 1e6


class OllamaClient:
    """Local models via Ollama's REST API (``/api/chat``) with JSON-schema structured output."""

    def __init__(self, cfg: LLMConfig, seed: int = 42) -> None:
        self.cfg = cfg
        self.seed = seed

    def complete(self, system, messages, schema=None) -> LLMResponse:
        options: dict[str, Any] = {
            "num_ctx": self.cfg.num_ctx,
            "num_predict": self.cfg.max_tokens,
            "seed": self.seed,
        }
        if self.cfg.temperature is not None:
            options["temperature"] = self.cfg.temperature
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": False,
            "options": options,
            "think": self.cfg.think,
        }
        if schema is not None and self.cfg.ollama_format == "schema":
            payload["format"] = schema
        elif schema is not None and self.cfg.ollama_format == "json":
            payload["format"] = "json"
        req = urllib.request.Request(
            f"{self.cfg.base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout_s) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError as e:
            raise LLMError(
                f"Ollama not reachable at {self.cfg.base_url} ({e}). Is `ollama serve` running and "
                f"`ollama pull {self.cfg.model}` done?"
            ) from e
        return LLMResponse(
            text=data.get("message", {}).get("content", ""),
            model=data.get("model", self.cfg.model),
            input_tokens=int(data.get("prompt_eval_count", 0)),
            output_tokens=int(data.get("eval_count", 0)),
            latency_s=time.perf_counter() - t0,
            raw={k: v for k, v in data.items() if k != "message"},
        )


class AnthropicClient:
    """Claude via the official SDK with ``output_config.format`` JSON schema."""

    def __init__(self, cfg: LLMConfig, api_key: str | None = None) -> None:
        import anthropic

        self.cfg = cfg
        self.client = anthropic.Anthropic(api_key=api_key, timeout=cfg.timeout_s)

    def complete(self, system, messages, schema=None) -> LLMResponse:
        output_config: dict[str, Any] = {}
        if self.cfg.effort:
            output_config["effort"] = self.cfg.effort
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        kwargs: dict[str, Any] = {
            "model": self.cfg.model,
            "max_tokens": self.cfg.max_tokens,
            "system": system,
            "messages": messages,
        }
        if output_config:
            kwargs["output_config"] = output_config
        t0 = time.perf_counter()
        resp = self.client.messages.create(**kwargs)
        if resp.stop_reason == "refusal":
            raise LLMError("model declined the request (stop_reason=refusal)")
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return LLMResponse(
            text=text,
            model=resp.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            latency_s=time.perf_counter() - t0,
            raw={"stop_reason": resp.stop_reason, "request_id": getattr(resp, "_request_id", None)},
        )


class StubClient:
    """Deterministic offline LLM for tests/CI.

    ``responses``: a list of canned outputs returned in order (str or callable(system, messages)).
    Default behaviour (no responses): a schema-valid answer that cites the top retrieved source of
    each tier, quoting its first sentence - enough to exercise the full pipeline end-to-end.
    """

    def __init__(
        self,
        cfg: LLMConfig | None = None,
        responses: Sequence[str | Callable[..., str]] | None = None,
    ) -> None:
        self.cfg = cfg or LLMConfig(provider="stub", model="stub")
        self.responses = list(responses or [])
        self.calls: list[dict[str, Any]] = []

    def complete(self, system, messages, schema=None) -> LLMResponse:
        self.calls.append({"system": system, "messages": messages, "schema": schema})
        if self.responses:
            r = self.responses.pop(0)
            text = r(system, messages) if callable(r) else r
        else:
            text = default_stub_answer(messages[0]["content"])
        n_in = sum(len(m["content"]) for m in messages) // 4 + len(system) // 4
        return LLMResponse(text=text, model="stub", input_tokens=n_in, output_tokens=len(text) // 4)


def default_stub_answer(user_prompt: str) -> str:
    import re

    section_for = {
        "binding": "mandatory",
        "expectation": "regulator_expects",
        "voluntary": "recommended",
    }
    out: dict[str, Any] = {k: [] for k in section_for.values()}
    for m in re.finditer(
        r'<source id="([^"]+)" tier="([^"]+)"[^>]*modality="([^"]+)"[^>]*>\n(.*?)\n</source>',
        user_prompt,
        re.S,
    ):
        cid, tier, modality, body = m.groups()
        section = section_for[tier]
        if out[section] or (section == "mandatory" and modality != "must"):
            continue
        first = body.split("\n", 1)[-1].split(". ")[0][:200]
        out[section].append({"claim": first, "citation_id": cid})
    abstained = not any(out.values())
    out["abstained"] = abstained
    out["abstain_reason"] = "No sources retrieved." if abstained else ""
    return json.dumps(out)


def make_llm(cfg: LLMConfig, seed: int = 42, api_key: str | None = None) -> LLMClient:
    if cfg.provider == "ollama":
        return OllamaClient(cfg, seed)
    if cfg.provider == "anthropic":
        return AnthropicClient(cfg, api_key)
    return StubClient(cfg)
