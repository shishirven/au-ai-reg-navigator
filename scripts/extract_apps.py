"""Extract Schedule 1 (Australian Privacy Principles) from an official Privacy Act compilation PDF
into a markdown source with one '## APP n' section per principle. Verbatim text; layout only.

    uv run python scripts/extract_apps.py <compilation.pdf> <first_page> <last_page> <out.md>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from regnav.ingest.parse import parse_pdf

RUNNING_HEADER = re.compile(
    r"^(Part \d+ [A-Z][^.;:]*|[A-Z][^.;:]* Part \d+|Australian Privacy Principles Schedule 1)$"
)
NEW_LINE = re.compile(
    r"^(\d{1,2}\.\d{1,2}\s|\([a-z]{1,4}\)\s|\([ivx]{1,5}\)\s|Note|Example|Australian Privacy Principle \d)"
)
# Page-top running headers ("Dealing with personal information Part 3") can be spliced into a
# sentence that continues across a page break; remove them wherever they appear.
PART_TITLES = (
    "Consideration of personal information privacy",
    "Collection of personal information",
    "Dealing with personal information",
    "Integrity of personal information",
    "Access to, and correction of, personal information",
)
EMBEDDED_HEADER = re.compile(
    r"(?:^|\s)(?:" + "|".join(re.escape(t) for t in PART_TITLES) + r") Part \d(?=\s)"
)
APP_HEADING = re.compile(r"^(\d{1,2})\s+Australian Privacy Principle \d{1,2}\s*[—–-]\s*(.+)$")


def convert(pdf: Path, first: int, last: int) -> str:
    lines = parse_pdf(pdf, start_page=first, end_page=last)
    out: list[str] = []
    for ln in lines:
        # italic spans leave a stray space before closing punctuation: "( the APP privacy policy )"
        text = re.sub(r"\s+([);,])", r"\1", ln.text.strip())
        text = EMBEDDED_HEADER.sub("", text).strip()
        if RUNNING_HEADER.match(text):
            continue
        m = APP_HEADING.match(text)
        if m:
            out.append(f"\n## APP {m.group(1)} - {m.group(2)}\n")
            continue
        if ln.kind == "heading":
            out.append(f"\n## {text}\n")
            continue
        prev = out[-1] if out else ""
        if (
            prev
            and not prev.startswith(("\n##", "##"))
            and not re.search(r"[.;:]$", prev)
            and not NEW_LINE.match(text)
            and len(prev) > 60
        ):
            out[-1] = f"{prev} {text}"  # undo a wrap the parser kept as a new line
        else:
            out.append(text)
    body = "\n\n".join(s.strip("\n") if not s.startswith("\n##") else s.strip() for s in out)
    return re.sub(r"\n{3,}", "\n\n", body)


if __name__ == "__main__":
    pdf, first, last, dest = (
        Path(sys.argv[1]),
        int(sys.argv[2]),
        int(sys.argv[3]),
        Path(sys.argv[4]),
    )
    header = Path(dest).read_text().split("---", 1)[0] + "---\n\n" if Path(dest).exists() else ""
    Path(dest).write_text(header + convert(pdf, first, last) + "\n")
    print(f"wrote {dest}")
