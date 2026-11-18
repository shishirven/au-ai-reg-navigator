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


SECTION_TITLES = {
    "mandatory": "MANDATORY (binding standards)",
    "regulator_expects": "REGULATOR EXPECTS (guidance - not itself enforceable)",
    "recommended": "RECOMMENDED (voluntary guidance)",
}


def format_answer(result) -> str:
    from regnav.generate.schema import SECTIONS

    by_id = {c.chunk_id: c for c in result.retrieved}
    out = [f"Q: {result.question}  [sector: {result.sector or 'any'}]", ""]
    if result.answer.abstained:
        out.append(f"ABSTAINED: {result.answer.abstain_reason}")
    for section in SECTIONS:
        claims = getattr(result.answer, section)
        if not claims:
            continue
        out.append(SECTION_TITLES[section])
        for c in claims:
            src = by_id.get(c.citation_id)
            label = src.metadata.get("short_name", "") if src else "?"
            para = f" para {src.metadata['para']}" if src and src.metadata.get("para") else ""
            out.append(f"  - {c.claim}  [{label}{para} | {c.citation_id}]")
        out.append("")
    out.append(f"Note: {result.disclaimer}")
    out.append(
        f"config={result.config_name} index={result.index_version} prompt={result.prompt_version} "
        f"valid={result.valid} attempts={len(result.attempts)} fallback={result.fallback} "
        f"latency={result.total_latency_s:.1f}s tokens={result.input_tokens}/{result.output_tokens} "
        f"cost=${result.cost_usd:.4f}"
    )
    if result.error:
        out.append(f"error: {result.error}")
    if result.trace_url:
        out.append(f"trace: {result.trace_url}")
    return "\n".join(out)


def cmd_ask(args: argparse.Namespace) -> int:
    from regnav.config import Secrets
    from regnav.generate.answer import answer_question
    from regnav.generate.llm import make_llm
    from regnav.observability.langfuse import get_tracer
    from regnav.retrieve import build_retrieval

    cfg = load_config(args.config)
    if args.model:
        cfg.generation.model = args.model
    secrets = Secrets()
    retrieval = build_retrieval(cfg)
    llm = make_llm(cfg.generation, cfg.seed, secrets.anthropic_api_key)
    tracer = get_tracer(secrets)
    for question in args.question:
        result = answer_question(question, cfg, retrieval, llm, sector=args.sector, tracer=tracer)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            print(format_answer(result))
            if args.show_sources:
                print("\nRetrieved:")
                for c in result.retrieved:
                    print(
                        f"  {c.rank}. {c.chunk_id:38s} {c.tier:11s} {c.modality:6s} {c.score:.4f}"
                    )
        print("-" * 80)
    tracer.flush()
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

    p = sub.add_parser("ask", help="answer one or more questions")
    p.add_argument("question", nargs="+")
    p.add_argument("--config", default=None)
    p.add_argument("--sector", default=None, choices=["bank", "insurer", "super", "any_business"])
    p.add_argument("--json", action="store_true")
    p.add_argument("--show-sources", action="store_true")
    p.add_argument("--model", default=None, help="override generation.model (e.g. qwen3:4b)")
    p.set_defaults(func=cmd_ask)

    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
