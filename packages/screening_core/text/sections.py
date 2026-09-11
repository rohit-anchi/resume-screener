"""Section identification for resumes and job descriptions with character offsets."""
from __future__ import annotations

import re
from dataclasses import dataclass

RESUME_HEADINGS = {
    "summary": r"(?:professional\s+)?summary|profile|about(?:\s+me)?|objective",
    "experience": r"(?:professional|work|employment)\s+(?:experience|history)|experience|career\s+history",
    "skills": r"(?:technical\s+|core\s+|key\s+)?skills|competenc(?:y|ies)|technologies|tools",
    "education": r"education|academic(?:\s+background)?|qualifications",
    "certifications": r"certifications?|licen[cs]es?|accreditations?",
    "projects": r"projects?",
    "other": r"awards|publications|languages|interests|volunteering|references",
}
JD_HEADINGS = {
    "about": r"about(?:\s+(?:us|the\s+role|the\s+team))?|overview|company",
    "responsibilities": r"responsibilities|what\s+you(?:'ll|\s+will)\s+do|the\s+role|duties|key\s+accountabilities",
    "minimum_qualifications": r"minimum\s+qualifications|basic\s+qualifications|required\s+(?:skills|qualifications|experience)|requirements|must[-\s]haves?|what\s+you(?:'ll|\s+will)\s+(?:need|bring)|essential",
    "preferred_qualifications": r"preferred\s+qualifications|nice[-\s]to[-\s]haves?|desirable|bonus|preferred|advantageous|good\s+to\s+have",
    "eligibility": r"eligibility|work\s+authori[sz]ation|location\s+requirements?",
    "benefits": r"benefits|compensation|perks|salary|what\s+we\s+offer",
    "eeo": r"equal\s+opportunity|diversity\s+statement|eeo",
}


@dataclass
class Section:
    name: str
    heading: str
    start: int
    end: int
    text: str


def _split(text: str, patterns: dict[str, str], default: str) -> list[Section]:
    heading_rx = re.compile(r"^[ \t]*(?:#+\s*)?(?P<h>[A-Za-z][A-Za-z '&/()\-]{1,60})[ \t]*:?[ \t]*$", re.M)
    marks: list[tuple[int, int, str, str]] = []
    for m in heading_rx.finditer(text):
        h = m.group("h").strip()
        if len(h.split()) > 6:
            continue
        for name, rx in patterns.items():
            if re.fullmatch(rx, h, re.I):
                marks.append((m.start(), m.end(), name, h))
                break
    sections: list[Section] = []
    if not marks or marks[0][0] > 0:
        end = marks[0][0] if marks else len(text)
        sections.append(Section(default, "", 0, end, text[0:end]))
    for i, (s, e, name, h) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        sections.append(Section(name, h, e, end, text[e:end]))
    return sections


def resume_sections(text: str) -> list[Section]:
    return _split(text, RESUME_HEADINGS, "header")


def jd_sections(text: str) -> list[Section]:
    return _split(text, JD_HEADINGS, "preamble")


def section_at(sections: list[Section], offset: int) -> str | None:
    for s in sections:
        if s.start <= offset < s.end:
            return s.name
    return None
