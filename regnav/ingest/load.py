"""Load the source registry (``sources.yaml``) and fingerprint source files."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from regnav.config import SECTORS, Sector, Tier


class SourceDoc(BaseModel):
    id: str
    file: str
    title: str
    short_name: str = ""
    issuer: str
    tier: Tier
    status: Literal["current", "superseded"] = "current"
    applies_to: list[Sector] = Field(min_length=1)
    effective_from: str = ""
    url: str = ""
    structure: Literal["numbered", "headings", "auto"] = "auto"
    start_page: int | None = None
    end_page: int | None = None
    drop_boxed_text: bool = False
    sha256: str = ""

    @field_validator("id")
    @classmethod
    def _id_slug(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9_]+", v):
            raise ValueError(f"doc id must be lowercase snake_case, got {v!r}")
        return v

    @property
    def label(self) -> str:
        return self.short_name or self.title

    def metadata_fingerprint(self) -> str:
        """Hash of the metadata that affects chunks/tags (not sha256 itself)."""
        payload = self.model_dump(exclude={"sha256"})
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]

    def applies_flags(self) -> dict[str, bool]:
        """Chroma metadata must be scalar: flatten ``applies_to`` into booleans."""
        return {f"applies_{s}": s in self.applies_to for s in SECTORS}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def load_sources(sources_file: Path) -> list[SourceDoc]:
    data = yaml.safe_load(sources_file.read_text()) or {}
    docs = [SourceDoc.model_validate(d) for d in data.get("documents", [])]
    ids = [d.id for d in docs]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate doc ids in {sources_file}: {sorted(dupes)}")
    return docs


def resolve_and_hash(docs: list[SourceDoc], raw_dir: Path) -> list[SourceDoc]:
    """Compute sha256 for each doc's file. Raises if a file is missing."""
    out = []
    for d in docs:
        if not d.file:
            raise FileNotFoundError(f"{d.id}: no `file` set in sources.yaml")
        path = raw_dir / d.file
        if not path.exists():
            raise FileNotFoundError(f"{d.id}: {path} not found")
        out.append(d.model_copy(update={"sha256": sha256_file(path)}))
    return out


def write_hashes(sources_file: Path, hashes: dict[str, str]) -> bool:
    """Write sha256 values back into sources.yaml in place, preserving comments.

    Returns True if the file changed.
    """
    lines = sources_file.read_text().splitlines(keepends=True)
    current: str | None = None
    changed = False
    for i, line in enumerate(lines):
        m = re.match(r"\s*-\s+id:\s*(\S+)", line)
        if m:
            current = m.group(1).strip("\"'")
            continue
        m = re.match(r"(\s*)sha256:\s*(\S*)(.*)$", line.rstrip("\n"))
        if m and current in hashes:
            new = f'{m.group(1)}sha256: "{hashes[current]}"\n'
            if new != line:
                lines[i] = new
                changed = True
    if changed:
        sources_file.write_text("".join(lines))
    return changed
