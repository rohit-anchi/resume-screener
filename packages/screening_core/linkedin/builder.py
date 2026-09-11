"""Assemble a JobDocument from a LinkedIn job-details PDF.

Only allowed employer blocks are concatenated into `employer_text`; excluded blocks are
retained with a category and reason for audit but never reach requirement extraction.
"""
from __future__ import annotations

import hashlib
import re
import uuid

from ..ats.detect import DETECTOR_VERSION, detect
from ..schemas.jobdoc import SECTION_IMPORTANCE, BlockCategory as C, ContentBlock, JobDocument, JobSection
from .blocks import BLOCK_EXTRACTOR_VERSION, canon, extract_blocks, is_page_furniture
from .classify import CLASSIFIER_VERSION, classify

BUILDER_VERSION = f"linkedin-builder-2.1.0+{BLOCK_EXTRACTOR_VERSION}+{CLASSIFIER_VERSION}+{DETECTOR_VERSION}"

LOCATION_RX = re.compile(r"^(?P<loc>[A-Z][\w .'-]+(?:,\s*[A-Z][\w .'-]+){1,3})\s*·\s*(?:reposted|posted|\d+\s+\w+\s+ago)", re.I | re.M)
JUNK_HEADER_RX = re.compile(r"^(?:\d+|save|apply|connect|follow|share|show all|show more|see more|sent|promoted by hirer.*|"
                            r"responses managed.*|hybrid|remote|on-?site|full-?time|part-?time|off|on|beta.*|\u00b7.*)$", re.I)
HEADER_NOISE_RX = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}|\|\s*LinkedIn\s*$|^https?://|^\d{1,3}/\d{1,3}$|"
                             r"about the job|people you can reach out to|company alum|top applicant|profile and resume|"
                             r"match(?:es)? the required|is this information helpful|show match details|tailor my resume|"
                             r"help me stand out|create cover|job match is|more likely to hear back|problem solver|"
                             r"set alert|resume writer|resume review|best foot forward", re.I)
WORKPLACE_RX = re.compile(r"\b(hybrid|remote|on-?site)\b", re.I)
# LinkedIn sticky header encodes the employer explicitly: "Employer \u2022 Location (Workplace)"
STICKY_RX = re.compile(r"^(?P<emp>[^\u2022\n]{2,60}?)\s*\u2022\s*(?P<loc>[^()\n]{2,80}?)\s*\(\s*(?P<wp>Hybrid|Remote|On-?site)\s*\)\s*$", re.I)
EMPLOYMENT_RX = re.compile(r"\b(full-?time|part-?time|contract|temporary|internship|volunteer)\b", re.I)
OFF_PLATFORM_RX = re.compile(r"responses managed off linkedin", re.I)
COMP_RX = re.compile(r"\$[\d,]{4,}\s*(?:-|–|to)\s*\$?[\d,]{4,}[^\n]*")


def _pick_header(raw_blocks) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """(employer, role_title, location, employment_type, workplace_type) from raw page-1 blocks.

    Read before classification, because the listing metadata line also carries applicant
    statistics and is therefore excluded from scored content.
    """
    employer = role = location = emp_type = workplace = None
    page1 = [b for b in raw_blocks if b.page == 1 and not is_page_furniture(b.text)]
    lines: list[tuple[str, float]] = []
    for b in page1:
        for l in canon(b.text).splitlines():
            if l.strip():
                lines.append((l.strip(), b.max_font_size))
    joined = "\n".join(l for l, _ in lines)
    named = [(l, sz) for l, sz in lines if not JUNK_HEADER_RX.match(l) and not HEADER_NOISE_RX.search(l)
             and len(l) >= 2 and any(ch.isalpha() for ch in l) and "\u00b7" not in l]
    plain = [l for l, _ in named]
    sticky_idx = next((i for i, l in enumerate(plain) if STICKY_RX.match(l)), None)
    if sticky_idx is not None:
        m = STICKY_RX.match(plain[sticky_idx])
        employer, location, workplace = m.group("emp").strip(), m.group("loc").strip(), m.group("wp").title()
        for l in reversed(plain[:sticky_idx]):
            if 3 <= len(l) <= 90 and l.lower() != employer.lower() and "\u2022" not in l:
                role = l
                break
        if role is None:
            role = next((l for l in plain[sticky_idx + 1:] if 3 <= len(l) <= 90), None)
    elif named:
        employer = named[0][0]
        for l, _ in named[1:]:
            if 3 <= len(l) <= 90 and l.lower() != employer.lower():
                role = l
                break
    if location is None:
        m = LOCATION_RX.search(joined)
        if m:
            location = m.group("loc").strip()
    if workplace is None:
        w = WORKPLACE_RX.search(joined)
        workplace = w.group(1).title() if w else None
    e = EMPLOYMENT_RX.search(joined)
    emp_type = e.group(1).title().replace("Time", "time") if e else None
    return employer, role, location, emp_type, workplace


def build_job_document(filename: str, data: bytes, *, listing_source: str = "linkedin", document_id: str | None = None) -> JobDocument:
    raw_blocks, links, page_count = extract_blocks(data)
    classified = classify(raw_blocks, page_count)
    header = _pick_header(raw_blocks)
    sha = hashlib.sha256(data).hexdigest()
    doc_id = document_id or f"JDOC-{uuid.uuid4().hex[:10]}"

    full_text = "\n".join(c.block.text for c in classified)
    off_platform = bool(OFF_PLATFORM_RX.search(full_text))
    ats = detect(links, full_text, responses_off_platform=off_platform, listing_source=listing_source)

    blocks: list[ContentBlock] = []
    sections: list[JobSection] = []
    excluded: list[str] = []
    counts: dict[str, int] = {}
    parts: list[str] = []
    cursor = 0
    pending_section = None
    allowed = C.allowed()
    req_bearing = C.requirement_bearing()

    for i, c in enumerate(classified, 1):
        bid = f"BLK-{i:04d}"
        counts[c.category.value] = counts.get(c.category.value, 0) + 1
        is_allowed = c.category in allowed
        can_score = c.category in req_bearing
        start = end = None
        if can_score and c.rule == "heading":
            can_score = False  # heading text defines the section; it is not requirement prose
            blocks.append(ContentBlock(block_id=bid, page=c.block.page, order=c.block.order, y=c.block.y, x=c.block.x,
                                       max_font_size=c.block.max_font_size, text=c.block.text, category=c.category,
                                       allowed_for_requirements=False, classification_reason=c.reason,
                                       classifier_rule=c.rule, review_required=c.review))
            pending_section = c.category
            continue
        if can_score:
            text = c.block.text.strip()
            start = cursor
            parts.append(text)
            cursor += len(text) + 1
            end = cursor - 1
            name = SECTION_IMPORTANCE.get(c.category, "responsibilities")
            force_new = pending_section is not None
            pending_section = None
            if not force_new and sections and sections[-1].category == c.category and sections[-1].char_end == start - 1:
                sections[-1].char_end = end
                sections[-1].block_ids.append(bid)
            else:
                sections.append(JobSection(name=name, category=c.category, char_start=start, char_end=end, block_ids=[bid]))
        elif not is_allowed:
            excluded.append(bid)
        blocks.append(ContentBlock(block_id=bid, page=c.block.page, order=c.block.order, y=c.block.y, x=c.block.x,
                                   max_font_size=c.block.max_font_size, text=c.block.text, category=c.category,
                                   allowed_for_requirements=can_score, classification_reason=c.reason,
                                   classifier_rule=c.rule, review_required=c.review, char_start=start, char_end=end))

    employer_text = "\n".join(parts)
    employer, role, location, emp_type, workplace = header
    comp_blocks = [b.text for b in blocks if b.category == C.employer_compensation]
    comp = None
    for t in comp_blocks:
        m = COMP_RX.search(t)
        if m:
            comp = m.group(0).strip()
            break
    if comp is None and comp_blocks:
        comp = comp_blocks[0].strip().splitlines()[0]

    warnings: list[str] = []
    unknown = [b for b in blocks if b.category == C.unknown]
    if unknown:
        warnings.append(f"{len(unknown)} block(s) could not be attributed and are excluded from scoring; human classification required.")
    review_blocks = [b for b in blocks if b.review_required and b.category != C.unknown]
    if review_blocks:
        warnings.append(f"{len(review_blocks)} block(s) were attributed by weaker prose cues and are flagged for review.")
    if not any(b.category == C.employer_requirements for b in blocks):
        warnings.append("No explicit requirements/qualifications section was identified; coverage may be understated.")
    if not ats.has_approved_knowledge_profile:
        warnings.append(f"Application platform '{ats.application_platform.value}' has no approved Phase 1 knowledge profile; "
                        "platform-neutral assessment applied and no nearest-known ATS substituted.")
    garbled = [b for b in blocks if b.category == C.garbled_fragment]
    if garbled:
        warnings.append(f"{len(garbled)} clipped render fragment(s) discarded; verify no unique requirement text was only present in a clipped block.")

    return JobDocument(job_document_id=doc_id, source_document_id=doc_id, filename=filename, sha256=sha, page_count=page_count,
                       listing_source=listing_source, employer=employer, role_title=role, location=location, employment_type=emp_type,
                       workplace_type=workplace, compensation_text=comp, employer_text=employer_text, blocks=blocks, sections=sections,
                       excluded_block_ids=excluded, excluded_categories={k: v for k, v in sorted(counts.items())}, ats=ats,
                       extraction_warnings=warnings, parser_version=BLOCK_EXTRACTOR_VERSION, classifier_version=CLASSIFIER_VERSION)


def requirement_sections(jd: JobDocument):
    """Classifier-derived sections in the shape the requirement extractor expects."""
    from ..text.sections import Section

    return [Section(name=s.name, heading=s.category.value, start=s.char_start, end=s.char_end + 1,
                    text=jd.employer_text[s.char_start:s.char_end + 1]) for s in jd.sections]
