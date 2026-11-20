"""Public-demo guardrails: password gate, question cap, missing Groq key."""

from pathlib import Path

from regnav.demo_guard import (
    banner_text,
    footer_text,
    force_offline,
    git_sha,
    password_ok,
    password_required,
    question_block_reason,
)


def test_password_gate_is_off_without_the_demo_flag(monkeypatch) -> None:
    monkeypatch.delenv("REGNAV_PUBLIC_DEMO", raising=False)
    monkeypatch.setenv("APP_PASSWORD", "secret")
    assert password_required() is False
    assert password_ok("wrong") is True


def test_password_gate_rejects_a_wrong_password(monkeypatch) -> None:
    monkeypatch.setenv("REGNAV_PUBLIC_DEMO", "1")
    monkeypatch.setenv("APP_PASSWORD", "secret")
    assert password_required() is True
    assert password_ok("secret") is True
    assert password_ok("wrong") is False
    assert password_ok("secret ") is False


def test_password_gate_is_off_when_the_password_is_unset(monkeypatch) -> None:
    monkeypatch.setenv("REGNAV_PUBLIC_DEMO", "1")
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert password_required() is False
    assert password_ok("anything") is True


def test_question_cap_blocks_the_next_question_at_the_limit(monkeypatch) -> None:
    monkeypatch.setenv("MAX_QUESTIONS_PER_SESSION", "20")
    assert question_block_reason("What does CPS 230 require?", 19) is None
    reason = question_block_reason("What does CPS 230 require?", 20)
    assert reason is not None
    assert "20" in reason


def test_question_length_limit_is_500_characters() -> None:
    assert question_block_reason("a" * 500, 0) is None
    reason = question_block_reason("a" * 501, 0)
    assert reason is not None
    assert "500" in reason


def test_missing_groq_key_forces_offline_only_in_the_public_demo(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("REGNAV_PUBLIC_DEMO", raising=False)
    assert force_offline(ui_offline=False) is False
    monkeypatch.setenv("REGNAV_PUBLIC_DEMO", "1")
    assert force_offline(ui_offline=False) is True
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    assert force_offline(ui_offline=False) is False
    assert force_offline(ui_offline=True) is True


def test_footer_carries_corpus_date_index_and_sha(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GIT_SHA", raising=False)
    monkeypatch.setattr("regnav.demo_guard.Path", lambda p: tmp_path / "missing")
    assert git_sha() == "unknown"
    text = footer_text("idx-2185d086e9c4")
    assert "November 2026" in text
    assert "idx-2185d086e9c4" in text
    assert "git unknown" in text
    monkeypatch.setenv("GIT_SHA", "abcdef1234567890")
    assert git_sha() == "abcdef123456"
    assert "logged to Langfuse" in banner_text(langfuse_enabled=True)
    assert "not sent to Langfuse" in banner_text(langfuse_enabled=False)


def test_serve_script_listens_on_port_and_relaxes_proxy_checks() -> None:
    text = Path("serve.sh").read_text()
    assert "${PORT:-8501}" in text
    assert "--server.enableCORS=false" in text
    assert "--server.enableXsrfProtection=false" in text
    assert "--server.enableWebsocketCompression=false" in text
    assert "--server.fileWatcherType=none" in text
