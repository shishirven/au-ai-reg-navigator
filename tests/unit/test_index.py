"""sha256 change detection: unchanged -> skip; changed -> new index version."""

import json
from pathlib import Path

from regnav.config import AppConfig
from regnav.ingest.index import (
    compute_index_version,
    get_collection,
    ingest,
    load_chunk_rows,
    manifest_path,
)


def test_first_ingest_then_unchanged_is_skipped(fixture_cfg: AppConfig) -> None:
    r1 = ingest(fixture_cfg)
    assert set(r1.actions.values()) == {"added"}
    assert r1.changed and r1.previous_version is None
    m1 = json.loads(manifest_path(fixture_cfg).read_text())
    assert m1["index_version"] == r1.index_version
    assert m1["embedding_model"] == "hashing-256"
    assert set(m1["docs"]) == {"xps901", "letter_ai", "ai_adoption"}
    assert m1["total_chunks"] == sum(d["chunk_count"] for d in m1["docs"].values())
    assert all(len(d["sha256"]) == 64 for d in m1["docs"].values())

    r2 = ingest(fixture_cfg)
    assert set(r2.actions.values()) == {"unchanged"}
    assert not r2.changed
    assert r2.index_version == r1.index_version
    assert json.loads(manifest_path(fixture_cfg).read_text())["created_at"] == m1["created_at"]


def test_changed_file_gets_new_version(fixture_cfg: AppConfig) -> None:
    r1 = ingest(fixture_cfg)
    pdf = fixture_cfg.paths.raw_dir / "letter_ai.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"\n%changed\n")
    r2 = ingest(fixture_cfg)
    assert r2.actions["letter_ai"] == "updated"
    assert r2.actions["xps901"] == "unchanged"
    assert r2.index_version != r1.index_version
    assert r2.previous_version == r1.index_version


def test_sources_yaml_gets_hashes(fixture_cfg: AppConfig) -> None:
    ingest(fixture_cfg)
    assert 'sha256: ""' not in fixture_cfg.paths.sources_file.read_text()


def test_removed_doc_is_deleted(fixture_cfg: AppConfig) -> None:
    ingest(fixture_cfg)
    src = fixture_cfg.paths.sources_file
    text = src.read_text()
    start = text.index("  - id: ai_adoption")
    src.write_text(text[:start])
    r = ingest(fixture_cfg)
    assert r.actions["ai_adoption"] == "removed"
    ids = get_collection(fixture_cfg).get()["ids"]
    assert not any(i.startswith("ai_adoption:") for i in ids)
    assert {row["doc_id"] for row in load_chunk_rows(fixture_cfg)} == {"xps901", "letter_ai"}


def test_rebuild_is_idempotent(fixture_cfg: AppConfig, tmp_path: Path) -> None:
    r1 = ingest(fixture_cfg)
    rows1 = load_chunk_rows(fixture_cfg)
    r2 = ingest(fixture_cfg, force=True)
    rows2 = load_chunk_rows(fixture_cfg)
    assert r1.index_version == r2.index_version
    assert [(r["chunk_id"], r["text"]) for r in rows1] == [
        (r["chunk_id"], r["text"]) for r in rows2
    ]
    assert get_collection(fixture_cfg).count() == len(rows1)


def test_version_is_content_derived() -> None:
    a = compute_index_version("k", {"x": "1", "y": "2"})
    assert a == compute_index_version("k", {"y": "2", "x": "1"})
    assert a != compute_index_version("k", {"x": "1", "y": "3"})
    assert a != compute_index_version("k2", {"x": "1", "y": "2"})
