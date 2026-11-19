"""Score the statement-authority tagger against human labels (D-044).

    uv run python -m regnav.legal.evaluate [--csv data/eval/clause_labels.csv]

Reports accuracy, per-label precision/recall, Cohen's kappa (8 labels), and kappa for the question
a user actually asks: "is this binding on someone?" (binding_requirement | restates_law vs the rest).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from regnav.eval.stats import cohens_kappa
from regnav.legal.tagger import LABELS

BINDING = {"binding_requirement", "restates_law"}


def score(pairs: list[tuple[str, str]]) -> dict:
    """pairs: (human, predicted)."""
    n = len(pairs)
    out: dict = {"n": n, "accuracy": sum(h == p for h, p in pairs) / n if n else None}
    if n >= 2:
        out["kappa"] = cohens_kappa([h for h, _ in pairs], [p for _, p in pairs])
        out["kappa_binding_vs_not"] = cohens_kappa(
            [h in BINDING for h, _ in pairs], [p in BINDING for _, p in pairs]
        )
    per = {}
    for label in LABELS:
        tp = sum(1 for h, p in pairs if h == label and p == label)
        pp = sum(1 for _, p in pairs if p == label)
        hp = sum(1 for h, _ in pairs if h == label)
        if pp or hp:
            per[label] = {
                "precision": tp / pp if pp else None,
                "recall": tp / hp if hp else None,
                "support": hp,
            }
    out["per_label"] = per
    out["confusion"] = Counter(f"{h} -> {p}" for h, p in pairs if h != p).most_common(10)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/eval/clause_labels.csv")
    ap.add_argument("--predictions", default="data/eval/clause_tagger_predictions.jsonl")
    args = ap.parse_args(argv)
    preds = {
        json.loads(line)["statement_id"]: json.loads(line)["label"]
        for line in Path(args.predictions).read_text().splitlines()
        if line.strip()
    }
    with Path(args.csv).open() as f:
        rows = [r for r in csv.DictReader(f) if r.get("human_label", "").strip()]
    bad = sorted({r["human_label"].strip() for r in rows} - set(LABELS))
    if bad:
        print(f"unknown labels in CSV: {bad}; use one of {LABELS}", file=sys.stderr)
        return 1
    if not rows:
        print("no human labels yet - fill the human_label column first", file=sys.stderr)
        return 1
    result = score(
        [
            (r["human_label"].strip(), preds[r["statement_id"]])
            for r in rows
            if r["statement_id"] in preds
        ]
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
