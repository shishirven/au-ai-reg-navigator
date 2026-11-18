from pathlib import Path

import pytest
from pydantic import ValidationError

from regnav.ingest.load import SourceDoc, load_sources, resolve_and_hash, sha256_file, write_hashes


def test_load_fixture_sources(fixture_sources: Path) -> None:
    docs = load_sources(fixture_sources)
    assert [d.tier for d in docs] == ["binding", "expectation", "voluntary"]


def test_write_hashes_preserves_comments(tmp_path: Path) -> None:
    p = tmp_path / "s.yaml"
    p.write_text(
        '# keep me\ndocuments:\n  - id: a\n    file: a.pdf  # inline\n    sha256: ""\n  - id: b\n    sha256: ""\n'
    )
    assert write_hashes(p, {"a": "111", "b": "222"}) is True
    text = p.read_text()
    assert "# keep me" in text and "# inline" in text
    assert 'sha256: "111"' in text and 'sha256: "222"' in text
    assert write_hashes(p, {"a": "111", "b": "222"}) is False  # idempotent


def test_sha256_and_missing_file(
    tmp_path: Path, fixture_sources: Path, fixture_raw_dir: Path
) -> None:
    f = tmp_path / "x.txt"
    f.write_text("abc")
    assert sha256_file(f) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    docs = resolve_and_hash(load_sources(fixture_sources), fixture_raw_dir)
    assert all(len(d.sha256) == 64 for d in docs)
    with pytest.raises(FileNotFoundError):
        resolve_and_hash(load_sources(fixture_sources), tmp_path)


def test_validation_rules(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        SourceDoc(id="Bad-Id", file="x", title="t", issuer="i", tier="binding", applies_to=["bank"])
    with pytest.raises(ValidationError):
        SourceDoc(id="ok", file="x", title="t", issuer="i", tier="law", applies_to=["bank"])  # type: ignore[arg-type]
    p = tmp_path / "dup.yaml"
    p.write_text(
        "documents:\n"
        + "".join(
            "  - {id: a, file: x, title: t, issuer: i, tier: binding, applies_to: [bank]}\n"
            for _ in range(2)
        )
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_sources(p)


def test_metadata_fingerprint_changes_with_tier() -> None:
    a = SourceDoc(id="a", file="x", title="t", issuer="i", tier="binding", applies_to=["bank"])
    b = a.model_copy(update={"tier": "voluntary"})
    c = a.model_copy(update={"sha256": "zzz"})
    assert a.metadata_fingerprint() != b.metadata_fingerprint()
    assert a.metadata_fingerprint() == c.metadata_fingerprint()  # sha256 tracked separately
