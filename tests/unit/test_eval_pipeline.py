"""compute_metrics, compare.render, release_check and the regression gate (hashing embedder)."""

import json
from pathlib import Path

import pytest

from regnav.eval.compare import load_runs, pick, render
from regnav.eval.regression_gate import run_gate
from regnav.eval.release_check import check_release
from regnav.eval.run_eval import compute_metrics


def _rows():
    return [
        {
            "recall_at_5": 1.0,
            "rr": 1.0,
            "binding_coverage": 1.0,
            "abstained": False,
            "answerable": True,
            "faithfulness": 1.0,
            "correctness": 1.0,
            "fallback": 0.0,
            "repaired": 0.0,
            "gated": 0.0,
            "total_latency_s": 2.0,
            "input_tokens": 100,
            "output_tokens": 10,
            "cost_usd": 0.0,
        },
        {
            "recall_at_5": 0.0,
            "rr": 0.5,
            "binding_coverage": None,
            "abstained": True,
            "answerable": True,
            "faithfulness": None,
            "correctness": 0.0,
            "fallback": 1.0,
            "repaired": 0.0,
            "gated": 0.0,
            "total_latency_s": 4.0,
            "input_tokens": 200,
            "output_tokens": 20,
            "cost_usd": 0.0,
        },
        {
            "recall_at_5": None,
            "rr": None,
            "binding_coverage": None,
            "abstained": True,
            "answerable": False,
            "faithfulness": None,
            "correctness": 1.0,
            "fallback": 0.0,
            "repaired": 0.0,
            "gated": 1.0,
            "total_latency_s": 0.1,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        },
    ]


def test_compute_metrics() -> None:
    m = compute_metrics(_rows())
    assert m["n_questions"] == 3
    assert m["recall_at_5"]["value"] == 0.5 and m["recall_at_5"]["n"] == 2
    assert m["mrr"]["value"] == 0.75
    assert m["binding_coverage"]["n"] == 1
    assert m["answer_correctness"]["value"] == pytest.approx(2 / 3)
    assert m["abstention_precision"]["value"] == 0.5 and m["abstention_recall"]["value"] == 1.0
    assert m["latency_p50_s"]["value"] == 3.0  # gated question excluded from latency
    assert m["fallback_rate"]["value"] == pytest.approx(1 / 3)


def _run(
    tmp: Path,
    name: str,
    config: str,
    mode: str,
    draft: bool,
    started: str,
    index: str,
    metrics: dict,
) -> None:
    d = tmp / name
    d.mkdir(parents=True)
    meta = {
        "config": config,
        "mode": mode,
        "is_draft": draft,
        "started": started,
        "index_version": index,
        "questions_file": "q.jsonl",
        "generator": "g",
    }
    (d / "metrics.json").write_text(
        json.dumps({"meta": meta, "metrics": {"n_questions": 30, **metrics}})
    )


GOOD = {
    "faithfulness": {"value": 0.9},
    "citation_validity": {"value": 1.0},
    "modality_error_rate": {"value": 0.0},
    "authority_label_accuracy": {"value": 1.0},
    "binding_coverage": {"value": 0.95},
}
TH = {
    "min_faithfulness": 0.85,
    "min_citation_validity": 0.98,
    "max_modality_error_rate": 0.02,
    "min_authority_label_accuracy": 0.95,
    "min_binding_coverage": 0.9,
}


def test_compare_prefers_gold_and_marks_drafts(tmp_path: Path) -> None:
    _run(
        tmp_path,
        "a",
        "hybrid_stratified",
        "full",
        True,
        "20260101",
        "idx-1",
        {"recall_at_5": {"value": 0.5}},
    )
    _run(
        tmp_path,
        "b",
        "hybrid_stratified",
        "full",
        False,
        "20250101",
        "idx-1",
        {"recall_at_5": {"value": 0.7}},
    )
    _run(
        tmp_path,
        "c",
        "baseline_dense",
        "retrieval-only",
        True,
        "20260101",
        "idx-1",
        {"recall_at_5": {"value": 0.4, "ci_low": 0.3, "ci_high": 0.5}},
    )
    runs = load_runs(tmp_path)
    full, _ = pick(runs, "hybrid_stratified")
    assert full["meta"]["is_draft"] is False  # gold beats a newer draft
    md = render(runs, ["baseline_dense", "hybrid_stratified"])
    assert "PROVISIONAL" in md and "0.400 [0.30, 0.50]" in md and "0.700" in md


def test_release_check(tmp_path: Path) -> None:
    _run(tmp_path, "g", "cfg", "full", False, "2", "idx-1", GOOD)
    ok, msgs = check_release(load_runs(tmp_path), "cfg", "idx-1", TH)
    assert ok, msgs
    ok, msgs = check_release(load_runs(tmp_path), "cfg", "idx-2", TH)  # sources changed since eval
    assert not ok and any("re-run the full eval" in m for m in msgs)
    bad = {**GOOD, "modality_error_rate": {"value": 0.1}}
    _run(tmp_path, "h", "cfg", "full", False, "3", "idx-1", bad)
    ok, msgs = check_release(load_runs(tmp_path), "cfg", "idx-1", TH)
    assert not ok and any(m.startswith("FAIL  modality_error_rate") for m in msgs)


def test_release_check_rejects_draft_only(tmp_path: Path) -> None:
    _run(tmp_path, "d", "cfg", "full", True, "1", "idx-1", GOOD)
    assert not check_release(load_runs(tmp_path), "cfg", "idx-1", TH)[0]
    assert check_release(load_runs(tmp_path), "cfg", "idx-1", TH, allow_draft=True)[0]


def test_regression_gate_runs_offline_with_hashing(tmp_path: Path) -> None:
    th = tmp_path / "th.yaml"
    th.write_text("min_recall_at_5: 0.0\nmin_mrr: 0.0\nmin_binding_coverage: 1.0\n")
    ok, metrics = run_gate("configs/hybrid_stratified.yaml", th, embedding_backend="hashing")
    assert ok and metrics["binding_coverage"] == 1.0
    th.write_text("min_recall_at_5: 1.01\nmin_mrr: 0.0\nmin_binding_coverage: 0.0\n")
    assert run_gate("configs/hybrid_stratified.yaml", th, embedding_backend="hashing")[0] is False


def test_infrastructure_errors_are_not_recorded_as_results() -> None:
    from regnav.eval.run_eval import infrastructure_error

    assert infrastructure_error({"error": "groq HTTP 429: tokens per day"}).startswith(
        "groq HTTP 429"
    )
    assert infrastructure_error({"judge_unavailable": "HTTP 429"}).startswith("judge:")
    assert (
        infrastructure_error({"judge_error": "bad JSON from judge"}) is None
    )  # model output problem: kept
    assert infrastructure_error({"abstained": True}) is None
