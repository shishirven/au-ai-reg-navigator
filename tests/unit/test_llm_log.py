"""Provider error text is short and has no secrets, and prod logging can use stdout."""

import io
import json
import logging

from regnav.generate.llm import provider_error_parts, redact_secrets
from regnav.logging_utils import setup_logging


def test_provider_error_parts_reads_groq_code() -> None:
    body = json.dumps(
        {
            "error": {
                "message": "Rate limit reached. Bearer gsk_notarealkey",
                "type": "tokens",
                "code": "rate_limit_exceeded",
            }
        }
    )
    code, message = provider_error_parts(body)
    assert code == "rate_limit_exceeded"
    assert "Rate limit reached" in message
    assert "gsk_notarealkey" not in message
    assert "Bearer [redacted]" in message or "[redacted]" in message


def test_redact_secrets_truncates_prompt_sized_text() -> None:
    text = "error " + ("word " * 200)
    assert len(redact_secrets(text)) <= 180
    assert "gsk_abc123" not in redact_secrets("token gsk_abc123 end")


def test_setup_logging_info_goes_to_the_given_stream() -> None:
    root = logging.getLogger()
    old_handlers, old_level = root.handlers[:], root.level
    buf = io.StringIO()
    try:
        setup_logging("INFO", stream=buf)
        logging.getLogger("regnav.demo").info("llm call failed")
        line = buf.getvalue()
        assert '"level": "INFO"' in line
        assert "llm call failed" in line
    finally:
        root.handlers[:] = old_handlers
        root.setLevel(old_level)
