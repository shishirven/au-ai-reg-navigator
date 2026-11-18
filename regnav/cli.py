"""Command-line entry point: ``python -m regnav.cli <command>``."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from regnav.config import load_config
from regnav.logging_utils import setup_logging


def cmd_ingest(args: argparse.Namespace) -> int:
    from regnav.ingest.index import ingest, load_chunk_rows

    cfg = load_config(args.config)
    report = ingest(cfg, force=args.force)
    rows = load_chunk_rows(cfg)
    tiers = {r["doc_id"]: r["tier"] for r in rows}
    status = {r["doc_id"]: r["status"] for r in rows}
    mods: dict[str, Counter] = {}
    for r in rows:
        mods.setdefault(r["doc_id"], Counter())[r["modality"]] += 1
    print(f"\nindex_version: {report.index_version}  (previous: {report.previous_version})")
    print(
        f"{'doc_id':26s} {'tier':12s} {'status':11s} {'action':10s} {'chunks':>6s}  must/should/info"
    )
    for doc_id, action in sorted(report.actions.items()):
        m = mods.get(doc_id, Counter())
        print(
            f"{doc_id:26s} {tiers.get(doc_id, '-'):12s} {status.get(doc_id, '-'):11s} {action:10s} "
            f"{report.chunk_counts.get(doc_id, 0):6d}  {m['must']}/{m['should']}/{m['info']}"
        )
    print(f"{'TOTAL':62s}{sum(report.chunk_counts.values()):6d}")
    return 0


def cmd_chunks(args: argparse.Namespace) -> int:
    """List chunk ids (for writing gold labels)."""
    from regnav.ingest.index import load_chunk_rows

    cfg = load_config(args.config)
    for r in load_chunk_rows(cfg):
        if args.doc and r["doc_id"] != args.doc:
            continue
        if args.full:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            body = r["text"].split("\n", 1)[-1].replace("\n", " ")
            print(f"{r['chunk_id']:34s} {r['modality']:6s} {body[:110]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="regnav")
    parser.add_argument("--log-level", default="WARNING")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest", help="parse, chunk, tag, embed and index data/raw")
    p.add_argument("--config", default=None)
    p.add_argument("--force", action="store_true", help="rebuild even if unchanged")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("chunks", help="list indexed chunks")
    p.add_argument("--config", default=None)
    p.add_argument("--doc", default=None)
    p.add_argument("--full", action="store_true")
    p.set_defaults(func=cmd_chunks)

    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
