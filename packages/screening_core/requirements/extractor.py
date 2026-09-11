"""Job-requirement extraction.

Handles both plain-text job descriptions (heading regexes) and LinkedIn job documents
(authoritative sections from the content classifier).

Key behaviours:
- Soft line wraps inside a PDF paragraph are unwrapped before splitting, so a requirement
  is never truncated mid-sentence.
- Explicit preference wording outranks section context; section context outranks weak cues.
- Requirements from qualification sections are never discarded by de-duplication.
- Subjective or potentially discriminatory criteria are marked unscorable, never scored.
"""
from __future__ import annotations

import re

from ..schemas.models import Importance, Requirement, RequirementCategory, SourceLocation, Threshold
from ..text.lexicon import LEXICON_VERSION, concepts_in
from ..text.sections import Section, jd_sections

EXTRACTOR_VERSION = f"req-extractor-2.1.0+{LEXICON_VERSION}"

REQUIRED_CUES = re.compile(r"\b(?:must|required|require|essential|minimum|mandatory|need to have|you will have|you have|at least|proven|you bring|you think|your approach)\b", re.I)
PREFERRED_CUES = re.compile(r"\b(?:preferred|desirable|nice to have|nice-to-have|bonus|advantage(?:ous)?|ideally|a plus|beneficial|good to have|familiarity with)\b", re.I)
STRONG_PREFERRED_CUES = re.compile(r"\bis a (?:strong )?plus\b|\bnice[- ]to[- ]have\b|\bbonus\b|\bdesirable\b|\badvantageous\b|\bwould be great\b|\bpreferred\b", re.I)
OBLIGATION_CUES = re.compile(r"\b(?:must be|required to|willing to|able to|need to be|only from|based in|relocat|travel up to|authoris|authoriz|visa|sponsor|clearance)\b", re.I)
ELIGIBILITY_CUES = re.compile(r"\b(?:authori[sz]ed to work|work authori[sz]ation|right to work|legally (?:able|eligible) to work|visa|sponsorship|security clearance|must be located|based in|relocate|willing to travel|travel up to|on-site|onsite|hybrid|remote)\b", re.I)
# Subjective or potentially discriminatory phrasing: specific phrases only, to avoid false positives.
UNSCORABLE = re.compile(
    r"\b(?:culture fit|cultural fit|young and energetic|young|energetic team|native speaker|native english|"
    r"recent graduate|fresh graduate|digital native|aggressive personality|like[- ]minded|perfect communication|"
    r"rockstar|rock star|ninja|guru|attractive|able[- ]bodied|no family commitments|unmarried|mature candidate|"
    r"good looking|work hard[,\s]+play hard)\b", re.I)
CONTEXTUAL = re.compile(r"\b(?:we are|we're|our team|our company|about us|benefits|salary|compensation|equal opportunity)\b", re.I)
THRESHOLD = re.compile(r"(?P<cmp>at least|minimum(?: of)?|more than|over|\b)\s*(?P<n>\d{1,2})\s*\+?\s*(?P<unit>years?|yrs?|months?)\b", re.I)
WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
BULLET = re.compile(r"^\s*[-*\u2022\u25cf\u25aa\u2023\u2043]\s+")
HEADING_LIKE = re.compile(
    r"^(?:skills?\s*(?:&|and)\s*qualifications?|qualifications?|requirements?|responsibilities|key responsibilities|"
    r"minimum qualifications?|basic qualifications?|preferred qualifications?|nice to have|about the (?:job|role|team)|"
    r"the role(?:\s*/?\s*impact)?|the team(?:\s*/?\s*how they connect)?|where and how you can work|how to apply|"
    r"our process(?: will generally be as follows)?|here are some of the things we are looking for.*|"
    r"the team is currently working on.*|initially,? you will focus on.*|what you'?ll do|what we'?re looking for|"
    r"the [a-z]+ product team develops and supports)\s*:?$", re.I)

SECTION_WEIGHT = {
    "minimum_qualifications": 1.0,
    "preferred_qualifications": 1.0,
    "eligibility": 1.0,
    "responsibilities": 0.6,
    "role_overview": 0.4,
    "about": 0.4,
    "work_arrangement": 1.0,
}
QUALIFICATION_SECTIONS = {"minimum_qualifications", "preferred_qualifications", "eligibility", "work_arrangement"}

CATEGORY_MAP = {
    "product_management": RequirementCategory.required_experience,
    "project_management": RequirementCategory.required_experience,
    "roadmap_ownership": RequirementCategory.delivery,
    "stakeholder_management": RequirementCategory.stakeholder_management,
    "cross_functional_collaboration": RequirementCategory.stakeholder_management,
    "org_alignment": RequirementCategory.stakeholder_management,
    "cloud_platforms": RequirementCategory.technical_knowledge,
    "data_pipelines": RequirementCategory.technical_knowledge,
    "platform_product_management": RequirementCategory.technical_knowledge,
    "ai_enablement": RequirementCategory.technical_knowledge,
    "telemetry": RequirementCategory.domain_knowledge,
    "saas_subscription": RequirementCategory.domain_knowledge,
    "enterprise_b2b": RequirementCategory.domain_knowledge,
    "hr_technology": RequirementCategory.domain_knowledge,
    "security_compliance": RequirementCategory.domain_knowledge,
    "multi_market_platform": RequirementCategory.domain_knowledge,
    "governance": RequirementCategory.domain_knowledge,
    "agile_delivery": RequirementCategory.delivery,
    "delivery_leadership": RequirementCategory.delivery,
    "product_practices": RequirementCategory.delivery,
    "adoption": RequirementCategory.delivery,
    "sql": RequirementCategory.skill,
    "python": RequirementCategory.skill,
    "api_design": RequirementCategory.skill,
    "analytics": RequirementCategory.skill,
    "customer_discovery": RequirementCategory.skill,
    "decision_making": RequirementCategory.skill,
    "systems_thinking": RequirementCategory.skill,
    "ambiguity_tolerance": RequirementCategory.skill,
    "learning_mindset": RequirementCategory.skill,
    "written_communication": RequirementCategory.communication,
    "product_strategy": RequirementCategory.leadership,
    "people_leadership": RequirementCategory.leadership,
    "people_management_of_managers": RequirementCategory.leadership,
    "exec_reporting": RequirementCategory.leadership,
    "bachelor_degree": RequirementCategory.qualification,
    "master_degree": RequirementCategory.qualification,
    "pmp_certification": RequirementCategory.certification,
    "scrum_certification": RequirementCategory.certification,
    "aws_certification": RequirementCategory.certification,
}
EVIDENCE_TYPE = {
    RequirementCategory.required_experience: "duration_and_role_evidence",
    RequirementCategory.preferred_experience: "role_evidence",
    RequirementCategory.certification: "certification_evidence",
    RequirementCategory.qualification: "education_evidence",
    RequirementCategory.eligibility: "explicit_candidate_answer",
    RequirementCategory.work_authorisation: "explicit_candidate_answer",
    RequirementCategory.location_or_work_arrangement: "explicit_candidate_answer",
    RequirementCategory.travel: "explicit_candidate_answer",
    RequirementCategory.leadership: "scope_and_leadership_evidence",
}
THRESHOLD_CATEGORIES = {RequirementCategory.required_experience, RequirementCategory.preferred_experience,
                        RequirementCategory.leadership, RequirementCategory.skill,
                        RequirementCategory.technical_knowledge, RequirementCategory.domain_knowledge,
                        RequirementCategory.delivery}


def _words_to_numbers(s: str) -> str:
    return re.sub(r"\b(" + "|".join(WORDNUM) + r")\b", lambda m: str(WORDNUM[m.group(1).lower()]), s, flags=re.I)


def _threshold(text: str) -> Threshold | None:
    m = THRESHOLD.search(_words_to_numbers(text))
    if not m:
        return None
    unit = "years" if m.group("unit").lower().startswith("y") else "months"
    cmp = ">" if re.search(r"more than|over", m.group("cmp") or "", re.I) else ">="
    return Threshold(value=float(m.group("n")), unit=unit, comparator=cmp)


def split_items(section_text: str, base_offset: int) -> list[tuple[str, int, int]]:
    """Split a section into logical requirement items with absolute offsets.

    Soft line wraps (continuation lines starting lowercase or with punctuation) are joined
    so a requirement is never cut mid-sentence. Offsets always refer to the original text.
    """
    items: list[tuple[str, int, int]] = []
    cur_lines: list[str] = []
    cur_start = cur_end = None
    pos = 0
    for raw in section_text.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        stripped = line.strip()
        start = pos
        end = pos + len(line)
        pos += len(raw)
        if not stripped:
            continue
        is_bullet = bool(BULLET.match(line))
        first = stripped.lstrip("-*\u2022\u25cf ").strip()[:1]
        continuation = bool(cur_lines) and not is_bullet and (
            first.islower() or first in ")]}\u201d'\"," or cur_lines[-1].rstrip().endswith(("-", ",", "or", "and"))
        )
        if continuation:
            cur_lines.append(stripped)
            cur_end = end
            continue
        if cur_lines:
            items.append((" ".join(cur_lines), base_offset + cur_start, base_offset + cur_end))
        cur_lines = [BULLET.sub("", stripped)]
        cur_start, cur_end = start, end
    if cur_lines:
        items.append((" ".join(cur_lines), base_offset + cur_start, base_offset + cur_end))
    # split remaining multi-clause items on semicolons and explicit conjunction cues
    out: list[tuple[str, int, int]] = []
    for text, a, b in items:
        parts = re.split(r"(?<=[a-z\)])\s+and\s+(?=(?:strong|experience|proven|ability|knowledge|familiarity|excellent|demonstrated)\b)", text, flags=re.I)
        if len(parts) == 1:
            out.append((text, a, b))
            continue
        cursor = a
        for p in parts:
            out.append((p.strip(), cursor, min(b, cursor + len(p))))
            cursor += len(p)
    return out


def _importance(section: str, text: str) -> tuple[Importance, str | None]:
    if UNSCORABLE.search(text):
        return Importance.unscorable, f"Subjective or potentially inappropriate criterion: '{UNSCORABLE.search(text).group(0)}'"
    if section == "work_arrangement":
        return (Importance.eligibility, None) if OBLIGATION_CUES.search(text) else (Importance.contextual, None)
    if STRONG_PREFERRED_CUES.search(text):
        return Importance.preferred, None  # explicit preference wording outranks section context
    if section == "eligibility":
        return (Importance.eligibility, None) if OBLIGATION_CUES.search(text) or ELIGIBILITY_CUES.search(text) else (Importance.contextual, None)
    if ELIGIBILITY_CUES.search(text) and OBLIGATION_CUES.search(text):
        return Importance.eligibility, None
    if section == "preferred_qualifications":
        return Importance.preferred, None
    if section == "minimum_qualifications":
        return Importance.required, None  # section context outranks weak cue words
    if PREFERRED_CUES.search(text):
        return Importance.preferred, None
    if section == "responsibilities":
        return Importance.required, "Derived from a responsibilities statement; confirm it is a candidate requirement"
    if section in ("about", "role_overview", "preamble", "benefits", "eeo"):
        return Importance.contextual, None
    if REQUIRED_CUES.search(text):
        return Importance.required, None
    return Importance.contextual, None


def _category(importance: Importance, concepts: list[str], text: str) -> RequirementCategory:
    if importance == Importance.eligibility:
        if re.search(r"authori|right to work|visa|sponsor|clearance", text, re.I):
            return RequirementCategory.work_authorisation
        if re.search(r"travel", text, re.I):
            return RequirementCategory.travel
        return RequirementCategory.location_or_work_arrangement
    for c in concepts:
        if c in CATEGORY_MAP:
            cat = CATEGORY_MAP[c]
            if cat == RequirementCategory.required_experience and importance == Importance.preferred:
                return RequirementCategory.preferred_experience
            return cat
    return RequirementCategory.other


def extract_requirements(document_id: str, text: str, sections: list[Section] | None = None) -> list[Requirement]:
    """Extract atomic requirements.

    `sections` supplies authoritative section boundaries (for example from the LinkedIn
    content classifier) instead of relying on heading regexes.
    """
    reqs: list[Requirement] = []
    seen: dict[tuple[str, str, str], Requirement] = {}
    n = 0
    for sec in (sections if sections is not None else jd_sections(text)):
        if sec.name in ("benefits", "eeo"):
            continue
        weight = SECTION_WEIGHT.get(sec.name, 0.6)
        for frag, start, end in split_items(sec.text, sec.start):
            frag = frag.strip(" \t\u2022-*")
            if len(frag) < 12 or HEADING_LIKE.match(frag):
                continue
            found = concepts_in(frag)
            concepts = sorted(found, key=lambda c: -max(e - s for s, e, _ in found[c]))
            if re.search(r"certif", frag, re.I):
                concepts.sort(key=lambda c: not c.endswith("_certification"))
            alternatives = [c for c in concepts[1:4]] if re.search(r"\bor\b|/", frag, re.I) else []
            importance, reason = _importance(sec.name, frag)
            if importance == Importance.contextual and not concepts:
                continue
            if not concepts and importance not in (Importance.eligibility, Importance.unscorable) and sec.name not in QUALIFICATION_SECTIONS:
                continue
            if importance == Importance.eligibility:
                concept = "eligibility_" + re.sub(r"\W+", "_", frag.lower())[:40]
            elif concepts:
                concept = concepts[0]
            else:
                concept = "unmapped_" + re.sub(r"\W+", "_", frag.lower())[:40]
            cat = _category(importance, concepts, frag)
            th = _threshold(frag) if cat in THRESHOLD_CATEGORIES else None
            key = (concept, importance.value, f"{th.value}{th.unit}" if th else "")
            prior = seen.get(key)
            if prior is not None:
                # never discard a qualification-section requirement in favour of narrative prose
                if sec.name in QUALIFICATION_SECTIONS and prior.weight < weight:
                    reqs.remove(prior)
                else:
                    continue
            n += 1
            review = importance == Importance.unscorable or reason is not None or concept.startswith("unmapped_")
            conf = 0.9 if concepts and importance in (Importance.required, Importance.preferred, Importance.eligibility) and reason is None else 0.6
            req = Requirement(
                requirement_id=f"REQ-{n:03d}", text=re.sub(r"\s+", " ", frag), normalised_concept=concept,
                alternative_concepts=alternatives, category=cat, importance=importance,
                evidence_type=EVIDENCE_TYPE.get(cat, "concept_evidence"), minimum_threshold=th,
                source_location=SourceLocation(document_id=document_id, section=sec.name or None, char_start=start, char_end=end, text_span=text[start:end]),
                confidence=conf, human_review_required=review,
                review_reason=reason or ("Concept not in lexicon; human classification required" if concept.startswith("unmapped_") else None),
                extraction_method="lexicon" if concepts else "rule", weight=weight,
            )
            reqs.append(req)
            seen[key] = req
    for i, r in enumerate(reqs, 1):
        r.requirement_id = f"REQ-{i:03d}"
    return reqs
