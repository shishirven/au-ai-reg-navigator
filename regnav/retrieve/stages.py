"""Playbooks: break a broad question (or a use case) into focused stage queries (D-052, D-053).

A single search for "what do we need to do before engaging an AI vendor?" averages several
questions into one vector and finds the generic due-diligence paragraphs. Searching each stage
(due diligence, contract, notifying APRA, vendor security, AI supply chain) separately and merging
reaches the specific requirements: CPS 230 para 60, CPS 234 para 16, the APRA AI letter.

Stages are templates in ``data/playbooks.yaml``: deterministic and reviewable, no LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PLAYBOOKS_PATH = Path("data/playbooks.yaml")

# Q&A mode only expands *broad* questions. A question naming a specific instrument or paragraph
# ("What does CPS 230 para 52 say?") is already focused; stages would only dilute it.
_SPECIFIC = re.compile(
    r"\b(CPS|CPG|SPS|APS|GPS|LPS|HPS)\s?\d{3}\b|\bAPP\s?\d|\bpara(graph)?s?\s+\d|\bsection\s+\d",
    re.I,
)
_BROAD = re.compile(
    r"\bwhat\s+(do|must|should|would|does)\s+(we|i|an?\s+\w+|our\s+\w+|the\s+\w+)\s+(need\s+to\s+|have\s+to\s+)?(do|consider|check|put in place)\b"
    r"|\b(requirements?|obligations?|checklist|steps|before\s+(we\s+)?(engag|deploy|launch|use|buy|sign|go)\w*)\b",
    re.I,
)


@dataclass(frozen=True)
class Stage:
    id: str
    title: str
    query: str
    playbook: str
    evidence: str = ""
    involve: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()  # chunk ids reviewed as misleading matches for this stage


@dataclass
class Playbook:
    id: str
    title: str
    trigger: re.Pattern[str]
    when: dict[str, Any]
    stages: list[Stage] = field(default_factory=list)


@lru_cache(maxsize=4)
def load_playbooks(path: str = str(PLAYBOOKS_PATH)) -> tuple[Playbook, ...]:
    p = Path(path)
    if not p.exists():
        return ()
    data = yaml.safe_load(p.read_text()) or {}
    out = []
    for pb in data.get("playbooks", []):
        stages = [
            Stage(
                s["id"],
                s["title"],
                " ".join(s["query"].split()),
                pb["id"],
                s.get("evidence", ""),
                tuple(s.get("involve", [])),
                tuple(s.get("exclude", [])),
            )
            for s in pb.get("stages", [])
        ]
        out.append(
            Playbook(
                pb["id"], pb["title"], re.compile(pb["trigger"], re.I), pb.get("when", {}), stages
            )
        )
    return tuple(out)


def is_broad(question: str) -> bool:
    return bool(_BROAD.search(question)) and not _SPECIFIC.search(question)


def stages_for_question(
    question: str, max_stages: int = 6, playbooks: tuple[Playbook, ...] | None = None
) -> list[Stage]:
    """Stage queries for a broad Q&A question: stages of every playbook whose trigger matches,
    taken round-robin across playbooks so one playbook cannot use the whole budget."""
    if not is_broad(question):
        return []
    pbs = [
        pb
        for pb in (playbooks if playbooks is not None else load_playbooks())
        if pb.trigger.search(question)
    ]
    queues = [list(pb.stages) for pb in pbs]
    out: list[Stage] = []
    while len(out) < max_stages and any(queues):
        for q in queues:
            if q and len(out) < max_stages:
                out.append(q.pop(0))
    return out
