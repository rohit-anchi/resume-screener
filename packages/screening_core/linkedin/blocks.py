"""Block-level extraction from a LinkedIn job-details PDF.

LinkedIn exports interleave employer job content with site chrome, so the unit of
analysis is the layout block (page, y, x, font size), not the line.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO

BLOCK_EXTRACTOR_VERSION = "linkedin-blocks-2.1.0"

URL_RX = re.compile(r"https?://\S+")
PAGE_NO_RX = re.compile(r"^\d{1,3}\s*/\s*\d{1,3}$")
TIMESTAMP_RX = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*(?:AM|PM)$", re.I)


@dataclass
class RawBlock:
    page: int
    order: int
    y: float
    x: float
    max_font_size: float
    text: str
    links: list[str] = field(default_factory=list)


def canon(s: str) -> str:
    """Canonicalise typography so patterns match LinkedIn's curly quotes and padded spacing."""
    return (s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
             .replace("\u00a0", " ").replace("\u2013", "-").replace("\u2014", "-"))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def is_garbled(text: str) -> bool:
    """Detect clipped/exploded render fragments such as 'ti I li ith l t G B ld'.

    These are PDF rendering artefacts of visually truncated text; the real content
    normally appears intact elsewhere in the document.
    """
    t = text.strip()
    if not t:
        return True
    tokens = t.split()
    if len(tokens) >= 4:
        singles = sum(1 for w in tokens if len(w) <= 2 and w.isalpha())
        if singles / len(tokens) >= 0.6:
            return True
    letters = sum(c.isalpha() for c in t)
    if len(t) >= 12 and letters / len(t) < 0.45 and not any(ch.isdigit() for ch in t):
        return True
    if len(tokens) <= 3 and len(t) <= 6 and not t.isdigit():
        # stray sidebar fragments: "1 1", "Off", "Sen", "Sh"
        return bool(re.fullmatch(r"[A-Za-z0-9 ]{1,6}", t))
    return False


def extract_blocks(data: bytes) -> tuple[list[RawBlock], list[str], int]:
    """Return (blocks in reading order, unique link URIs, page_count)."""
    import fitz

    doc = fitz.open(stream=data, filetype="pdf")
    blocks: list[RawBlock] = []
    links: list[str] = []
    seen_links: set[str] = set()
    order = 0
    for pno, page in enumerate(doc, 1):
        for l in page.get_links():
            uri = l.get("uri")
            if uri and uri not in seen_links:
                seen_links.add(uri)
                links.append(uri)
        page_blocks = []
        for b in page.get_text("dict").get("blocks", []):
            if b.get("type") != 0:
                continue
            spans = [s for line in b.get("lines", []) for s in line.get("spans", [])]
            if not spans:
                continue
            text = "\n".join(" ".join(s["text"] for s in line.get("spans", [])) for line in b.get("lines", []))
            if not text.strip():
                continue
            page_blocks.append((b["bbox"][1], b["bbox"][0], max(s.get("size", 10) for s in spans), text))
        for y, x, size, text in sorted(page_blocks, key=lambda t: (round(t[0], 1), t[1])):
            order += 1
            blocks.append(RawBlock(page=pno, order=order, y=round(y, 1), x=round(x, 1), max_font_size=round(size, 1), text=text))
    return blocks, links, doc.page_count


def repeated_chrome(blocks: list[RawBlock], page_count: int) -> set[str]:
    """Normalised texts that repeat across most pages (running headers/footers).

    Short strings are excluded: a company name can legitimately repeat (e.g. in the
    job header and again in an 'About the company' card) without being furniture.
    """
    from collections import Counter

    counts = Counter(_norm(b.text) for b in blocks)
    threshold = max(2, round(page_count * 0.6))
    return {t for t, c in counts.items() if c >= threshold and len(t) >= 25}


BROWSER_TITLE_RX = re.compile(r"\|\s*LinkedIn\s*$", re.I)


def is_page_furniture(text: str) -> bool:
    """Print header/footer emitted by the browser when the page was saved as PDF."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return True
    if len(lines) <= 4 and any(URL_RX.search(l) and "linkedin.com" in l for l in lines):
        return True
    if len(lines) <= 4 and any(TIMESTAMP_RX.match(l) for l in lines):
        return True
    if len(lines) <= 2 and any(BROWSER_TITLE_RX.search(l) for l in lines):
        return True
    return all(PAGE_NO_RX.match(l) or TIMESTAMP_RX.match(l) or (URL_RX.search(l) is not None) for l in lines)
