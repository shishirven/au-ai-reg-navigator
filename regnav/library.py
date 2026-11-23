"""The documents in the regulation library, for display (Home page, docs).

Read from the source registry so the list shown to users can never drift from what is indexed:
``data/sources.yaml`` (live; ``current`` documents are searched, ``superseded`` ones are kept for
history and excluded) and ``data/sources_pending.yaml`` (staged, not yet searched).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from regnav.config import TIER_LABELS, TIERS


@dataclass(frozen=True)
class LibraryDoc:
    id: str
    title: str
    short_name: str
    issuer: str
    tier: str
    status: str  # current | superseded | staged
    effective_from: str
    url: str
    applies_to: tuple[str, ...]

    @property
    def tier_label(self) -> str:
        return TIER_LABELS.get(self.tier, self.tier)


def _docs(path: Path, staged: bool = False) -> list[LibraryDoc]:
    if not path.exists():
        return []
    data: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    out = []
    for d in data.get("documents", []):
        out.append(
            LibraryDoc(
                id=str(d["id"]),
                title=str(d.get("title", d["id"])),
                short_name=str(d.get("short_name", d["id"])),
                issuer=str(d.get("issuer", "")),
                tier=str(d.get("tier", "")),
                status="staged" if staged else str(d.get("status", "current")),
                effective_from=str(d.get("effective_from", "")),
                url=str(d.get("url", "")),
                applies_to=tuple(d.get("applies_to", []) or []),
            )
        )
    order: dict[str, int] = {str(t): i for i, t in enumerate(TIERS)}
    return sorted(out, key=lambda x: (order.get(x.tier, 9), x.short_name))


def library(root: Path = Path(".")) -> dict[str, list[LibraryDoc]]:
    """{'current': [...], 'superseded': [...], 'staged': [...]}, each sorted by tier then name."""
    live = _docs(root / "data" / "sources.yaml")
    return {
        "current": [d for d in live if d.status == "current"],
        "superseded": [d for d in live if d.status == "superseded"],
        "staged": _docs(root / "data" / "sources_pending.yaml", staged=True),
    }
