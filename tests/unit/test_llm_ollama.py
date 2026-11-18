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
        ollama_format=fmt,
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
