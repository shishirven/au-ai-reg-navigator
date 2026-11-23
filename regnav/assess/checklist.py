"""Model-use check: use case -> requirement checklist by lifecycle stage (D-053).

Deterministic on purpose: no LLM call, so it costs no API quota, gives the same output every time
and every line is a quotation from a cited paragraph. For each playbook stage that applies to the
use case, the stage query is searched per tier (binding 2, regulator expectation 2, voluntary 1),
with the per-document cap. A paragraph found by several stages is listed once, under the first.

What it is not: a compliance verdict. The output is a list of requirements and expectations to
check, with the evidence a team would typically produce and who usually signs off.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from regnav.assess.usecase import UseCase
from regnav.authority import note_for
from regnav.config import TIER_LABELS, TIERS, AppConfig
from regnav.coverage import CoverageGap, conditions_met, gaps_for_use_case
from regnav.links import citation_url
from regnav.retrieve.base import Filters, RetrievedChunk
from regnav.retrieve.expand import expand_query
from regnav.retrieve.stages import Playbook, Stage, load_playbooks
from regnav.retrieve.stratified import StratifiedRetriever, select

TIER_QUOTA = {"binding": 2, "expectation": 2, "voluntary": 1}
STAGE_DEPTH = 20  # candidates per tier per stage (stage queries are already focused)
# Cross-encoder (ms-marco MiniLM) logits, per tier, calibrated on data/use_cases/*.yaml by
# reading every item (docs/model_use_check.md). Terse binding paragraphs score high when they
# match; off-topic ones (a CPS 234 definition returned for a privacy stage, because no binding
# privacy text is live) score below -3.5. AI6's long, discursive text scores low even when
# relevant, so the voluntary floor is lower.
FLOORS = {  # tier: (weak below, drop below)
    "binding": (-1.0, -3.5),
    "expectation": (0.0, -4.0),
    "voluntary": (-4.0, -7.0),
}
_STAGE_CACHE: dict[tuple, list[RetrievedChunk]] = {}  # stage queries are fixed: reuse results
CACHE_DIR = Path("chroma/stage_cache")  # persisted per index version + retrieval settings


def _cache_file(cfg: AppConfig, index_version: str) -> Path:
    key = hashlib.sha256(
        json.dumps(
            {
                "retrieval": cfg.retrieval.model_dump(),
                "embedding": cfg.embedding.model_dump(),
                "depth": STAGE_DEPTH,
            },
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()[:12]
    return CACHE_DIR / f"{index_version}__{key}.json"


def _load_disk_cache(path: Path) -> dict[str, list[RetrievedChunk]]:
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return {k: [RetrievedChunk(**c) for c in v] for k, v in raw.items()}


def _save_disk_cache(path: Path, data: dict[str, list[RetrievedChunk]]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({k: [asdict(c) for c in v] for k, v in data.items()}))
        tmp.replace(path)
    except OSError:
        pass  # read-only filesystem (e.g. baked image): in-memory cache still works


@dataclass
class ChecklistItem:
    stage_id: str
    tier: str
    document: str
    citation: str
    chunk_id: str
    excerpt: str
    modality: str
    effective_from: str = ""
    not_yet_in_force: bool = False
    url: str = ""
    score: float | None = None
    weak: bool = False
    explains_law: str = ""
    also_in: list[str] = field(default_factory=list)
    also_ids: list[str] = field(default_factory=list)

    @property
    def tier_label(self) -> str:
        return TIER_LABELS.get(self.tier, self.tier)


@dataclass
class ChecklistStage:
    stage: Stage
    playbook_title: str
    items: list[ChecklistItem] = field(default_factory=list)
    see_also: list[ChecklistItem] = field(
        default_factory=list
    )  # relevant, listed in an earlier stage
    playbook_id: str = ""

    @property
    def has_binding(self) -> bool:
        return any(i.tier == "binding" for i in self.items + self.see_also)


@dataclass
class Checklist:
    use_case: UseCase
    stages: list[ChecklistStage]
    notes: list[str]
    gaps: list[CoverageGap]
    assumptions: list[str]
    index_version: str
    config_name: str
    generated: date

    @property
    def items(self) -> list[ChecklistItem]:
        return [i for s in self.stages for i in s.items]

    def counts(self) -> dict[str, int]:
        return {t: sum(1 for i in self.items if i.tier == t) for t in TIERS}


def selected_playbooks(
    uc: UseCase, playbooks: tuple[Playbook, ...] | None = None
) -> list[Playbook]:
    facts = uc.facts()
    return [pb for pb in (playbooks or load_playbooks()) if conditions_met(pb.when, facts)]


def _excerpt(text: str, limit: int = 420) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if lines and lines[0].startswith("[") and lines[0].endswith("]"):
        lines = lines[1:]
    body = " ".join(" ".join(lines).split())
    if len(body) <= limit:
        return body
    cut = body[:limit]
    end = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(": "))
    return (cut[: end + 1] if end > limit // 2 else cut.rsplit(" ", 1)[0]) + " …"


def _citation(m: dict[str, Any]) -> str:
    para = str(m.get("para") or "")
    if para:
        return f"para {para}"
    section = str(m.get("section") or "")
    return section.split("›")[-1].strip() if section else ""


def _item(stage: Stage, c: RetrievedChunk, today: date) -> ChecklistItem:
    m = c.metadata
    eff = str(m.get("effective_from") or "")
    score = c.scores.get("rerank")
    note = note_for(str(m.get("doc_id", "")))
    return ChecklistItem(
        stage_id=stage.id,
        tier=c.tier,
        document=str(m.get("short_name", "")),
        citation=_citation(m),
        chunk_id=c.chunk_id,
        excerpt=_excerpt(c.text),
        modality=c.modality,
        effective_from=eff,
        not_yet_in_force=bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", eff)) and eff > today.isoformat(),
        url=citation_url(m, c.text),
        score=score,
        weak=score is not None and score < FLOORS.get(c.tier, (0.0, 0.0))[0],
        explains_law=note.note if note else "",
    )


def _copy(c: RetrievedChunk) -> RetrievedChunk:
    return RetrievedChunk(c.chunk_id, c.text, dict(c.metadata), c.score, c.rank, dict(c.scores))


def applicability_notes(uc: UseCase, today: date) -> list[str]:
    """Deterministic notes tied to intake answers. Each cites the paragraph it rests on."""
    f = uc.facts()
    notes = [
        "Prudential standards (CPS 230, CPS 234, CPS 220) bind APRA-regulated entities. This "
        f"check assumes your organisation is an APRA-regulated {uc.sector}."
    ]
    if f["third_party"] and f["critical_operation"]:
        notes.append(
            "If the vendor's service supports a critical operation, notify APRA as soon as possible "
            "and not more than 20 business days after entering into or materially changing the "
            "agreement (CPS 230 para 60(a))."
            + (
                " You answered 'unsure' on critical operation: confirm with operational risk."
                if uc.critical_operation == "unsure"
                else ""
            )
        )
    if f["third_party"] and f["offshore"]:
        notes.append(
            "Notify APRA before entering into a material offshoring arrangement, including where "
            "data or personnel for the service will be located offshore (CPS 230 para 60(b))."
            + (
                " You answered 'unsure' on offshore: find out where the vendor hosts data and models."
                if uc.offshore == "unsure"
                else ""
            )
        )
    if f["decisions_about_individuals"] and f["personal_information"]:
        start = date(2026, 12, 10)
        when = (
            f"commences on 10 December 2026 ({(start - today).days} days from today)"
            if today < start
            else "has applied since 10 December 2026"
        )
        notes.append(
            "Automated decision-making transparency (APP 1.7-1.9) "
            f"{when}: the privacy policy must describe decisions a computer program makes, or "
            "substantially and directly informs, that could significantly affect individuals "
            "(OAIC APP 1.7-1.9 fact sheet). Banks and insurers are assumed to be APP entities."
        )
    if uc.sensitive_information in ("yes", "unsure"):
        notes.append(
            "Sensitive information (e.g. health) generally needs consent to collect under the "
            "Privacy Act (APP 3). The Act's text is not yet live in this library: confirm with "
            "your privacy officer."
        )
    return notes


def build_checklist(
    uc: UseCase,
    cfg: AppConfig,
    strat: StratifiedRetriever,
    index_version: str,
    today: date | None = None,
) -> Checklist:
    today = today or date.today()
    filters = Filters(sector=uc.sector if cfg.retrieval.sector_filter else None)
    seen: dict[str, ChecklistItem] = {}
    stages: list[ChecklistStage] = []
    cache_path = _cache_file(cfg, index_version)
    disk = _load_disk_cache(cache_path)
    dirty = False
    for pb in selected_playbooks(uc):
        for st in pb.stages:
            query = expand_query(st.query) if cfg.retrieval.query_expansion else st.query
            cs = ChecklistStage(st, pb.title, playbook_id=pb.id)
            for tier, quota in TIER_QUOTA.items():
                key = (id(strat), index_version, query, tier, filters.sector)
                dkey = f"{tier}|{filters.sector}|{query}"
                if key not in _STAGE_CACHE:
                    if dkey in disk:
                        _STAGE_CACHE[key] = disk[dkey]
                    else:
                        _STAGE_CACHE[key] = strat.base.search(
                            query, STAGE_DEPTH, filters.with_tier(tier)
                        )
                        disk[dkey] = _STAGE_CACHE[key]
                        dirty = True
                ranking = [_copy(c) for c in _STAGE_CACHE[key]]
                floor = FLOORS.get(tier, (0.0, -99.0))[1]
                ranking = [
                    c
                    for c in ranking
                    if c.scores.get("rerank", 0.0) >= floor and c.chunk_id not in st.exclude
                ]
                for c in select([ranking], quota, strat.per_doc_cap or 2):
                    if c.chunk_id in seen:
                        first = seen[c.chunk_id]
                        if st.title not in first.also_in:
                            first.also_in.append(st.title)
                        cs.see_also.append(first)
                        continue
                    item = _item(st, c, today)
                    seen[c.chunk_id] = item
                    cs.items.append(item)
            stages.append(cs)
    if dirty:
        _save_disk_cache(cache_path, disk)
    assumptions = (
        [f"'Unsure' treated as 'yes' for: {', '.join(uc.unsure_fields())}."]
        if uc.unsure_fields()
        else []
    )
    return Checklist(
        uc,
        stages,
        applicability_notes(uc, today),
        gaps_for_use_case(uc.facts(), f"{uc.name} {uc.description}"),
        assumptions,
        index_version,
        cfg.name,
        today,
    )
