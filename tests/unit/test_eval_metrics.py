"""Metric maths on hand-computed toy examples."""

import json
from pathlib import Path

import pytest

from regnav.eval.dataset import DraftQuestionsError, load_questions, validate_gold_ids
from regnav.eval.generation_metrics import abstention_scores, claim_metrics, parse_raw, tier_recall
from regnav.eval.retrieval_metrics import (
    binding_coverage,
    binding_gold_hit,
    recall_at_k,
    reciprocal_rank,
)
from regnav.eval.stats import bootstrap_ci, cohens_kappa, mean_or_none, percentile
from regnav.generate.schema import Claim, StructuredAnswer


def test_recall_at_k() -> None:
    ret = ["a", "b", "c", "d", "e", "f"]
    assert recall_at_k(ret, ["a", "f"], k=5) == 0.5
    assert recall_at_k(ret, ["a", "f"], k=6) == 1.0
    assert recall_at_k(ret, ["z"], k=5) == 0.0
    assert recall_at_k(ret, [], k=5) is None
    assert recall_at_k(ret, ["a", "a"], k=1) == 1.0  # duplicate gold counted once


def test_reciprocal_rank() -> None:
    assert reciprocal_rank(["x", "y", "g"], ["g"]) == pytest.approx(1 / 3)
    assert reciprocal_rank(["g"], ["g", "h"]) == 1.0
    assert reciprocal_rank(["x"], ["g"]) == 0.0
    assert reciprocal_rank(["x"], []) is None


def test_binding_coverage_and_gold_hit() -> None:
    assert binding_coverage(["voluntary", "binding"], ["binding", "voluntary"]) == 1.0
    assert binding_coverage(["voluntary"], ["binding"]) == 0.0
    assert binding_coverage(["binding"], ["voluntary"]) is None  # no binding gold -> excluded
    tier_of = {"b1": "binding", "b2": "binding", "v1": "voluntary"}
    assert (
        binding_gold_hit(["b2", "v1"], ["b1", "v1"], tier_of) == 0.0
    )  # a binding chunk, but not the gold one
    assert binding_gold_hit(["b1"], ["b1"], tier_of) == 1.0
    assert binding_gold_hit(["b1"], ["v1"], tier_of) is None


RET = {
    "b:1": {"tier": "binding", "modality": "must"},
    "e:1": {"tier": "expectation", "modality": "should"},
}


def test_claim_metrics_hand_computed() -> None:
    ans = StructuredAnswer(
        mandatory=[
            Claim(claim="must do x", citation_id="b:1"),
            Claim(claim="must do y", citation_id="e:1"),
        ],
        regulator_expects=[Claim(claim="z", citation_id="nope")],
    )
    m = claim_metrics(ans, RET)
    assert m["n_claims"] == 3
    assert m["citation_validity"] == pytest.approx(2 / 3)
    assert m["authority_label_accuracy"] == pytest.approx(
        1 / 2
    )  # e:1 under mandatory is mislabelled
    assert m["modality_error_rate"] == pytest.approx(1 / 3)
    assert claim_metrics(StructuredAnswer(abstained=True), RET)["citation_validity"] is None
    assert claim_metrics(None, RET)["n_claims"] == 0


def test_parse_raw_and_tier_recall() -> None:
    assert parse_raw("garbage") is None
    ans = parse_raw(json.dumps({"mandatory": [{"claim": "x", "citation_id": "b:1"}]}))
    assert ans is not None
    assert tier_recall(ans, ["binding", "voluntary"]) == 0.5
    assert tier_recall(ans, []) is None


def test_abstention_precision_recall() -> None:
    rows = [
        {"abstained": True, "answerable": False},  # TP
        {"abstained": True, "answerable": True},  # FP
        {"abstained": False, "answerable": False},  # FN
        {"abstained": False, "answerable": True},  # TN
        {"abstained": True, "answerable": False},  # TP
    ]
    s = abstention_scores(rows)
    assert s["abstention_precision"] == pytest.approx(2 / 3)
    assert s["abstention_recall"] == pytest.approx(2 / 3)
    assert abstention_scores([{"abstained": False, "answerable": True}]) == {
        "abstention_precision": None,
        "abstention_recall": None,
    }


def test_cohens_kappa_hand_computed() -> None:
    # 2x2: agree on 8/10; p_o = .8; marginals a: 6 yes/4 no, b: 6 yes/4 no -> p_e = .36+.16 = .52
    a = [1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
    b = [1, 1, 1, 1, 1, 0, 1, 0, 0, 0]
    assert cohens_kappa(a, b) == pytest.approx((0.8 - 0.52) / (1 - 0.52))
    assert cohens_kappa([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert cohens_kappa([3, 3], [3, 3]) == 1.0
    # quadratic weights penalise near-misses less than far misses
    near = cohens_kappa([1, 2, 3, 4, 5], [2, 2, 3, 4, 5], weights="quadratic")
    far = cohens_kappa([1, 2, 3, 4, 5], [5, 2, 3, 4, 5], weights="quadratic")
    assert near > far
    with pytest.raises(ValueError):
        cohens_kappa([1], [1, 2])


def test_bootstrap_ci_contains_mean_and_is_deterministic() -> None:
    vals = [0.0] * 10 + [1.0] * 30
    point, lo, hi = bootstrap_ci(vals, lambda xs: sum(xs) / len(xs), n_boot=500, seed=1)
    assert point == 0.75 and lo < 0.75 < hi and lo > 0.5 and hi <= 1.0
    assert (point, lo, hi) == bootstrap_ci(vals, lambda xs: sum(xs) / len(xs), n_boot=500, seed=1)
    assert bootstrap_ci([1.0], lambda xs: xs[0]) == (1.0, None, None)
    const = bootstrap_ci([1.0] * 20, lambda xs: sum(xs) / len(xs), n_boot=200)
    assert const == (1.0, 1.0, 1.0)


def test_small_helpers() -> None:
    assert mean_or_none([None, 1.0, 3.0]) == 2.0 and mean_or_none([None]) is None
    assert percentile([1, 2, 3, 4], 50) == 2.5 and percentile([], 50) is None


def _write(p: Path, rows: list[dict]) -> Path:
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def test_dataset_refuses_drafts_unless_allowed(tmp_path: Path) -> None:
    rows = [
        {"id": "D1", "status": "DRAFT", "question": "q", "type": "factual", "gold_chunk_ids": ["a"]}
    ]
    p = _write(tmp_path / "q.jsonl", rows)
    with pytest.raises(DraftQuestionsError):
        load_questions(p)
    assert load_questions(p, allow_draft=True)[0].id == "D1"


def test_dataset_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="without gold"):
        load_questions(
            _write(tmp_path / "a.jsonl", [{"id": "1", "question": "q", "type": "factual"}])
        )
    with pytest.raises(ValueError, match="duplicate"):
        load_questions(
            _write(tmp_path / "b.jsonl", [{"id": "1", "question": "q", "type": "unanswerable"}] * 2)
        )
    qs = load_questions(
        _write(
            tmp_path / "c.jsonl",
            [{"id": "1", "question": "q", "type": "factual", "gold_chunk_ids": ["x", "y"]}],
        )
    )
    assert validate_gold_ids(qs, {"x"}) == ["1:y"]


def test_draft_file_in_repo_is_draft_and_valid() -> None:
    qs = load_questions(Path("data/eval/questions_draft.jsonl"), allow_draft=True)
    assert len(qs) == 40 and all(q.status == "DRAFT" for q in qs)
    assert {q.type for q in qs} == {"split", "factual", "cross_doc", "unanswerable"}
