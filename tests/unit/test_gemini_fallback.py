"""Groq 429 falls through to Gemini Flash, and the answer still validates."""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from regnav.config import load_config
from regnav.generate.answer import answer_question
from regnav.generate.llm import make_llm
from regnav.retrieve import RetrievalSystem
from regnav.retrieve.base import Filters, RetrievedChunk

GOOD = {
    "mandatory": [{"claim": "Entities must undertake due diligence.", "citation_id": "cps:p52"}],
    "regulator_expects": [],
    "recommended": [],
    "abstained": False,
    "abstain_reason": "",
}


class _Static:
    def __init__(self, chunks):
        self.chunks = chunks

    def search(self, query, k, filters: Filters):
        return self.chunks[:k]


def _system() -> RetrievalSystem:
    chunk = RetrievedChunk(
        "cps:p52",
        "52. An APRA-regulated institution must undertake due diligence.",
        {"tier": "binding", "modality": "must", "short_name": "CPS 230"},
        0.9,
        1,
        {"dense": 0.9},
    )
    return RetrievalSystem(_Static([chunk]), 9, "idx-test", False, True)


class _Groq429(BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self):
        _Groq429.calls += 1
        body = json.dumps(
            {
                "error": {
                    "message": (
                        "Rate limit reached for model on tokens per day (TPD): "
                        "Limit 200000. Please try again in 10m."
                    ),
                    "type": "tokens",
                    "code": "rate_limit_exceeded",
                }
            }
        ).encode()
        self.send_response(429)
        self.send_header("Content-Type", "application/json")
        self.send_header("retry-after", "600")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class _GeminiOK(BaseHTTPRequestHandler):
    calls = 0
    seen_model = ""

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _GeminiOK.calls += 1
        _GeminiOK.seen_model = payload["model"]
        out = json.dumps(
            {
                "model": "gemini-3.8-flash",
                "choices": [{"message": {"content": json.dumps(GOOD)}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 400, "completion_tokens": 40},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


def _serve(handler):
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def test_groq_429_uses_gemini_and_the_answer_validates(monkeypatch, caplog) -> None:
    caplog.set_level(logging.INFO, logger="regnav.generate.llm")
    groq, gemini = _serve(_Groq429), _serve(_GeminiOK)
    _Groq429.calls = _GeminiOK.calls = 0
    monkeypatch.setenv("GROQ_API_KEY", "groq-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    try:
        cfg = load_config("configs/prod.yaml")
        cfg.generation.base_url = f"http://127.0.0.1:{groq.server_port}/v1"
        cfg.generation.fallback.base_url = f"http://127.0.0.1:{gemini.server_port}/v1"
        cfg.generation.scope_gate = False
        llm = make_llm(cfg.generation)
        first = answer_question(
            "What must an entity do before a material arrangement?", cfg, _system(), llm
        )
        assert first.valid and not first.answer.abstained
        assert first.llm_provider == "openai_compat"
        assert first.llm_model == "gemini-3.8-flash"
        assert first.llm_fallback_reason
        assert first.cited()[0][2] == "cps:p52"
        assert _Groq429.calls == 1 and _GeminiOK.calls == 1
        assert _GeminiOK.seen_model == "gemini-3.8-flash"
        events = [r.extra_fields["event"] for r in caplog.records if hasattr(r, "extra_fields")]
        assert "llm_call_failed" in events and "fallback_used" in events
        failed = next(
            r.extra_fields
            for r in caplog.records
            if r.extra_fields.get("event") == "llm_call_failed"
        )
        assert failed["http_status"] == 429
        assert failed["error_type"] == "rate_limit_exceeded"
        assert failed["model"] == "qwen/qwen3.8-27b"
        assert "groq-test" not in str(failed) and "gemini-test" not in str(failed)

        answer_question("What must an entity do?", cfg, _system(), llm)
        assert _Groq429.calls == 1  # TPD window: Groq is not called again
        assert _GeminiOK.calls == 2
    finally:
        groq.shutdown()
        gemini.shutdown()
