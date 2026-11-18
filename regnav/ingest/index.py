"""Build / update the persistent Chroma index with change detection.

Each source doc has a fingerprint = sha256(file) + hash(its sources.yaml metadata).
On ingest:
  * unchanged docs are skipped (their chunks stay in the index);
  * new or changed docs are re-parsed, re-chunked, re-embedded and replaced;
  * docs removed from sources.yaml are deleted from the index.
If anything changed, a new ``index_version`` is written to the manifest. The version id
is derived from the content (index key + all doc fingerprints), so rebuilding identical
inputs yields the identical version (idempotent).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chromadb

from regnav.config import AppConfig
from regnav.ingest.chunk import Chunk, chunk_document
from regnav.ingest.embed import get_embedder
from regnav.ingest.load import SourceDoc, load_sources, resolve_and_hash, write_hashes
from regnav.ingest.parse import parse_document
from regnav.ingest.tag import chunk_metadata

log = logging.getLogger(__name__)


def collection_name(cfg: AppConfig) -> str:
    return f"regnav_{cfg.index_key()}"


def manifest_path(cfg: AppConfig) -> Path:
    return cfg.paths.chroma_dir / f"index_manifest_{collection_name(cfg)}.json"


def chunks_path(cfg: AppConfig) -> Path:
    return cfg.paths.chroma_dir / f"chunks_{collection_name(cfg)}.jsonl"


_CODE_FILES = ("load.py", "parse.py", "chunk.py", "tag.py")


def ingest_code_hash() -> str:
    """Hash of the parsing/chunking/tagging code: changing the pipeline invalidates chunks
    exactly like changing a source file does (change management)."""
    here = Path(__file__).parent
    h = hashlib.sha256()
    for name in _CODE_FILES:
        h.update((here / name).read_bytes())
    return h.hexdigest()[:12]


def doc_fingerprint(doc: SourceDoc) -> str:
    return f"{doc.sha256}:{doc.metadata_fingerprint()}:{ingest_code_hash()}"


def compute_index_version(index_key: str, fingerprints: dict[str, str]) -> str:
    payload = json.dumps({"index_key": index_key, "docs": fingerprints}, sort_keys=True)
    return "idx-" + hashlib.sha256(payload.encode()).hexdigest()[:12]


def load_manifest(cfg: AppConfig) -> dict[str, Any] | None:
    path = manifest_path(cfg)
    return json.loads(path.read_text()) if path.exists() else None


def get_client(cfg: AppConfig) -> chromadb.ClientAPI:
    cfg.paths.chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(cfg.paths.chroma_dir), settings=chromadb.Settings(anonymized_telemetry=False)
    )


def get_collection(cfg: AppConfig, client: chromadb.ClientAPI | None = None):
    client = client or get_client(cfg)
    return client.get_or_create_collection(
        collection_name(cfg), metadata={"hnsw:space": "cosine"}, embedding_function=None
    )


@dataclass
class IngestReport:
    index_version: str
    previous_version: str | None
    changed: bool
    actions: dict[str, str] = field(
        default_factory=dict
    )  # doc_id -> added|updated|unchanged|removed
    chunk_counts: dict[str, int] = field(default_factory=dict)


def build_chunks(doc: SourceDoc, raw_dir: Path, cfg: AppConfig) -> list[Chunk]:
    lines = parse_document(raw_dir / doc.file, doc.start_page, doc.end_page, doc.drop_boxed_text)
    return chunk_document(lines, doc, cfg.chunking)


def ingest(cfg: AppConfig, *, force: bool = False, write_sources: bool = True) -> IngestReport:
    docs = resolve_and_hash(load_sources(cfg.paths.sources_file), cfg.paths.raw_dir)
    if write_sources:
        write_hashes(cfg.paths.sources_file, {d.id: d.sha256 for d in docs})
    fingerprints = {d.id: doc_fingerprint(d) for d in docs}
    new_version = compute_index_version(cfg.index_key(), fingerprints)

    manifest = load_manifest(cfg)
    old_docs: dict[str, Any] = (manifest or {}).get("docs", {})
    collection = get_collection(cfg)
    embedder = get_embedder(cfg.embedding)

    report = IngestReport(
        index_version=new_version,
        previous_version=(manifest or {}).get("index_version"),
        changed=False,
    )
    for doc_id in sorted(set(old_docs) - set(fingerprints)):
        collection.delete(where={"doc_id": doc_id})
        report.actions[doc_id] = "removed"

    for doc in docs:
        prev = old_docs.get(doc.id)
        unchanged = prev is not None and prev.get("fingerprint") == fingerprints[doc.id]
        if prev is not None and unchanged and not force and collection.count() > 0:
            report.actions[doc.id] = "unchanged"
            report.chunk_counts[doc.id] = prev["chunk_count"]
            continue
        chunks = build_chunks(doc, cfg.paths.raw_dir, cfg)
        collection.delete(where={"doc_id": doc.id})
        if chunks:
            vectors = embedder.embed_documents([c.text for c in chunks])
            for i in range(0, len(chunks), 500):
                batch = chunks[i : i + 500]
                collection.add(
                    ids=[c.chunk_id for c in batch],
                    documents=[c.text for c in batch],
                    embeddings=vectors[i : i + 500].tolist(),
                    metadatas=[chunk_metadata(c, doc) for c in batch],  # type: ignore[misc]
                )
        report.actions[doc.id] = "updated" if prev else "added"
        report.chunk_counts[doc.id] = len(chunks)
        log.info("indexed %s: %d chunks", doc.id, len(chunks))

    report.changed = any(a != "unchanged" for a in report.actions.values()) or manifest is None
    if report.changed or force:
        _write_outputs(cfg, docs, fingerprints, report, embedder.name)
    return report


def _write_outputs(cfg, docs, fingerprints, report: IngestReport, embedder_name: str) -> None:
    collection = get_collection(cfg)
    got = collection.get(include=["documents", "metadatas"])
    rows = sorted(
        (
            {"chunk_id": cid, "text": text, **meta}
            for cid, text, meta in zip(got["ids"], got["documents"], got["metadatas"], strict=True)
        ),
        key=lambda r: (r["doc_id"], r["ordinal"]),
    )
    path = chunks_path(cfg)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    manifest = {
        "index_version": report.index_version,
        "previous_version": report.previous_version,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "collection": collection_name(cfg),
        "index_key": cfg.index_key(),
        "embedding_model": embedder_name,
        "ingest_code_hash": ingest_code_hash(),
        "embedding": cfg.embedding.model_dump(),
        "chunking": cfg.chunking.model_dump(),
        "total_chunks": len(rows),
        "docs": {
            d.id: {
                "file": d.file,
                "sha256": d.sha256,
                "fingerprint": fingerprints[d.id],
                "tier": d.tier,
                "status": d.status,
                "chunk_count": sum(1 for r in rows if r["doc_id"] == d.id),
            }
            for d in docs
        },
    }
    manifest_path(cfg).write_text(json.dumps(manifest, indent=2) + "\n")


def load_chunk_rows(cfg: AppConfig) -> list[dict[str, Any]]:
    path = chunks_path(cfg)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run `make ingest` first")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
