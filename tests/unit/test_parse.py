from pathlib import Path

import pymupdf

from regnav.ingest.parse import parse_document, parse_markdown, strip_provenance_header


def test_markdown_headings_lists_and_paragraphs() -> None:
    md = "# Title\n\nIntro line one\ncontinues here.\n\n## Section\n- first item\n- second **bold** item\n1. numbered\n"
    lines = parse_markdown(md)
    assert [(ln.kind, ln.text) for ln in lines] == [
        ("heading", "Title"),
        ("text", "Intro line one continues here."),
        ("heading", "Section"),
        ("text", "• first item"),
        ("text", "• second bold item"),
        ("text", "1. numbered"),
    ]
    assert lines[2].level == 2


def test_provenance_header_is_stripped() -> None:
    md = "# Doc\n\n- **Issuer:** X\n- **Retrieved:** today\n\n---\n\n# Real content\n\nBody."
    assert "Issuer" not in strip_provenance_header(md)
    assert [ln.text for ln in parse_markdown(md)] == ["Real content", "Body."]


def test_hard_wrapped_markdown_and_question_headings() -> None:
    md = (
        "Page 1\n\nFirst sentence ends here.\nSecond sentence starts here and\ncontinues.\n"
        "When does it apply?\nIt applies when:\n a thing happens\n"
    )
    lines = parse_markdown(md)
    assert [(ln.kind, ln.text) for ln in lines] == [
        ("text", "First sentence ends here."),
        ("text", "Second sentence starts here and continues."),
        ("heading", "When does it apply?"),
        ("text", "It applies when:"),
        ("text", "• a thing happens"),
    ]


def test_fixture_pdf_numbered_paragraphs_and_headings(fixture_raw_dir: Path) -> None:
    lines = parse_document(fixture_raw_dir / "xps901_operational_risk.pdf")
    headings = [ln.text for ln in lines if ln.kind == "heading"]
    assert headings[:3] == [
        "Prudential Standard XPS 901 Operational Risk Management",
        "Application",
        "Service provider management",
    ]
    texts = [ln.text for ln in lines if ln.kind == "text"]
    assert any(t.startswith("3. Before entering into") for t in texts)
    assert any(t.startswith("(b) assess the financial") for t in texts)
    assert any(t.startswith("7. This Prudential Standard commences") for t in texts)


def _pdf_with_running_header(path: Path) -> Path:
    doc = pymupdf.open()
    for i in range(4):
        page = doc.new_page()
        page.insert_text((50, 40), "Synthetic Standard July 2026", fontsize=10)
        page.insert_text((50, 200), f"{i + 1}.", fontsize=10)
        page.insert_text(
            (80, 200),
            f"Paragraph {i + 1} must be kept and the regulated entity must comply",
            fontsize=10,
        )
        page.insert_text((80, 220), "with this standard at all times.", fontsize=10)
        page.insert_text((300, 800), str(i + 1), fontsize=10)
        page.insert_text((50, 700), "1 a footnote in smaller type", fontsize=6)
    doc.save(str(path))
    return path


def test_pdf_running_headers_page_numbers_and_footnotes_removed(tmp_path: Path) -> None:
    lines = parse_document(_pdf_with_running_header(tmp_path / "h.pdf"))
    texts = [ln.text for ln in lines]
    assert not any("Synthetic Standard" in t for t in texts)
    assert not any("footnote" in t for t in texts)
    assert texts[0].startswith("1. Paragraph 1 must be kept")
    assert texts[0].endswith("at all times.")  # wrapped continuation joined
    assert len(texts) == 4


def test_unsupported_suffix(tmp_path: Path) -> None:
    p = tmp_path / "x.docx"
    p.write_text("x")
    try:
        parse_document(p)
    except ValueError as e:
        assert "unsupported" in str(e)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")
