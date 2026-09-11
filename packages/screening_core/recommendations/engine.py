"""Resume-tailoring recommendations.

Hard rule: nothing is invented. Every proposed edit is assembled from text the candidate
already wrote, plus terminology taken from the employer's own job document. Each edit
carries the requirement it addresses, the supporting evidence and a verification note.
"""
from __future__ import annotations

import re

from ..schemas.jobdoc import Recommendation, RecommendationKind, RecommendedEdit
from ..schemas.models import (Candidate, EligibilityResult, EligibilityStatus, Evidence, EvidenceType, Importance, Match,
                              MatchStatus, MatchType, ParseabilityReport, Requirement)
from ..text.lexicon import label

RECOMMENDER_VERSION = "recommendations-2.1.0"
VERIFY_TRUTH = "Include only if it is accurate and you can evidence it in an interview."
MAX_PER_KIND = 6


def _ev_map(cand: Candidate) -> dict[str, Evidence]:
    return {e.evidence_id: e for e in cand.evidence}


def _spans(ids: list[str], ev: dict[str, Evidence], limit: int = 3) -> list[str]:
    return [re.sub(r"\s+", " ", ev[i].source_location.text_span).strip() for i in ids[:limit] if i in ev]


def generate(reqs: list[Requirement], matches: list[Match], cand: Candidate, elig: EligibilityResult,
             parse: ParseabilityReport, role_title: str | None, employer: str | None) -> list[Recommendation]:
    ev = _ev_map(cand)
    by_req = {r.requirement_id: r for r in reqs}
    out: list[Recommendation] = []
    n = 0

    def add(kind: RecommendationKind, priority: str, title: str, rationale: str, *, req_ids=None, ev_ids=None, edit=None) -> None:
        nonlocal n
        if sum(1 for r in out if r.kind == kind) >= MAX_PER_KIND:
            return
        n += 1
        out.append(Recommendation(recommendation_id=f"REC-{n:03d}", kind=kind, priority=priority, title=title, rationale=rationale,
                                  requirement_ids=req_ids or [], evidence_ids=ev_ids or [], edit=edit))

    # 1. critical application gaps: required requirements with no located evidence
    for m in matches:
        r = by_req[m.requirement_id]
        if r.importance == Importance.required and r.weight >= 1.0 and m.match_status == MatchStatus.no_evidence_located:
            add(RecommendationKind.critical_application_gap, "critical",
                f"No resume evidence located for: {r.text[:90]}",
                "The employer states this as a required qualification and the resume does not currently show it. "
                "This does not mean you lack it; if you have it, make it explicit with a dated, concrete example.",
                req_ids=[r.requirement_id],
                edit=RecommendedEdit(original_text=None,
                                     proposed_text=f"Add a bullet under the most relevant role describing your experience with {label(r.normalised_concept)}, including scope, action and outcome.",
                                     job_requirement_addressed=r.text, candidate_evidence_supporting=[],
                                     verification_required="Only add this if you have the experience; be ready to give a specific example."))

    # 2. evidence that should be made more explicit: partial/weak matches
    for m in matches:
        r = by_req[m.requirement_id]
        if r.importance not in (Importance.required, Importance.preferred):
            continue
        if m.match_status == MatchStatus.no_evidence_located and r.importance == Importance.required and r.weight < 1.0:
            add(RecommendationKind.make_evidence_explicit, "medium",
                f"Consider addressing the role narrative: {r.text[:70]}",
                "This comes from the role description rather than the stated qualifications, so treat it as context for tailoring rather than a hard gap.",
                req_ids=[r.requirement_id], edit=None)
            continue
        if m.match_status in (MatchStatus.partial, MatchStatus.weak) and m.evidence_ids:
            spans = _spans(m.evidence_ids, ev, 1)
            if not spans:
                continue
            add(RecommendationKind.make_evidence_explicit, "high",
                f"Strengthen the evidence for: {r.text[:80]}",
                f"The resume touches this requirement but the evidence is {m.match_status.value}. {m.reason}",
                req_ids=[r.requirement_id], ev_ids=m.evidence_ids[:3],
                edit=RecommendedEdit(original_text=spans[0],
                                     proposed_text=f"{spans[0]} — extend this line with the scope and measurable outcome that show {label(r.normalised_concept)}.",
                                     job_requirement_addressed=r.text, candidate_evidence_supporting=spans,
                                     verification_required=VERIFY_TRUTH))

    # 3. terminology alignment: transferable or alternative-concept matches
    for m in matches:
        r = by_req[m.requirement_id]
        if m.match_type == MatchType.transferable and m.evidence_ids:
            spans = _spans(m.evidence_ids, ev, 1)
            if not spans:
                continue
            add(RecommendationKind.terminology_alignment, "high",
                f"Use the employer's terminology for '{label(r.normalised_concept)}'",
                "Your evidence is related but uses different wording, so a recruiter search or reviewer may not connect it. "
                "Where it is accurate, mirror the job's own phrasing.",
                req_ids=[r.requirement_id], ev_ids=m.evidence_ids[:2],
                edit=RecommendedEdit(original_text=spans[0],
                                     proposed_text=re.sub(r"\s+", " ", f"{spans[0]} (describe this using the job's term '{label(r.normalised_concept)}' if that is what it was)"),
                                     job_requirement_addressed=r.text, candidate_evidence_supporting=spans,
                                     verification_required="Do not relabel work as something it was not."))

    # 4. quantification: matched requirements whose evidence has no numbers
    for m in matches:
        r = by_req[m.requirement_id]
        if r.importance != Importance.required or not m.evidence_ids:
            continue
        items = [ev[i] for i in m.evidence_ids if i in ev]
        if items and not any(i.quantified for i in items):
            spans = _spans(m.evidence_ids, ev, 1)
            if not spans:
                continue
            add(RecommendationKind.quantify_achievement, "medium",
                f"Quantify the outcome for: {r.text[:70]}",
                "The supporting line describes activity but no measurable result. A number, scale or time frame makes the evidence verifiable.",
                req_ids=[r.requirement_id], ev_ids=m.evidence_ids[:2],
                edit=RecommendedEdit(original_text=spans[0],
                                     proposed_text=f"{spans[0]} — add the real figure (scale, %, count, or time saved) if you have it.",
                                     job_requirement_addressed=r.text, candidate_evidence_supporting=spans,
                                     verification_required="Use only figures you can substantiate."))

    # 5. skills asserted without context
    skill_only = [e for e in cand.evidence if e.evidence_type == EvidenceType.skill_mention]
    achievement_concepts = {c for e in cand.evidence if e.evidence_type in (EvidenceType.employment_achievement, EvidenceType.employment_role) for c in e.normalised_concepts}
    needed = {r.normalised_concept for r in reqs if r.importance in (Importance.required, Importance.preferred)}
    for e in skill_only:
        bare = [c for c in e.normalised_concepts if c in needed and c not in achievement_concepts]
        if bare:
            add(RecommendationKind.skill_needs_context, "medium",
                f"Give context for listed skill: {label(bare[0])}",
                "This skill appears only in a list. Reviewers weight demonstrated use more heavily than a keyword.",
                ev_ids=[e.evidence_id],
                edit=RecommendedEdit(original_text=re.sub(r"\s+", " ", e.source_location.text_span).strip(),
                                     proposed_text=f"Move {label(bare[0])} into a role bullet that shows where you used it and what changed.",
                                     job_requirement_addressed=None, candidate_evidence_supporting=[],
                                     verification_required=VERIFY_TRUTH))

    # 6. targeted professional summary assembled only from confirmed evidence
    strong = [m for m in matches if m.match_status in (MatchStatus.confirmed, MatchStatus.strong) and m.evidence_ids
              and by_req[m.requirement_id].importance in (Importance.required, Importance.preferred)]
    if strong:
        concepts = []
        for m in strong[:4]:
            c = label(by_req[m.requirement_id].normalised_concept)
            if c not in concepts:
                concepts.append(c)
        target = f"{role_title} at {employer}" if role_title and employer else (role_title or "this role")
        add(RecommendationKind.targeted_summary, "high",
            "Retarget the professional summary to this role",
            "A summary that names the role and leads with your already-evidenced strengths helps a human reviewer in the first pass.",
            req_ids=[by_req[m.requirement_id].requirement_id for m in strong[:4]],
            ev_ids=[i for m in strong[:2] for i in m.evidence_ids[:1]],
            edit=RecommendedEdit(original_text=next((re.sub(r"\s+", " ", e.source_location.text_span).strip() for e in cand.evidence if e.evidence_type == EvidenceType.summary_statement), None),
                                 proposed_text=f"Summary tailored to {target}: lead with " + "; ".join(concepts) + " — each already evidenced in your roles below.",
                                 job_requirement_addressed=None,
                                 candidate_evidence_supporting=[i for m in strong[:3] for i in _spans(m.evidence_ids, ev, 1)],
                                 verification_required="Keep every claim traceable to a role on the resume."))

    # 7. section ordering and parseability
    if not parse.section_order_clear or parse.table_or_column_interference or parse.hidden_text_suspected or parse.parseability_score < 80:
        issues = []
        if not parse.section_order_clear:
            issues.append("experience does not clearly precede education")
        if parse.table_or_column_interference:
            issues.append("tables or columns may scramble reading order")
        if parse.hidden_text_suspected:
            issues.append("very small or white text was detected")
        if parse.missing_dates:
            issues.append(f"{parse.missing_dates} role(s) appear to be missing dates")
        add(RecommendationKind.section_ordering, "high" if parse.parseability_score < 60 else "medium",
            "Simplify the document so it extracts reliably",
            "Parseability affects whether your content can be read at all. It is not a measure of your suitability: " + "; ".join(issues) + ".",
            edit=RecommendedEdit(original_text=None,
                                 proposed_text="Use a single-column layout with one reading order, standard headings (Summary, Experience, Skills, Education), dated roles, and no hidden or white text.",
                                 job_requirement_addressed=None, candidate_evidence_supporting=[],
                                 verification_required="Re-upload and re-check the parseability report after editing."))

    # 8. content that can be reduced
    unused = [e for e in cand.evidence if e.evidence_type in (EvidenceType.employment_achievement, EvidenceType.skill_mention)
              and not (set(e.normalised_concepts) & needed)]
    if len(unused) >= 3:
        add(RecommendationKind.reduce_or_remove, "low",
            f"Consider tightening {len(unused)} line(s) unrelated to this role's stated requirements",
            "These lines do not map to any requirement in this job document. Shortening them makes room for the evidence this employer asked for.",
            ev_ids=[e.evidence_id for e in unused[:5]],
            edit=RecommendedEdit(original_text=re.sub(r"\s+", " ", unused[0].source_location.text_span).strip(),
                                 proposed_text="Shorten or merge this line for this application; keep it in your master resume.",
                                 job_requirement_addressed=None, candidate_evidence_supporting=[],
                                 verification_required="Relevance is job-specific; do not delete accurate history from your master resume."))

    # 9. application fields needing care
    if elig.status in (EligibilityStatus.additional_information_required, EligibilityStatus.human_review_required,
                       EligibilityStatus.does_not_meet_declared_eligibility):
        for f in elig.findings:
            if f.status != EligibilityStatus.meets_declared_eligibility:
                add(RecommendationKind.application_field_care, "critical",
                    f"Answer carefully: {f.explanation[:100]}",
                    "Eligibility answers are evaluated literally from what you enter, never inferred from your resume. "
                    "Answer exactly and truthfully.",
                    edit=None)
    elig_reqs = [r for r in reqs if r.importance == Importance.eligibility]
    for r in elig_reqs:
        add(RecommendationKind.application_field_care, "high",
            f"Prepare an explicit answer for: {r.text[:90]}",
            "This is an eligibility criterion in the job document. It cannot be assessed from a resume, so expect an application question.",
            req_ids=[r.requirement_id], edit=None)
    return out
