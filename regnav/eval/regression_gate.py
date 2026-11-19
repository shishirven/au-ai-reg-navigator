"""Retrieval regression gate (CI, no API key, no LLM).

Builds the synthetic fixture corpus into a temp dir, indexes it with the configured embedding
model (BGE by default), runs retrieval for ``tests/fixtures/questions.jsonl`` and fails if
recall@5, MRR or binding-source coverage fall below ``configs/ci_thresholds.yaml``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from regnav.config import EmbeddingConfig, load_config
from regnav.eval.dataset import load_questions
from regnav.eval.retrieval_metrics import binding_coverage, recall_at_k, reciprocal_rank
from regnav.eval.stats import mean_or_none
from regnav.fixtures import build_fixture_pdfs

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


def run_gate(
    config: str, thresholds_path: Path, embedding_backend: str | None = None
) -> tuple[bool, dict[str, float | None]]:
    from regnav.ingest.index import ingest, load_chunk_rows
    from regnav.retrieve import build_retrieval

    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        build_fixture_pdfs(FIXTURES / "corpus", tmp / "raw")
        shutil.copy(FIXTURES / "sources.yaml", tmp / "sources.yaml")
        cfg = load_config(config)
        cfg.paths.raw_dir, cfg.paths.sources_file, cfg.paths.chroma_dir = (
            tmp / "raw",
            tmp / "sources.yaml",
            tmp / "chroma",
        )
        if embedding_backend == "hashing":
            cfg.embedding = EmbeddingConfig(backend="hashing", dim=256)
        ingest(cfg)
        tier_of = {r["chunk_id"]: r["tier"] for r in load_chunk_rows(cfg)}
        retrieval = build_retrieval(cfg)
        recall, rr, cov = [], [], []
        for q in load_questions(FIXTURES / "questions.jsonl"):
            chunks = retrieval.search(q.question, sector=q.sector)
            ids, tiers = [c.chunk_id for c in chunks], [c.tier for c in chunks]
            recall.append(recall_at_k(ids, q.gold_chunk_ids, 5))
            rr.append(reciprocal_rank(ids, q.gold_chunk_ids))
            cov.append(binding_coverage(tiers, [tier_of.get(g, "") for g in q.gold_chunk_ids]))
    metrics = {
        "recall_at_5": mean_or_none(recall),
        "mrr": mean_or_none(rr),
        "binding_coverage": mean_or_none(cov),
    }
    th = yaml.safe_load(thresholds_path.read_text())
    checks = {
        "recall_at_5": th["min_recall_at_5"],
        "mrr": th["min_mrr"],
        "binding_coverage": th["min_binding_coverage"],
    }
    ok = True
    print(
        f"Retrieval regression gate ({cfg.name}, {cfg.embedding.backend}:{cfg.embedding.model_name})"
    )
    for k, minimum in checks.items():
        v = metrics[k]
        passed = v is not None and v >= minimum
        ok &= passed
        print(
            f"  {'PASS' if passed else 'FAIL'}  {k:18s} {v if v is None else round(v, 3)!s:>6}  (min {minimum})"
        )
    return ok, metrics


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="regnav.eval.regression_gate")
    ap.add_argument("--config", default=str(ROOT / "configs" / "hybrid_stratified.yaml"))
    ap.add_argument("--thresholds", default=str(ROOT / "configs" / "ci_thresholds.yaml"))
    ap.add_argument("--embedding", choices=["config", "hashing"], default="config")
    args = ap.parse_args(argv)
    ok, _ = run_gate(
        args.config, Path(args.thresholds), None if args.embedding == "config" else "hashing"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
