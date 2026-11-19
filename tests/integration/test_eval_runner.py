"""run_eval end-to-end on fixtures with the stub LLM and a stub judge (no network)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import yaml

from regnav.config import AppConfig
from regnav.ingest.index import ingest

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parents[1] / "fixtures"


def _cfg_file(cfg: AppConfig, tmp_path: Path) -> Path:
    data = json.loads(cfg.model_dump_json())
    data["judge"] = {"provider": "stub", "model": "stub-judge"}
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(data))
    return p


def test_run_eval_full_with_stubs_and_resume(
    fixture_cfg: AppConfig, tmp_path: Path, monkeypatch
) -> None:
    from regnav.eval import run_eval
    from regnav.generate import llm as llm_mod

    ingest(fixture_cfg)
    cfg_path = _cfg_file(fixture_cfg, tmp_path)
    judge_reply = json.dumps(
        {"claims": [{"i": 1, "supported": True}, {"i": 2, "supported": False}], "correctness": 4}
    )
    real_make = llm_mod.make_llm

    def fake_make(cfg, seed=42, api_key=None, use_fallback=True):
        assert use_fallback is False  # evals must never fall back to another model
        if cfg.model == "stub-judge":
            return llm_mod.StubClient(cfg, responses=[judge_reply] * 50)
        return real_make(cfg, seed, api_key, use_fallback=False)

    monkeypatch.setattr(llm_mod, "make_llm", fake_make)
    args = argparse.Namespace(
        config=str(cfg_path),
        questions=str(FIXTURES / "questions.jsonl"),
        allow_draft=False,
        retrieval_only=False,
        no_judge=False,
        no_mlflow=False,
        limit=None,
        ids=None,
        resume=None,
    )
    assert run_eval.run(args) == 0
    out = next(fixture_cfg.paths.results_dir.glob("fixture__*"))
    rows = [json.loads(line) for line in (out / "per_question.jsonl").read_text().splitlines()]
    assert [r["id"] for r in rows] == ["F01", "F02", "F03", "F04", "F05", "F06"]
    assert all("_judge_payload" not in r for r in rows)
    judged = [r for r in rows if r.get("correctness_raw") is not None]
    assert judged and all(r["correctness"] == 0.75 for r in judged)
    metrics = json.loads((out / "metrics.json").read_text())
    assert metrics["meta"]["mode"] == "full" and metrics["meta"]["is_draft"] is False
    assert metrics["metrics"]["binding_coverage"]["value"] == 1.0
    assert (fixture_cfg.paths.mlruns_dir / "mlflow.db").exists()

    # resume: nothing re-generated, same rows
    args.resume, args.no_mlflow = str(out), True
    assert run_eval.run(args) == 0
    assert len((out / "per_question.jsonl").read_text().splitlines()) == 6


def test_run_eval_retrieval_only_refuses_drafts(fixture_cfg: AppConfig, tmp_path: Path) -> None:
    from regnav.eval import run_eval
    from regnav.eval.dataset import DraftQuestionsError

    ingest(fixture_cfg)
    drafts = tmp_path / "d.jsonl"
    drafts.write_text(
        json.dumps(
            {
                "id": "X",
                "status": "DRAFT",
                "question": "q",
                "type": "factual",
                "gold_chunk_ids": ["xps901:p2"],
            }
        )
        + "\n"
    )
    args = argparse.Namespace(
        config=str(_cfg_file(fixture_cfg, tmp_path)),
        questions=str(drafts),
        allow_draft=False,
        retrieval_only=True,
        no_judge=True,
        no_mlflow=True,
        limit=None,
        ids=None,
        resume=None,
    )
    with pytest.raises(DraftQuestionsError):
        run_eval.run(args)
    args.allow_draft = True
    assert run_eval.run(args) == 0
    assert next(fixture_cfg.paths.results_dir.glob("fixture__*__DRAFT__retrieval"))
