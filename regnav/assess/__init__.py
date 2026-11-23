"""Model-use check for data, AI and analytics teams (D-053)."""

from __future__ import annotations

from regnav.assess.checklist import Checklist, build_checklist
from regnav.assess.usecase import UseCase
from regnav.config import AppConfig
from regnav.retrieve import RetrievalSystem, build_retrieval
from regnav.retrieve.stratified import StratifiedRetriever


def stratified_of(system: RetrievalSystem) -> StratifiedRetriever:
    """The stratified retriever inside a retrieval system (under any planner / expander)."""
    r: object = system.retriever
    while not isinstance(r, StratifiedRetriever):
        r = getattr(r, "base", None)
        if r is None:
            raise ValueError("the model-use check needs a config with retrieval.mode: stratified")
    return r


def run_check(uc: UseCase, cfg: AppConfig, system: RetrievalSystem | None = None) -> Checklist:
    system = system or build_retrieval(cfg)
    return build_checklist(uc, cfg, stratified_of(system), system.index_version)


__all__ = ["Checklist", "UseCase", "run_check", "stratified_of"]
