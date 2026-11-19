"""Evaluation question set (JSONL). Draft questions are never scored as gold."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from regnav.config import Tier

QType = Literal["split", "factual", "cross_doc", "unanswerable"]


class EvalQuestion(BaseModel):
    id: str
    question: str
    sector: str | None = None
    type: QType
    gold_chunk_ids: list[str] = Field(default_factory=list)
    reference_answer: str = ""
    expected_tiers: list[Tier] = Field(default_factory=list)
    status: str | None = None  # "DRAFT" for unreviewed candidates

    @property
    def answerable(self) -> bool:
        return self.type != "unanswerable"


class DraftQuestionsError(ValueError):
    pass


def load_questions(path: Path, allow_draft: bool = False) -> list[EvalQuestion]:
    qs = [
        EvalQuestion.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    drafts = [q.id for q in qs if (q.status or "").upper() == "DRAFT"]
    if drafts and not allow_draft:
        raise DraftQuestionsError(
            f"{path} contains {len(drafts)} DRAFT questions (e.g. {drafts[:3]}); review them and remove "
            "`status` before scoring, or pass --allow-draft for a clearly-labelled provisional run."
        )
    ids = [q.id for q in qs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate question ids in {path}")
    for q in qs:
        if q.answerable and not q.gold_chunk_ids:
            raise ValueError(f"{q.id}: answerable question without gold_chunk_ids")
    return qs


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_gold_ids(questions: list[EvalQuestion], known_ids: set[str]) -> list[str]:
    """Gold ids that do not exist in the current index (stale labels after a re-chunk)."""
    return [f"{q.id}:{g}" for q in questions for g in q.gold_chunk_ids if g not in known_ids]


def dump(questions: list[EvalQuestion], path: Path) -> None:
    path.write_text("".join(json.dumps(q.model_dump(exclude_none=True)) + "\n" for q in questions))
