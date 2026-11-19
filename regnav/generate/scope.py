"""Scope gate: cheap, deterministic checks that a question is answerable from this corpus
before spending an LLM call. Abstaining here is logged as `gate_reason`.

Two signals (D-030):
  1. the best dense similarity is below a floor (off-topic question);
  2. the question names a jurisdiction or a numbered instrument that is not in the corpus
     (e.g. "EU AI Act", "GDPR", "APS 115", "RG 255").
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from regnav.retrieve.base import RetrievedChunk

_FOREIGN = re.compile(
    r"\b(EU|European Union|GDPR|UK|United Kingdom|US|USA|United States|Singapore|New Zealand|NZ|Canada|"
    r"China|Hong Kong|India|Japan|NIST|ISO/IEC|EU AI Act)\b"
)
_INSTRUMENT = re.compile(r"\b(?:[A-Z]{2,3}\s?\d{3}|RG\s?\d{1,3}|INFO\s?\d{1,3})\b")


def corpus_instruments(short_names: Iterable[str]) -> set[str]:
    out = set()
    for name in short_names:
        for m in _INSTRUMENT.finditer(name):
            out.add(m.group(0).replace(" ", ""))
    return out


def check_scope(
    question: str,
    chunks: list[RetrievedChunk],
    known_instruments: set[str],
    min_dense_similarity: float,
) -> str | None:
    """Return a reason to abstain, or None if the question looks in scope."""
    dense = [c.scores["dense"] for c in chunks if "dense" in c.scores]
    if dense and max(dense) < min_dense_similarity:
        return f"No sufficiently relevant source (best similarity {max(dense):.2f} < {min_dense_similarity})."
    m = _FOREIGN.search(question)
    if m:
        return f"The question refers to '{m.group(0)}', which is outside this Australian corpus."
    for inst in _INSTRUMENT.finditer(question):
        code = inst.group(0).replace(" ", "")
        if code not in known_instruments:
            return f"The question refers to '{inst.group(0)}', which is not in the document corpus."
    return None
