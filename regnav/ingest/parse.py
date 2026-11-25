"""Parse source documents (PDF via PyMuPDF, or Markdown) into logical lines.

Output is a flat list of :class:`Line`: headings and text lines, where each text line
is one logical paragraph or list item (``12. ...``, ``(a) ...``, ``• ...``) with PDF
line wrapping undone. Running headers/footers, page numbers and (optionally) shaded quote
boxes are removed. Both formats produce the same representation, so the chunker does not care
where a document came from.

Tables and footnotes (F-13, D-059) are kept, not dropped:
* **Tables** become one line per row, labelled with the column headers ("Category: Regulators;
  Description: Statutory authorities ..."), flagged ``table=True``. PDF tables are found where
  PyMuPDF detects a ruled table *or* where small-type text sits in aligned columns; the cell text
  comes from the parser's own lines (PyMuPDF's table extractor drops spaces in some files).
  Markdown pipe tables are converted the same way.
* **Footnotes** (a small superscript number, then smaller text in the lower part of the page)
  become separate lines flagged ``footnote="16"``, emitted after the body so the ids of existing
  chunks don't move. They often carry definitions ("Material offshoring arrangement means ...").
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
    table: bool = False  # one row of a table, cells labelled by column header
    footnote: str | None = None  # footnote number; the chunker gives it its own chunk


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
    x1: float = 0.0
    rel_y: float = 0.0  # y0 / page height
    spans: list[tuple[float, str]] | None = None  # (size, text) of every span, incl. small ones
    full_text: str = ""  # all spans, before small-type filtering
    table_rows: list[str] | None = None  # set on a placeholder line that stands for a table
    fn: str | None = None  # footnote number, on a line that holds a whole footnote

    def in_margin_header(self) -> bool:
        return self.in_margin and self.rel_y < 0.12


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
                # Some PDFs (e.g. CPS 220) emit a paragraph marker after its text; restore
                # visual order within the block: top-to-bottom rows, then left-to-right.
                block_lines = sorted(
                    block.get("lines", []), key=lambda ln: (round(ln["bbox"][1] / 3), ln["bbox"][0])
                )
                for line in block_lines:
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
                            x1=line["bbox"][2],
                            rel_y=line["bbox"][1] / height,
                            in_margin=line["bbox"][1] < 0.12 * height
                            or line["bbox"][3] > 0.88 * height,
                            spans=[(float(s["size"]), s["text"]) for s in spans],
                        )
                    )
                    raw[-1].text = "\x00".join(f"{s['size']:.1f}\x01{s['text']}" for s in spans)
        table_boxes = _ruled_tables(path, first, last)
    body = size_chars.most_common(1)[0][0] if size_chars else 10.0
    for r in raw:
        r.full_text = _clean(" ".join(t for _, t in (r.spans or [])))
    # Footnotes and tables first, from the unfiltered lines; they are often set in small type.
    footnotes, raw = _extract_footnotes(raw, body)
    raw = _extract_tables(raw, body, table_boxes)
    # Then drop small spans (superscript footnote references, tiny headers) from the rest.
    kept: list[_RawLine] = list(footnotes)
    for r in raw:
        if r.table_rows is not None:
            kept.append(r)
            continue
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


# --------------------------------------------------------------------------- tables, footnotes

_FN_START = re.compile(r"^(\d{1,3})(?:\s+|\t)(\S.*)$")


_RUNNING = re.compile(
    r"Authorised Version \S+ registered \d{2}/\d{2}/\d{4}|^APRA\s+\w+ \d{4}$|^\w+ \d{4}$"
)


def _is_running_text(r: _RawLine) -> bool:
    """Page headers and footers: top margin, or margin text that reads like a running footer."""
    if r.in_margin and r.rel_y < 0.12:
        return True
    return r.in_margin and bool(_RUNNING.search(r.full_text or r.text))


def _ruled_tables(path: Path, first: int, last: int) -> dict[int, list[pymupdf.Rect]]:
    """Bounding boxes of tables PyMuPDF detects from ruling lines, by page number (1-based)."""
    out: dict[int, list[pymupdf.Rect]] = {}
    with pymupdf.open(str(path)) as doc:
        for pno in range(first, last):
            try:
                found = doc[pno].find_tables().tables
            except Exception:
                continue
            rects = []
            for tb in found:
                rows = tb.extract()
                if len(rows) >= 2 and max((len(r) for r in rows), default=0) >= 2:
                    rects.append(pymupdf.Rect(tb.bbox))
            if rects:
                out[pno + 1] = rects
    return out


def _extract_footnotes(raw: list[_RawLine], body: float) -> tuple[list[_RawLine], list[_RawLine]]:
    """Split off footnotes: in the lower part of a page, a small number (superscript or the start
    of a small-type line) followed by small-type text. Returns (footnote lines, other lines)."""
    small = body - 1.0
    notes: list[_RawLine] = []
    rest: list[_RawLine] = []
    cur: _RawLine | None = None
    pending_num: tuple[int, float, str] | None = None  # (page, y0, number) of a lone marker
    for r in raw:
        spans = r.spans or []
        low = r.rel_y > 0.5 and r.size < small
        text = r.full_text
        lone = re.fullmatch(r"\d{1,3}", text)
        if low and lone and r.size <= body - 2.5:
            pending_num = (r.page, r.y0, text)
            cur = None
            continue
        if low and pending_num and pending_num[0] == r.page and abs(pending_num[1] - r.y0) < 4:
            cur = _RawLine(
                text, r.size, False, r.page, r.block, r.y0, r.y1, r.x0, fn=pending_num[2]
            )
            notes.append(cur)
            pending_num = None
            continue
        m = _FN_START.match(text)
        first_small = bool(spans) and spans[0][0] < small
        if low and m and first_small and not r.side_by_side:
            cur = _RawLine(
                m.group(2), r.size, False, r.page, r.block, r.y0, r.y1, r.x0, fn=m.group(1)
            )
            notes.append(cur)
            continue
        if low and cur is not None and cur.page == r.page and not _is_running_text(r):
            cur.text = _join(cur.text, text)
            continue
        if r.page != (cur.page if cur else r.page) or not low:
            cur = None
        rest.append(r)
    for n in notes:
        n.text = _clean(n.text)
    return notes, rest


def _extract_tables(
    raw: list[_RawLine], body: float, ruled: dict[int, list[pymupdf.Rect]]
) -> list[_RawLine]:
    """Replace the lines of each table with one placeholder line carrying its rows."""
    _mark_side_by_side_all(raw)
    by_page: dict[int, list[int]] = {}
    for i, r in enumerate(raw):
        by_page.setdefault(r.page, []).append(i)
    consumed: set[int] = set()
    placeholders: dict[int, _RawLine] = {}
    for page, idxs in by_page.items():
        regions = [pymupdf.Rect(b) for b in ruled.get(page, [])]
        # Small-type text in aligned columns is a table even without ruling lines.
        cells = [raw[i] for i in idxs if raw[i].side_by_side and raw[i].size < body - 1.5]
        if len(cells) >= 2:
            regions.append(
                pymupdf.Rect(
                    min(c.x0 for c in cells) - 2,
                    min(c.y0 for c in cells) - 2,
                    max(c.x1 for c in cells) + 2,
                    max(c.y1 for c in cells) + 2,
                )
            )
        regions = _merge_rects(regions)
        for reg in regions:
            members = [
                i
                for i in idxs
                if i not in consumed
                and reg.contains(
                    pymupdf.Point((raw[i].x0 + raw[i].x1) / 2, (raw[i].y0 + raw[i].y1) / 2)
                )
                and not _is_running_text(raw[i])
            ]
            # Grow down: small-type continuation lines just below the region (wrapped cells).
            if members:
                bottom = max(raw[i].y1 for i in members)
                for i in idxs:
                    r = raw[i]
                    if i in consumed or i in members:
                        continue
                    if (
                        r.size < body - 1.5
                        and 0 <= r.y0 - bottom < 16
                        and reg.x0 - 2 <= r.x0 <= reg.x1
                    ):
                        members.append(i)
                        bottom = max(bottom, r.y1)
            rows = _table_rows([raw[i] for i in sorted(members)], body)
            if len(rows) < 1 or len(members) < 2:
                continue
            first = min(members)
            consumed.update(members)
            ph = raw[first]
            placeholders[first] = _RawLine(
                "", body, False, ph.page, ph.block, ph.y0, ph.y1, ph.x0, table_rows=rows
            )
    out: list[_RawLine] = []
    for i, r in enumerate(raw):
        r.side_by_side = False  # recomputed on clean text by parse_pdf
        if i in placeholders:
            out.append(placeholders[i])
        if i not in consumed:
            out.append(r)
    return out


def _merge_rects(rects: list[pymupdf.Rect]) -> list[pymupdf.Rect]:
    out: list[pymupdf.Rect] = []
    for r in rects:
        for o in out:
            if o.intersects(r):
                o |= r
                break
        else:
            out.append(pymupdf.Rect(r))
    return out


def _is_marker_cell(text: str) -> bool:
    """A bullet, dash or list marker on its own (any symbol font's rendering of a bullet)."""
    return not text or bool(MARKER_ONLY_RE.match(text)) or bool(re.fullmatch(r"[^\w\s]{1,2}", text))


def _cell_text(line: _RawLine, body: float) -> str:
    # Drop superscript footnote references inside cells ("Notifications to APRA2").
    parts = [
        t
        for s, t in (line.spans or [])
        if not (s <= body - 3 and re.fullmatch(r"\s*\d{1,3}\s*", t))
    ]
    return _clean(" ".join(parts))


def _table_rows(lines: list[_RawLine], body: float) -> list[str]:
    """Rebuild rows from positioned lines: columns from x positions, a new row wherever two or
    more columns start on the same line; wrapped lines join the cell above them."""
    if not lines:
        return []
    xs = sorted({round(ln.x0) for ln in lines})
    cols: list[float] = []
    for x in xs:
        if not cols or x - cols[-1] > 12:
            cols.append(x)

    def col_of(ln: _RawLine) -> int:
        return max(i for i, c in enumerate(cols) if c <= ln.x0 + 12) if ln.x0 + 12 >= cols[0] else 0

    lines = sorted(lines, key=lambda ln: (ln.y0, ln.x0))

    # A table needs two columns with real content (not a column of bullets or markers).
    def has_partner(ln: _RawLine) -> bool:
        return any(o is not ln and abs(o.y0 - ln.y0) < 3 and col_of(o) != col_of(ln) for o in lines)

    # A table needs two columns of real content side by side (not bullets beside text, nor a
    # caption above one column).
    real_cols = {
        col_of(ln) for ln in lines if has_partner(ln) and not _is_marker_cell(_cell_text(ln, body))
    }
    if len(real_cols) < 2:
        return []
    # Typical line spacing inside a cell; a new row needs a bigger gap above it in its column,
    # so a wrapped first-column cell ("Operators of clearing and settlement / facilities")
    # stays one row.
    prev_in_col: dict[int, float] = {}
    gaps: list[float] = []
    for ln in lines:
        c = col_of(ln)
        if c in prev_in_col and 0 < ln.y0 - prev_in_col[c] < 3 * body:
            gaps.append(ln.y0 - prev_in_col[c])
        prev_in_col[c] = ln.y0
    spacing = sorted(gaps)[len(gaps) // 2] if gaps else body * 1.2
    last_in_col: dict[int, _RawLine] = {}
    anchors: list[float] = []
    for ln in lines:
        c = col_of(ln)
        partners = [o for o in lines if o is not ln and abs(o.y0 - ln.y0) < 3 and col_of(o) != c]
        prev = last_in_col.get(c)
        row_lines = [ln, *partners]
        # A new row: a clear gap above it, or a bold header line ending, or every cell on the
        # line starting like a new entry (capital or digit) rather than a wrapped continuation.
        fresh = (
            prev is None
            or ln.y0 - prev.y0 > spacing * 1.15
            or (prev.bold and not ln.bold)
            or all(re.match(r"[A-Z0-9(]", _cell_text(o, body) or "a") for o in row_lines)
        )
        if partners and fresh and not any(abs(a - ln.y0) < 3 for a in anchors):
            anchors.append(ln.y0)
        last_in_col[c] = ln
    anchors.sort()
    rows: list[dict[int, list[str]]] = []
    bold_rows: list[bool] = []
    row_of_anchor: dict[float, int] = {}
    caption: list[str] = []
    for ln in lines:
        text = _cell_text(ln, body)
        if not text:
            continue
        a = [y for y in anchors if y <= ln.y0 + 3]
        if not a:
            caption.append(text)  # a title row above the first full row
            continue
        key = a[-1]
        if key not in row_of_anchor:
            row_of_anchor[key] = len(rows)
            rows.append({})
            bold_rows.append(True)
        ri = row_of_anchor[key]
        rows[ri].setdefault(col_of(ln), []).append(text)
        bold_rows[ri] = bold_rows[ri] and ln.bold
    header: list[str] | None = None
    if rows and bold_rows[0]:
        header = [" ".join(rows[0].get(c, [])) for c in range(len(cols))]
        rows, bold_rows = rows[1:], bold_rows[1:]
    out = [_clean(" ".join(caption))] if caption else []
    for row in rows:
        cells = [(c, _join_all(row[c])) for c in sorted(row)]
        if header:
            out.append("; ".join(f"{header[c]}: {v}" if header[c] else v for c, v in cells))
        else:
            out.append(" | ".join(v for _, v in cells))
    return [r for r in out if r]


def _join_all(parts: list[str]) -> str:
    text = ""
    for p in parts:
        text = _join(text, p) if text else p
    return text


def _mark_side_by_side_all(lines: list[_RawLine]) -> None:
    """Like _mark_side_by_side but on the unfiltered text, before small type is dropped."""
    saved = [ln.text for ln in lines]
    for ln in lines:
        ln.text = ln.full_text
    _mark_side_by_side(lines)
    for ln, s in zip(lines, saved, strict=True):
        ln.text = s


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
    notes = [ln for ln in raw if ln.fn]
    raw = _drop_repeated([ln for ln in raw if not ln.fn], n_pages)
    _mark_side_by_side(raw)
    out: list[Line] = []
    pending_marker: str | None = None
    prev: _RawLine | None = None
    for ln in raw:
        if ln.table_rows is not None:
            out.extend(Line("text", row, ln.page, table=True) for row in ln.table_rows)
            prev = None
            continue
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
            and not out[-1].table
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
    # Footnotes after the body, each its own line, so existing chunk ids stay where they are.
    seen: set[str] = set()
    for n in notes:
        key = n.fn or ""
        label = key if key not in seen else f"{key}~p{n.page}"
        seen.add(key)
        out.append(Line("text", n.text, n.page, footnote=label))
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

    header: list[str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 3:
            cells = [_md_inline(c.strip()) for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells if c):
                continue  # header separator row
            flush()
            if header is None:
                header = cells
                continue
            out.append(
                Line(
                    "text",
                    "; ".join(
                        f"{h}: {c}" if h else c for h, c in zip(header, cells, strict=False) if c
                    ),
                    page,
                    table=True,
                )
            )
            continue
        header = None
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
