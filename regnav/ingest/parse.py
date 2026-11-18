"""Parse source documents (PDF via PyMuPDF, or Markdown) into logical lines.

Output is a flat list of :class:`Line`: headings and text lines, where each text line
is one logical paragraph or list item (``12. ...``, ``(a) ...``, ``• ...``) with PDF
line wrapping undone. Running headers/footers, footnotes, page numbers and (optionally)
shaded quote boxes are removed. Both formats produce the same representation, so the
chunker does not care where a document came from.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pymupdf

# A marker that starts a new logical line: numbered paragraph, (a)/(iv) sub-item,
# "a)" sub-item (CPG style), bullet or markdown list item.
PARA_RE = re.compile(r"^(\d{1,3})\.\s")
# Includes Wingdings/Symbol private-use bullets that survive PDF text extraction.
BULLETS = "•▪◦\uf0b7\uf0a7\uf076\uf0fc\uf0fb\uf0d8\u25cf\u2013\\-*"
MARKER_RE = re.compile(
    rf"^(\d{{1,3}}\.|\([a-z]{{1,4}}\)|\([ivx]{{1,5}}\)|[a-z]\)|[{BULLETS}])(\s|$)"
)
MARKER_ONLY_RE = re.compile(
    rf"^(\d{{1,3}}\.|\([a-z]{{1,4}}\)|\([ivx]{{1,5}}\)|[a-z]\)|[{BULLETS}])$"
)


@dataclass
class Line:
    kind: Literal["heading", "text"]
    text: str
    page: int = 1
    level: int = 1  # heading level (markdown #-count; PDFs use 1)


@dataclass
class _RawLine:
    text: str
    size: float
    bold: bool
    page: int
    block: int
    y0: float
    y1: float
    x0: float = 0.0
    in_margin: bool = False  # top/bottom 12% of the page (running header/footer zone)
    side_by_side: bool = False  # shares a row with another line (table cell)


def _clean(text: str) -> str:
    text = text.replace(" ", " ").replace("­", "")
    return re.sub(r"\s+", " ", text).strip()


def _join(a: str, b: str) -> str:
    """Join wrapped lines; undo line-end hyphenation inside compounds (APRA-\nregulated)."""
    if re.search(r"[A-Za-z]-$", a) and b[:1].isalpha():
        return _clean(a + b)
    return _clean(f"{a} {b}")


def _norm_for_repeat(text: str) -> str:
    return re.sub(r"\d+", "#", text.lower()).strip()


_BOLD_WORDS = ("bold", "medium", "semibold", "demi", "heavy", "black")


def _is_bold_span(span: dict) -> bool:
    font = span["font"].lower()
    return bool(span["flags"] & 16) or any(w in font for w in _BOLD_WORDS)


def _shaded_rects(page: pymupdf.Page) -> list[pymupdf.Rect]:
    """Light, non-white filled rectangles (e.g. CPG 'blue boxes')."""
    rects = []
    for d in page.get_drawings():
        fill = d.get("fill")
        if not fill or len(fill) != 3:
            continue
        r, g, b = fill
        light = min(r, g, b) > 0.75
        tinted = max(r, g, b) - min(r, g, b) > 0.03
        if light and tinted:
            rects.append(pymupdf.Rect(d["rect"]))
    return rects


def _in_any(rect: pymupdf.Rect, rects: list[pymupdf.Rect]) -> bool:
    cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
    return any(r.x0 - 2 <= cx <= r.x1 + 2 and r.y0 - 2 <= cy <= r.y1 + 2 for r in rects)


def _pdf_raw_lines(
    path: Path, start_page: int | None, end_page: int | None, drop_boxed_text: bool
) -> tuple[list[_RawLine], float, int]:
    raw: list[_RawLine] = []
    size_chars: Counter[float] = Counter()
    with pymupdf.open(str(path)) as doc:
        first = (start_page or 1) - 1
        last = min(end_page or doc.page_count, doc.page_count)
        n_pages = last - first
        for pno in range(first, last):
            page = doc[pno]
            height = page.rect.height
            boxes = _shaded_rects(page) if drop_boxed_text else []
            for bno, block in enumerate(page.get_text("dict")["blocks"]):
                for line in block.get("lines", []):
                    spans = [s for s in line["spans"] if s["text"].strip()]
                    if not spans:
                        continue
                    if boxes and _in_any(pymupdf.Rect(line["bbox"]), boxes):
                        continue
                    for s in spans:
                        size_chars[round(s["size"], 1)] += len(s["text"])
                    raw.append(
                        _RawLine(
                            text="",  # filled below once body size is known
                            size=max(s["size"] for s in spans),
                            bold=all(_is_bold_span(s) for s in spans),
                            page=pno + 1,
                            block=bno,
                            y0=line["bbox"][1],
                            y1=line["bbox"][3],
                            x0=line["bbox"][0],
                            in_margin=line["bbox"][1] < 0.12 * height
                            or line["bbox"][3] > 0.88 * height,
                        )
                    )
                    raw[-1].text = "\x00".join(f"{s['size']:.1f}\x01{s['text']}" for s in spans)
    body = size_chars.most_common(1)[0][0] if size_chars else 10.0
    # Drop small spans (footnotes, superscript footnote references, tiny headers).
    kept: list[_RawLine] = []
    for r in raw:
        parts = []
        for chunk in r.text.split("\x00"):
            size_s, text = chunk.split("\x01", 1)
            if float(size_s) >= body - 1.5:
                parts.append(text)
        text = _clean(" ".join(parts))
        if text:
            r.text = text
            r.size = max(r.size, body) if r.size >= body - 1.5 else r.size
            kept.append(r)
    return kept, body, n_pages


def _mark_side_by_side(lines: list[_RawLine]) -> None:
    """Flag lines that share a row with a non-marker line further right/left (table cells)."""
    by_page: dict[int, list[_RawLine]] = {}
    for ln in lines:
        by_page.setdefault(ln.page, []).append(ln)
    for page_lines in by_page.values():
        for a in page_lines:
            for b in page_lines:
                if a is b or abs(a.y0 - b.y0) > 2 or abs(a.x0 - b.x0) < 20:
                    continue
                a_text, b_text = a.text, b.text
                # A paragraph marker sitting left of its text is not a table.
                if MARKER_ONLY_RE.match(b_text) or MARKER_ONLY_RE.match(a_text):
                    continue
                a.side_by_side = True
                break


def _drop_repeated(lines: list[_RawLine], n_pages: int) -> list[_RawLine]:
    """Remove running headers/footers: short lines that recur on many pages."""
    if n_pages < 3:
        return [ln for ln in lines if not re.fullmatch(r"\d{1,3}", ln.text)]
    pages_with: dict[str, set[int]] = {}
    for ln in lines:
        pages_with.setdefault(_norm_for_repeat(ln.text), set()).add(ln.page)
    threshold = max(3, int(0.4 * n_pages))
    out = []
    for ln in lines:
        key = _norm_for_repeat(ln.text)
        if (
            ln.in_margin
            and len(ln.text) < 100
            and len(pages_with[key]) >= threshold
            and not MARKER_ONLY_RE.match(ln.text)
        ):
            continue
        if re.fullmatch(r"\d{1,3}", ln.text) and ln.in_margin:
            continue
        out.append(ln)
    return out


def _is_heading(ln: _RawLine, body: float) -> bool:
    text = ln.text
    if MARKER_RE.match(text) or len(text) > 150 or text.endswith((";", ",")):
        return False
    if not re.search(r"[A-Za-z]{3}", text):
        return False
    if ln.size >= body + 1.5:  # strong heading: clearly larger font
        return True
    if ln.size >= body + 0.9 and len(text) <= 80 and not text.endswith("."):
        return True  # sub-heading one point above body size (e.g. CPS 230 13pt italics)
    # Weak heading: bold at body size - but not a bold cell in a table row.
    return ln.bold and ln.size >= body - 0.5 and not ln.side_by_side


def _starts_new_line(text: str, prev: str | None) -> bool:
    if prev is None or MARKER_RE.match(text):
        return True
    # Continuation if previous line is unfinished and this one starts lower-case.
    return not (not re.search(r"[.;:!?]$", prev) and text[:1].islower())


def parse_pdf(
    path: Path,
    start_page: int | None = None,
    end_page: int | None = None,
    drop_boxed_text: bool = False,
) -> list[Line]:
    raw, body, n_pages = _pdf_raw_lines(path, start_page, end_page, drop_boxed_text)
    raw = _drop_repeated(raw, n_pages)
    _mark_side_by_side(raw)
    out: list[Line] = []
    pending_marker: str | None = None
    prev: _RawLine | None = None
    for ln in raw:
        text = ln.text
        if _is_heading(ln, body) and pending_marker is None:
            if (
                out
                and out[-1].kind == "heading"
                and prev is not None
                and prev.page == ln.page
                and (ln.y0 - prev.y1) < ln.size
            ):
                out[-1].text = _clean(f"{out[-1].text} {text}")  # multi-line heading
            else:
                out.append(Line("heading", text, ln.page))
            prev = ln
            continue
        if MARKER_ONLY_RE.match(text):
            pending_marker = text
            prev = ln
            continue
        if pending_marker is not None:
            text = f"{pending_marker} {text}"
            pending_marker = None
            out.append(Line("text", text, ln.page))
        elif (
            out
            and out[-1].kind == "text"
            and (
                (
                    prev is not None
                    and ln.block == prev.block
                    and ln.page == prev.page
                    and not MARKER_RE.match(text)
                )
                or not _starts_new_line(text, out[-1].text)
            )
        ):
            out[-1].text = _join(out[-1].text, text)
        else:
            out.append(Line("text", text, ln.page))
        prev = ln
    return out


# --------------------------------------------------------------------------- markdown

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_LIST = re.compile(r"^(\s*)([-*+•]|\d{1,3}\.)\s+")


def _md_inline(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links -> text
    text = re.sub(r"(\*\*|__|\*|_)(\S(?:.*?\S)?)\1", r"\2", text)  # emphasis
    text = text.replace("`", "")
    return _clean(text)


def strip_provenance_header(text: str) -> str:
    """Our saved web pages start with a provenance block (issuer, URL, retrieved date)
    ending in a ``---`` rule. It is metadata, not regulatory content."""
    head = text[:4000]
    if "**Issuer:**" in head or "**Official source:**" in head:
        m = re.search(r"^---\s*$", text, flags=re.M)
        if m:
            return text[m.end() :]
    return text


def _looks_like_question_heading(line: str, para: list[str]) -> bool:
    """Short question lines in PDF-derived markdown act as sub-headings
    ("When does the transparency obligation apply?")."""
    return (
        not para
        and len(line) <= 90
        and line.endswith("?")
        and line[:1].isupper()
        and not MARKER_RE.match(line)
    )


def parse_markdown(text: str) -> list[Line]:
    text = strip_provenance_header(text)
    out: list[Line] = []
    para: list[str] = []
    page = 1

    def flush() -> None:
        if para:
            joined = _md_inline(" ".join(para))
            if joined:
                out.append(Line("text", joined, page))
            para.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        m_page = re.fullmatch(r"Page (\d+)", stripped)
        if m_page:
            flush()
            page = int(m_page.group(1))
            continue
        if not stripped or re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            flush()
            continue
        m = _MD_HEADING.match(stripped)
        if m:
            flush()
            heading = _md_inline(m.group(2))
            if heading:
                out.append(Line("heading", heading, page, level=len(m.group(1))))
            continue
        if _MD_LIST.match(line) or MARKER_RE.match(stripped):
            flush()
            stripped = re.sub(rf"^[{BULLETS}+]\s*", "• ", stripped)
        elif para and re.search(r"[.!?:]$", para[-1]) and stripped[:1].isupper():
            # Hard-wrapped text (PDF extracted to markdown): a line that ends a
            # sentence followed by a capitalised line starts a new logical line.
            flush()
        if _looks_like_question_heading(stripped, para):
            flush()
            out.append(Line("heading", _md_inline(stripped), page, level=5))
            continue
        para.append(stripped)
    flush()
    return out


def parse_document(
    path: Path,
    start_page: int | None = None,
    end_page: int | None = None,
    drop_boxed_text: bool = False,
) -> list[Line]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path, start_page, end_page, drop_boxed_text)
    if suffix in {".md", ".markdown", ".txt"}:
        return parse_markdown(path.read_text(encoding="utf-8"))
    raise ValueError(f"unsupported file type: {path}")
