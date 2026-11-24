"""Every commencement date is backed by quotes that really are in the sources (D-056).

Live sources: the quote must be in the indexed chunk the answers cite. Staged sources (not yet
searched): the quote must be in the staged statutory extract. Fails if a source is re-ingested,
re-chunked or replaced and the quote no longer matches. Needs the real index (make ingest).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from regnav.commencement import load_commencements
from regnav.config import load_config
from regnav.ingest.index import load_chunk_rows, load_manifest


def _norm(s: str) -> str:
    return " ".join(s.split())


@pytest.fixture(scope="module")
def rows():
    cfg = load_config()
    if load_manifest(cfg) is None:
        pytest.skip("real corpus not indexed - run `make ingest`")
    return {r["chunk_id"]: r for r in load_chunk_rows(cfg)}


def test_live_quotes_are_in_the_cited_chunks(rows) -> None:
    for c in load_commencements():
        for s in c.sources:
            if s.live:
                assert s.chunk in rows, f"{c.id}: {s.chunk} not in the index"
                assert _norm(s.quote) in _norm(rows[s.chunk]["text"]), (
                    f"{c.id}: quote not in {s.chunk}"
                )
                assert c.stated_in(s.quote), f"{c.id}: live quote does not state the date"


def test_staged_quotes_are_in_the_statutory_extracts() -> None:
    pending = {
        d["id"]: d
        for d in yaml.safe_load(Path("data/sources_pending.yaml").read_text())["documents"]
    }
    for c in load_commencements():
        for s in c.sources:
            if not s.live:
                text = Path("data/raw", pending[s.doc]["file"]).read_text()
                assert _norm(s.quote) in _norm(text), f"{c.id}: quote not in {s.doc}"


def test_every_commencement_has_a_live_source_and_the_law() -> None:
    for c in load_commencements():
        assert c.live_source is not None, f"{c.id}: no live source to cite"
        assert any(
            not s.live and re.search(r"Act|Regulation|Standard", s.cite) for s in c.sources
        ), f"{c.id}: no legal source for the date"
