"""Per-chunk tagging: modality (must / should / info) and flat Chroma metadata."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from regnav.config import Modality

if TYPE_CHECKING:
    from regnav.ingest.chunk import Chunk
    from regnav.ingest.load import SourceDoc

# Negated obligations are removed before matching so "is not required to" or
# "need not" do not read as mandatory. ("must not" IS a mandatory prohibition.)
_NEGATED = re.compile(
    r"\b(is|are|be|was|were)\s+not\s+(required|obliged|obligated)\s+to\b"
    r"|\bnot\s+(mandatory|compulsory)\b"
    r"|\bneed\s+not\b|\bdoes\s+not\s+need\s+to\b|\bdo\s+not\s+need\s+to\b",
    re.I,
)
_MUST = re.compile(
    r"\bmust\b|\bshall\b|\bmust\s+not\b"
    r"|\b(is|are)\s+(required|obliged|obligated)\s+to\b"
    r"|\b(is|are)\s+prohibited\b|\bmandatory\b",
    re.I,
)
_SHOULD = re.compile(
    r"\bshould\b|\bought\s+to\b"
    r"|\b(APRA|OAIC|the\s+regulator|the\s+commissioner)\s+(expects|envisages|considers|encourages|recommends)\b"
    r"|\bexpects?\s+(that\s+)?(entities|boards?|organisations|businesses|regulated)\b"
    r"|\b(recommend|recommends|recommended|encourage|encourages|encouraged)\b"
    r"|\b(good|better|sound|best)\s+practice\b"
    r"|\b(a\s+)?prudent\s+(entity|institution)\s+would\b"
    r"|\bwould\s+(typically|normally|ordinarily)\b",
    re.I,
)


def classify_modality(text: str) -> Modality:
    """Strongest normative force in ``text``: must > should > info."""
    cleaned = _NEGATED.sub(" ", text)
    if _MUST.search(cleaned):
        return "must"
    if _SHOULD.search(cleaned):
        return "should"
    return "info"


def chunk_metadata(
    chunk: Chunk, doc: SourceDoc, index_version: str = ""
) -> dict[str, str | int | float | bool]:
    """Flat, scalar-only metadata (Chroma rejects lists/None)."""
    meta: dict[str, str | int | float | bool] = {
        "chunk_id": chunk.chunk_id,
        "doc_id": doc.id,
        "doc_title": doc.title,
        "short_name": doc.label,
        "issuer": doc.issuer,
        "tier": doc.tier,
        "status": doc.status,
        "effective_from": doc.effective_from or "",
        "url": doc.url or "",
        "section": chunk.section or "",
        "para": chunk.para or "",
        "modality": chunk.modality,
        "page": chunk.page,
        "ordinal": chunk.ordinal,
        "n_tokens": chunk.n_tokens,
        "doc_sha256": doc.sha256,
    }
    if index_version:
        meta["index_version"] = index_version
    meta.update(doc.applies_flags())
    return meta
