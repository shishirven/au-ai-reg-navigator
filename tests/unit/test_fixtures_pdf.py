from pathlib import Path

import pymupdf


def test_fixture_pdfs_render(fixture_raw_dir: Path) -> None:
    pdfs = sorted(p.name for p in fixture_raw_dir.glob("*.pdf"))
    assert pdfs == ["ai_adoption_foundations.pdf", "letter_ai.pdf", "xps901_operational_risk.pdf"]
    with pymupdf.open(fixture_raw_dir / "xps901_operational_risk.pdf") as doc:
        text = "".join(page.get_text() for page in doc)
    assert "must not enter into a material arrangement" in text
