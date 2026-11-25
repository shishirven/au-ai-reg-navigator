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


def test_pdf_running_headers_and_page_numbers_removed_footnotes_kept_apart(tmp_path: Path) -> None:
    lines = parse_document(_pdf_with_running_header(tmp_path / "h.pdf"))
    body = [ln.text for ln in lines if not ln.footnote]
    notes = [ln for ln in lines if ln.footnote]
    assert not any("Synthetic Standard" in t for t in body + [n.text for n in notes])
    assert not any("footnote" in t for t in body)  # never mixed into body text
    assert body[0].startswith("1. Paragraph 1 must be kept")
    assert body[0].endswith("at all times.")  # wrapped continuation joined
    assert len(body) == 4
    # F-13: footnotes are kept, after the body, each labelled with its number (repeats per page)
    assert [n.footnote for n in notes] == ["1", "1~p2", "1~p3", "1~p4"]
    assert all(n.text == "a footnote in smaller type" for n in notes)
    assert lines[-1].footnote is not None


def test_unsupported_suffix(tmp_path: Path) -> None:
    p = tmp_path / "x.docx"
    p.write_text("x")
    try:
        parse_document(p)
    except ValueError as e:
        assert "unsupported" in str(e)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_marker_emitted_after_its_text_is_reordered(tmp_path: Path) -> None:
    """CPS 220 PDFs emit '28.' after the paragraph text in the same block; visual order wins."""
    doc = pymupdf.open()
    page = doc.new_page()
    # Insert text first, marker second, on the same baseline (as the CPS 220 PDF stream does).
    page.insert_text(
        (118, 300), "The risk appetite statement must, at a minimum, convey:", fontsize=10
    )
    page.insert_text((90, 300), "28.", fontsize=10)
    page.insert_text((118, 330), "Another paragraph without marker.", fontsize=10)
    path = tmp_path / "order.pdf"
    doc.save(str(path))
    texts = [ln.text for ln in parse_document(path)]
    assert texts[0] == "28. The risk appetite statement must, at a minimum, convey:"


# --------------------------------------------------------------------------- tables (F-13)


def _small_type_table(path: Path) -> Path:
    """A heading, then a two-column table set in 8pt under 12pt body text, with a wrapped
    first-column cell (the CPS 230 Attachment shape)."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (72, 100), "61. The internal audit function must review arrangements.", fontsize=12
    )
    page.insert_text((72, 140), "Attachment - Categories of exempt providers", fontsize=14)
    rows = [
        (170, "Regulators", ["Statutory authorities that supervise the", "financial system."]),
        (
            205,
            "Operators of clearing and",
            ["Entities that operate a licensed clearing", "facility under Part 7.3."],
        ),
        (240, "Central banks", ["Public authorities responsible for monetary policy."]),
    ]
    for y, cat, desc in rows:
        page.insert_text((80, y), cat, fontsize=8)
        for k, d in enumerate(desc):
            page.insert_text((220, y + 11 * k), d, fontsize=8)
    page.insert_text((80, 216), "settlement facilities", fontsize=8)  # wrapped first-column cell
    for k in range(12):  # enough 12pt body text to make 12pt the body size
        page.insert_text(
            (72, 300 + 14 * k), f"{62 + k}. Body paragraph {k} must be read.", fontsize=12
        )
    doc.save(str(path))
    return path


def test_small_type_table_becomes_rows_not_dropped(tmp_path: Path) -> None:
    lines = parse_document(_small_type_table(tmp_path / "t.pdf"))
    rows = [ln.text for ln in lines if ln.table]
    assert rows == [
        "Regulators | Statutory authorities that supervise the financial system.",
        "Operators of clearing and settlement facilities | Entities that operate a licensed "
        "clearing facility under Part 7.3.",
        "Central banks | Public authorities responsible for monetary policy.",
    ]
    heading = next(i for i, ln in enumerate(lines) if ln.kind == "heading")
    assert lines[heading + 1].table  # the rows sit under their heading, in reading order
    assert any(ln.text.startswith("62. Body paragraph 0") for ln in lines if not ln.table)


def test_bullets_beside_text_are_not_a_table(tmp_path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    for k in range(3):
        page.insert_text((80, 120 + 20 * k), "•", fontsize=8)
        page.insert_text(
            (100, 120 + 20 * k), f"key requirement number {k} in small type", fontsize=8
        )
    for k in range(12):
        page.insert_text((72, 300 + 14 * k), f"{k + 1}. Body paragraph {k}.", fontsize=12)
    path = tmp_path / "b.pdf"
    doc.save(str(path))
    assert not any(ln.table for ln in parse_document(path))


def test_markdown_pipe_table_rows_labelled_by_header() -> None:
    md = "# Checklist\n\n| Question | Considerations |\n| --- | --- |\n| Is it reliable? | Test it. |\n| Who can see inputs? | Check the terms. |\n\nAfter the table."
    lines = parse_markdown(md)
    rows = [ln.text for ln in lines if ln.table]
    assert rows == [
        "Question: Is it reliable?; Considerations: Test it.",
        "Question: Who can see inputs?; Considerations: Check the terms.",
    ]
    assert not any("---" in ln.text or "|" in ln.text for ln in lines)
    assert lines[-1].text == "After the table." and not lines[-1].table
