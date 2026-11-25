from pathlib import Path

import pytest

from regnav.config import ChunkingConfig
from regnav.ingest.chunk import chunk_document, count_tokens, detect_structure, make_prefix
from regnav.ingest.load import SourceDoc
from regnav.ingest.parse import Line, parse_document


def _doc(structure: str = "numbered", tier: str = "binding") -> SourceDoc:
    return SourceDoc(
        id="xps",
        file="x.pdf",
        title="Synthetic Standard",
        short_name="XPS 1",
        issuer="APRA",
        tier=tier,  # type: ignore[arg-type]
        applies_to=["bank"],
        structure=structure,  # type: ignore[arg-type]
    )


H = lambda t: Line("heading", t)  # noqa: E731
T = lambda t: Line("text", t)  # noqa: E731

NUMBERED = [
    H("Service providers"),
    T(
        "1. An entity must maintain a comprehensive service provider management policy for all providers."
    ),
    T("2. Before entering into a material arrangement, an entity must:"),
    T("(a) undertake appropriate due diligence on the provider and its subcontractors;"),
    T("(b) assess the financial and non-financial risks of the arrangement; and"),
    T("(c) notify APRA within twenty business days of entering into the arrangement."),
    H("Governance"),
    T("3. The Board is ultimately accountable for the oversight of operational risk management."),
]


def test_numbered_paragraphs_split_with_subitems_kept_with_lead_in() -> None:
    chunks = chunk_document(NUMBERED, _doc(), ChunkingConfig(min_tokens=5))
    assert [c.chunk_id for c in chunks] == ["xps:p1", "xps:p2", "xps:p3"]
    p2 = chunks[1]
    assert p2.body.splitlines()[0].startswith("2. Before entering")
    assert [ln[:3] for ln in p2.body.splitlines()[1:]] == ["(a)", "(b)", "(c)"]
    assert p2.section == "Service providers" and p2.para == "2"
    assert chunks[2].section == "Governance"


def test_header_prefix() -> None:
    c = chunk_document(NUMBERED, _doc(), ChunkingConfig(min_tokens=5))[1]
    assert c.prefix == "[XPS 1 · Binding · Service providers · para 2]"
    assert c.text.startswith(c.prefix + "\n2. Before")
    assert make_prefix(_doc(tier="voluntary"), "Intro", None) == "[XPS 1 · Voluntary · Intro]"


def test_long_paragraph_split_at_subitems_repeats_lead_in() -> None:
    chunks = chunk_document(NUMBERED, _doc(), ChunkingConfig(min_tokens=5, max_tokens=40))
    parts = [c for c in chunks if c.chunk_id.startswith("xps:p2.")]
    assert len(parts) >= 2
    for part in parts:
        assert part.body.startswith(
            "2. Before entering into a material arrangement, an entity must:"
        )
        assert part.para == "2"
    # every sub-item appears exactly once across the pieces
    joined = "\n".join(p.body for p in parts)
    for marker in ("(a)", "(b)", "(c)"):
        assert joined.count(marker) == 1
    assert "part 1" in parts[0].prefix


def test_tiny_paragraphs_merged_within_section() -> None:
    lines = [H("S"), T("1. Short one."), T("2. Short two."), T("3. " + "word " * 40)]
    chunks = chunk_document(lines, _doc(), ChunkingConfig(min_tokens=10))
    assert chunks[0].chunk_id == "xps:p1-2"
    assert "Short one" in chunks[0].body and "Short two" in chunks[0].body
    assert chunks[0].para == "1-2"


def test_duplicate_paragraph_numbers_get_unique_ids() -> None:
    lines = [H("Main"), T("1. " + "a " * 30), H("Attachment A"), T("1. " + "b " * 30)]
    ids = [c.chunk_id for c in chunk_document(lines, _doc(), ChunkingConfig(min_tokens=5))]
    assert ids == ["xps:p1", "xps:p1~2"]


def test_heading_based_split_for_unnumbered_docs() -> None:
    lines = [
        H("Decide who is accountable"),
        T("Organisations should assign an accountable owner for each AI system."),
        T("Document the AI use case."),
        H("Test and monitor"),
        T("Organisations should test AI systems before deployment and monitor for drift."),
    ]
    chunks = chunk_document(lines, _doc("headings", "voluntary"), ChunkingConfig(min_tokens=5))
    assert [c.chunk_id for c in chunks] == ["xps:s001", "xps:s002"]
    assert chunks[0].section == "Decide who is accountable"
    assert "Document the AI use case." in chunks[0].body
    assert chunks[1].prefix == "[XPS 1 · Voluntary · Test and monitor]"


def test_consecutive_headings_form_section_path() -> None:
    lines = [
        H("Part A"),
        H("Sub 1"),
        T("Some text that is long enough to stand on its own as a chunk here."),
    ]
    c = chunk_document(lines, _doc("headings"), ChunkingConfig(min_tokens=5))[0]
    assert c.section == "Part A › Sub 1"


def test_auto_structure_detection() -> None:
    numbered = [T(f"{i}. para") for i in range(1, 20)]
    assert detect_structure(numbered) == "numbered"
    assert detect_structure([T("plain"), H("h")]) == "headings"


def test_chunking_is_deterministic(fixture_raw_dir: Path) -> None:
    lines = parse_document(fixture_raw_dir / "xps901_operational_risk.pdf")
    a = chunk_document(lines, _doc(), ChunkingConfig())
    b = chunk_document(lines, _doc(), ChunkingConfig())
    assert [(c.chunk_id, c.text) for c in a] == [(c.chunk_id, c.text) for c in b]


def test_fixture_binding_doc_chunks(fixture_raw_dir: Path) -> None:
    lines = parse_document(fixture_raw_dir / "xps901_operational_risk.pdf")
    chunks = chunk_document(lines, _doc(), ChunkingConfig())
    by_id = {c.chunk_id: c for c in chunks}
    assert "xps:p3" in by_id
    assert "(c) notify APRA" in by_id["xps:p3"].body
    assert by_id["xps:p3"].modality == "must"


@pytest.mark.parametrize("size,overlap", [(40, 8), (64, 16)])
def test_fixed_size_windows_overlap(size: int, overlap: int) -> None:
    lines = [H("S"), T(" ".join(f"w{i}" for i in range(200)))]
    cfg = ChunkingConfig(strategy="fixed", fixed_size=size, fixed_overlap=overlap)
    chunks = chunk_document(lines, _doc(), cfg)
    assert len(chunks) > 2
    assert all(count_tokens(c.body) <= size for c in chunks)
    first, second = chunks[0].body.split(), chunks[1].body.split()
    assert set(first) & set(second)  # windows overlap
    assert chunks[0].chunk_id == "xps:w0000"
    assert chunks[-1].body.split()[-1] == "w199"  # nothing dropped at the end


def test_footnotes_get_their_own_chunks_without_moving_other_ids() -> None:
    """F-13: footnotes are appended after the body, so adding them leaves every other id as is."""
    from regnav.ingest.parse import Line

    body = [
        Line("text", "1. An entity must do the first thing in full and on time.", 1),
        Line("text", "2. An entity must do the second thing in full and on time.", 1),
        Line("heading", "Attachment", 2),
        Line("text", "Category: Regulators; Description: Statutory authorities.", 2, table=True),
    ]
    notes = [
        Line(
            "text",
            "Material offshoring arrangement means a material arrangement offshore.",
            2,
            footnote="16",
        ),
        Line("text", "Refer to CPS 190.", 2, footnote="17"),
    ]
    doc = _doc()
    without = [c.chunk_id for c in chunk_document(body, doc, ChunkingConfig())]
    with_notes = chunk_document(body + notes, doc, ChunkingConfig())
    ids = [c.chunk_id for c in with_notes]
    assert ids[: len(without)] == without
    assert ids[len(without) :] == [f"{doc.id}:fn16", f"{doc.id}:fn17"]
    fn = with_notes[-2]
    assert fn.section == "Footnote 16" and fn.para is None
    assert "Footnote 16" in fn.text.split("\n")[0]  # the prefix names it for search and citation
    assert fn.body.startswith("Material offshoring arrangement means")
