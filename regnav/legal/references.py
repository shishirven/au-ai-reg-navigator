"""Extract citations of legal provisions and resolve them to corpus chunks (D-044).

Deterministic on purpose: references in these documents are regular ("paragraph 60(a) of CPS 230",
"CPS 230 paragraph 35", "APP 6", "Australian Privacy Principle 1.7", "section 6D of the Privacy
Act"), so a parser + lookup is exact and auditable. Unresolvable references (provision not in the
corpus) are kept and flagged rather than dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

STD = r"(CPS|CPG|SPS|APS|GPS|LPS|HPS)\s?(\d{3})"
_PARA_OF = re.compile(
    r"\b(?:paragraphs?|paras?)\s+(\d{1,3})(\([a-z]{1,4}\))?((?:\s*(?:,|and|to|-|–)\s*\d{1,3}(?:\([a-z]{1,4}\))?)*)"
    rf"\s+of\s+{STD}",
    re.I,
)
_STD_PARA = re.compile(rf"\b{STD}\s+(?:paragraphs?|paras?)\s+(\d{{1,3}})(\([a-z]{{1,4}}\))?", re.I)
_STD = re.compile(rf"\b{STD}\b")
_APP = re.compile(
    r"\b(?:APPs?|Australian Privacy Principles?)\s?(\d{1,2})(?:\.(\d{1,2}))?(?:\s*(?:-|–|to)\s*\d{1,2}\.(\d{1,2}))?"
)
_SECTION = re.compile(
    r"\b(?:section|s)\s?(\d{1,3}[A-Z]{0,3})(?:\(\d+\))?\s+of\s+the\s+Privacy\s+Act", re.I
)


@dataclass(frozen=True)
class Reference:
    instrument: str  # "CPS 230", "APP 1.7", "APP 6", "Privacy Act s 6D"
    provision: str = ""  # "60(a)", "" for whole instrument
    text: str = ""  # matched text

    @property
    def citation(self) -> str:
        if (
            self.instrument.startswith(("CPS", "CPG", "SPS", "APS", "GPS", "LPS", "HPS"))
            and self.provision
        ):
            return f"{self.instrument} para {self.provision}"
        if self.instrument.startswith("APP"):
            return f"Privacy Act 1988 (Cth), {self.instrument}"
        return self.instrument


@dataclass
class Resolution:
    ref: Reference
    doc_id: str | None
    chunk_ids: list[str] = field(default_factory=list)
    in_corpus: bool = False

    @property
    def resolved(self) -> bool:
        return bool(self.chunk_ids)


def extract_references(text: str) -> list[Reference]:
    refs: list[Reference] = []
    seen_spans: list[tuple[int, int]] = []

    def add(ref: Reference, span: tuple[int, int]) -> None:
        if any(a <= span[0] < b for a, b in seen_spans):
            return
        seen_spans.append(span)
        if ref not in refs:
            refs.append(ref)

    for m in _PARA_OF.finditer(text):
        inst = f"{m.group(4).upper()} {m.group(5)}"
        add(Reference(inst, m.group(1) + (m.group(2) or ""), m.group(0)), m.span())
        for extra in re.findall(r"\d{1,3}(?:\([a-z]{1,4}\))?", m.group(3) or ""):
            refs.append(Reference(inst, extra, m.group(0)))
    for m in _STD_PARA.finditer(text):
        add(
            Reference(
                f"{m.group(1).upper()} {m.group(2)}", m.group(3) + (m.group(4) or ""), m.group(0)
            ),
            m.span(),
        )
    for m in _APP.finditer(text):
        major, minor, range_end = m.group(1), m.group(2), m.group(3)
        if minor and range_end:  # "APP 1.7-1.9" -> 1.7, 1.8, 1.9
            for k in range(int(minor), int(range_end) + 1):
                add(Reference(f"APP {major}.{k}", "", m.group(0)), (m.start(), m.end()))
                seen_spans.pop()  # allow siblings from the same span
            seen_spans.append(m.span())
        else:
            add(
                Reference(f"APP {major}.{minor}" if minor else f"APP {major}", "", m.group(0)),
                m.span(),
            )
    for m in _SECTION.finditer(text):
        add(Reference(f"Privacy Act s {m.group(1)}", "", m.group(0)), m.span())
    for m in _STD.finditer(text):  # bare instrument mentions last (lowest precedence)
        add(Reference(f"{m.group(1)} {m.group(2)}", "", m.group(0)), m.span())
    return refs


@lru_cache(maxsize=2)
def load_registry(path: str = "data/legal_refs.yaml") -> dict[str, Any]:
    p = Path(path)
    return yaml.safe_load(p.read_text()) if p.exists() else {"instruments": {}, "documents": {}}


class Resolver:
    """Resolves references against chunk rows (``load_chunk_rows``) of a given index."""

    def __init__(
        self, chunk_rows: list[dict[str, Any]], registry: dict[str, Any] | None = None
    ) -> None:
        self.registry = registry or load_registry()
        self.by_para: dict[tuple[str, str], list[str]] = {}
        self.by_doc: dict[str, list[dict[str, Any]]] = {}
        for r in chunk_rows:
            self.by_doc.setdefault(r["doc_id"], []).append(r)
            for p in _para_numbers(str(r.get("para", ""))):
                self.by_para.setdefault((r["doc_id"], p), []).append(r["chunk_id"])

    def resolve(self, ref: Reference) -> Resolution:
        instruments = self.registry.get("instruments", {})
        inst = instruments.get(ref.instrument)
        subclause = None
        if inst is None and (m := re.fullmatch(r"APP (\d{1,2})(?:\.(\d{1,2}))?", ref.instrument)):
            template = instruments.get("APP *")
            if template is None:
                return Resolution(ref, None)  # APPs not registered
            inst = {**template, "heading": template["heading"].format(n=m.group(1))}
            subclause = f"{m.group(1)}.{m.group(2)}" if m.group(2) else None
        if inst is None:
            return Resolution(ref, None)
        doc_id = inst["doc_id"]
        in_corpus = doc_id in self.by_doc
        if not in_corpus:
            return Resolution(ref, doc_id, in_corpus=False)
        if ref.provision:
            base = re.match(r"\d+", ref.provision)
            ids = self.by_para.get((doc_id, base.group(0) if base else ref.provision), [])
            return Resolution(ref, doc_id, list(ids), True)
        heading = inst.get("heading")
        if heading:
            rows = [
                r
                for r in self.by_doc[doc_id]
                if _heading_matches(str(r.get("section", "")), heading)
            ]
            if subclause:  # "APP 6.2" -> the chunk(s) of APP 6 that contain subclause 6.2
                exact = [
                    r for r in rows if re.search(rf"(^|\n){re.escape(subclause)}\s", r["text"])
                ]
                rows = exact or rows
            return Resolution(ref, doc_id, [r["chunk_id"] for r in rows], True)
        return Resolution(ref, doc_id, [], True)  # whole-instrument mention

    def regime(self, doc_id: str) -> str:
        return str(self.registry.get("documents", {}).get(doc_id, {}).get("regime", "unknown"))


def _para_numbers(label: str) -> list[str]:
    """'52' -> ['52']; '50-51' -> ['50', '51']; '' -> []."""
    m = re.fullmatch(r"(\d+)(?:-(\d+))?(?: \(part \d+\))?", label.strip())
    if not m:
        return []
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    return [str(i) for i in range(a, b + 1)] if b - a < 20 else [str(a)]


def _heading_matches(section: str, heading: str) -> bool:
    """True if a component of the section path starts with ``heading`` ("APP 1.7 - ...") or names
    it as a (sub)section ("Subsection 6D(1) - ...", "Section 6 - ...")."""
    pat = re.compile(rf"^(?:(?:Sub)?[Ss]ections?\s+)?{re.escape(heading)}(?=[\s(\-–]|$)")
    return any(pat.match(comp.strip()) for comp in section.split("›"))
