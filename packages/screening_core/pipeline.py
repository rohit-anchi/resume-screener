"""Screening orchestrator: ingestion -> extraction -> matching -> eligibility -> scoring -> profile -> findings."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from . import __version__
from .eligibility.engine import ENGINE_VERSION, evaluate
from .evidence.extractor import EVIDENCE_EXTRACTOR_VERSION, build_candidate
from .ingestion.extract import PARSER_VERSION
from .ingestion.service import ingest
from .llm.adapter import PROMPT_REGISTRY_VERSION, NullLLMAdapter
from .matching.matcher import MATCHER_VERSION, match_requirements
from .profiles.loader import load_profile, render_scenarios
from .requirements.extractor import EXTRACTOR_VERSION, extract_requirements
from .schemas.models import (SCHEMA_VERSION, Candidate, EligibilityStatus, Finding, HumanAction, Importance, IngestedDocument, Job, Match, MatchStatus, Mode,
                             Requirement, ScreeningRequest, ScreeningResult)
from .scoring.engine import SCORING_VERSION, score
from .scoring.rubrics import load_rubric

CANDIDATE_LABELS = {
    MatchStatus.confirmed: "Strong evidence", MatchStatus.strong: "Strong evidence", MatchStatus.partial: "Partial evidence", MatchStatus.weak: "Partial evidence",
    MatchStatus.no_evidence_located: "No evidence located", MatchStatus.contradictory: "Ambiguous", MatchStatus.not_assessable: "Not assessable",
    MatchStatus.human_review_required: "Ambiguous",
}
LIMITATIONS = [
    "This is an evidence-based, platform-informed application readiness assessment. It does not reproduce Greenhouse, Lever, Workday, SAP SuccessFactors or any employer's private configuration.",
    "'No evidence located' means the submitted documents did not show it; it does not mean the candidate lacks it.",
    "Eligibility uses only explicit application answers and employer-declared rules; nothing is inferred from the resume.",
    "Protected and identifying attributes are removed before evaluation and do not affect any score.",
    "Optional or configured platform capabilities are labelled; they may not be enabled by a given employer.",
    "Human review is required before any adverse decision; this system does not decline candidates.",
]


def build_job(job_id: str, title: str, filename: str, data: bytes, media_type: str | None = None) -> Job:
    doc = ingest("job_description", filename, data, media_type)
    reqs = extract_requirements(doc.document_id, doc.extracted_text) if doc.accepted else []
    return Job(job_id=job_id, title=title, document=doc, requirements=reqs)


def build_candidate_from_bytes(candidate_id: str, filename: str, data: bytes, media_type: str | None = None, *, today: date | None = None) -> Candidate:
    doc = ingest("resume", filename, data, media_type)
    if not doc.accepted:
        from .evidence.extractor import assess_parseability
        parse = assess_parseability(doc, [], [], [], name_found=False, contact_found=False)
        return Candidate(candidate_id=candidate_id, document=doc, evidence=[], parseability=parse, contradictions=[])
    return build_candidate(candidate_id, doc, today=today)


def _findings(reqs: list[Requirement], matches: list[Match], cand: Candidate, mode: Mode, score_result) -> list[Finding]:
    ev = {e.evidence_id: e for e in cand.evidence}
    effects: dict[str, str] = {}
    for c in score_result.components:
        for k in c.contributions:
            effects.setdefault(k.requirement_id, f"{k.points_awarded} of {k.points_available} points in {c.component}")
    out = []
    for r, m in zip(reqs, matches):
        if r.importance == Importance.contextual:
            continue
        evs = [ev[i] for i in m.evidence_ids if i in ev]
        missing = None
        if m.match_status == MatchStatus.no_evidence_located:
            missing = "Candidate input required: evidence for this requirement was not located in the resume." if mode == Mode.candidate else "No resume evidence; verify with candidate."
        elif m.match_status == MatchStatus.not_assessable and r.importance == Importance.eligibility:
            missing = "Candidate input required: answer the corresponding application question."
        out.append(Finding(requirement_id=r.requirement_id, requirement_text=r.text.strip(), importance=r.importance, status=m.match_status,
                           candidate_label=("Candidate input required" if missing and "Candidate input" in missing else CANDIDATE_LABELS[m.match_status]),
                           evidence_excerpts=[e.source_location.text_span.strip() for e in evs], locations=[e.source_location for e in evs], confidence=m.confidence,
                           explanation=m.reason, missing_information=missing, verification_question=m.verification_question if mode != Mode.candidate else None,
                           score_effect=effects.get(r.requirement_id), human_review_required=m.human_review_required))
    return out


def _review_triggers(reqs, matches, cand: Candidate, elig, score_result) -> list[str]:
    t = []
    by = {r.requirement_id: r for r in reqs}
    for m in matches:
        r = by[m.requirement_id]
        if m.human_review_required and r.importance in (Importance.required, Importance.eligibility):
            t.append(f"{r.requirement_id}: {m.match_status.value} on a {r.importance.value} requirement")
        if m.match_type.value == "transferable":
            t.append(f"{r.requirement_id}: transferable (inferred) match")
        if r.importance == Importance.unscorable:
            t.append(f"{r.requirement_id}: potentially inappropriate criterion excluded")
    if elig.status in (EligibilityStatus.does_not_meet_declared_eligibility, EligibilityStatus.human_review_required):
        t.append(f"eligibility: {elig.status.value}")
    if cand.contradictions:
        t.extend(f"resume: {c}" for c in cand.contradictions)
    if cand.parseability and (cand.parseability.injection_suspected or cand.parseability.hidden_text_suspected):
        t.append("document: suspicious content flagged (treated as data)")
    if score_result.overall_confidence < 0.6:
        t.append("overall confidence below review threshold")
    return t


def run_screening(job: Job, cand: Candidate, req: ScreeningRequest, *, today: date | None = None, llm=None) -> ScreeningResult:
    llm = llm or NullLLMAdapter()
    rubric = load_rubric(req.rubric_id)
    matches = match_requirements(job.requirements, cand.evidence, review_confidence=rubric.confidence_review_threshold, near_tolerance_months=rubric.near_threshold_tolerance_months, today=today)
    elig = evaluate(req.employer_rules + job.eligibility_rules, req.application_answers)
    sr = score(job.requirements, matches, cand.parseability, req.application_answers, req.employer_rules + job.eligibility_rules, rubric)
    prof = load_profile(req.screening_profile)
    findings = _findings(job.requirements, matches, cand, req.mode, sr)
    triggers = _review_triggers(job.requirements, matches, cand, elig, sr)
    if elig.status == EligibilityStatus.does_not_meet_declared_eligibility or sr.qualification_scoring_suppressed:
        action = HumanAction.hold_for_review
    elif elig.status == EligibilityStatus.additional_information_required or any(m.match_status == MatchStatus.no_evidence_located and job.requirements[i].importance == Importance.required for i, m in enumerate(matches)):
        action = HumanAction.request_additional_information
    elif triggers:
        action = HumanAction.hold_for_review
    else:
        action = HumanAction.move_forward
    return ScreeningResult(
        screening_id=f"SCR-{uuid.uuid4().hex[:12]}", request=req, job_title=job.title, requirements=job.requirements, evidence=cand.evidence, matches=matches,
        eligibility=elig, score=sr, parseability=cand.parseability, findings=findings, scenarios=render_scenarios(prof), profile=prof,
        recommended_human_action=action, review_triggers=triggers, document_findings=cand.document.findings + job.document.findings,
        versions={"schema": SCHEMA_VERSION, "core": __version__, "parser": PARSER_VERSION, "requirement_extractor": EXTRACTOR_VERSION, "evidence_extractor": EVIDENCE_EXTRACTOR_VERSION,
                  "matcher": MATCHER_VERSION, "eligibility": ENGINE_VERSION, "scoring": SCORING_VERSION, "rubric": f"{rubric.rubric_id}@{rubric.rubric_version}#{rubric.rubric_hash}",
                  "profile": prof.profile_id, "prompts": PROMPT_REGISTRY_VERSION, "llm": f"{llm.provider}:{llm.model_version}",
                  "resume_sha256": cand.document.sha256, "jd_sha256": job.document.sha256},
        limitations=LIMITATIONS, created_at=datetime.now(timezone.utc).isoformat(),
    )
