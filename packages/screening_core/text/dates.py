"""Deterministic date normalisation and duration arithmetic (YYYY-MM granularity)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTHS["sept"] = 9
PRESENT = re.compile(r"\b(?:present|current|now|to date|ongoing|till date)\b", re.I)
MONTH_YEAR = re.compile(r"\b(?P<m>jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(?P<y>(?:19|20)\d{2})\b", re.I)
NUM_MONTH_YEAR = re.compile(r"\b(?P<m>0?[1-9]|1[0-2])/(?P<y>(?:19|20)\d{2})\b")
YEAR = re.compile(r"\b(?P<y>(?:19|20)\d{2})\b")
RANGE_SEP = r"\s*(?:-|–|—|to|through|until)\s*"
_MY = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(?:19|20)\d{2}"
_NMY = r"(?:0?[1-9]|1[0-2])/(?:19|20)\d{2}"
_Y = r"(?:19|20)\d{2}"
_POINT = rf"(?:{_MY}|{_NMY}|{_Y})"
RANGE = re.compile(rf"\b(?P<a>{_POINT}){RANGE_SEP}(?P<b>{_POINT}|{PRESENT.pattern})", re.I)


@dataclass(frozen=True)
class YM:
    year: int
    month: int
    uncertain: bool = False  # True when only the year was given

    def index(self) -> int:
        return self.year * 12 + self.month

    def iso(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


def parse_point(s: str, *, as_end: bool = False, today: date | None = None) -> YM | None:
    s = s.strip()
    if PRESENT.search(s):
        t = today or date.today()
        return YM(t.year, t.month)
    m = MONTH_YEAR.search(s)
    if m:
        return YM(int(m.group("y")), MONTHS[m.group("m").lower()[:4] if m.group("m").lower().startswith("sept") else m.group("m").lower()[:3]])
    m = NUM_MONTH_YEAR.search(s)
    if m:
        return YM(int(m.group("y")), int(m.group("m")))
    m = YEAR.search(s)
    if m:
        return YM(int(m.group("y")), 12 if as_end else 1, uncertain=True)
    return None


def find_ranges(text: str, today: date | None = None) -> list[tuple[YM, YM, bool, int, int]]:
    """Return (start, end, is_present, char_start, char_end)."""
    out = []
    for m in RANGE.finditer(text):
        a = parse_point(m.group("a"), today=today)
        b_raw = m.group("b")
        b = parse_point(b_raw, as_end=True, today=today)
        if a and b and b.index() >= a.index():
            out.append((a, b, bool(PRESENT.search(b_raw)), m.start(), m.end()))
    return out


def months_between(a: YM, b: YM) -> int:
    return max(0, b.index() - a.index() + 1)


def merged_months(periods: list[tuple[YM, YM]]) -> int:
    """Union of periods in months (overlapping roles are not double counted)."""
    idx = sorted((a.index(), b.index()) for a, b in periods)
    total, cur = 0, None
    for s, e in idx:
        if cur is None:
            cur = [s, e]
        elif s <= cur[1] + 1:
            cur[1] = max(cur[1], e)
        else:
            total += cur[1] - cur[0] + 1
            cur = [s, e]
    if cur:
        total += cur[1] - cur[0] + 1
    return total


def overlaps(periods: list[tuple[YM, YM]]) -> int:
    idx = sorted((a.index(), b.index()) for a, b in periods)
    return sum(1 for i in range(1, len(idx)) if idx[i][0] < idx[i - 1][1])
