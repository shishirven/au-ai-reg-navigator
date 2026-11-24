"""Merge a full eval run with a re-run of a few questions into one run (D-056).

Used when a change only affects some questions (the commencement check only acts when a
not-yet-commenced obligation is in the context): re-run just those ids with `run_eval --ids`,
then merge. Questions outside the re-run keep their original rows, which is valid only because
the pipeline for them is unchanged; the merged run records both sources in its metadata.

Usage:
  uv run python scripts/merge_rerun.py BASE_RUN_DIR RERUN_DIR --config-name NAME
Writes results/NAME__<timestamp>__DRAFT/ (metrics.json, per_question.jsonl, summary.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from regnav.eval.run_eval import compute_metrics


def load(d: Path) -> tuple[dict, list[dict]]:
    meta = json.loads((d / "metrics.json").read_text())["meta"]
    rows = [
        json.loads(line) for line in (d / "per_question.jsonl").read_text().splitlines() if line
    ]
    return meta, rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("rerun")
    ap.add_argument("--config-name", required=True)
    args = ap.parse_args(argv)
    base_meta, base_rows = load(Path(args.base))
    rerun_meta, rerun_rows = load(Path(args.rerun))
    bad = [r["id"] for r in rerun_rows if r.get("error") or r.get("judge_unavailable")]
    if bad:
        print(f"re-run has infrastructure errors on {bad}; not merging", file=sys.stderr)
        return 2
    new = {r["id"]: r for r in rerun_rows}
    rows = [new.get(r["id"], r) for r in base_rows]
    missing = set(new) - {r["id"] for r in base_rows}
    if missing:
        print(f"re-run ids not in base: {sorted(missing)}", file=sys.stderr)
        return 2
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out = Path("results") / f"{args.config_name}__{stamp}__DRAFT"
    out.mkdir(parents=True)
    meta = {
        **base_meta,
        "config": args.config_name,
        "started": rerun_meta.get("started", stamp),
        "merged_from": {"base": Path(args.base).name, "rerun": Path(args.rerun).name},
        "rerun_ids": sorted(new),
        "note": "Merged run: re-run ids replace the base rows; other questions' pipeline unchanged.",
    }
    metrics = compute_metrics(rows)
    (out / "metrics.json").write_text(json.dumps({"meta": meta, "metrics": metrics}, indent=2))
    (out / "per_question.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "summary.md").write_text(
        f"# Merged eval: {args.config_name} (DRAFT)\n\n- base: `{meta['merged_from']['base']}`\n"
        f"- re-run ids ({len(new)}): {', '.join(sorted(new))} from `{meta['merged_from']['rerun']}`\n"
        f"- correctness: {metrics.get('answer_correctness', {}).get('value')}\n"
    )
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
