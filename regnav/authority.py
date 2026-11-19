"""Display-only authority notes: which guidance documents explain binding law (D-043).

Loaded by the UI and CLI to annotate claims. Deliberately NOT used by ingest, retrieval or the
prompt, so adding/changing a note never changes the index version or evaluation results.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

DEFAULT_PATH = Path("data/authority_notes.yaml")


@dataclass(frozen=True)
class AuthorityNote:
    doc_id: str
    explains_binding: str
    note: str
    in_force_from: str = ""

    @property
    def badge(self) -> str:
        when = f", in force from {self.in_force_from}" if self.in_force_from else ""
        return f"Explains binding law: {self.explains_binding}{when}"


@lru_cache(maxsize=4)
def load_notes(path: str = str(DEFAULT_PATH)) -> dict[str, AuthorityNote]:
    p = Path(path)
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text()) or {}
    return {
        doc_id: AuthorityNote(
            doc_id=doc_id,
            explains_binding=str(v.get("explains_binding", "")),
            note=" ".join(str(v.get("note", "")).split()),
            in_force_from=str(v.get("in_force_from", "") or ""),
        )
        for doc_id, v in (data.get("notes") or {}).items()
    }


def note_for(doc_id: str, path: str = str(DEFAULT_PATH)) -> AuthorityNote | None:
    return load_notes(path).get(doc_id)
