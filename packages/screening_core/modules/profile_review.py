"""Optional module 2: LinkedIn profile PDF vs resume comparison.

Requires a user-supplied profile export and explicit authorisation. No private LinkedIn
data is accessed; only the document the user provides is read.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from ..schemas.jobdoc import ProfileComparisonRow, ProfileReview
from ..schemas.models import Candidate, EvidenceType, IngestedDocument
from ..security.redaction import redact
from ..text import dates
from ..text.lexicon import concepts_in, label

PROFILE_REVIEW_VERSION = "profile-review-2.1.0"

SECTION_RX = {
    "headline": re.compile(r"^(?P<v>[^\n]{10,160})$", re.M),
    "summary": re.compile(r"^Summary\s*\n(?P<v>.+?)(?=\n(?:Experience|Education|Top Skills|Certifications|Languages|Honors)\b|\Z)", re.S | re.M),
    "experience": re.compile(r"^Experience\s*\n(?P<v>.+?)(?=\n(?:Education|Licenses|Certifications|Skills|Honors|Languages)\b|\Z)", re.S | re.M),
    "skills": re.compile(r"^(?:Top Skills|Skills)\s*\n(?P<v>.+?)(?=\n(?:Certifications|Languages|Honors|Rohit|Summary|Experience)\b|\Z)", re.S | re.M),
    "certifications": re.compile(r"^Certifications\s*\n(?P<v>.+?)(?=\n(?:Languages|Honors|Summary|Experience|Top Skills)\b|\Z)", re.S | re.M),
    "featured": re.compile(r"^(?:Featured|Publications|Projects)\s*\n(?P<v>.+?)(?=\n[A-Z][a-z]+\b|\Z)", re.S | re.M),
}
HEADLINE_HINT = re.compile(r"\b(?:leader|manager|director|head of|consultant|engineer|architect|analyst|specialist|owner|lead)\b", re.I)


def _section(text: str, name: str) -> str | None:
    rx = SECTION_RX.get(name)
    if not rx or name == "headline":
        return None
    m = rx.search(text)
    return re.sub(r"\s+", " ", m.group("v")).strip() if m else None


def _headline(text: str) -> str | None:
    for line in text.splitlines():
        s = line.strip()
        if 15 <= len(s) <= 180 and HEADLINE_HINT.search(s) and not s.lower().startswith(("contact", "top skills", "certifications", "summary")):
            return s
    return None


def _titles(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", l).strip() for l in text.splitlines()
            if 5 <= len(l.strip()) <= 90 and HEADLINE_HINT.search(l)]


def review(candidate_id: str, profile_doc: IngestedDocument, cand: Candidate, *, authorisation_confirmed: bool) -> ProfileReview:
    if not authorisation_confirmed:
        raise PermissionError("LinkedIn profile review requires explicit user authorisation for the supplied document.")
    ptext = redact(profile_doc.extracted_text).redacted_text
    rtext = cand.document.redacted_text

    p_sections = {k: _section(ptext, k) for k in ("summary", "experience", "skills", "certifications", "featured")}
    p_sections["headline"] = _headline(ptext)
    p_concepts = set(concepts_in(ptext))
    r_concepts = {c for e in cand.evidence for c in e.normalised_concepts}
    p_periods = [(a, b) for a, b, _, _, _ in dates.find_ranges(ptext)]
    r_roles = [e for e in cand.evidence if e.evidence_type == EvidenceType.employment_role]

    rows: list[ProfileComparisonRow] = []

    def add(dim: str, r_ev: str | None, p_ev: str | None, status: str, why: str) -> None:
        rows.append(ProfileComparisonRow(dimension=dim, resume_evidence=r_ev, profile_evidence=p_ev, status=status, explanation=why))

    r_summary = next((re.sub(r"\s+", " ", e.source_location.text_span).strip() for e in cand.evidence
                      if e.evidence_type == EvidenceType.summary_statement), None)
    add("Headline", (r_summary or "")[:180] or None, (p_sections["headline"] or "")[:180] or None,
        "aligned" if p_sections["headline"] and r_summary else ("missing_in_profile" if r_summary and not p_sections["headline"]
                                                               else "missing_in_resume" if p_sections["headline"] else "not_assessable"),
        "A headline and a resume summary should describe the same current positioning.")
    add("About / Summary", (r_summary or "")[:180] or None, (p_sections["summary"] or "")[:180] or None,
        "aligned" if p_sections["summary"] and r_summary else ("missing_in_resume" if p_sections["summary"] else "missing_in_profile"),
        "Long-form positioning should be consistent across both documents.")
    add("Experience", f"{len(r_roles)} dated role(s) extracted", f"{len(p_periods)} dated period(s) detected",
        "aligned" if r_roles and p_periods else ("missing_in_profile" if r_roles else "missing_in_resume"),
        "Role counts are indicative only; profile exports vary in layout.")

    only_profile = sorted(p_concepts - r_concepts)
    only_resume = sorted(r_concepts - p_concepts)
    add("Skills", ", ".join(label(c) for c in sorted(r_concepts)[:12]) or None,
        ", ".join(label(c) for c in sorted(p_concepts)[:12]) or None,
        "aligned" if not only_profile and not only_resume else "potential_contradiction" if False else ("missing_in_resume" if only_profile else "missing_in_profile"),
        "Skill vocabulary differs between the two documents; alignment helps recruiter search and reviewer confidence.")
    add("Certifications", "present" if any(e.evidence_type == EvidenceType.certification for e in cand.evidence) else None,
        (p_sections["certifications"] or "")[:180] or None,
        "aligned" if p_sections["certifications"] and any(e.evidence_type == EvidenceType.certification for e in cand.evidence)
        else ("missing_in_resume" if p_sections["certifications"] else "missing_in_profile"),
        "Certifications listed in one document should appear in the other if still relevant.")
    add("Featured content", None, (p_sections["featured"] or "")[:160] or None,
        "missing_in_resume" if p_sections["featured"] else "not_assessable",
        "Featured profile content has no resume equivalent; it is informational only.")

    # employment dates and current title
    r_current = [e for e in r_roles if e.employment_period and e.employment_period.end == "present"]
    add("Employment dates", f"{len(r_roles)} dated role(s); {len(r_current)} marked current",
        f"{len(p_periods)} dated period(s) detected",
        "potential_contradiction" if r_roles and p_periods and abs(len(r_roles) - len(p_periods)) > 2 else "aligned" if r_roles and p_periods else "not_assessable",
        "Large differences in dated history can raise reviewer questions; verify both documents tell the same story.")
    p_titles = _titles(ptext)
    add("Current title", (r_current[0].role if r_current and r_current[0].role else None), p_titles[0] if p_titles else None,
        "aligned" if r_current and p_titles else "not_assessable",
        "The current title should match across documents.")

    for dim, concept_set in (("Product leadership scope", {"people_leadership", "people_management_of_managers", "product_strategy", "exec_reporting", "org_alignment"}),
                             ("AI and platform experience", {"ai_enablement", "platform_product_management", "cloud_platforms", "data_pipelines", "systems_thinking"})):
        in_p = sorted(concept_set & p_concepts)
        in_r = sorted(concept_set & r_concepts)
        status = "aligned" if in_p and in_r else ("missing_in_resume" if in_p else "missing_in_profile" if in_r else "not_assessable")
        add(dim, ", ".join(label(c) for c in in_r) or None, ", ".join(label(c) for c in in_p) or None, status,
            "Target-market positioning should be evidenced in both documents.")

    missing_profile = [f"{label(c)} appears in the resume but not in the profile document" for c in only_resume[:10]]
    missing_resume = [f"{label(c)} appears in the profile document but not in the resume" for c in only_profile[:10]]
    contradictions = [r.dimension + ": " + r.explanation for r in rows if r.status == "potential_contradiction"]
    recs = []
    if missing_resume:
        recs.append("Bring profile-only strengths into the resume where they are relevant to the target role.")
    if missing_profile:
        recs.append("Update the LinkedIn profile so recruiters searching it see the same evidence as the resume.")
    if p_sections["headline"]:
        recs.append("Keep the headline aligned to the target-market role title you are applying for.")
    recs.append("Ensure dates and current title are identical in both documents.")
    return ProfileReview(review_id=f"PRV-{uuid.uuid4().hex[:10]}", created_at=datetime.now(timezone.utc).isoformat(),
                         candidate_id=candidate_id, profile_document_id=profile_doc.document_id,
                         resume_document_id=cand.document.document_id, authorisation_confirmed=authorisation_confirmed,
                         rows=rows, missing_profile_evidence=missing_profile, missing_resume_evidence=missing_resume,
                         potential_contradictions=contradictions, target_market_recommendations=recs,
                         limitations=[
                             "Only the supplied LinkedIn profile PDF was read; no private LinkedIn data was accessed.",
                             "Profile exports vary in layout, so section and role detection is indicative rather than exact.",
                             "Differences are prompts for your review, not findings of inaccuracy.",
                         ])


def render(r: ProfileReview) -> str:
    L = ["# LinkedIn profile review", "", f"Review `{r.review_id}` · created {r.created_at}",
         f"Authorisation confirmed: **{r.authorisation_confirmed}**", "", "## Resume vs profile", "",
         "| Dimension | Resume | Profile | Status | Notes |", "|---|---|---|---|---|"]
    for row in r.rows:
        L.append(f"| {row.dimension} | {(row.resume_evidence or '—')[:70]} | {(row.profile_evidence or '—')[:70]} | "
                 f"{row.status.replace('_', ' ')} | {row.explanation[:80]} |")
    L += ["", "## Missing profile evidence", ""] + ([f"- {m}" for m in r.missing_profile_evidence] or ["- none identified"])
    L += ["", "## Missing resume evidence", ""] + ([f"- {m}" for m in r.missing_resume_evidence] or ["- none identified"])
    L += ["", "## Potential contradictions", ""] + ([f"- {c}" for c in r.potential_contradictions] or ["- none identified"])
    L += ["", "## Target-market recommendations", ""] + [f"- {x}" for x in r.target_market_recommendations]
    L += ["", "## Limitations", ""] + [f"- {x}" for x in r.limitations] + [""]
    return "\n".join(L)
