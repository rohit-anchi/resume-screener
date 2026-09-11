"""Deterministic eligibility engine (ADR-007).

Inputs: explicit application answers + employer-declared rules with a stated legal basis.
Never reads resume text. Output is categorical.
"""
from __future__ import annotations

from ..schemas.models import ApplicationAnswer, EligibilityFinding, EligibilityResult, EligibilityRule, EligibilityStatus

ENGINE_VERSION = "eligibility-2.0.0"


def _compare(op: str, answer, expected) -> bool | None:
    try:
        if op == "equals":
            return str(answer).strip().lower() == str(expected).strip().lower()
        if op == "not_equals":
            return str(answer).strip().lower() != str(expected).strip().lower()
        if op == "in":
            return str(answer).strip().lower() in [str(x).strip().lower() for x in expected]
        if op == "gte":
            return float(answer) >= float(expected)
        if op == "lte":
            return float(answer) <= float(expected)
        if op == "truthy":
            return str(answer).strip().lower() in ("yes", "true", "y", "1")
    except (TypeError, ValueError):
        return None
    return None


def evaluate(rules: list[EligibilityRule], answers: list[ApplicationAnswer]) -> EligibilityResult:
    if not rules:
        return EligibilityResult(status=EligibilityStatus.not_evaluated, findings=[])
    by_q: dict[str, list[ApplicationAnswer]] = {}
    for a in answers:
        by_q.setdefault(a.question_id, []).append(a)
    findings: list[EligibilityFinding] = []
    for r in rules:
        got = by_q.get(r.question_id, [])
        if not got:
            findings.append(EligibilityFinding(rule_id=r.rule_id, status=EligibilityStatus.additional_information_required, explanation=f"No answer supplied for '{r.description}'."))
            continue
        distinct = {str(a.answer).strip().lower() for a in got}
        if len(distinct) > 1:
            findings.append(EligibilityFinding(rule_id=r.rule_id, status=EligibilityStatus.human_review_required, explanation=f"Conflicting answers supplied for '{r.description}': {sorted(distinct)}.", answer_used=[a.answer for a in got]))
            continue
        res = _compare(r.operator, got[0].answer, r.expected)
        if res is None:
            findings.append(EligibilityFinding(rule_id=r.rule_id, status=EligibilityStatus.human_review_required, explanation=f"Answer '{got[0].answer}' could not be evaluated against rule '{r.description}'.", answer_used=got[0].answer))
        elif res:
            findings.append(EligibilityFinding(rule_id=r.rule_id, status=EligibilityStatus.meets_declared_eligibility, explanation=f"Answer satisfies declared rule '{r.description}' (basis: {r.legal_basis}).", answer_used=got[0].answer))
        else:
            findings.append(EligibilityFinding(rule_id=r.rule_id, status=EligibilityStatus.does_not_meet_declared_eligibility, explanation=f"Answer does not satisfy declared rule '{r.description}' (basis: {r.legal_basis}). Human review required before any adverse action.", answer_used=got[0].answer))
    statuses = [f.status for f in findings]
    if EligibilityStatus.does_not_meet_declared_eligibility in statuses:
        overall = EligibilityStatus.does_not_meet_declared_eligibility
    elif EligibilityStatus.human_review_required in statuses:
        overall = EligibilityStatus.human_review_required
    elif EligibilityStatus.additional_information_required in statuses:
        overall = EligibilityStatus.additional_information_required
    else:
        overall = EligibilityStatus.meets_declared_eligibility
    return EligibilityResult(status=overall, findings=findings)
