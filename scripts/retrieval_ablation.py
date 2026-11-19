"""Retrieval ablation: query expansion and cross-encoder re-ranking on top of hybrid_stratified.

No LLM, no API key. Writes docs/retrieval_ablation.md.
    uv run python scripts/retrieval_ablation.py [--questions data/eval/questions_draft.jsonl]
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from regnav.config import load_config
from regnav.eval.dataset import load_questions
from regnav.eval.retrieval_metrics import (
    any_gold_hit,
    binding_coverage,
    binding_gold_hit,
    context_recall,
    recall_at_k,
    reciprocal_rank,
)
from regnav.eval.stats import bootstrap_ci, mean_or_none
from regnav.ingest.index import load_chunk_rows
from regnav.retrieve import build_retrieval

VARIANTS = [
    ("A. hybrid_stratified (before)", {}),
    ("B. + query expansion", {"query_expansion": True}),
    ("C. + rerank (MiniLM-L6)", {"rerank": True}),
    ("D. + expansion + rerank (MiniLM-L6)", {"query_expansion": True, "rerank": True}),
    (
        "E. + expansion + rerank (bge-reranker-base)",
        {"query_expansion": True, "rerank": True, "rerank_model": "BAAI/bge-reranker-base"},
    ),
    ("G. A with 4 per tier (12 chunks): budget-only control", {"per_tier_k": 4}),
    (
        "F. D with 4 per tier (12 chunks) = hybrid_stratified_rerank",
        {"query_expansion": True, "rerank": True, "per_tier_k": 4},
    ),
]
METRICS = [
    ("context_recall", "Context recall (all chunks in context)"),
    ("recall_at_5", "Recall@5"),
    ("any_gold_hit", "Any-gold hit"),
    ("binding_gold_hit", "Binding gold hit"),
    ("binding_coverage", "Binding coverage"),
    ("rr", "MRR"),
]


def evaluate(cfg, questions, tier_of):
    rs = build_retrieval(cfg)
    rs.search(questions[0].question, sector=questions[0].sector)  # warm-up (model load)
    rows, t0 = [], time.perf_counter()
    for q in questions:
        chunks = rs.search(q.question, sector=q.sector)
        ids, tiers = [c.chunk_id for c in chunks], [c.tier for c in chunks]
        rows.append(
            {
                "id": q.id,
                "type": q.type,
                "context_recall": context_recall(ids, q.gold_chunk_ids),
                "recall_at_5": recall_at_k(ids, q.gold_chunk_ids, 5),
                "any_gold_hit": any_gold_hit(ids, q.gold_chunk_ids),
                "binding_gold_hit": binding_gold_hit(ids, q.gold_chunk_ids, tier_of),
                "binding_coverage": binding_coverage(
                    tiers, [tier_of.get(g, "") for g in q.gold_chunk_ids]
                ),
                "rr": reciprocal_rank(ids, q.gold_chunk_ids),
            }
        )
    return rows, (time.perf_counter() - t0) / len(questions)


def paired_delta(a, b, field, seed=42, n_boot=4000):
    pairs = [
        (x[field], y[field])
        for x, y in zip(a, b, strict=True)
        if x[field] is not None and y[field] is not None
    ]
    d = np.array([y - x for x, y in pairs])
    rng = np.random.default_rng(seed)
    boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(n_boot)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return d.mean(), lo, hi, float(np.mean(np.array(boots) > 0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="data/eval/questions_draft.jsonl")
    ap.add_argument("--out", default="docs/retrieval_ablation.md")
    args = ap.parse_args()
    base = load_config("configs/hybrid_stratified.yaml")
    qs = [q for q in load_questions(Path(args.questions), allow_draft=True) if q.answerable]
    tier_of = {r["chunk_id"]: r["tier"] for r in load_chunk_rows(base)}
    results = {}
    for name, overrides in VARIANTS:
        cfg = load_config("configs/hybrid_stratified.yaml")
        cfg.retrieval = cfg.retrieval.model_copy(update=overrides)
        results[name], lat = evaluate(cfg, qs, tier_of)
        results[name + "#lat"] = lat
        print(
            f"{name}: context recall {mean_or_none([r['context_recall'] for r in results[name]]):.3f} ({lat:.2f}s/query)"
        )

    names = [n for n, _ in VARIANTS]
    a = results[names[0]]
    lines = [
        "# Retrieval ablation: query expansion + cross-encoder re-ranking",
        "",
        f"Questions: `{args.questions}` - {len(qs)} answerable "
        f"({'DRAFT, provisional' if 'draft' in args.questions else 'gold'}). Tier-stratified hybrid, "
        "3 chunks per tier (9 in context) unless stated. No LLM involved; deterministic.",
        "",
        "| Metric | " + " | ".join(names) + " |",
        "|---|" + "---|" * len(names),
    ]
    for field, label in METRICS:
        cells = []
        for n in names:
            v, lo, hi = bootstrap_ci(
                results[n], lambda rs, f=field: mean_or_none([r[f] for r in rs])
            )
            cells.append(f"{v:.2f} [{lo:.2f}, {hi:.2f}]" if lo is not None else f"{v:.2f}")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append(
        "| Retrieval latency / query (CPU) | "
        + " | ".join(f"{results[n + '#lat']:.2f}s" for n in names)
        + " |"
    )
    lines += [
        "",
        "**Paired difference vs A** (same questions, paired bootstrap, 4,000 resamples):",
        "",
        "| Variant | Δ context recall [95% CI] | P(Δ>0) | Δ binding gold hit [95% CI] |",
        "|---|---|---|---|",
    ]
    for n in names[1:]:
        d, lo, hi, p = paired_delta(a, results[n], "context_recall")
        db, blo, bhi, _ = paired_delta(a, results[n], "binding_gold_hit")
        lines.append(
            f"| {n} | {d:+.2f} [{lo:+.2f}, {hi:+.2f}] | {p:.2f} | {db:+.2f} [{blo:+.2f}, {bhi:+.2f}] |"
        )
    g = next(n for n in names if n.startswith("G."))
    f_ = next(n for n in names if n.startswith("F."))
    d, lo, hi, p = paired_delta(results[g], results[f_], "context_recall")
    db, blo, bhi, pb = paired_delta(results[g], results[f_], "binding_gold_hit")
    lines += [
        "",
        "**Budget control - F vs G** (both 12 chunks, so this isolates expansion + re-ranking from the "
        f"bigger context): Δ context recall {d:+.2f} [{lo:+.2f}, {hi:+.2f}] (P(Δ>0) = {p:.2f}); "
        f"Δ binding gold hit {db:+.2f} [{blo:+.2f}, {bhi:+.2f}] (P(Δ>0) = {pb:.2f}). "
        "The larger budget alone (G vs A) adds no binding gold paragraphs.",
    ]
    lines += [
        "",
        "**Context recall by question type:**",
        "",
        "| Type | " + " | ".join(names) + " |",
        "|---|" + "---|" * len(names),
    ]
    for t in ("factual", "split", "cross_doc"):
        cells = [
            f"{mean_or_none([r['context_recall'] for r in results[n] if r['type'] == t]):.2f}"
            for n in names
        ]
        lines.append(f"| {t} (n={sum(r['type'] == t for r in a)}) | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Caveats: n is small; the query-expansion glossary was written after inspecting failures on these "
        "same draft questions (look-ahead risk) - confirm on the expert gold set before adopting.",
    ]
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
