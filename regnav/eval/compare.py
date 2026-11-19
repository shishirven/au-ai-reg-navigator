"""Compare the latest eval run of each config and write ``docs/results.md``.

Prefers runs on the reviewed gold set; falls back to DRAFT runs (clearly labelled) when no gold
run exists. Retrieval metrics may come from a retrieval-only run if no full run exists.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CONFIGS = ["baseline_dense", "hybrid_pooled", "hybrid_stratified"]
ROWS = [
    ("Retrieval", None),
    ("recall_at_5", "Recall@5"),
    ("mrr", "MRR"),
    ("binding_coverage", "**Binding-source coverage**"),
    ("binding_gold_hit", "Binding gold chunk retrieved"),
    ("Generation (LLM judge)", None),
    ("faithfulness", "Faithfulness"),
    ("answer_correctness", "Answer correctness"),
    ("Generation (rule-based, final answer)", None),
    ("citation_validity", "Citation validity"),
    ("authority_label_accuracy", "Authority-label accuracy"),
    ("modality_error_rate", "Modality error rate (lower is better)"),
    ("tier_recall", "Expected-tier recall"),
    ("Model reliability (first raw attempt, before validation/repair)", None),
    ("raw_citation_validity", "Raw citation validity"),
    ("raw_authority_label_accuracy", "Raw authority-label accuracy"),
    ("raw_modality_error_rate", "Raw modality error rate"),
    ("Abstention & safety net", None),
    ("abstention_precision", "Abstention precision"),
    ("abstention_recall", "Abstention recall"),
    ("gate_abstain_rate", "Scope-gate abstentions"),
    ("repair_rate", "Claim-repair rate"),
    ("fallback_rate", "Safe-fallback rate"),
    ("System", None),
    ("latency_p50_s", "Latency p50 (s)"),
    ("latency_p95_s", "Latency p95 (s)"),
    ("mean_input_tokens", "Input tokens / query"),
    ("mean_output_tokens", "Output tokens / query"),
    ("mean_cost_usd", "Cost / query (USD)"),
]


def load_runs(results_dir: Path) -> list[dict[str, Any]]:
    runs = []
    for p in sorted(results_dir.glob("*/metrics.json")):
        data = json.loads(p.read_text())
        data["dir"] = str(p.parent)
        runs.append(data)
    return runs


def pick(runs: list[dict[str, Any]], config: str) -> tuple[dict | None, dict | None]:
    """(best full run, best retrieval run) for a config: gold before draft, then most recent."""
    mine = [r for r in runs if r["meta"]["config"] == config]

    def key(r: dict) -> tuple:
        return (not r["meta"]["is_draft"], r["meta"]["started"])

    full = sorted((r for r in mine if r["meta"]["mode"] != "retrieval-only"), key=key)
    retr = sorted(mine, key=key)
    return (full[-1] if full else None), (retr[-1] if retr else None)


def fmt(m: dict | None, key: str) -> str:
    if not m or m.get("value") is None:
        return "-"
    v = m["value"]
    digits = (
        1
        if key.startswith(("latency", "mean_input", "mean_output"))
        else 3
        if key != "mean_cost_usd"
        else 4
    )
    s = f"{v:.{digits}f}"
    if m.get("ci_low") is not None:
        s += f" [{m['ci_low']:.2f}, {m['ci_high']:.2f}]"
    return s


def render(runs: list[dict[str, Any]], configs: list[str]) -> str:
    chosen = {c: pick(runs, c) for c in configs}
    any_draft = any(r and r["meta"]["is_draft"] for pair in chosen.values() for r in pair)
    lines = ["# Results", ""]
    if any_draft:
        lines += [
            "> **PROVISIONAL - scored on DRAFT questions** (`data/eval/questions_draft.jsonl`) that have not yet "
            "been reviewed by a domain expert. Re-run `make eval-all && make compare` after the gold set "
            "(`data/eval/questions.jsonl`) is written.",
            "",
        ]
    header = "| Metric | " + " | ".join(f"`{c}`" for c in configs) + " |"
    lines += [header, "|---|" + "---|" * len(configs)]
    for key, label in ROWS:
        if label is None:
            lines.append(f"| ***{key}*** |" + " |" * len(configs))
            continue
        cells = []
        for c in configs:
            full, retr = chosen[c]
            src = full if full and key in full["metrics"] else retr
            cells.append(fmt(src["metrics"].get(key) if src else None, key))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines += ["", "Values: mean [95% percentile-bootstrap CI over questions].", ""]
    lines += [
        "### Runs",
        "",
        "| config | run | questions | n | index | generator / judge |",
        "|---|---|---|---|---|---|",
    ]
    for c in configs:
        for r in {id(x): x for x in chosen[c] if x}.values():
            m = r["meta"]
            lines.append(
                f"| `{c}` | `{Path(r['dir']).name}` ({m['mode']}) | `{m['questions_file']}` | "
                f"{r['metrics']['n_questions']} | `{m['index_version']}` | {m.get('generator', '')} |"
            )
    lines += [
        "",
        "### How to read this",
        "",
        "- **n is small (30-40 questions).** Differences smaller than the CI widths are noise; treat only "
        "non-overlapping intervals as evidence.",
        "- **Binding-source coverage** = share of questions whose gold answer includes a binding standard "
        "where at least one binding chunk reached the generator. This is the metric the tier-stratified "
        "design is meant to move.",
        "- Final-answer citation validity / authority labels are enforced by the validator (invalid answers "
        "are repaired or replaced by a safe abstention), so the *raw* rows are the honest measure of model "
        "reliability; the repair and fallback rates show how often the safety net was needed.",
        "- Rule-based metrics are deterministic; judge metrics depend on the judge model (see judge calibration "
        "in VALIDATION_REPORT.md).",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="regnav.eval.compare")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--out", default="docs/results.md")
    ap.add_argument("--configs", default=",".join(CONFIGS))
    args = ap.parse_args(argv)
    runs = load_runs(Path(args.results_dir))
    if not runs:
        print("no eval runs found - run `make eval-all` first", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(runs, args.configs.split(",")))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
