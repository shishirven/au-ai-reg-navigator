"""Structured (JSON-lines) logging. Never log secrets or user PII."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        JsonFormatter() if json_format else logging.Formatter("%(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for noisy in ("httpx", "httpx2", "chromadb", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    # Offline-by-design containers: "could not reach the Hub ... using cached" is expected noise.
    for offline_noise in ("huggingface_hub", "sentence_transformers", "transformers"):
        logging.getLogger(offline_noise).setLevel(logging.ERROR)
