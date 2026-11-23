"""Deep links from a citation to the cited place in the source (not just the document).

* PDF sources parsed from the same PDF the URL serves (APRA standards and guides): ``#page=N``,
  which Chrome, Edge, Firefox and Acrobat open at that page. Page numbers come from the parser and
  were checked against the PDFs (e.g. CPS 230 para 52 → page 14).
* Web pages (OAIC guidance, the APRA AI letter): a text fragment ``#:~:text=...`` built from the
  first words of the cited passage; Chrome and Edge scroll to and highlight it, other browsers
  simply open the page.
* Anything else (a PDF we hold as a Markdown copy, so page numbers are unknown): the document URL.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

SOURCES = Path("data/sources.yaml")
_PDF_URL = re.compile(r"(\.pdf($|[?#])|/pdf($|[/?#]))", re.I)


@lru_cache(maxsize=4)
def _source_files(path: str = str(SOURCES)) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    docs = (yaml.safe_load(p.read_text()) or {}).get("documents", [])
    return {str(d["id"]): str(d.get("file", "")) for d in docs}


def _opening_words(text: str, n: int = 6) -> str:
    """First words of the passage body (skips the [Doc · Tier · ...] prefix line and a leading
    paragraph number or bullet), trimmed to whole words without trailing punctuation."""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if lines and lines[0].startswith("[") and lines[0].endswith("]"):
        lines = lines[1:]
    body = " ".join(lines)
    body = re.sub(r"^(\d{1,3}\.\s+|[•\-–]\s+|\([a-z]{1,4}\)\s+)", "", body)
    words = re.findall(r"[^\s]+", body)[:n]
    phrase = " ".join(words).rstrip(".,;:•–-")
    return phrase if len(phrase) >= 12 else ""


def citation_url(meta: dict[str, Any], text: str = "") -> str:
    url = str(meta.get("url") or "")
    if not url:
        return ""
    base = url.split("#", 1)[0]
    file = _source_files().get(str(meta.get("doc_id", "")), "")
    page = meta.get("page")
    if _PDF_URL.search(base):
        if file.lower().endswith(".pdf") and isinstance(page, int | float) and int(page) > 0:
            return f"{base}#page={int(page)}"
        return base
    phrase = _opening_words(text)
    return f"{base}#:~:text={quote(phrase, safe='')}" if phrase else base
