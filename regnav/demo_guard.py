"""Public-demo guardrails for the Streamlit UI.

Off unless ``REGNAV_PUBLIC_DEMO=1`` (set in the Cloud Run image, unset by
docker-compose). Retrieval and generation are unchanged; the app calls these
checks before ``answer_question``.
"""

from __future__ import annotations

import hmac
import os
from pathlib import Path

CORPUS_AS_OF = "November 2026"
MAX_QUESTION_CHARS = 500
DEFAULT_MAX_QUESTIONS = 20


def public_demo_enabled() -> bool:
    return os.environ.get("REGNAV_PUBLIC_DEMO") == "1"


def max_questions_per_session() -> int:
    raw = os.environ.get("MAX_QUESTIONS_PER_SESSION", "").strip()
    if not raw:
        return DEFAULT_MAX_QUESTIONS
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_MAX_QUESTIONS
    return max(1, n)


def password_required() -> bool:
    return public_demo_enabled() and bool(os.environ.get("APP_PASSWORD", "").strip())


def password_ok(provided: str) -> bool:
    """Constant-time check. A missing password, or the demo flag off, allows everyone."""
    expected = os.environ.get("APP_PASSWORD", "")
    if not password_required():
        return True
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def question_block_reason(question: str, asked: int) -> str | None:
    """Why this question must not be sent, or None when it may be."""
    if len(question) > MAX_QUESTION_CHARS:
        return f"Questions are limited to {MAX_QUESTION_CHARS} characters on the public demo."
    cap = max_questions_per_session()
    if asked >= cap:
        return (
            f"This session has reached the limit of {cap} questions. "
            "Refresh the page to start a new session."
        )
    return None


def force_offline(*, ui_offline: bool) -> bool:
    """Offline stub when the toggle is on, or when the public demo has no Groq key.

    An empty key outside the public demo stays on the normal client. That client
    sends a placeholder so a dev proxy can inject the key (see OpenAICompatClient).
    """
    if ui_offline:
        return True
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return public_demo_enabled() and not key


def git_sha() -> str:
    env = os.environ.get("GIT_SHA", "").strip()
    if env and env != "unknown":
        return env[:12]
    revision = Path("/app/REVISION")
    if revision.is_file():
        text = revision.read_text().strip()
        if text and text != "unknown":
            return text[:12]
    return "unknown"


def banner_text(*, langfuse_enabled: bool) -> str:
    notice = "Not legal advice. Do not enter personal, customer, or confidential information. "
    if langfuse_enabled:
        return notice + "Questions are logged to Langfuse for quality monitoring."
    return notice + "Questions are not sent to Langfuse on this deployment."


def footer_text(index_version: str) -> str:
    return (
        f"Corpus retrieved {CORPUS_AS_OF} · index {index_version} · git {git_sha()} · "
        "General information from public documents, not legal advice."
    )
