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
        if schema is not None and self.cfg.json_mode == "schema":
            payload["format"] = schema
        elif schema is not None and self.cfg.json_mode == "json":
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


GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _retry_after_seconds(value: str | None, default: float) -> float:
    """Parse Retry-After / x-ratelimit-reset values like '7', '7.5s', '1m30s', '250ms'."""
    if not value:
        return default
    import re

    total, matched = 0.0, False
    for num, unit in re.findall(r"([\d.]+)\s*(ms|s|m|h)?", value):
        matched = True
        total += float(num) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "": 1}[unit]
    return total if matched else default


class OpenAICompatClient:
    """OpenAI-compatible ``/chat/completions`` (Groq by default) with 429/5xx back-off.

    The Groq key is injected by the session's network proxy (never stored in code or env); a
    locally-set ``GROQ_API_KEY`` is used if present (e.g. on a laptop).
    """

    def __init__(self, cfg: LLMConfig, seed: int = 42) -> None:
        import os

        self.cfg = cfg
        self.seed = seed
        self.base_url = (
            cfg.base_url
            if cfg.provider == "openai_compat"
            else (cfg.base_url if "11434" not in cfg.base_url else GROQ_BASE_URL)
        )
        # Locally the key comes from the env (e.g. .env via docker compose). In the cloud dev
        # environment a network proxy injects it, so a placeholder is sent.
        self.api_key = os.environ.get(cfg.api_key_env) or "proxy-injected"
        self.sleep = time.sleep  # injectable for tests

    def complete(self, system, messages, schema=None) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "max_completion_tokens": self.cfg.max_tokens,
            "seed": self.seed,
        }
        if self.cfg.temperature is not None:
            payload["temperature"] = self.cfg.temperature
        if self.cfg.reasoning_effort:
            payload["reasoning_effort"] = self.cfg.reasoning_effort
        if schema is not None and self.cfg.json_mode == "json":
            payload["response_format"] = {"type": "json_object"}
        elif schema is not None and self.cfg.json_mode == "schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "answer", "schema": schema, "strict": False},
            }
        data = json.dumps(payload).encode()
        t0 = time.perf_counter()
        for attempt in range(self.cfg.max_rate_limit_retries + 1):
            req = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    # Cloudflare in front of Groq rejects Python-urllib's default UA (error 1010)
                    "User-Agent": "regnav/0.1",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.cfg.timeout_s) as resp:
                    body = json.loads(resp.read())
                break
            except urllib.error.HTTPError as e:
                retryable = e.code == 429 or e.code >= 500
                if not retryable or attempt == self.cfg.max_rate_limit_retries:
                    detail = e.read().decode(errors="replace")[:300]
                    hint = ""
                    if e.code == 401 and self.api_key == "proxy-injected":
                        hint = f" - {self.cfg.api_key_env} is not set (add it to .env and recreate the container)"
                    elif e.code == 401:
                        hint = f" - check {self.cfg.api_key_env} in .env (expected a full key, e.g. 56 chars for Groq)"
                    raise LLMError(f"{self.cfg.provider} HTTP {e.code}{hint}: {detail}") from e
                wait = _retry_after_seconds(
                    e.headers.get("retry-after") or e.headers.get("x-ratelimit-reset-tokens"),
                    default=min(60.0, 2.0**attempt),
                )
                self.sleep(min(wait + 0.5, 120.0))
            except urllib.error.URLError as e:
                raise LLMError(f"{self.cfg.provider} not reachable at {self.base_url}: {e}") from e
        choice = body["choices"][0]
        usage = body.get("usage", {})
        return LLMResponse(
            text=choice["message"].get("content") or "",
            model=body.get("model", self.cfg.model),
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            latency_s=time.perf_counter() - t0,
            raw={"finish_reason": choice.get("finish_reason"), "usage": usage},
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
        text = body.split("\n", 1)[-1]
        text = re.sub(r"^\s*\d{1,3}\.\s+", "", text)  # drop a leading paragraph number ("52. ")
        first = re.split(r"(?<=[a-z\)])\.\s", text, maxsplit=1)[0][:200]
        out[section].append({"claim": first, "citation_id": cid})
    abstained = not any(out.values())
    out["abstained"] = abstained
    out["abstain_reason"] = "No sources retrieved." if abstained else ""
    return json.dumps(out)


def make_llm(cfg: LLMConfig, seed: int = 42, api_key: str | None = None) -> LLMClient:
    if cfg.provider == "ollama":
        return OllamaClient(cfg, seed)
    if cfg.provider in ("groq", "openai_compat"):
        return OpenAICompatClient(cfg, seed)
    if cfg.provider == "anthropic":
        return AnthropicClient(cfg, api_key)
    return StubClient(cfg)
