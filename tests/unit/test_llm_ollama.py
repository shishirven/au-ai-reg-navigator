"""OllamaClient against a local fake HTTP server (no Ollama needed)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from regnav.config import LLMConfig
from regnav.generate.llm import LLMError, OllamaClient


class _Handler(BaseHTTPRequestHandler):
    received: ClassVar[list[dict]] = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Handler.received.append(body)
        out = {
            "model": body["model"],
            "message": {"role": "assistant", "content": '{"ok": true}'},
            "prompt_eval_count": 123,
            "eval_count": 7,
        }
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture()
def server():
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    _Handler.received.clear()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


@pytest.mark.parametrize(
    "fmt,expected", [("none", None), ("json", "json"), ("schema", {"type": "object"})]
)
def test_payload_and_usage(server, fmt, expected) -> None:
    cfg = LLMConfig(
        provider="ollama",
        model="qwen3:4b",
        base_url=server,
        json_mode=fmt,
        num_ctx=8192,
        temperature=0.0,
    )
    r = OllamaClient(cfg, seed=7).complete(
        "SYS", [{"role": "user", "content": "hi"}], schema={"type": "object"}
    )
    sent = _Handler.received[-1]
    assert sent["messages"][0] == {"role": "system", "content": "SYS"}
    assert sent["options"] == {
        "num_ctx": 8192,
        "num_predict": cfg.max_tokens,
        "seed": 7,
        "temperature": 0.0,
    }
    assert sent["think"] is False and sent["stream"] is False
    assert sent.get("format") == expected
    assert (r.text, r.input_tokens, r.output_tokens) == ('{"ok": true}', 123, 7)


def test_unreachable_server_raises_helpful_error() -> None:
    cfg = LLMConfig(provider="ollama", base_url="http://127.0.0.1:9", timeout_s=2)
    with pytest.raises(LLMError, match="ollama pull"):
        OllamaClient(cfg).complete("s", [{"role": "user", "content": "x"}])


# --------------------------------------------------------------- OpenAI-compatible (Groq) client


class _GroqHandler(BaseHTTPRequestHandler):
    calls: ClassVar[list[dict]] = []
    fail_first: ClassVar[int] = 0

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _GroqHandler.calls.append({"body": body, "headers": dict(self.headers)})
        if _GroqHandler.fail_first > 0:
            _GroqHandler.fail_first -= 1
            self.send_response(429)
            self.send_header("retry-after", "0")
            self.end_headers()
            return
        out = {
            "model": body["model"],
            "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 5},
        }
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture()
def groq_server():
    httpd = HTTPServer(("127.0.0.1", 0), _GroqHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    _GroqHandler.calls.clear()
    yield f"http://127.0.0.1:{httpd.server_port}/v1"
    httpd.shutdown()


def test_openai_compat_payload_retry_and_headers(groq_server) -> None:
    from regnav.generate.llm import OpenAICompatClient

    _GroqHandler.fail_first = 2
    cfg = LLMConfig(
        provider="openai_compat",
        model="qwen/x",
        base_url=groq_server,
        reasoning_effort="none",
        json_mode="json",
        temperature=0.0,
    )
    client = OpenAICompatClient(cfg, seed=3)
    slept: list[float] = []
    client.sleep = slept.append
    r = client.complete("SYS", [{"role": "user", "content": "hi"}], schema={"type": "object"})
    assert (r.text, r.input_tokens, r.output_tokens) == ('{"ok": true}', 50, 5)
    assert len(_GroqHandler.calls) == 3 and len(slept) == 2  # two 429s, backed off, then success
    sent = _GroqHandler.calls[-1]
    assert sent["body"]["reasoning_effort"] == "none" and sent["body"]["response_format"] == {
        "type": "json_object"
    }
    assert sent["body"]["seed"] == 3 and sent["body"]["messages"][0]["role"] == "system"
    assert sent["headers"]["User-Agent"] == "regnav/0.1" and sent["headers"][
        "Authorization"
    ].startswith("Bearer ")


def test_openai_compat_gives_up_after_max_retries(groq_server) -> None:
    from regnav.generate.llm import OpenAICompatClient

    _GroqHandler.fail_first = 10
    cfg = LLMConfig(
        provider="openai_compat", model="m", base_url=groq_server, max_rate_limit_retries=1
    )
    client = OpenAICompatClient(cfg)
    client.sleep = lambda s: None
    with pytest.raises(LLMError, match="429"):
        client.complete("s", [{"role": "user", "content": "x"}])
    _GroqHandler.fail_first = 0


@pytest.mark.parametrize(
    "value,expected", [("7", 7.0), ("7.5s", 7.5), ("1m30s", 90.0), ("250ms", 0.25), (None, 3.0)]
)
def test_retry_after_parsing(value, expected) -> None:
    from regnav.generate.llm import _retry_after_seconds

    assert _retry_after_seconds(value, 3.0) == pytest.approx(expected)
