import pytest

from regnav.ingest.chunk import Chunk
from regnav.ingest.load import SourceDoc
from regnav.ingest.tag import chunk_metadata, classify_modality


@pytest.mark.parametrize(
    "text,expected",
    [
        ("An APRA-regulated entity must maintain a policy.", "must"),
        ("An entity must not rely on a service provider unless...", "must"),
        ("The Board shall approve the plan.", "must"),
        ("Entities are required to notify APRA within 72 hours.", "must"),
        ("It is mandatory to keep records.", "must"),
        ("Organisations should consider telling people when AI is used.", "should"),
        ("APRA expects boards to maintain sufficient understanding of AI.", "should"),
        ("APRA envisages that the data architecture would align.", "should"),
        ("A prudent entity would start with its critical operations.", "should"),
        ("The OAIC recommends that organisations do not enter personal information.", "should"),
        ("This is better practice for most entities.", "should"),
        ("Entities are encouraged to adopt the guidance.", "should"),
        ("An entity is not required to notify APRA of minor changes.", "info"),
        ("An entity need not repeat the assessment.", "info"),
        ("Material arrangements are those on which an entity relies.", "info"),
        ("This Prudential Standard commences on 1 July 2026.", "info"),
        ("Entities should ensure X. The entity must also do Y.", "must"),  # strongest wins
        ("MUST in capitals still counts.", "must"),
        ("A mustard seed is not an obligation.", "info"),  # word boundary
    ],
)
def test_classify_modality(text: str, expected: str) -> None:
    assert classify_modality(text) == expected


def test_metadata_is_flat_and_scalar() -> None:
    doc = SourceDoc(
        id="d1",
        file="d.pdf",
        title="T",
        issuer="I",
        tier="binding",
        applies_to=["bank", "super"],
        sha256="abc",
    )
    chunk = Chunk(
        "d1:p1", "d1", "body", "Sec", "1", 3, 0, prefix="[x]", modality="must", n_tokens=5
    )
    meta = chunk_metadata(chunk, doc, index_version="idx-1")
    assert all(isinstance(v, (str, int, float, bool)) for v in meta.values())
    assert meta["applies_bank"] is True and meta["applies_super"] is True
    assert meta["applies_insurer"] is False and meta["applies_any_business"] is False
    assert meta["tier"] == "binding" and meta["modality"] == "must" and meta["para"] == "1"
    assert meta["index_version"] == "idx-1"


def test_metadata_none_para_becomes_empty_string() -> None:
    doc = SourceDoc(
        id="d1", file="d.md", title="T", issuer="I", tier="voluntary", applies_to=["any_business"]
    )
    chunk = Chunk("d1:s001", "d1", "body", "", None, 1, 0)
    meta = chunk_metadata(chunk, doc)
    assert meta["para"] == "" and meta["section"] == "" and meta["applies_any_business"] is True
