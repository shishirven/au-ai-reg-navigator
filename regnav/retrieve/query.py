"""Separate *what to search for* from *how to format the answer* (D-052).

Users often append formatting instructions to a question ("...and highlight which are mandatory,
which the regulator expects and which are voluntary"). The answer format already does that, and
the words "mandatory / binding / voluntary / guidance" pull retrieval towards chunks *about* legal
status and away from the topic. Measured on the live index: with the instruction appended, CPS 230
para 52 (the due-diligence requirement) dropped out of the context entirely.

Deterministic and conservative on purpose: a span is removed only when it both *starts like an
instruction* and *talks about authority or format*. Everything else is kept.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Words that describe legal force or answer layout rather than the regulatory topic.
_AUTHORITY = re.compile(
    r"\b(mandatory|binding|enforceable|legally|by law|regulat\w*\s+expect\w*|expect\w*|"
    r"recomm?e?n+d\w*|voluntary|optional|guidance|best practice)\b",
    re.I,
)
_FORMAT = re.compile(
    r"\b(table|bullet\w*|format\w*|concise\w*|summar\w*|plain english|word count|"
    r"step[- ]by[- ]step|cite|citations?|references?)\b",
    re.I,
)
# An instruction lead: optional "and/please", then a directive verb ("highlight", with common
# misspellings), then a word that introduces the thing to sort.
_LEAD = re.compile(
    r"(?:^|[,;]\s*|\s+)(?:and\s+)?(?:please\s+)?"
    r"(?:h[a-z]{2,8}t|indicate\w*|show\w*|mark\w*|separate\w*|split\w*|label\w*|flag\w*|"
    r"identify\w*|tell\s+me|classify\w*|distinguish\w*|clarify\w*|group\w*|categori[sz]e\w*|"
    r"break\s+(?:it|this|them)\s+down|format\w*|present\w*|structure\w*|list\w*|use)\s+"
    r"(?:it\s+|them\s+|this\s+|the\s+answer\s+)?"
    r"(?:which|what|whether|between|by|into|as|in|the|each|those|items?|bullet\w*|a\s+table)\b",
    re.I,
)
_SENTENCE = re.compile(r"(?<=[.?!])\s+")


@dataclass
class CleanedQuery:
    search: str
    removed: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.removed)


def strip_instructions(question: str) -> CleanedQuery:
    """Return the question with answer-format instructions removed (and what was removed)."""
    kept: list[str] = []
    removed: list[str] = []
    for sentence in _SENTENCE.split(question.strip()):
        m = _LEAD.search(sentence)
        tail = sentence[m.start() :] if m else ""
        if m and (len(_AUTHORITY.findall(tail)) >= 2 or _FORMAT.search(tail)):
            head = sentence[: m.start()].rstrip(" ,;")
            removed.append(tail.strip(" ,;"))
            if head:
                kept.append(head)
            continue
        # A whole sentence that is only a formatting request ("Use a table.").
        if (
            _FORMAT.search(sentence)
            and len(sentence.split()) <= 8
            and not re.search(r"\?", sentence)
        ):
            removed.append(sentence.strip())
            continue
        kept.append(sentence)
    search = " ".join(kept).strip() or question.strip()
    return CleanedQuery(search, removed)
