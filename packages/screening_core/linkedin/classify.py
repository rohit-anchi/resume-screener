"""Content-block classifier for LinkedIn job-details PDFs.

Allow-list model: a block enters requirement extraction only if it is classified as
employer job content in a requirement-bearing category. Everything else is retained
for audit with a reason, and never scored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..schemas.jobdoc import BlockCategory as C
from .blocks import RawBlock, canon, is_garbled, is_page_furniture, repeated_chrome

CLASSIFIER_VERSION = "linkedin-classifier-2.1.0"

# ---------------------------------------------------------------- exclusion rules (checked first)
EXCLUDE_RULES: list[tuple[str, C, re.Pattern[str]]] = [
    ("job_match_statement", C.linkedin_job_match, re.compile(
        r"job match is (?:high|good|low)|you'?d be a top applicant|your profile and resume (?:match|seem to match)|"
        r"is this information helpful|show match details|tailor my resume|help me stand out|create cover lette|"
        r"see how you compare to others|how you match", re.I)),
    ("resume_promotion", C.linkedin_resume_promotion, re.compile(
        r"hire a resume writer|get a resume review|put your best foot forward|resume builder|career coaching", re.I)),
    ("applicant_stats", C.linkedin_applicant_stats, re.compile(
        r"candidates who clicked apply|\d+\s+total\b|\d+\s+in the past day|people clicked apply|"
        r"based on linkedin data|excludes subsidiaries", re.I)),
    ("seniority_stats", C.linkedin_candidate_seniority_stats, re.compile(
        r"candidate seniority level|\d+%\s+(?:senior|director|cxo|manager|entry)\s+level candidates", re.I)),
    ("education_stats", C.linkedin_candidate_education_stats, re.compile(
        r"candidate education level|\d+%\s+have (?:a|other)\b|master of business administration|bachelor of science\b.*%|similar to you", re.I)),
    ("premium_insights", C.linkedin_premium_insights, re.compile(
        r"exclusive job seeker insights|premium insights|powered by bing|show premium insights|unlock premium", re.I)),
    ("company_insights", C.linkedin_company_insights, re.compile(
        r"company focus areas|hiring & headcount|the latest hiring trend|total employees|company-wide|"
        r"2 year growth|median employee tenure|hires candidates from some of these companies|hired \d+ (?:person|people) from|"
        r"competitors|about the company|followers\b|employees\b.*on linkedin|significant growth in|expansion in|focus on business development|"
        r"growth in customer success|sources:\s", re.I)),
    ("similar_jobs", C.linkedin_similar_jobs, re.compile(
        r"set alert for similar jobs|similar jobs|more jobs like this|people also viewed", re.I)),
    ("people_suggestions", C.linkedin_people_suggestions, re.compile(
        r"people you can reach out to|company alum(?:ni)? from|•\s*\d(?:st|nd|rd)\b|see all\b", re.I)),
    ("nav", C.linkedin_nav, re.compile(
        r"^(?:home|my network|jobs|messaging|notifications|me|for business|try premium|learning|follow|connect|save|apply|share|show all|show more|see more|"
        r"sign in|join now|advertise|off|on)$", re.I)),
    ("advertisement", C.linkedin_advertisement, re.compile(r"\bad\b\s*·|promoted\s*·\s*ad|sponsored", re.I)),
]

# ---------------------------------------------------------------- employer heading rules
HEADINGS: list[tuple[C, re.Pattern[str]]] = [
    (C.employer_requirements, re.compile(
        r"^(?:skills?\s*(?:&|and)\s*qualifications?|qualifications?|requirements?|minimum qualifications?|basic qualifications?|"
        r"what you'?ll need|what you will need|what we'?re looking for|here are some of the things we are looking for.*|"
        r"about you|who you are|your experience|essential skills?|you will have)\s*:?$", re.I)),
    (C.employer_preferred, re.compile(
        r"^(?:preferred qualifications?|nice to have|nice-to-haves?|desirable|bonus points?|it'?d be great if|"
        r"preferred|advantageous|good to have)\s*:?$", re.I)),
    (C.employer_responsibilities, re.compile(
        r"^(?:responsibilities|key responsibilities|what you'?ll do|what you will do|duties|the role|your role|"
        r"in this role you will|day to day|what success looks like|the team is currently working on.*|"
        r"initially,? you will focus on.*)\s*:?$", re.I)),
    (C.employer_role_overview, re.compile(
        r"^(?:about the role|the role\s*/?\s*impact|the role|role overview|overview|why this role|the opportunity|"
        r"about the job|the amber product team develops and supports)\s*:?$", re.I)),
    (C.employer_team, re.compile(r"^(?:about the team|the team\s*/?\s*how they connect|the team|who you'?ll work with|your team)\s*:?$", re.I)),
    (C.employer_about, re.compile(r"^(?:about (?:us|the company|amber|xero|[a-z][\w .&'-]{1,40})|company overview|who we are|our mission)\s*:?$", re.I)),
    (C.employer_work_arrangement, re.compile(r"^(?:where and how you can work|working arrangements?|location|work location|how we work|flexible working)\s*:?$", re.I)),
    (C.employer_compensation, re.compile(r"^(?:salary|compensation|salary range|pay|benefits|what we offer|remuneration)\s*:?$", re.I)),
    (C.employer_process, re.compile(r"^(?:our process(?: will generally be as follows)?|hiring process|interview process|what to expect|next steps)\s*:?$", re.I)),
    (C.employer_application_instructions, re.compile(r"^(?:how to apply|to apply|application process|applying)\s*:?$", re.I)),
]

# ---------------------------------------------------------------- employer body cues
BODY_CUES: list[tuple[str, C, re.Pattern[str]]] = [
    ("eeo_statement", C.employer_eeo, re.compile(
        r"we (?:never )?(?:do not |don'?t )?discriminate|equal opportunit|underrepresented groups|"
        r"regardless of race|all backgrounds|we hire based on your skills|apply even if your experience isn'?t a perfect match|"
        r"even if you don'?t meet 100% of the requirements", re.I)),
    ("ai_disclosure", C.employer_ai_disclosure, re.compile(
        r"artificial intelligence \(ai\) tools to support|ai tools? (?:to|in) (?:support|assist).{0,40}hiring|"
        r"do not replace human judgment|final hiring decisions are ultimately made by humans", re.I)),
    ("compensation_body", C.employer_compensation, re.compile(
        r"\$[\d,]{5,}\s*(?:-|–|to)\s*\$?[\d,]{5,}|salary range is between|base per annum|excluding superannuation|"
        r"employee stock options|a year\b.*\$|\bbase salary\b", re.I)),
    ("eligibility_body", C.employer_eligibility, re.compile(
        r"applications will be accepted only from|already based in|not looking to relocate|sponsor(?:ing|ship)?\b|"
        r"working visa|right to work|work authoris|work authoriz|must be located|eligible to work|security clearance", re.I)),
    ("process_body", C.employer_process, re.compile(
        r"screening interview|take-home challenge|a final chat|interviews? (?:discussing|with)|shortlisted candidates|"
        r"we promise to be respectful of your time|no recruitment agencies", re.I)),
    ("application_body", C.employer_application_instructions, re.compile(
        r"please include your resume|include a cover letter|send your (?:cv|resume)|submit your application", re.I)),
    ("work_arrangement_body", C.employer_work_arrangement, re.compile(
        r"we support a flexible working model|hybrid capacity|remote work|office spaces|team boost days|"
        r"^(?:hybrid|remote|on-site|onsite|full-time|part-time|contract|internship)$", re.I)),
]

CHART_FURNITURE = re.compile(r"^(?:\.{2,}\s*more|\u2026\s*mo?r?e?|more)$|^(?:\d{1,3}(?:[.,]\d+)?[kKmM%]?)$|"
                             r"^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*\d{4}$", re.I)
INSIGHT_CONTINUATION = re.compile(r"^\s*[\u2022\-]|\d+%|sources?:|leading provider|trusted by|is focused on", re.I)
SIMILAR_JOB_TARGET = re.compile(r"^[A-Z][\w ,'&/()-]{3,80}(?:,\s*[A-Z][\w .'-]+){1,3}\s*(?:\n\s*(?:on|off))?$")
EXCLUDED_CONTEXTS = (C.linkedin_premium_insights, C.linkedin_company_insights, C.linkedin_similar_jobs,
                     C.linkedin_applicant_stats, C.linkedin_candidate_seniority_stats, C.linkedin_candidate_education_stats)

REQUIREMENT_BODY_CUE = re.compile(
    r"^\s*(?:\d+\+?\s*years?|experience\b|proven\b|track record\b|demonstrated\b|strong\b|you bring\b|you think\b|"
    r"you (?:are|have|know)\b|your approach\b|ability to\b|excellent\b|familiarity\b|knowledge of\b|comfortable\b|"
    r"curiosity\b|ambiguity\b)", re.I)
PREFERRED_BODY_CUE = re.compile(r"is a (?:strong )?plus\b|nice to have\b|ideally\b|preferred\b|bonus\b|advantageous\b", re.I)
JOB_HEADER_CUES = re.compile(r"·\s*(?:reposted|posted|\d+\s+(?:days?|weeks?|hours?|minutes?|months?) ago)|promoted by hirer|responses managed off linkedin", re.I)
ABOUT_JOB_MARKER = re.compile(r"^about the job$", re.I)
EMOJI_HEADING = re.compile(r"^[\U0001F300-\U0001FAFF\u26A0-\u27BF\u2B00-\u2BFF\uFE0F\s]*(?P<t>[A-Za-z][\w .,&'/()-]{2,60})\s*:?$")


@dataclass
class Classified:
    block: RawBlock
    category: C
    reason: str
    rule: str | None
    review: bool


def _strip_emoji_heading(text: str) -> str | None:
    line = text.strip()
    if "\n" in line:
        return None
    m = EMOJI_HEADING.match(line)
    return m.group("t").strip() if m else None


def _heading_category(text: str) -> tuple[C, str] | None:
    candidate = _strip_emoji_heading(text)
    if not candidate:
        first = text.strip().splitlines()[0].strip() if text.strip() else ""
        candidate = first if len(first) <= 70 and len(text.strip().splitlines()) == 1 else None
    if not candidate:
        return None
    for cat, rx in HEADINGS:
        if rx.match(candidate):
            return cat, f"heading '{candidate}'"
    return None


def classify(blocks: list[RawBlock], page_count: int) -> list[Classified]:
    chrome = repeated_chrome(blocks, page_count)
    out: list[Classified] = []
    current: C | None = None
    excluded_context: C | None = None
    seen_about_job = False
    max_size = max((b.max_font_size for b in blocks), default=12)

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip().lower()

    for b in blocks:
        text = canon(b.text).strip()
        n = norm(text)
        # 1. page furniture and repeated chrome
        if is_page_furniture(text) or n in chrome:
            out.append(Classified(b, C.page_header_footer, "repeated page header/footer or URL furniture", "page_furniture", False))
            continue
        # 2. render artefacts
        if is_garbled(text):
            out.append(Classified(b, C.garbled_fragment, "clipped or exploded render fragment; content appears intact elsewhere", "garbled", False))
            continue
        # 3. LinkedIn chrome
        excluded = None
        for rule, cat, rx in EXCLUDE_RULES:
            if rx.search(text):
                excluded = Classified(b, cat, f"matched LinkedIn-generated pattern ({rule})", rule, False)
                break
        if excluded:
            out.append(excluded)
            if excluded.category in EXCLUDED_CONTEXTS:
                current, excluded_context = None, excluded.category
            continue
        # 4. 'About the job' marker starts employer content
        if ABOUT_JOB_MARKER.match(n):
            seen_about_job = True
            out.append(Classified(b, C.linkedin_nav, "LinkedIn 'About the job' label; marks the start of employer-authored content", "about_job_marker", False))
            current, excluded_context = C.employer_role_overview, None
            continue
        # 5. job header (page 1, large type, or listing metadata cues)
        if b.page == 1 and not seen_about_job and (b.max_font_size >= max_size - 0.5 or JOB_HEADER_CUES.search(text) or len(n) < 90):
            out.append(Classified(b, C.job_header, "page-1 listing metadata (employer, role, location, type)", "job_header", False))
            continue
        # 6. employer heading -> switches section state
        head = _heading_category(text)
        if head:
            cat, why = head
            current, excluded_context = cat, None
            out.append(Classified(b, cat, f"employer section {why}", "heading", False))
            continue
        # 7. employer body cues
        body = None
        for rule, cat, rx in BODY_CUES:
            if rx.search(text):
                body = Classified(b, cat, f"employer body cue ({rule})", rule, False)
                break
        if body:
            out.append(body)
            excluded_context = None
            if body.category in (C.employer_eligibility, C.employer_work_arrangement):
                current = body.category
            continue
        # chart/axis furniture and continuation prose belonging to an excluded LinkedIn region
        if CHART_FURNITURE.match(n):
            out.append(Classified(b, excluded_context or C.linkedin_company_insights, "chart axis or truncation control inside a LinkedIn insight region", "chart_furniture", False))
            continue
        if excluded_context is not None and (len(text) <= 200 or INSIGHT_CONTINUATION.search(text)):
            out.append(Classified(b, excluded_context, f"continuation of excluded LinkedIn region '{excluded_context.value}'", "excluded_inherit", False))
            continue
        if excluded_context == C.linkedin_similar_jobs and SIMILAR_JOB_TARGET.match(text):
            out.append(Classified(b, C.linkedin_similar_jobs, "similar-job alert target", "similar_job_target", False))
            continue
        # 8. inherit current employer section
        if current is not None:
            cat = current
            single_item = len([l for l in text.splitlines() if l.strip()]) == 1
            if single_item and cat in (C.employer_requirements, C.employer_responsibilities) and PREFERRED_BODY_CUE.search(text):
                cat = C.employer_preferred  # per-line preference cues are resolved during requirement extraction
            out.append(Classified(b, cat, f"continuation of employer section '{current.value}'", "section_inherit", False))
            continue
        # 9. unattributed prose after employer content started
        if seen_about_job and REQUIREMENT_BODY_CUE.search(text):
            out.append(Classified(b, C.employer_requirements, "requirement-style prose without a recognised heading", "requirement_prose", True))
            continue
        out.append(Classified(b, C.unknown, "could not be attributed to employer content or LinkedIn chrome", None, True))
    return out
