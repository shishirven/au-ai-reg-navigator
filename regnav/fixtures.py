"""Render the plain-text fixture corpus to real PDFs.

Fixture docs are kept as readable ``.txt`` in ``tests/fixtures/`` and rendered to PDF at
test time so that the *real* PyMuPDF parsing path (font-size heading detection etc.)
is exercised end-to-end. Format: ``# `` lines are headings (rendered larger + bold),
every other non-empty line is a body paragraph.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

PAGE_W, PAGE_H = 595, 842  # A4 points
MARGIN = 56
BODY_SIZE = 10.0
HEADING_SIZE = 14.0


def text_to_pdf(text: str, out_path: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    y: float = MARGIN
    width = PAGE_W - 2 * MARGIN
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        is_heading = line.startswith("# ")
        content = line[2:] if is_heading else line
        size = HEADING_SIZE if is_heading else BODY_SIZE
        font = "hebo" if is_heading else "helv"
        # Estimate wrapped height; start a new page if needed.
        chars_per_line = max(1, int(width / (size * 0.5)))
        n_lines = max(1, -(-len(content) // chars_per_line))
        height = n_lines * size * 1.5 + 6
        if y + height > PAGE_H - MARGIN:
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            y = MARGIN
        rect = pymupdf.Rect(MARGIN, y, PAGE_W - MARGIN, y + height + size)
        page.insert_textbox(rect, content, fontsize=size, fontname=font)
        y += height + (8 if is_heading else 4)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    doc.close()
    return out_path


def build_fixture_pdfs(src_dir: Path, out_dir: Path) -> list[Path]:
    """Render every ``*.txt`` in ``src_dir`` to ``out_dir/<stem>.pdf``."""
    return [
        text_to_pdf(p.read_text(), out_dir / f"{p.stem}.pdf") for p in sorted(src_dir.glob("*.txt"))
    ]
