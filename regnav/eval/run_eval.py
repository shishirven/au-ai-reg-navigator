"""Run an evaluation of one config on a question set and log it to MLflow.

    python -m regnav.eval.run_eval --config configs/hybrid_stratified.yaml
    python -m regnav.eval.run_eval --config ... --retrieval-only        # no LLM, deterministic
    python -m regnav.eval.run_eval --config ... --questions data/eval/questions_draft.jsonl --allow-draft

Outputs (results/<config>__<timestamp>[__DRAFT]/): per_question.jsonl (checkpointed after every
question; re-run with --resume <dir> to continue), per_question.csv, metrics.json, summary.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from regnav.config import TIER_TO_SECTION, AppConfig, Secrets, load_config
from regnav.eval.dataset import EvalQuestion, file_sha256, load_questions, validate_gold_ids
from regnav.eval.generation_metrics import abstention_scores, claim_metrics, parse_raw, tier_recall
from regnav.eval.retrieval_metrics import (
    binding_coverage,
    binding_gold_hit,
    recall_at_k,
    reciprocal_rank,
)
from regnav.eval.stats import bootstrap_ci, mean_or_none, percentile

log = logging.getLogger(__name__)
K = 5

# metric name -> per-question field (bootstrapped as a mean over questions where not None)
MEAN_METRICS = {
    "recall_at_5": "recall_at_5",
    "mrr": "rr",
    "binding_coverage": "binding_coverage",
    "binding_gold_hit": "binding_gold_hit",
    "faithfulness": "faithfulness",
    "answer_correctness": "correctness",
    "citation_validity": "citation_validity",
    "authority_label_accuracy": "authority_label_accuracy",
    "modality_error_rate": "modality_error_rate",
    "raw_citation_validity": "raw_citation_validity",
    "raw_authority_label_accuracy": "raw_authority_label_accuracy",
    "raw_modality_error_rate": "raw_modality_error_rate",
    "tier_recall": "tier_recall",
    "fallback_rate": "fallback",
    "repair_rate": "repaired",
    "gate_abstain_rate": "gated",
}


def evaluate_question(
    q: EvalQuestion, cfg: AppConfig, retrieval, llm, judge_llm, tracer, tier_of
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": q.id,
        "question": q.question,
        "sector": q.sector,
        "type": q.type,
        "answerable": q.answerable,
        "gold_chunk_ids": q.gold_chunk_ids,
        "expected_tiers": q.expected_tiers,
        "reference_answer": q.reference_answer,
    }
    t0 = time.perf_counter()
    if llm is None:
        chunks = retrieval.search(q.question, sector=q.sector)
        result = None
    else:
        from regnav.generate.answer import answer_question

        result = answer_question(q.question, cfg, retrieval, llm, sector=q.sector, tracer=tracer)
        chunks = result.retrieved
    ids = [c.chunk_id for c in chunks]
    tiers = [c.tier for c in chunks]
    gold_tiers = [tier_of.get(g, "") for g in q.gold_chunk_ids]
    row.update(
        retrieved_ids=ids,
        retrieved_tiers=tiers,
        recall_at_5=recall_at_k(ids, q.gold_chunk_ids, K),
        rr=reciprocal_rank(ids, q.gold_chunk_ids),
        binding_coverage=binding_coverage(tiers, gold_tiers),
        binding_gold_hit=binding_gold_hit(ids, q.gold_chunk_ids, tier_of),
        retrieval_latency_s=time.perf_counter() - t0
        if result is None
        else result.retrieval_latency_s,
    )
    if result is None:
        return row

    meta = {c.chunk_id: c.metadata for c in chunks}
    text = {c.chunk_id: c.text for c in chunks}
    final = claim_metrics(result.answer, meta)
    raw = (
        claim_metrics(parse_raw(result.attempts[0].raw), meta)
        if result.attempts
        else claim_metrics(None, meta)
    )
    claims = [{"section": s, "claim": c, "citation_id": cid} for s, c, cid in result.cited()]
    row.update(
        abstained=result.answer.abstained,
        abstain_reason=result.answer.abstain_reason,
        gated=1.0 if result.gate_reason else 0.0,
        fallback=1.0 if result.fallback else 0.0,
        repaired=1.0 if result.repaired else 0.0,
        valid=result.valid,
        n_attempts=len(result.attempts),
        validation_errors=[a.error_types for a in result.attempts],
        repairs=[a.repairs for a in result.attempts],
        claims=claims,
        citation_validity=final["citation_validity"],
        authority_label_accuracy=final["authority_label_accuracy"],
        modality_error_rate=final["modality_error_rate"],
        n_claims=final["n_claims"],
        raw_citation_validity=raw["citation_validity"],
        raw_authority_label_accuracy=raw["authority_label_accuracy"],
        raw_modality_error_rate=raw["modality_error_rate"],
        tier_recall=tier_recall(result.answer, q.expected_tiers) if q.answerable else None,
        total_latency_s=result.total_latency_s,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
        error=result.error,
        index_version=result.index_version,
        trace_url=result.trace_url,
    )
    # correctness: abstention handled by rule, answers by the judge
    if not q.answerable:
        row.update(
            correctness=1.0 if result.answer.abstained else 0.0,
            correctness_raw=None,
            faithfulness=None,
        )
    elif result.answer.abstained or not claims:
        row.update(correctness=0.0, correctness_raw=None, faithfulness=None)
    elif judge_llm is not None:
        # Deferred: judged by run() in a background thread (separate rate-limit quota), so the
        # judge call for this question overlaps generation of the next one.
        row["_judge_payload"] = (
            q.question,
            q.reference_answer,
            [{**c, "source_text": text.get(c["citation_id"], "")} for c in claims],
        )
    return row


def infrastructure_error(row: dict[str, Any]) -> str | None:
    """An LLM or judge outage (rate limit, auth, network) - not model behaviour. Such rows are
    not recorded, so a quota hit can never masquerade as an abstention or a judge score."""
    if row.get("error"):
        return str(row["error"])[:300]
    if row.get("judge_unavailable"):
        return "judge: " + str(row["judge_unavailable"])[:300]
    return None


def finish_judging(row: dict[str, Any], judge_llm) -> dict[str, Any]:
    payload = row.pop("_judge_payload", None)
    if payload is not None and judge_llm is not None:
        from regnav.eval.judge import judge_answer

        row.update(judge_answer(judge_llm, *payload))
    return row


def compute_metrics(rows: list[dict[str, Any]], seed: int = 42) -> dict[str, Any]:
    out: dict[str, Any] = {"n_questions": len(rows)}

    def mean_of(field: str) -> Callable[[Sequence[dict[str, Any]]], float | None]:
        def stat(rs: Sequence[dict[str, Any]]) -> float | None:
            return mean_or_none([r.get(field) for r in rs])

        return stat

    def abstention(key: str) -> Callable[[Sequence[dict[str, Any]]], float | None]:
        def stat(rs: Sequence[dict[str, Any]]) -> float | None:
            return abstention_scores(list(rs))[key]

        return stat

    for name, field in MEAN_METRICS.items():
        if not any(r.get(field) is not None for r in rows):
            continue
        point, lo, hi = bootstrap_ci(rows, mean_of(field), seed=seed)
        n = sum(1 for r in rows if r.get(field) is not None)
        out[name] = {"value": point, "ci_low": lo, "ci_high": hi, "n": n}
    if any("abstained" in r for r in rows):
        for key in ("abstention_precision", "abstention_recall"):
            point, lo, hi = bootstrap_ci(rows, abstention(key), seed=seed)
            out[key] = {"value": point, "ci_low": lo, "ci_high": hi, "n": len(rows)}
        lat = [
            r["total_latency_s"]
            for r in rows
            if r.get("total_latency_s") is not None and not r.get("gated")
        ]
        out["latency_p50_s"] = {"value": percentile(lat, 50), "n": len(lat)}
        out["latency_p95_s"] = {"value": percentile(lat, 95), "n": len(lat)}
        out["mean_input_tokens"] = {"value": mean_or_none([r.get("input_tokens") for r in rows])}
        out["mean_output_tokens"] = {"value": mean_or_none([r.get("output_tokens") for r in rows])}
        out["mean_cost_usd"] = {"value": mean_or_none([r.get("cost_usd") for r in rows])}
    return out


def _fmt(m: dict[str, Any] | None) -> str:
    if not m or m.get("value") is None:
        return "-"
    v = m["value"]
    if m.get("ci_low") is None:
        return f"{v:.3f}"
    return f"{v:.3f} [{m['ci_low']:.2f}, {m['ci_high']:.2f}]"


def write_summary(
    path: Path, cfg: AppConfig, metrics: dict[str, Any], meta: dict[str, Any]
) -> None:
    lines = [
        f"# Eval: {cfg.name}" + ("  (DRAFT QUESTIONS - provisional)" if meta["is_draft"] else ""),
        "",
        f"- questions: `{meta['questions_file']}` (n={metrics['n_questions']}, sha256 {meta['questions_sha256'][:12]})",
        f"- index_version: `{meta['index_version']}`; retrieval mode: `{cfg.retrieval.mode}`",
        f"- generator: `{cfg.generation.provider}/{cfg.generation.model}`; judge: `{cfg.judge.provider}/{cfg.judge.model}`",
        f"- mode: {meta['mode']}; started {meta['started']}",
        "",
        "| metric | value [95% bootstrap CI] | n |",
        "|---|---|---|",
    ]
    for k, m in metrics.items():
        if isinstance(m, dict):
            lines.append(f"| {k} | {_fmt(m)} | {m.get('n', '')} |")
    lines += ["", f"n={metrics['n_questions']}: differences smaller than the CI widths are noise."]
    path.write_text("\n".join(lines) + "\n")


def log_to_mlflow(
    cfg: AppConfig,
    metrics: dict[str, Any],
    meta: dict[str, Any],
    out_dir: Path,
    config_path: str | None,
) -> str:
    import mlflow

    from regnav.eval.tracking import setup_mlflow

    setup_mlflow(cfg, "regnav-eval")
    with mlflow.start_run(run_name=out_dir.name) as run:
        mlflow.set_tags(
            {
                "config_name": cfg.name,
                "index_version": meta["index_version"],
                "is_draft": str(meta["is_draft"]),
                "mode": meta["mode"],
                "questions_sha256": meta["questions_sha256"],
            }
        )
        params = cfg.flat_params()
        params.update(
            {"questions_file": meta["questions_file"], "n_questions": str(metrics["n_questions"])}
        )
        mlflow.log_params({k: v[:250] for k, v in params.items()})
        flat: dict[str, float] = {}
        for k, m in metrics.items():
            if isinstance(m, dict) and m.get("value") is not None:
                flat[k] = float(m["value"])
                if m.get("ci_low") is not None:
                    flat[f"{k}_ci_low"] = float(m["ci_low"])
                    flat[f"{k}_ci_high"] = float(m["ci_high"])
        mlflow.log_metrics(flat)
        for name in ("per_question.jsonl", "per_question.csv", "metrics.json", "summary.md"):
            mlflow.log_artifact(str(out_dir / name))
        if config_path:
            mlflow.log_artifact(config_path)
        return run.info.run_id


CSV_FIELDS = [
    "id",
    "type",
    "sector",
    "recall_at_5",
    "rr",
    "binding_coverage",
    "abstained",
    "gated",
    "fallback",
    "repaired",
    "n_claims",
    "citation_validity",
    "authority_label_accuracy",
    "modality_error_rate",
    "raw_modality_error_rate",
    "tier_recall",
    "faithfulness",
    "correctness",
    "total_latency_s",
    "input_tokens",
    "output_tokens",
    "question",
]


def run(args: argparse.Namespace) -> int:
    from regnav.ingest.index import load_chunk_rows
    from regnav.retrieve import build_retrieval

    cfg = load_config(args.config)
    qpath = Path(args.questions) if args.questions else cfg.paths.eval_questions
    questions = load_questions(qpath, allow_draft=args.allow_draft)
    is_draft = any((q.status or "").upper() == "DRAFT" for q in questions)
    if args.limit:
        questions = questions[: args.limit]
    if args.ids:
        wanted = set(args.ids.split(","))
        questions = [q for q in questions if q.id in wanted]

    rows_index = load_chunk_rows(cfg)
    tier_of = {r["chunk_id"]: r["tier"] for r in rows_index}
    stale = validate_gold_ids(questions, set(tier_of))
    if stale:
        print(
            f"WARNING: {len(stale)} gold ids not in the current index (re-chunked?): {stale[:5]}",
            file=sys.stderr,
        )

    retrieval = build_retrieval(cfg)
    llm = judge_llm = tracer = None
    mode = "retrieval-only"
    if not args.retrieval_only:
        from regnav.generate.llm import make_llm
        from regnav.observability.langfuse import get_tracer

        secrets = Secrets()
        # Evaluation never uses the local fallback: mixing models would contaminate comparisons.
        llm = make_llm(cfg.generation, cfg.seed, secrets.anthropic_api_key, use_fallback=False)
        judge_llm = (
            None
            if args.no_judge
            else make_llm(cfg.judge, cfg.seed, secrets.anthropic_api_key, use_fallback=False)
        )
        tracer = get_tracer(secrets)
        mode = "full" if judge_llm else "generation-no-judge"

    started = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = (
        Path(args.resume)
        if args.resume
        else cfg.paths.results_dir
        / (
            f"{cfg.name}__{started}"
            + ("__DRAFT" if is_draft else "")
            + ("__retrieval" if args.retrieval_only else "")
        )
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    pq = out_dir / "per_question.jsonl"
    done = (
        {json.loads(line)["id"]: json.loads(line) for line in pq.read_text().splitlines()}
        if pq.exists()
        else {}
    )
    rows: list[dict[str, Any]] = []
    from concurrent.futures import Future, ThreadPoolExecutor

    def write(f, i: int, row: dict[str, Any]) -> None:
        rows.append(row)
        f.write(json.dumps(row, default=str) + "\n")
        f.flush()
        status = (
            ""
            if llm is None
            else f" abst={row.get('abstained')} faith={row.get('faithfulness')} corr={row.get('correctness')}"
        )
        print(
            f"[{i}/{len(questions)}] {row['id']} recall@5={row['recall_at_5']} rr={row['rr']}{status}",
            flush=True,
        )

    pending: list[tuple[int, Future]] = []
    aborted: str | None = None

    def flush_ready(f, wait: bool) -> None:
        nonlocal aborted
        while pending and (wait or pending[0][1].done()):  # write completed rows in question order
            j, fut = pending.pop(0)
            row = fut.result()
            problem = infrastructure_error(row)
            if problem or aborted:
                aborted = aborted or f"{row['id']}: {problem}"
                continue  # never record an outage as a model result; --resume redoes it
            write(f, j, row)

    with pq.open("a") as f, ThreadPoolExecutor(max_workers=1) as judge_pool:
        for i, q in enumerate(questions, start=1):
            if q.id in done:
                rows.append(done[q.id])
                continue
            if aborted:
                break
            row = evaluate_question(q, cfg, retrieval, llm, judge_llm, tracer, tier_of)
            pending.append((i, judge_pool.submit(finish_judging, row, judge_llm)))
            flush_ready(f, wait=False)
        flush_ready(f, wait=True)
    if tracer is not None:
        tracer.flush()
    if aborted:
        print(
            f"\nABORTED - LLM/judge unavailable ({aborted[:300]}).\n"
            f"Completed rows are saved. Continue later with:\n"
            f"  python -m regnav.eval.run_eval --config {args.config} "
            f"--questions {qpath}{' --allow-draft' if is_draft else ''} --resume {out_dir}",
            file=sys.stderr,
        )
        return 2

    metrics = compute_metrics(rows, cfg.seed)
    meta = {
        "config": cfg.name,
        "questions_file": str(qpath),
        "questions_sha256": file_sha256(qpath),
        "is_draft": is_draft,
        "index_version": retrieval.index_version,
        "mode": mode,
        "started": started,
        "run_dir": str(out_dir),
        "generator": f"{cfg.generation.provider}/{cfg.generation.model}",
        "judge": f"{cfg.judge.provider}/{cfg.judge.model}",
    }
    (out_dir / "metrics.json").write_text(json.dumps({"meta": meta, "metrics": metrics}, indent=2))
    with (out_dir / "per_question.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    write_summary(out_dir / "summary.md", cfg, metrics, meta)
    if not args.no_mlflow:
        run_id = log_to_mlflow(cfg, metrics, meta, out_dir, args.config)
        print(f"MLflow run {run_id}")
    print((out_dir / "summary.md").read_text())
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="regnav.eval.run_eval")
    ap.add_argument("--config", default=None)
    ap.add_argument("--questions", default=None)
    ap.add_argument("--allow-draft", action="store_true")
    ap.add_argument("--retrieval-only", action="store_true")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--no-mlflow", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", default=None, help="comma-separated question ids")
    ap.add_argument("--resume", default=None, help="existing output dir to continue")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    return run(args)


__all__ = ["TIER_TO_SECTION", "compute_metrics", "evaluate_question", "main"]

if __name__ == "__main__":
    sys.exit(main())
