"""Model-use check for data, AI and analytics teams (D-053)."""

from __future__ import annotations

import threading

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


_LOCK = threading.Lock()  # one check at a time: a waiting check reuses the warm-up's results


def run_check(uc: UseCase, cfg: AppConfig, system: RetrievalSystem | None = None) -> Checklist:
    system = system or build_retrieval(cfg)
    with _LOCK:
        return build_checklist(uc, cfg, stratified_of(system), system.index_version)


WARMUP_CASES = [
    UseCase(
        name="warm-up",
        sector=sector,
        personal_information="yes",
        sensitive_information="yes",
        decisions_about_individuals="yes",
        third_party="yes",
        offshore="yes",
        critical_operation="yes",
        generative_ai="yes",
    )
    for sector in ("bank", "insurer")
]


def warm_up(cfg: AppConfig, system: RetrievalSystem) -> None:
    """Search every stage for both sectors so later checks are instant (fills the stage cache)."""
    for uc in WARMUP_CASES:
        run_check(uc, cfg, system)


__all__ = ["Checklist", "UseCase", "run_check", "stratified_of", "warm_up"]
