"""Explainable component scoring.

- Every awarded point references a match, which references evidence spans.
- Unscorable / contextual / eligibility / not-assessable requirements are excluded from
  denominators and listed, never scored as zero.
- Eligibility is a separate categorical result and never enters the weighted index.
- Confidence lowers certainty and raises review; it never lowers the score.
- Components are built from the rubric's weight keys, so a rubric version defines the
  component set.
"""
from __future__ import annotations

from ..schemas.models import (ApplicationAnswer, ComponentScore, Contribution, EligibilityRule, Importance, Match, MatchStatus,
                              ParseabilityReport, Requirement, RequirementCategory, RubricConfig, ScoreResult)
from .rubrics import load_thresholds

SCORING_VERSION = "scoring-2.1.0"
STATUS_CREDIT = {MatchStatus.confirmed: 1.0, MatchStatus.strong: 0.85, MatchStatus.partial: 0.5, MatchStatus.weak: 0.2}

SKILL_CATS = {RequirementCategory.skill, RequirementCategory.technical_knowledge, RequirementCategory.certification,
              RequirementCategory.qualification, RequirementCategory.communication}
EXPERIENCE_CATS = {RequirementCategory.required_experience, RequirementCategory.preferred_experience,
                   RequirementCategory.domain_knowledge, RequirementCategory.delivery}
LEADERSHIP_CATS = {RequirementCategory.leadership, RequirementCategory.stakeholder_management}
LEADERSHIP_CONCEPTS = {"people_leadership", "people_management_of_managers", "exec_reporting", "product_strategy",
                       "org_alignment", "delivery_leadership", "multi_market_platform"}
EXCLUDED_IMPORTANCE = {Importance.unscorable, Importance.contextual, Importance.eligibility}


def _credit(m: Match) -> float:
    """Status credit scaled by coverage (duration ratio or transferable discount)."""
    return round(STATUS_CREDIT.get(m.match_status, 0.0) * m.coverage, 3)


def _coverage_component(name: str, weight: float, reqs: list[Requirement], matches: dict[str, Match], explanation: str) -> ComponentScore:
    contribs, excluded, available, awarded = [], [], 0.0, 0.0
    for r in reqs:
        m = matches.get(r.requirement_id)
        if m is None:
            continue
        if m.match_status in (MatchStatus.not_assessable, MatchStatus.human_review_required) or r.importance in EXCLUDED_IMPORTANCE:
            excluded.append(r.requirement_id)
            continue
        pts = 10.0 * r.weight
        got = round(pts * _credit(m), 2)
        available += pts
        awarded += got
        contribs.append(Contribution(requirement_id=r.requirement_id, match_id=m.match_id, points_available=round(pts, 2),
                                     points_awarded=got, explanation=f"{m.match_status.value}: {m.reason}"))
    raw = round(100 * awarded / available, 1) if available else 0.0
    note = explanation if available else explanation + " No assessable requirements in this component; it contributes 0 and is flagged for review."
    return ComponentScore(component=name, weight_percent=weight, raw_score=raw, weighted_points=round(raw * weight / 100, 2),
                          contributions=contribs, excluded_requirement_ids=excluded, explanation=note)


def _strength_component(name: str, weight: float, matches: list[Match], explanation: str) -> ComponentScore:
    scored = [m for m in matches if m.match_status in STATUS_CREDIT and m.evidence_ids]
    raw = round(100 * sum(m.evidence_strength for m in scored) / len(scored), 1) if scored else 0.0
    return ComponentScore(component=name, weight_percent=weight, raw_score=raw, weighted_points=round(raw * weight / 100, 2),
                          contributions=[Contribution(requirement_id=m.requirement_id, match_id=m.match_id, points_available=10,
                                                      points_awarded=round(10 * m.evidence_strength, 2),
                                                      explanation=f"evidence strength {m.evidence_strength}") for m in scored],
                          explanation=explanation)


def _flat_component(name: str, weight: float, raw: float, explanation: str) -> ComponentScore:
    return ComponentScore(component=name, weight_percent=weight, raw_score=raw, weighted_points=round(raw * weight / 100, 2), explanation=explanation)


def score(reqs: list[Requirement], matches: list[Match], parse: ParseabilityReport, answers: list[ApplicationAnswer],
          rules: list[EligibilityRule], rubric: RubricConfig) -> ScoreResult:
    th = load_thresholds()
    by_id = {m.requirement_id: m for m in matches}
    w = rubric.weights
    required = [r for r in reqs if r.importance == Importance.required]
    preferred = [r for r in reqs if r.importance == Importance.preferred]
    both = required + preferred
    leadership = [r for r in both if r.category in LEADERSHIP_CATS or r.normalised_concept in LEADERSHIP_CONCEPTS]
    needed = {r.question_id for r in rules}
    have = {a.question_id for a in answers}
    completeness = 100.0 if not needed else round(100 * len(needed & have) / len(needed), 1)

    builders = {
        "required_qualification_coverage": lambda k: _coverage_component(
            k, w[k], required, by_id, "Weighted share of assessable required requirements supported by cited resume evidence."),
        "preferred_qualification_coverage": lambda k: _coverage_component(
            k, w[k], preferred, by_id, "Weighted share of assessable preferred requirements supported by evidence. Never compensates for eligibility."),
        "relevant_experience_alignment": lambda k: _coverage_component(
            k, w[k], [r for r in both if r.category in EXPERIENCE_CATS], by_id,
            "Evidence for experience, domain and delivery requirements, including computed duration where the job states a threshold."),
        "demonstrated_skill_evidence": lambda k: _coverage_component(
            k, w[k], [r for r in both if r.category in SKILL_CATS], by_id,
            "Evidence for skills, technical knowledge, qualifications, certifications and communication requirements."),
        "leadership_and_operating_scope": lambda k: _coverage_component(
            k, w[k], leadership, by_id,
            "Evidence for leadership, people-management, executive exposure, strategy and cross-organisation scope requirements."),
        "achievement_and_impact_evidence": lambda k: _strength_component(
            k, w[k], matches,
            "Average evidence strength (context, action, outcome, quantification, repetition) across matched requirements. Unquantified achievements still earn credit."),
        "application_completeness": lambda k: _flat_component(
            k, w[k], completeness,
            f"{len(needed & have)} of {len(needed)} employer-declared eligibility questions answered." if needed else "No employer-declared questions supplied; treated as complete."),
        "resume_parseability": lambda k: _flat_component(
            k, w[k], parse.parseability_score, "Document-readiness signal only; not a measure of candidate quality."),
    }
    comps = [builders[k](k) for k in w if k in builders]
    unknown_keys = [k for k in w if k not in builders]
    if unknown_keys:
        raise ValueError(f"rubric references unknown components: {unknown_keys}")

    suppressed = not parse.text_extraction_success
    index = 0.0 if suppressed else round(sum(c.weighted_points for c in comps), 1)
    band = next(b["label"] for b in th["bands"] if index >= b["min"])
    if suppressed:
        band = "Not assessable - OCR required"
    confs = [m.confidence for m in matches if m.match_status in STATUS_CREDIT]
    overall_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
    return ScoreResult(alignment_index=index, band_label=band, band_caveat=th["band_caveat"], components=comps,
                       overall_confidence=overall_conf, rubric_id=rubric.rubric_id, rubric_version=rubric.rubric_version,
                       rubric_hash=rubric.rubric_hash, qualification_scoring_suppressed=suppressed,
                       suppression_reason="Text could not be extracted (image-only or failed document); OCR unavailable." if suppressed else None)
