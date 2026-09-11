"""Prompt-injection and document-manipulation detection. Detects and reports; never acts."""
from __future__ import annotations

import re
from collections import Counter

INJECTION_PATTERNS = [
    re.compile(r"ignore (?:all |the |any )?(?:previous|prior|above|the) (?:instructions|rules|job description)", re.I),
    re.compile(r"(?:give|assign|award|rate) (?:this|the) (?:candidate|resume|applicant) (?:a |an )?(?:perfect|maximum|full|top|100|highest)", re.I),
    re.compile(r"\b(?:system|assistant|developer) (?:prompt|message|instruction)\b", re.I),
    re.compile(r"you are (?:now )?(?:an? )?(?:ai|assistant|recruiter|screener)\b", re.I),
    re.compile(r"(?:bypass|skip|disable|override) (?:the )?(?:eligibility|screening|knockout|rules?)", re.I),
    re.compile(r"mark (?:as )?(?:eligible|qualified|hired|passed)", re.I),
    re.compile(r"<\s*/?\s*(?:system|instruction|prompt)\s*>", re.I),
]


def detect_injection(text: str) -> list[tuple[str, int, int]]:
    hits = []
    for rx in INJECTION_PATTERNS:
        for m in rx.finditer(text):
            hits.append((m.group(0), m.start(), m.end()))
    return hits


def keyword_stuffing(text: str, *, min_len: int = 4, ratio: float = 0.04, min_count: int = 12) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z+#.-]{%d,}" % (min_len - 1), text)]
    if len(words) < 50:
        return []
    counts = Counter(words)
    stop = {"with", "and", "the", "for", "that", "this", "from", "experience", "management", "product", "team", "work", "including", "across"}
    return sorted(w for w, c in counts.items() if w not in stop and c >= min_count and c / len(words) >= ratio)


def repeated_lines(text: str) -> int:
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 30]
    c = Counter(lines)
    return sum(v - 1 for v in c.values() if v > 1)
