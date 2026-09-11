"""Candidate-evidence extraction from the *redacted* screening view.

Every item carries a verbatim span. Nothing is inferred from absence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from ..schemas.models import Candidate, Evidence, EvidenceType, IngestedDocument, ParseabilityReport, Period, SourceLocation
from ..text import dates
from ..text.lexicon import LEXICON_VERSION, concepts_in
from ..text.sections import Section, resume_sections, section_at

EVIDENCE_EXTRACTOR_VERSION = f"evidence-extractor-2.0.0+{LEXICON_VERSION}"
QUANT = re.compile(r"(?:\$|€|£|₹)?\d[\d,.]*\s*(?:%|percent|k\b|m\b|bn\b|million|billion|x\b|hours|days|weeks|customers|users|accounts|devices|sites|teams?|engineers|people)", re.I)
ACTION = re.compile(r"^\s*(?:led|owned|delivered|launched|built|designed|defined|drove|reduced|increased|improved|managed|shipped|created|established|negotiated|migrated|scaled|partnered|coordinated|authored|implemented|architected|prioriti[sz]ed|conducted)\b", re.I)
ABSENCE = re.compile(r"\b(?:no|not|never|without)\s+(?:prior|previous|formal|hands-on|direct)?\s*(?:experience|exposure|background|certification|degree)\b[^.\n]*", re.I)
ROLE_LINE = re.compile(r"^(?P<a>[^|,\n@]{3,80}?)\s*(?:\||,|@|–|-|at)\s*(?P<b>[^|,\n]{2,80}?)\s*(?:[|,(]\s*)?(?P<d>(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?:19|20)\d{2}|(?:0?[1-9]|1[0-2])/(?:19|20)\d{2}|(?:19|20)\d{2})", re.I | re.M)
DEGREE = re.compile(r"\b(?:bachelor|master|mba|b\.?sc|m\.?sc|b\.?tech|m\.?tech|b\.?e\.?|ph\.?d|doctorate|diploma|associate)\b[^\n]*", re.I)
CERT = re.compile(r"\b(?:certified|certificate|certification|pmp|cspo|csm|psm|pspo|aws certified|azure|itil|prince2|six sigma|cissp)\b[^\n]*", re.I)


@dataclass
class Role:
    employer: str | None
    title: str | None
    start: dates.YM
    end: dates.YM
    is_present: bool
    span: tuple[int, int]
    section_start: int
    section_end: int


def _roles(text: str, sections: list[Section], today: date | None) -> list[Role]:
    roles: list[Role] = []
    exp = [s for s in sections if s.name == "experience"] or sections
    for sec in exp:
        for a, b, present, cs, ce in dates.find_ranges(sec.text, today):
            line_start = sec.text.rfind("\n", 0, cs) + 1
            line_end = sec.text.find("\n", ce)
            line_end = len(sec.text) if line_end == -1 else line_end
            header = (sec.text[line_start:cs] + " " + sec.text[ce:line_end]).strip(" |,-–—()")
            # header may be on the previous line
            if len(header) < 3 and line_start > 0:
                prev_start = sec.text.rfind("\n", 0, line_start - 1) + 1
                header = sec.text[prev_start:line_start].strip()
                line_start = prev_start
            parts = [p.strip() for p in re.split(r"\s*[|,@–—]\s*|\s+at\s+|\s-\s", header) if p.strip()]
            title = parts[0] if parts else None
            employer = parts[1] if len(parts) > 1 else None
            next_range = sec.text.find("\n", ce)
            block_end = len(sec.text)
            for a2, b2, p2, cs2, ce2 in dates.find_ranges(sec.text, today):
                if cs2 > ce:
                    block_end = sec.text.rfind("\n", 0, cs2) + 1
                    break
            roles.append(Role(employer, title, a, b, present, (sec.start + line_start, sec.start + line_end), sec.start + line_end, sec.start + block_end))
    return roles


def extract_evidence(candidate_id: str, doc: IngestedDocument, *, today: date | None = None) -> tuple[list[Evidence], list[str], list[Role]]:
    text = doc.redacted_text
    sections = resume_sections(text)
    roles = _roles(text, sections, today)
    evidence: list[Evidence] = []
    contradictions: list[str] = []
    n = 0

    def loc(a: int, b: int) -> SourceLocation:
        return SourceLocation(document_id=doc.document_id, section=section_at(sections, a), char_start=a, char_end=b, text_span=text[a:b])

    def add(et: EvidenceType, concepts: list[str], a: int, b: int, **kw) -> None:
        nonlocal n
        n += 1
        evidence.append(Evidence(evidence_id=f"EVD-{n:03d}", candidate_id=candidate_id, evidence_type=et, normalised_concepts=sorted(set(concepts)), source_location=loc(a, b), **kw))

    absence_spans = [(m.start(), m.end()) for m in ABSENCE.finditer(text)]

    def in_absence(a: int, b: int) -> bool:
        return any(a >= s and b <= e for s, e in absence_spans)

    # roles and achievements
    for r in roles:
        period = Period(start=r.start.iso(), end="present" if r.is_present else r.end.iso(), start_uncertain=r.start.uncertain, end_uncertain=r.end.uncertain)
        header_concepts = list(concepts_in(text[r.span[0]:r.span[1]]).keys())
        add(EvidenceType.employment_role, header_concepts, r.span[0], r.span[1], employer=r.employer, role=r.title, employment_period=period, confidence=0.85 if not (r.start.uncertain or r.end.uncertain) else 0.7)
        block = text[r.section_start:r.section_end]
        for m in re.finditer(r"[^\n]+", block):
            line = m.group(0).strip(" •\u2022-*\t")
            if len(line) < 15:
                continue
            a = r.section_start + m.start() + (len(m.group(0)) - len(m.group(0).lstrip(" •\u2022-*\t")))
            b = r.section_start + m.end()
            cs = list(concepts_in(line).keys())
            if ACTION.search(line) or cs:
                add(EvidenceType.employment_achievement, cs + header_concepts, a, b, employer=r.employer, role=r.title, employment_period=period,
                    quantified=bool(QUANT.search(line)), confidence=0.9 if cs else 0.7)

    # skills / summary
    for sec in sections:
        if sec.name in ("skills", "summary", "projects", "header"):
            for concept, occ in concepts_in(sec.text).items():
                occ = [o for o in occ if not in_absence(sec.start + o[0], sec.start + o[1])]
                if not occ:
                    continue
                a, b, _ = occ[0]
                et = EvidenceType.skill_mention if sec.name == "skills" else EvidenceType.summary_statement
                ls = sec.text.rfind("\n", 0, a) + 1
                le = sec.text.find("\n", b)
                le = len(sec.text) if le == -1 else le
                add(et, [concept], sec.start + ls, sec.start + le, confidence=0.6 if et == EvidenceType.skill_mention else 0.55)
        if sec.name == "education":
            for m in DEGREE.finditer(sec.text):
                add(EvidenceType.education, list(concepts_in(m.group(0)).keys()), sec.start + m.start(), sec.start + m.end(), confidence=0.8)
        if sec.name in ("certifications", "education", "skills"):
            for m in CERT.finditer(sec.text):
                cs = [c for c in concepts_in(m.group(0)).keys() if c.endswith("_certification")]
                if cs:
                    add(EvidenceType.certification, cs, sec.start + m.start(), sec.start + m.end(), confidence=0.8)

    # explicit statements of absence (only source of 'confirmed absent')
    for m in ABSENCE.finditer(text):
        add(EvidenceType.explicit_statement_of_absence, list(concepts_in(m.group(0)).keys()), m.start(), m.end(), confidence=0.8)

    # contradictions
    periods = [(r.start, r.end) for r in roles]
    ov = dates.overlaps(periods)
    if ov:
        contradictions.append(f"{ov} overlapping employment period(s) detected; may be concurrent roles or a date error")
    presents = sum(1 for r in roles if r.is_present)
    if presents > 1:
        contradictions.append(f"{presents} roles marked as current")
    return evidence, contradictions, roles


def assess_parseability(doc: IngestedDocument, roles: list[Role], evidence: list[Evidence], contradictions: list[str], *, name_found: bool, contact_found: bool) -> ParseabilityReport:
    text = doc.extracted_text
    codes = {f.code for f in doc.findings}
    sections = resume_sections(text)
    names = [s.name for s in sections]
    image_only = "image_only_content" in codes
    ok = doc.accepted and len(text.strip()) > 0 and not image_only
    has_exp = any(r for r in roles)
    has_dates = bool(dates.find_ranges(text))
    edu = any(e.evidence_type.value == "education" for e in evidence)
    cert = any(e.evidence_type.value == "certification" for e in evidence)
    missing_dates = 0
    for s in sections:
        if s.name == "experience":
            role_like = len(re.findall(r"^[A-Z][^\n]{5,80}$", s.text, re.M))
            missing_dates = max(0, role_like // 2 - len([r for r in roles]))
    order_ok = ("experience" in names) and (names.index("experience") < (names.index("education") if "education" in names else 999))
    checks = [ok, has_exp, has_dates, edu or cert, order_ok, "layout_interference" not in codes, not contradictions, "hidden_text_suspected" not in codes, missing_dates == 0]
    score = round(100 * sum(checks) / len(checks), 1) if ok else 0.0
    notes = [f.message for f in doc.findings if f.severity != "info"]
    return ParseabilityReport(
        document_id=doc.document_id, text_extraction_success=ok, image_only_content=image_only, ocr_required=image_only, ocr_available=False,
        name_extracted=name_found, contact_fields_extracted=contact_found, employment_history_extracted=has_exp, dates_extracted=has_dates,
        education_extracted=edu, certifications_extracted=cert, section_order_clear=order_ok, table_or_column_interference="layout_interference" in codes,
        chronology_conflicts=len(contradictions), missing_dates=missing_dates, duplicate_content="duplicate_content" in codes,
        injection_suspected="injection_suspected" in codes, hidden_text_suspected="hidden_text_suspected" in codes, parseability_score=score, notes=notes,
    )


def build_candidate(candidate_id: str, doc: IngestedDocument, *, today: date | None = None) -> Candidate:
    from ..security.redaction import redact

    red = redact(doc.extracted_text)
    evidence, contradictions, roles = extract_evidence(candidate_id, doc, today=today)
    parse = assess_parseability(doc, roles, evidence, contradictions, name_found=red.candidate_name is not None, contact_found=red.contact_fields_found)
    return Candidate(candidate_id=candidate_id, document=doc, evidence=evidence, parseability=parse, contradictions=contradictions)
