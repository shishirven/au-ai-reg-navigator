"""Split a chunk into statements: one per sentence or list item, keeping the lead-in.

A numbered paragraph such as "52. Before entering into ... an entity must: (a) ...; (b) ..." has
its legal force in the lead-in and its content in the items, so each item statement carries the
lead-in as ``context``. Authority is then judged on ``context + text``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_ITEM = re.compile(r"^(\([a-z]{1,4}\)|\([ivx]{1,5}\)|[a-z]\)|•)\s+")
_SENT_SPLIT = re.compile(r"(?<=[.;])\s+(?=[A-Z(•])")


@dataclass
class Statement:
    chunk_id: str
    index: int
    text: str
    context: str = ""  # lead-in sentence that governs a list item ("An entity must:")
    refs: list = field(default_factory=list)

    @property
    def full(self) -> str:
        return f"{self.context} {self.text}".strip() if self.context else self.text


def split_statements(chunk_id: str, chunk_text: str) -> list[Statement]:
    """``chunk_text`` may include the ``[Doc · Tier · ...]`` prefix line; it is skipped."""
    lines = [ln.strip() for ln in chunk_text.split("\n") if ln.strip()]
    if lines and lines[0].startswith("[") and lines[0].endswith("]"):
        lines = lines[1:]
    out: list[Statement] = []
    lead = ""
    for line in lines:
        if _ITEM.match(line):
            out.append(Statement(chunk_id, len(out), _ITEM.sub("", line), context=lead))
            continue
        # Keep a leading paragraph/subclause number ("52. ", "1.7 ") attached to its first sentence.
        num = re.match(r"^(\d{1,3}(?:\.\d{1,2})?\.?\s+)", line)
        body = line[num.end() :] if num else line
        sentences = [s.strip() for s in _SENT_SPLIT.split(body) if s.strip()]
        if num and sentences:
            sentences[0] = num.group(1) + sentences[0]
        for s in sentences:
            out.append(Statement(chunk_id, len(out), s))
        # A line ending in ":" introduces the list items that follow.
        lead = sentences[-1] if sentences and sentences[-1].rstrip().endswith(":") else ""
    return out
