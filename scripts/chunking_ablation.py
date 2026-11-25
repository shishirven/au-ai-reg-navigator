"""Chunking ablation: one chunk per paragraph (structural) vs fixed-size windows.

Gold labels name paragraph chunks (`apra_cps230_2026:p52`), which don't exist in a fixed-window
index, so retrieval is scored on *text*: a gold paragraph counts as reaching the model when at
least 80% of its 3-word shingles appear in the retrieved chunks from the same document. The same
rule is applied to the structural index, so both are measured identically.

Each fixed-window config is scored twice:
  * same chunk count: the config as is (4 per tier, 12 chunks);
  * same token budget: its ranked list cut at the structural run's context size for that question.

Also reported: context size, and how many source paragraphs a retrieved chunk spans (the citation
problem: a window that spans three paragraphs can't be cited as "para 52").

Retrieval only; no LLM. Usage:
  uv run python scripts/chunking_ablation.py configs/hybrid_stratified_capped.yaml \
      configs/ablation_fixed512.yaml configs/ablation_fixed256.yaml
Writes docs/chunking_ablation.md.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path
from typing import Any

from regnav.config import load_config
from regnav.eval.stats import bootstrap_ci
from regnav.ingest.chunk import count_tokens
from regnav.ingest.index import load_chunk_rows, load_manifest
from regnav.retrieve import build_retrieval

QUESTIONS = Path("data/eval/questions_draft.jsonl")
BROAD = Path("data/eval/broad_questions_draft.jsonl")
OUT = Path("docs/chunking_ablation.md")
COVERED = 0.8  # share of a gold paragraph's shingles that must reach the context
SPAN = 0.25  # a chunk "spans" a paragraph if it holds >= 25% of that paragraph's shingles


def body(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if lines and lines[0].startswith("[") and lines[0].endswith("]"):
        lines = lines[1:]
    return " ".join(lines)


def shingles(text: str, n: int = 3) -> set[tuple[str, ...]]:
    w = re.findall(r"[a-z0-9]+", text.lower())
    if len(w) < n:
        return {tuple(w)} if w else set()
    return {tuple(w[i : i + n]) for i in range(len(w) - n + 1)}


def mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def ci(xs: list[float]) -> str:
    if not xs:
        return "-"
    p, lo, hi = bootstrap_ci(xs, lambda v: sum(v) / len(v))
    return f"{p:.3f} [{lo:.2f}, {hi:.2f}]"


def paired(a: list[float], b: list[float]) -> str:
    d = [y - x for x, y in zip(a, b, strict=True)]
    random.seed(42)
    bs = sorted(sum(random.choices(d, k=len(d))) / len(d) for _ in range(10000))
    return f"{sum(d) / len(d):+.3f} [{bs[250]:+.2f}, {bs[9749]:+.2f}]"


class Gold:
    """Paragraph texts from the structural index, the reference for every config."""

    def __init__(self) -> None:
        rows = load_chunk_rows(load_config())
        self.rows = {r["chunk_id"]: r for r in rows}
        self.sh = {cid: shingles(body(r["text"])) for cid, r in self.rows.items()}
        self.by_doc: dict[str, list[str]] = {}
        for cid, r in self.rows.items():
            self.by_doc.setdefault(r["doc_id"], []).append(cid)

    def covered(self, gold_id: str, chunks: list[Any]) -> bool:
        g = self.sh.get(gold_id)
        if not g:
            return False
        doc = self.rows[gold_id]["doc_id"]
        have: set[tuple[str, ...]] = set()
        for c in chunks:
            if c.metadata.get("doc_id") == doc:
                have |= shingles(body(c.text))
        return len(g & have) / len(g) >= COVERED

    def spans(self, chunk: Any) -> int:
        """How many structural paragraphs/sections this chunk holds a real share of."""
        s = shingles(body(chunk.text))
        doc = chunk.metadata.get("doc_id")
        return sum(
            1
            for cid in self.by_doc.get(doc, [])
            if self.sh[cid] and len(self.sh[cid] & s) / len(self.sh[cid]) >= SPAN
        )


def score(chunks: list[Any], q: dict, gold: Gold) -> dict[str, Any]:
    ids = q["gold_chunk_ids"]
    binding_gold = [g for g in ids if gold.rows.get(g, {}).get("tier") == "binding"]
    cov = [gold.covered(g, chunks) for g in ids]
    return {
        "recall": sum(cov) / len(cov),
        "any": float(any(cov)),
        "binding_gold": (
            float(any(gold.covered(g, chunks) for g in binding_gold)) if binding_gold else None
        ),
        "binding_cov": (
            float(any(c.tier == "binding" for c in chunks))
            if "binding" in (q.get("expected_tiers") or [])
            else None
        ),
        "tokens": sum(count_tokens(c.text) for c in chunks),
        "n": len(chunks),
    }


def cut_to_budget(chunks: list[Any], budget: int) -> list[Any]:
    out, used = [], 0
    for c in chunks:
        t = count_tokens(c.text)
        if out and used + t > budget:
            break
        out.append(c)
        used += t
    return out


def main(argv: list[str]) -> int:
    qs = [json.loads(x) for x in QUESTIONS.read_text().splitlines() if x.strip()]
    qs = [q for q in qs if q.get("gold_chunk_ids")]
    broad = [json.loads(x) for x in BROAD.read_text().splitlines() if x.strip()]
    gold = Gold()
    runs: dict[str, dict[str, Any]] = {}
    base_tokens: dict[str, int] = {}
    base_btokens: dict[str, int] = {}
    for path in argv:
        cfg = load_config(path)
        system = build_retrieval(cfg)
        man = load_manifest(cfg) or {}
        hits = {q["id"]: system.search(q["question"], sector=q.get("sector")) for q in qs}
        bhits = {b["id"]: system.search(b["question"], sector=b.get("sector")) for b in broad}
        fixed = cfg.chunking.strategy == "fixed"
        if not fixed and not base_tokens:
            base_tokens = {i: sum(count_tokens(c.text) for c in h) for i, h in hits.items()}
            base_btokens = {i: sum(count_tokens(c.text) for c in h) for i, h in bhits.items()}
        variants = {"same count": (hits, bhits)}
        if fixed and base_tokens:
            variants["same tokens"] = (
                {i: cut_to_budget(h, base_tokens[i]) for i, h in hits.items()},
                {i: cut_to_budget(h, base_btokens[i]) for i, h in bhits.items()},
            )
        all_chunks = load_chunk_rows(cfg)
        for vname, (vhits, vbhits) in variants.items():
            rows = {q["id"]: score(vhits[q["id"]], q, gold) for q in qs}
            spans = [gold.spans(c) for h in vhits.values() for c in h]
            broad_cov = []
            for b in broad:
                h = vbhits[b["id"]]
                docs = {c.metadata.get("doc_id") for c in h}
                got = [
                    any(
                        (m[4:] in docs) if m.startswith("doc:") else gold.covered(m, h)
                        for m in members
                    )
                    for members in b["groups"].values()
                ]
                broad_cov.append(sum(got) / len(got))
            label = cfg.name + ("" if not fixed else f" ({vname})")
            runs[label] = {
                "cfg": cfg,
                "fixed": fixed,
                "variant": vname,
                "rows": rows,
                "spans": spans,
                "broad": broad_cov,
                "n_chunks": len(all_chunks),
                "index": man.get("index_version", "?"),
            }

    names = list(runs)
    base = names[0]

    def col(name: str, key: str) -> list[float]:
        return [r[key] for r in runs[name]["rows"].values() if r[key] is not None]

    lines = [
        "# Chunking ablation: one chunk per paragraph vs fixed-size windows",
        "",
        f"35 answerable DRAFT questions (`{QUESTIONS}`) and 8 broad DRAFT questions "
        f"(`{BROAD}`); retrieval only, no LLM. Every config uses the default retrieval "
        "(`hybrid_stratified_capped`: hybrid dense + BM25 per legal-force tier, query expansion, "
        "cross-encoder re-ranking, 4 chunks per tier); only the chunking differs. "
        "Generated by `scripts/chunking_ablation.py`.",
        "",
        "A gold paragraph counts as reaching the model when >= 80% of its 3-word shingles are in "
        "the retrieved chunks from its document, the same rule for every index. *Same tokens* cuts "
        "each fixed-window list at the paragraph run's context size for that question.",
        "",
        "| config | chunks in index | gold paragraph text recall | any gold reached | right binding paragraph | binding source reached | broad-question coverage | context tokens / question | paragraphs spanned per retrieved chunk |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for n in names:
        r = runs[n]
        lines.append(
            f"| `{n}` | {r['n_chunks']} | {ci(col(n, 'recall'))} | {ci(col(n, 'any'))} | "
            f"{ci(col(n, 'binding_gold'))} | {ci(col(n, 'binding_cov'))} | "
            f"{mean(r['broad']):.2f} | {mean(col(n, 'tokens')):.0f} | {mean([float(s) for s in r['spans']]):.2f} |"
        )
    lines += [
        "",
        "Paired difference vs the paragraph index (same 35 questions, 10,000 resamples, seed 42):",
        "",
    ]
    lines += ["| config | Δ gold text recall | Δ right binding paragraph |", "|---|---|---|"]
    for n in names[1:]:
        a, b = col(base, "recall"), col(n, "recall")
        ab = [runs[base]["rows"][i]["binding_gold"] for i in runs[base]["rows"]]
        bb = [runs[n]["rows"][i]["binding_gold"] for i in runs[n]["rows"]]
        pa = [x for x, y in zip(ab, bb, strict=True) if x is not None and y is not None]
        pb = [y for x, y in zip(ab, bb, strict=True) if x is not None and y is not None]
        lines.append(f"| `{n}` | {paired(a, b)} | {paired(pa, pb)} |")
    lines += [
        "",
        "Index versions: "
        + ", ".join(
            f"`{n.split(' (')[0]}` {runs[n]['index']}"
            for n in names
            if runs[n]["variant"] == "same count"
        )
        + ".",
        "",
    ]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
