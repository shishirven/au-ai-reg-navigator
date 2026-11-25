"""Chunking.

``structural`` (default): one chunk per numbered paragraph (``^\\d{1,3}\\.\\s``) for
numbered documents, or per heading section for unnumbered ones. Over-long units are split
at their (a)/(b)/(c) sub-items, repeating the lead-in sentence in every piece; tiny units
are merged into a neighbour in the same section. ``fixed``: sliding windows of N tokens
with overlap (ablation baseline).

Every chunk's text is prefixed with ``[Doc · Tier · Section · para N]`` so that the
embedding, BM25 and the LLM all see where the text comes from.

Chunk ids are deterministic and human-readable (used in gold labels):
``<doc_id>:p36`` (paragraph 36), ``p36.2`` (2nd piece of a split paragraph),
``p5-6`` (merged), ``p3~2`` (2nd paragraph numbered 3, e.g. in an attachment),
``s007`` (7th heading section), ``w0012`` (fixed-size window).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from regnav.config import ChunkingConfig
from regnav.ingest.load import SourceDoc
from regnav.ingest.parse import BULLETS, PARA_RE, Line
from regnav.ingest.tag import classify_modality

TIER_SHORT = {
    "binding": "Binding",
    "expectation": "Regulator expectation",
    "voluntary": "Voluntary",
}
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")
_SUBITEM_RE = re.compile(rf"^(\([a-z]{{1,4}}\)|\([ivx]{{1,5}}\)|[a-z]\)|[{BULLETS}])\s")


def count_tokens(text: str) -> int:
    """Cheap tokenizer-free estimate (~ subword count for English prose)."""
    return len(_TOKEN_RE.findall(text))


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    body: str
    section: str
    para: str | None
    page: int
    ordinal: int
    prefix: str = ""
    modality: str = "info"
    n_tokens: int = 0

    @property
    def text(self) -> str:
        return f"{self.prefix}\n{self.body}" if self.prefix else self.body


@dataclass
class _Unit:
    section: str
    para: str | None
    page: int
    lines: list[str] = field(default_factory=list)
    part: int | None = None
    merged_paras: list[str] = field(default_factory=list)
    fn: str | None = None  # footnote number: its own chunk, id ``fn<n>`` (D-059)

    @property
    def body(self) -> str:
        return "\n".join(self.lines)

    @property
    def n_tokens(self) -> int:
        return count_tokens(self.body)


def make_prefix(doc: SourceDoc, section: str, para: str | None) -> str:
    parts = [doc.label, TIER_SHORT[doc.tier]]
    if section:
        parts.append(section)
    if para:
        parts.append(f"para {para}")
    return "[" + " · ".join(parts) + "]"


def detect_structure(lines: list[Line]) -> str:
    n = sum(1 for ln in lines if ln.kind == "text" and PARA_RE.match(ln.text))
    return "numbered" if n >= 15 else "headings"


# ------------------------------------------------------------------ unit building


def _build_units(lines: list[Line], numbered: bool) -> list[_Unit]:
    units: list[_Unit] = []
    section = ""
    heading_has_content = True
    cur: _Unit | None = None
    for ln in lines:
        if ln.footnote:
            units.append(
                _Unit(
                    section=f"Footnote {ln.footnote}",
                    para=None,
                    page=ln.page,
                    lines=[ln.text],
                    fn=ln.footnote,
                )
            )
            cur = None
            continue
        if ln.kind == "heading":
            # Consecutive headings collapse into a "Parent › Child" path.
            section = f"{section} › {ln.text}" if not heading_has_content and section else ln.text
            heading_has_content = False
            cur = None
            continue
        m = PARA_RE.match(ln.text) if numbered else None
        if m or cur is None:
            cur = _Unit(section=section, para=m.group(1) if m else None, page=ln.page)
            units.append(cur)
        cur.lines.append(ln.text)
        heading_has_content = True
    return units


def _split_long(unit: _Unit, max_tokens: int) -> list[_Unit]:
    if unit.n_tokens <= max_tokens or (
        len(unit.lines) == 1 and count_tokens(unit.lines[0]) <= max_tokens
    ):
        return [unit]
    lines = unit.lines
    has_subitems = len(lines) > 1 and any(_SUBITEM_RE.match(x) for x in lines[1:])
    # Repeat the lead-in ("An entity must:") in every piece - only if it is a short
    # introduction to the list, never a long paragraph.
    lead = lines[0] if has_subitems and count_tokens(lines[0]) <= max_tokens // 3 else ""
    items = lines[1:] if has_subitems else lines
    # Break any single over-long item into sentence groups.
    pieces: list[str] = []
    budget = max_tokens - count_tokens(lead)
    for item in items:
        if count_tokens(item) <= budget:
            pieces.append(item)
            continue
        sentences = re.split(r"(?<=[.;:])\s+(?=[A-Z(•])", item)
        buf = ""
        for s in sentences:
            if buf and count_tokens(buf + " " + s) > budget:
                pieces.append(buf)
                buf = s
            else:
                buf = f"{buf} {s}".strip()
        if buf:
            pieces.append(buf)
    groups: list[list[str]] = [[]]
    for p in pieces:
        if groups[-1] and count_tokens("\n".join([lead, *groups[-1], p])) > max_tokens:
            groups.append([])
        groups[-1].append(p)
    out = []
    for i, g in enumerate(groups, start=1):
        body = [lead, *g] if lead else g
        out.append(
            _Unit(unit.section, unit.para, unit.page, body, part=i if len(groups) > 1 else None)
        )
    return out


def _merge_small(units: list[_Unit], min_tokens: int, max_tokens: int) -> list[_Unit]:
    out: list[_Unit] = []
    pending: _Unit | None = None
    for u in units:
        if u.fn is not None or (pending is not None and pending.fn is not None):
            if pending is not None:
                out.append(pending)
                pending = None
            out.append(u)
            continue
        if pending is not None:
            if (
                pending.section == u.section
                and pending.n_tokens + u.n_tokens <= max_tokens
                and u.part is None
            ):
                merged = _Unit(u.section, pending.para, pending.page, pending.lines + u.lines)
                merged.merged_paras = (pending.merged_paras or [pending.para or ""]) + [
                    u.para or ""
                ]
                u = merged
            else:
                out.append(pending)
            pending = None
        if u.n_tokens < min_tokens and u.part is None:
            pending = u
            continue
        out.append(u)
    if pending is not None:
        prev = out[-1] if out else None
        if (
            prev
            and prev.section == pending.section
            and prev.part is None
            and prev.n_tokens + pending.n_tokens <= max_tokens
        ):
            prev.lines += pending.lines
            prev.merged_paras = (prev.merged_paras or [prev.para or ""]) + [pending.para or ""]
        else:
            out.append(pending)
    return out


def _unit_ids(doc_id: str, units: list[_Unit]) -> list[tuple[str, str | None]]:
    """Deterministic ids + display para label for each unit."""
    seen: dict[str, int] = {}
    ids: list[tuple[str, str | None]] = []
    section_ord = 0
    last_key = None
    for u in units:
        if u.fn is not None:
            ids.append((f"{doc_id}:fn{u.fn}", None))
            continue
        paras = [p for p in u.merged_paras if p] if u.merged_paras else ([u.para] if u.para else [])
        if paras:
            label = paras[0] if len(paras) == 1 else f"{paras[0]}-{paras[-1]}"
            base = f"p{label}"
        else:
            key = (u.section, id(u) if u.part is None else u.section + str(u.page))
            if u.part is None or u.part == 1 or key != last_key:
                section_ord += 1
            last_key = key
            label = None
            base = f"s{section_ord:03d}"
        dup_key = base if u.part in (None, 1) else None
        if dup_key is not None:
            seen[dup_key] = seen.get(dup_key, 0) + 1
        n = seen.get(base, 1)
        cid = base if n == 1 else f"{base}~{n}"
        if u.part is not None:
            cid = f"{cid}.{u.part}"
        ids.append((f"{doc_id}:{cid}", label))
    return ids


def chunk_structural(lines: list[Line], doc: SourceDoc, cfg: ChunkingConfig) -> list[Chunk]:
    structure = doc.structure if doc.structure != "auto" else detect_structure(lines)
    units = _build_units(lines, numbered=structure == "numbered")
    split: list[_Unit] = []
    for u in units:
        split.extend(_split_long(u, cfg.max_tokens))
    merged = _merge_small(split, cfg.min_tokens, cfg.max_tokens)
    chunks = []
    for ordinal, (u, (cid, label)) in enumerate(
        zip(merged, _unit_ids(doc.id, merged), strict=True)
    ):
        para_label = label if label is None else (f"{label} (part {u.part})" if u.part else label)
        chunk = Chunk(
            chunk_id=cid,
            doc_id=doc.id,
            body=u.body,
            section=u.section,
            para=label,
            page=u.page,
            ordinal=ordinal,
            prefix=make_prefix(doc, u.section, para_label),
        )
        chunk.modality = classify_modality(chunk.body)
        chunk.n_tokens = count_tokens(chunk.text)
        chunks.append(chunk)
    return chunks


def chunk_fixed(lines: list[Line], doc: SourceDoc, cfg: ChunkingConfig) -> list[Chunk]:
    """Sliding token windows over the whole document (ablation baseline)."""
    tokens: list[tuple[str, str, int]] = []  # (token-with-trailing-space, section, page)
    section = ""
    for ln in lines:
        if ln.kind == "heading":
            section = ln.text
        for m in re.finditer(r"\S+\s*", ln.text + "\n"):
            tokens.append((m.group(0), section, ln.page))
    size, step = cfg.fixed_size, max(1, cfg.fixed_size - cfg.fixed_overlap)
    # Window over whitespace words, sized by estimated sub-tokens.
    chunks: list[Chunk] = []
    start = 0
    ordinal = 0
    while start < len(tokens):
        end, n = start, 0
        while end < len(tokens) and n < size:
            n += max(1, count_tokens(tokens[end][0]))
            end += 1
        window = tokens[start:end]
        body = "".join(t for t, _, _ in window).strip()
        sec, page = window[0][1], window[0][2]
        chunk = Chunk(
            chunk_id=f"{doc.id}:w{ordinal:04d}",
            doc_id=doc.id,
            body=body,
            section=sec,
            para=None,
            page=page,
            ordinal=ordinal,
            prefix=make_prefix(doc, sec, None),
        )
        chunk.modality = classify_modality(body)
        chunk.n_tokens = count_tokens(chunk.text)
        chunks.append(chunk)
        ordinal += 1
        if end >= len(tokens):
            break
        # step back by the overlap, measured in estimated tokens
        back, k = 0, end
        while k > start + 1 and back < size - step:
            k -= 1
            back += max(1, count_tokens(tokens[k][0]))
        start = max(k, start + 1)
    return chunks


def chunk_document(lines: list[Line], doc: SourceDoc, cfg: ChunkingConfig) -> list[Chunk]:
    if cfg.strategy == "fixed":
        return chunk_fixed(lines, doc, cfg)
    return chunk_structural(lines, doc, cfg)
