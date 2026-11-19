"""Release gate. Passes only if the latest *full* eval of the config:
* was run on the reviewed gold set (not DRAFT) - unless --allow-draft,
* was run against the CURRENT index version (any source-hash, chunking, embedding or ingest-code
  change creates a new index version and therefore requires a fresh full eval), and
* meets every threshold in configs/release_thresholds.yaml.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from regnav.config import load_config
from regnav.eval.compare import load_runs

# threshold key -> (metric name, direction)
CHECKS = {
    "min_faithfulness": ("faithfulness", ">="),
    "min_citation_validity": ("citation_validity", ">="),
    "max_modality_error_rate": ("modality_error_rate", "<="),
    "min_authority_label_accuracy": ("authority_label_accuracy", ">="),
    "min_binding_coverage": ("binding_coverage", ">="),
    "min_abstention_recall": ("abstention_recall", ">="),
    "max_fallback_rate": ("fallback_rate", "<="),
}


def check_release(
    runs: list[dict],
    config_name: str,
    current_index: str,
    thresholds: dict,
    allow_draft: bool = False,
) -> tuple[bool, list[str]]:
    msgs: list[str] = []
    full = [r for r in runs if r["meta"]["config"] == config_name and r["meta"]["mode"] == "full"]
    if not allow_draft:
        full = [r for r in full if not r["meta"]["is_draft"]]
    if not full:
        return False, [
            f"FAIL  no full eval run for {config_name}"
            + ("" if allow_draft else " on the gold set")
        ]
    run = max(full, key=lambda r: r["meta"]["started"])
    meta, metrics = run["meta"], run["metrics"]
    ok = True
    msgs.append(
        f"run: {Path(run['dir']).name} ({'DRAFT' if meta['is_draft'] else 'gold'}, n={metrics['n_questions']})"
    )
    if meta["index_version"] != current_index:
        ok = False
        msgs.append(
            f"FAIL  eval index {meta['index_version']} != current index {current_index}: sources, chunking, "
            "embedding or ingest code changed since the last eval - re-run the full eval"
        )
    else:
        msgs.append(f"PASS  index version matches ({current_index})")
    for key, limit in thresholds.items():
        if key not in CHECKS:
            continue
        name, op = CHECKS[key]
        v = metrics.get(name, {}).get("value")
        passed = v is not None and (v >= limit if op == ">=" else v <= limit)
        ok &= passed
        shown = "missing" if v is None else f"{v:.3f}"
        msgs.append(f"{'PASS' if passed else 'FAIL'}  {name:26s} {shown:>8}  (needs {op} {limit})")
    return ok, msgs


def main(argv: list[str] | None = None) -> int:
    from regnav.ingest.index import load_manifest

    ap = argparse.ArgumentParser(prog="regnav.eval.release_check")
    ap.add_argument("--config", default=None)
    ap.add_argument("--thresholds", default="configs/release_thresholds.yaml")
    ap.add_argument("--allow-draft", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    manifest = load_manifest(cfg)
    if manifest is None:
        print("FAIL  no index - run `make ingest`")
        return 1
    ok, msgs = check_release(
        load_runs(cfg.paths.results_dir),
        cfg.name,
        manifest["index_version"],
        yaml.safe_load(Path(args.thresholds).read_text()),
        args.allow_draft,
    )
    print(f"Release check for {cfg.name}")
    print("\n".join("  " + m for m in msgs))
    print("RELEASE: " + ("APPROVED" if ok else "BLOCKED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
