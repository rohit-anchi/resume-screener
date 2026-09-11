"""Two-input assessment orchestrator: LinkedIn job PDF + resume -> Assessment."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from .linkedin.builder import BUILDER_VERSION, build_job_document, requirement_sections
from .pipeline import LIMITATIONS, run_screening
from .questions.engine import QUESTIONS_VERSION, generate as gen_questions
from .recommendations.engine import RECOMMENDER_VERSION, generate as gen_recommendations
from .requirements.extractor import extract_requirements
from .schemas.jobdoc import Assessment, CriticalGap, JobDocument
from .schemas.models import (ApplicationAnswer, Candidate, DocumentFinding, EligibilityRule, EligibilityStatus, Importance,
                             IngestedDocument, Job, MatchStatus, Mode, ScreeningRequest, ScreeningResult)

ASSESSMENT_VERSION = "assessment-2.1.0"
EXTRA_LIMITATIONS = [
    "Job requirements are read only from employer-authored content in the supplied LinkedIn PDF. LinkedIn-generated match statements, "
    "applicant statistics, candidate demographics, premium insights, promotions and similar-job blocks are excluded from scoring and retained only for audit.",
    "The listing source and the application platform are different things. The application platform is detected from the application link; "
    "if it has no approved knowledge profile, a platform-neutral assessment is used and no other ATS profile is substituted.",
    "Employer configuration inside any ATS is private and is not reproduced or predicted here.",
]


def job_document_from_pdf(filename: str, data: bytes) -> JobDocument:
    return build_job_document(filename, data)


def job_from_document(jd: JobDocument) -> Job:
    """Adapt a JobDocument into the core Job model so one screening pipeline serves both inputs."""
    findings = [DocumentFinding(code="extraction_warning", severity="warning", message=w) for w in jd.extraction_warnings]
    doc = IngestedDocument(document_id=jd.job_document_id, kind="job_description", filename=jd.filename,
                           media_type="application/pdf", sha256=jd.sha256, byte_size=0, page_count=jd.page_count,
                           extracted_text=jd.employer_text, redacted_text=jd.employer_text, accepted=True,
                           findings=findings, parser_version=jd.parser_version)
    reqs = extract_requirements(jd.job_document_id, jd.employer_text, requirement_sections(jd))
    title = " - ".join([p for p in (jd.role_title, jd.employer) if p]) or jd.filename
    return Job(job_id=jd.job_document_id, title=title, document=doc, requirements=reqs)


def eligibility_rules_from_job(job: Job) -> list[EligibilityRule]:
    """One rule per eligibility criterion stated in the employer's job document.

    The legal basis cites the employer's own wording; nothing is inferred from the resume.
    """
    return [EligibilityRule(rule_id=r.requirement_id, question_id=r.requirement_id,
                            description=r.text[:200], operator="truthy", expected=True,
                            legal_basis=f"Stated by the employer in the job document ({r.source_location.section or 'employer content'}).")
            for r in job.requirements if r.importance == Importance.eligibility]


def _critical_gaps(reqs, matches, elig) -> list[CriticalGap]:
    by = {r.requirement_id: r for r in reqs}
    gaps: list[CriticalGap] = []
    for f in elig.findings:
        if f.status == EligibilityStatus.does_not_meet_declared_eligibility:
            gaps.append(CriticalGap(requirement_id=f.rule_id, requirement_text=f.explanation, status=f.status.value,
                                    why_critical="A declared eligibility criterion is not met by the supplied answer.",
                                    what_would_resolve_it="Correct the application answer if it was entered in error, or confirm the employer's flexibility. Human review is required before any adverse decision."))
    for m in matches:
        r = by[m.requirement_id]
        # only requirements the employer stated in a qualification/eligibility section can be critical;
        # narrative role prose is reported as missing or ambiguous evidence instead
        if r.importance != Importance.required or r.weight < 1.0:
            continue
        if m.match_status == MatchStatus.no_evidence_located:
            gaps.append(CriticalGap(requirement_id=r.requirement_id, requirement_text=r.text, status=m.match_status.value,
                                    why_critical="Stated as a required qualification with no evidence located in the resume.",
                                    what_would_resolve_it="Add a dated, specific example if you have this experience, or prepare to address it directly."))
        elif m.match_status == MatchStatus.contradictory:
            gaps.append(CriticalGap(requirement_id=r.requirement_id, requirement_text=r.text, status=m.match_status.value,
                                    why_critical="The resume both suggests and denies this capability.",
                                    what_would_resolve_it="Resolve the wording so the document is internally consistent."))
        elif m.computed_duration_months is not None and m.coverage < 1.0:
            gaps.append(CriticalGap(requirement_id=r.requirement_id, requirement_text=r.text, status=m.match_status.value,
                                    why_critical=f"Stated duration threshold not met by dated evidence ({m.computed_duration_months} months computed).",
                                    what_would_resolve_it="Include earlier relevant roles or clarify concurrent responsibility if the dated history understates it."))
    return gaps


def _missing_or_ambiguous(reqs, matches, cand) -> list[str]:
    by = {r.requirement_id: r for r in reqs}
    out: list[str] = []
    for m in matches:
        r = by[m.requirement_id]
        if m.match_status == MatchStatus.no_evidence_located:
            out.append(f"{r.requirement_id}: no evidence located for '{r.text[:80]}' (missing evidence, not confirmed absence)")
        elif m.match_status == MatchStatus.not_assessable and r.importance == Importance.eligibility:
            out.append(f"{r.requirement_id}: '{r.text[:80]}' cannot be assessed from a resume; requires an explicit application answer")
        elif m.match_type.value == "transferable":
            out.append(f"{r.requirement_id}: only transferable (inferred) evidence for '{r.text[:70]}'; treat as unconfirmed")
        elif m.human_review_required and r.importance in (Importance.required, Importance.preferred):
            out.append(f"{r.requirement_id}: ambiguous evidence for '{r.text[:70]}' — {m.reason[:80]}")
    out.extend(f"resume: {c}" for c in cand.contradictions)
    for b in (0,):
        pass
    return out


def run_assessment(jd: JobDocument, cand: Candidate, *, mode: Mode = Mode.candidate, answers: list[ApplicationAnswer] | None = None,
                   employer_rules: list[EligibilityRule] | None = None, rubric_id: str = "default",
                   today: date | None = None) -> tuple[Assessment, ScreeningResult, Job]:
    job = job_from_document(jd)
    req = ScreeningRequest(job_id=job.job_id, candidate_id=cand.candidate_id, screening_profile=jd.ats.selected_profile_id,
                           rubric_id=rubric_id, mode=mode, application_answers=answers or [], employer_rules=employer_rules or [])
    screening = run_screening(job, cand, req, today=today)
    recs = gen_recommendations(job.requirements, screening.matches, cand, screening.eligibility, screening.parseability,
                               jd.role_title, jd.employer)
    qs = gen_questions(jd, job.requirements, screening.matches, cand, screening.eligibility)
    gaps = _critical_gaps(job.requirements, screening.matches, screening.eligibility)
    versions = dict(screening.versions)
    versions.update({"assessment": ASSESSMENT_VERSION, "linkedin_builder": BUILDER_VERSION,
                     "recommendations": RECOMMENDER_VERSION, "questions": QUESTIONS_VERSION,
                     "job_pdf_sha256": jd.sha256, "ats_platform": jd.ats.application_platform.value})
    a = Assessment(
        assessment_id=f"ASM-{uuid.uuid4().hex[:12]}", created_at=datetime.now(timezone.utc).isoformat(), mode=mode.value,
        job=jd, candidate_id=cand.candidate_id, resume_document_id=cand.document.document_id, screening_id=screening.screening_id,
        ats=jd.ats, profile_id=screening.profile.profile_id, profile_display_name=screening.profile.display_name,
        eligibility_status=screening.eligibility.status.value,
        alignment_index=None if screening.score.qualification_scoring_suppressed else screening.score.alignment_index,
        band_label=screening.score.band_label,
        component_scores={c.component: c.raw_score for c in screening.score.components},
        evidence_confidence=screening.score.overall_confidence, critical_gaps=gaps,
        missing_or_ambiguous=_missing_or_ambiguous(job.requirements, screening.matches, cand),
        recommendations=recs, questions=qs, scenario_ids=[s.scenario_id for s in screening.scenarios],
        versions=versions, limitations=LIMITATIONS + EXTRA_LIMITATIONS,
    )
    return a, screening, job
