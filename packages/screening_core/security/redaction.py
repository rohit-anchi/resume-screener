"""Structural protected-attribute redaction (ADR-006).

Produces the screening view consumed by extraction and scoring. Contact and
identity data are retained only in the parseability assessment.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
URL = re.compile(r"https?://\S+|www\.\S+|linkedin\.com/\S+", re.I)
DOB = re.compile(r"\b(?:date of birth|dob|born)\b[^\n]*", re.I)
STREET = re.compile(r"\b\d{1,5}\s+[A-Z][\w.]*(?:\s+[A-Z][\w.]*){0,3}\s+(?:Street|St\.|Road|Rd\.|Avenue|Ave\.|Lane|Ln\.|Drive|Dr\.|Boulevard|Blvd\.)\b[^\n]*", re.I)
POSTCODE = re.compile(r"\b\d{5}(?:-\d{4})?\b|\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b")
PROTECTED_LINES = re.compile(
    r"^\s*(?:gender|sex|marital status|nationality|citizenship|religion|ethnicity|race|"
    r"disability|health|political|pronouns|age|photo|photograph|date of birth|dob|"
    r"place of birth|hobbies)\s*[:\-–].*$",
    re.I | re.M,
)
PRONOUNS = re.compile(r"\b(?:he|she|him|her|his|hers|they|them|their|theirs)\b", re.I)
HONORIFIC = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof)\.?\s+", re.I)
GRAD_YEAR = re.compile(r"(?i)(graduated|class of|batch of)\s*(?:in\s*)?(19|20)\d{2}")
PLACEHOLDER = "[REDACTED]"


@dataclass
class RedactionResult:
    redacted_text: str
    candidate_name: str | None
    contact_fields_found: bool
    removed_categories: list[str] = field(default_factory=list)


def _guess_name(text: str) -> str | None:
    for line in text.splitlines()[:5]:
        s = line.strip()
        if 2 <= len(s.split()) <= 4 and s.replace(" ", "").replace(".", "").replace("-", "").isalpha() and (s == s.title() or s.isupper()):
            return s
    return None


def redact(text: str, *, blind: bool = True) -> RedactionResult:
    """Remove identity, contact and protected markers before any evaluation."""
    removed: list[str] = []
    name = _guess_name(text)
    out = text
    contact_found = bool(EMAIL.search(out) or PHONE.search(out))
    for cat, rx in (("email", EMAIL), ("phone", PHONE), ("url", URL), ("dob", DOB), ("address", STREET), ("postcode", POSTCODE), ("protected_line", PROTECTED_LINES)):
        if rx.search(out):
            removed.append(cat)
            out = rx.sub(PLACEHOLDER, out)
    if name:
        out = re.sub(re.escape(name), PLACEHOLDER, out)
        removed.append("name")
    if HONORIFIC.search(out):
        out = HONORIFIC.sub("", out)
        removed.append("honorific")
    if blind:
        if PRONOUNS.search(out):
            out = PRONOUNS.sub("[P]", out)
            removed.append("pronoun")
        if GRAD_YEAR.search(out):
            out = GRAD_YEAR.sub(r"\1 [YEAR]", out)
            removed.append("graduation_year")
    return RedactionResult(out, name, contact_found, sorted(set(removed)))


PROTECTED_MARKERS = ("gender", "marital", "religion", "ethnicity", "date of birth", "nationality", "disability", "pronouns", "@", "linkedin.com")


def assert_no_protected_markers(text: str) -> list[str]:
    """Return any protected markers still present in a redacted view (for tests)."""
    low = text.lower()
    return [m for m in PROTECTED_MARKERS if m in low and f"{m}: [redacted]" not in low]
