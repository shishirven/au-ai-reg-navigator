"""Deep links from citations to the cited place in the source."""

from __future__ import annotations

from regnav import links
from regnav.links import citation_url


def _files(monkeypatch, mapping: dict[str, str]) -> None:
    monkeypatch.setattr(links, "_source_files", lambda path=None: mapping)


def test_pdf_source_links_to_page(monkeypatch) -> None:
    _files(monkeypatch, {"apra_cps230_2026": "apra_cps230_2026-07.pdf"})
    meta = {
        "doc_id": "apra_cps230_2026",
        "page": 14,
        "url": "https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf",
    }
    assert citation_url(meta, "x").endswith("/text/original/pdf#page=14")


def test_pdf_url_without_parsed_pdf_has_no_page(monkeypatch) -> None:
    # we hold a Markdown copy of this PDF: page numbers would be wrong, so link the document
    _files(monkeypatch, {"naic_ai6_foundations": "naic_ai6.md"})
    meta = {"doc_id": "naic_ai6_foundations", "page": 1, "url": "https://x.gov.au/ai6.pdf"}
    assert citation_url(meta, "x") == "https://x.gov.au/ai6.pdf"


def test_web_page_gets_text_fragment_from_passage_body(monkeypatch) -> None:
    _files(monkeypatch, {"oaic": "oaic.md"})
    meta = {"doc_id": "oaic", "url": "https://www.oaic.gov.au/guidance#old"}
    text = "[OAIC AI products guidance · Regulator expectation · Tips]\n• Carefully review the terms and settings of any AI product."
    url = citation_url(meta, text)
    assert (
        url
        == "https://www.oaic.gov.au/guidance#:~:text=Carefully%20review%20the%20terms%20and%20settings"
    )


def test_numbered_paragraph_prefix_is_skipped_and_short_text_falls_back(monkeypatch) -> None:
    _files(monkeypatch, {"d": "d.md"})
    meta = {"doc_id": "d", "url": "https://example.gov.au/page"}
    assert "#:~:text=APRA%20expects%20an%20entity" in citation_url(
        meta, "[D]\n52. APRA expects an entity to do things."
    )
    assert citation_url(meta, "[D]\nShort.") == "https://example.gov.au/page"


def test_no_url_no_link(monkeypatch) -> None:
    _files(monkeypatch, {})
    assert citation_url({"doc_id": "d"}, "text") == ""
