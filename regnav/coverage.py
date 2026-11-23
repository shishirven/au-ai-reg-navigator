"""'Not covered by this library' notes (D-054). Pointers only, never advice."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

COVERAGE_PATH = Path("data/coverage.yaml")


@dataclass(frozen=True)
class CoverageGap:
    id: str
    title: str
    note: str
    trigger: re.Pattern[str]
    when: dict[str, Any]


@lru_cache(maxsize=2)
def load_coverage(path: str = str(COVERAGE_PATH)) -> tuple[str, tuple[CoverageGap, ...]]:
    p = Path(path)
    if not p.exists():
        return "", ()
    data = yaml.safe_load(p.read_text()) or {}
    gaps = tuple(
        CoverageGap(
            g["id"],
            g["title"],
            " ".join(g["note"].split()),
            re.compile(g["trigger"], re.I),
            g.get("when", {}),
        )
        for g in data.get("not_covered", [])
    )
    return " ".join(str(data.get("library", "")).split()), gaps


def gaps_for_question(question: str) -> list[CoverageGap]:
    """Gaps whose trigger matches the question (Q&A mode)."""
    return [g for g in load_coverage()[1] if g.trigger.search(question)]


def conditions_met(when: dict[str, Any], facts: dict[str, Any]) -> bool:
    """``when`` is a conjunction of field == value; ``{always: true}`` always matches."""
    if when.get("always"):
        return True
    return bool(when) and all(facts.get(k) == v for k, v in when.items())


def gaps_for_use_case(facts: dict[str, Any], text: str = "") -> list[CoverageGap]:
    """Gaps whose conditions match the use case, or whose trigger matches its description."""
    return [
        g
        for g in load_coverage()[1]
        if conditions_met(g.when, facts) or (text and g.trigger.search(text))
    ]
