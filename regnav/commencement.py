"""Obligations that have not commenced yet, and the sourced statement of when they do (D-056).

Used in three places:
* **Answers** (`regnav/generate/answer.py`, when `generation.commencement_check` is on): if a
  retrieved source explains an obligation that hasn't commenced, the live source that *states* the
  date is added to the context; the answer must then state the date, citing it. If the model still
  omits it after the retry, the answer gets a claim quoting that source verbatim, never an
  unsourced date.
* **Model-use check**: the commencement note and the per-item ⏳ flag come from here, with the
  sources shown, instead of a date written in code.
* **Home page**: which library documents explain an obligation that hasn't started.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REGISTRY = Path("data/commencements.yaml")
_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip


@dataclass(frozen=True)
class CommencementSource:
    cite: str
    quote: str
    live: bool
    chunk: str = ""  # live chunk id (answers cite it)
    doc: str = ""  # staged document id (shown, not cited)
    url: str = ""


@dataclass(frozen=True)
class Commencement:
    id: str
    short: str
    obligation: str
    commences: date
    applies: str
    explained_by: tuple[str, ...]
    mentions: re.Pattern[str] | None
    sources: tuple[CommencementSource, ...] = field(default_factory=tuple)

    @property
    def long_date(self) -> str:
        d = self.commences
        return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"

    @property
    def live_source(self) -> CommencementSource | None:
        return next((s for s in self.sources if s.live and s.chunk), None)

    def pending(self, today: date) -> bool:
        return self.commences > today

    def date_pattern(self) -> re.Pattern[str]:
        d = self.commences
        mon = _MONTHS[d.month - 1]
        return re.compile(
            rf"\b{d.day}(st|nd|rd|th)?\s+({mon}|{mon[:3]})\.?,?\s+{d.year}\b"
            rf"|\b({mon}|{mon[:3]})\.?\s+{d.day}(st|nd|rd|th)?,?\s+{d.year}\b"
            rf"|\b{d.isoformat()}\b|\b{d.day:02d}/{d.month:02d}/{d.year}\b",
            re.I,
        )

    def stated_in(self, text: str) -> bool:
        return bool(self.date_pattern().search(text))

    def relevant_to(self, doc_id: str, text: str = "") -> bool:
        return doc_id in self.explained_by or bool(self.mentions and self.mentions.search(text))


@lru_cache(maxsize=2)
def load_commencements(path: str = str(REGISTRY)) -> tuple[Commencement, ...]:
    p = Path(path)
    if not p.exists():
        return ()
    out = []
    for c in (yaml.safe_load(p.read_text()) or {}).get("commencements", []):
        out.append(
            Commencement(
                id=str(c["id"]),
                short=str(c.get("short", c["id"])),
                obligation=" ".join(str(c["obligation"]).split()),
                commences=date.fromisoformat(str(c["commences"])),
                applies=" ".join(str(c.get("applies", "")).split()),
                explained_by=tuple(c.get("explained_by", [])),
                mentions=re.compile(c["mentions"], re.I) if c.get("mentions") else None,
                sources=tuple(
                    CommencementSource(
                        cite=str(s["cite"]),
                        quote=" ".join(str(s["quote"]).split()),
                        live=bool(s.get("live", False)),
                        chunk=str(s.get("chunk", "")),
                        doc=str(s.get("doc", "")),
                        url=str(s.get("url", "")),
                    )
                    for s in c.get("sources", [])
                ),
            )
        )
    return tuple(out)


def pending_for(chunks: list[Any], today: date) -> list[Commencement]:
    """Commencements not yet reached that are relevant to these retrieved chunks."""
    out = []
    for c in load_commencements():
        if not c.pending(today):
            continue
        if any(
            c.relevant_to(str(ch.metadata.get("doc_id", "")), getattr(ch, "text", ""))
            for ch in chunks
        ):
            out.append(c)
    return out


def for_doc(doc_id: str, today: date) -> list[Commencement]:
    return [c for c in load_commencements() if c.pending(today) and doc_id in c.explained_by]


def by_id(cid: str) -> Commencement | None:
    return next((c for c in load_commencements() if c.id == cid), None)
