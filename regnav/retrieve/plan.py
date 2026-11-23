"""Query planning in front of stratified retrieval (D-052).

question -> strip answer-format instructions -> add stage sub-queries (broad questions only)
-> AI->tech-neutral expansion of each -> stratified, per-document-capped multi-query search.
The plan actually used is kept on ``last_plan`` for display and tracing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from regnav.retrieve.base import Filters, RetrievedChunk
from regnav.retrieve.expand import expand_query
from regnav.retrieve.query import strip_instructions
from regnav.retrieve.stages import Stage, stages_for_question
from regnav.retrieve.stratified import StratifiedRetriever


@dataclass
class QueryPlan:
    question: str
    search: str
    removed: list[str] = field(default_factory=list)
    stages: list[Stage] = field(default_factory=list)

    def queries(self, expand: bool) -> list[str]:
        qs = [self.search] + [s.query for s in self.stages]
        return [expand_query(q) for q in qs] if expand else qs

    def labels(self) -> list[str]:
        return ["question"] + [s.id for s in self.stages]


def make_plan(question: str, strip: bool, stages: bool, max_stages: int = 6) -> QueryPlan:
    cleaned = strip_instructions(question) if strip else None
    search = cleaned.search if cleaned else question
    return QueryPlan(
        question,
        search,
        cleaned.removed if cleaned else [],
        stages_for_question(search, max_stages) if stages else [],
    )


class PlannedRetriever:
    name = "planned"

    def __init__(
        self,
        base: StratifiedRetriever,
        strip: bool = True,
        stages: bool = True,
        expand: bool = True,
        max_stages: int = 6,
    ) -> None:
        self.base = base
        self.strip = strip
        self.stages = stages
        self.expand = expand
        self.max_stages = max_stages
        self.last_plan: QueryPlan | None = None

    def search(self, query: str, k: int, filters: Filters) -> list[RetrievedChunk]:
        plan = make_plan(query, self.strip, self.stages, self.max_stages)
        self.last_plan = plan
        return self.base.search_multi(plan.queries(self.expand), k, filters, plan.labels())
