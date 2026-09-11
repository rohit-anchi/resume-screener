"""Requirement-to-evidence mapping.

Statuses are assigned deterministically from visible lexicon relationships.
`no_evidence_located` is never converted into absence; `contradictory` only
arises from an explicit statement of absence in the resume.
"""
from __future__ import annotations

from datetime import date

from ..schemas.models import Evidence, EvidenceType, Importance, Match, MatchStatus, MatchType, Requirement, RequirementCategory
from ..text import dates
from ..text.lexicon import TRANSFERABLE, label

MATCHER_VERSION = "matcher-2.0.0"
STATUS_ORDER = [MatchStatus.confirmed, MatchStatus.strong, MatchStatus.partial, MatchStatus.weak]  # best -> worst
UNASSESSABLE_FROM_RESUME = {RequirementCategory.work_authorisation, RequirementCategory.location_or_work_arrangement, RequirementCategory.travel}


def _strength(evs: list[Evidence]) -> float:
    """Evidence strength rewards context/outcome/quantification/repetition, never verbosity."""
    if not evs:
        return 0.0
    kinds = {e.evidence_type for e in evs}
    s = 0.35
    if EvidenceType.employment_achievement in kinds:
        s += 0.3
    if EvidenceType.employment_role in kinds or EvidenceType.certification in kinds or EvidenceType.education in kinds:
        s += 0.15
    if any(e.quantified for e in evs):
        s += 0.1
    roles = {(e.employer, e.role) for e in evs if e.role}
    if len(roles) >= 2:
        s += 0.1
    return min(1.0, round(s, 2))


def _duration_months(evs: list[Evidence], today: date | None) -> tuple[int | None, bool]:
    periods, uncertain = [], False
    for e in evs:
        p = e.employment_period
        if not p or not p.start:
            continue
        a = dates.parse_point(p.start, today=today)
        b = dates.parse_point("present" if p.end == "present" else (p.end or p.start), as_end=True, today=today)
        if a and b:
            periods.append((a, b))
            uncertain |= p.start_uncertain or p.end_uncertain
    return (dates.merged_months(periods) if periods else None), uncertain


def match_requirements(reqs: list[Requirement], evidence: list[Evidence], *, review_confidence: float = 0.6, near_tolerance_months: int = 6, today: date | None = None) -> list[Match]:
    by_concept: dict[str, list[Evidence]] = {}
    absences: dict[str, list[Evidence]] = {}
    for e in evidence:
        target = absences if e.evidence_type == EvidenceType.explicit_statement_of_absence else by_concept
        for c in e.normalised_concepts:
            target.setdefault(c, []).append(e)
    out: list[Match] = []
    for i, r in enumerate(reqs, 1):
        mid = f"MAT-{i:03d}"
        c = r.normalised_concept
        base = dict(match_id=mid, requirement_id=r.requirement_id)
        if r.importance == Importance.unscorable:
            out.append(Match(**base, evidence_ids=[], match_status=MatchStatus.not_assessable, match_type=MatchType.none, coverage=0, evidence_strength=0, confidence=1.0,
                             reason="Requirement is subjective or potentially inappropriate and is excluded from scoring.", human_review_required=True))
            continue
        if r.importance == Importance.contextual:
            out.append(Match(**base, evidence_ids=[], match_status=MatchStatus.not_assessable, match_type=MatchType.none, coverage=0, evidence_strength=0, confidence=1.0,
                             reason="Contextual statement about the role or employer; not a candidate requirement."))
            continue
        if r.importance == Importance.eligibility or r.category in UNASSESSABLE_FROM_RESUME:
            out.append(Match(**base, evidence_ids=[], match_status=MatchStatus.not_assessable, match_type=MatchType.none, coverage=0, evidence_strength=0, confidence=1.0,
                             reason="Eligibility criteria are evaluated only from explicit application answers, never inferred from the resume.",
                             verification_question=f"Please confirm: {r.text}"))
            continue
        if c in absences:
            a = absences[c][0]
            conflicting = c in by_concept
            out.append(Match(**base, evidence_ids=[a.evidence_id], match_status=MatchStatus.contradictory if conflicting else MatchStatus.weak, match_type=MatchType.direct,
                             coverage=0, evidence_strength=0, confidence=0.8,
                             reason=("The resume both mentions this concept and explicitly states its absence; human review required." if conflicting
                                     else "Confirmed absent: the candidate explicitly states they lack this. This is distinct from 'no evidence located'."),
                             human_review_required=True, verification_question=f"Clarify the statement '{a.source_location.text_span.strip()}' against the requirement."))
            continue
        direct = by_concept.get(c, [])
        mtype, evs, explanation = MatchType.direct, direct, ""
        for alt in r.alternative_concepts:  # 'X or Y': evidence for any alternative is direct evidence
            if alt in by_concept and alt not in absences:
                evs = evs + [e for e in by_concept[alt] if e not in evs]
                explanation += f" Alternative '{label(alt)}' accepted because the requirement offers it as an option."
        if not direct:
            transfer_sources = [src for src, targets in TRANSFERABLE.items() if c in targets and src in by_concept]
            if transfer_sources:
                mtype = MatchType.transferable
                evs = [e for s in transfer_sources for e in by_concept[s]]
                explanation = f"Transferable evidence via {', '.join(label(s) for s in transfer_sources)} -> {label(c)} (lexicon relationship, labelled inference)."
        if not evs:
            out.append(Match(**base, evidence_ids=[], match_status=MatchStatus.no_evidence_located, match_type=MatchType.none, coverage=0, evidence_strength=0, confidence=0.7,
                             reason=f"No resume evidence located for '{label(c)}'. This does not establish that the candidate lacks it.",
                             verification_question=f"Does the candidate have experience relevant to '{r.text.strip()}' that is not shown in the resume?",
                             human_review_required=r.importance == Importance.required))
            continue
        strength = _strength(evs)
        conf = min(1.0, round(sum(e.confidence for e in evs) / len(evs) * (0.75 if mtype == MatchType.transferable else 1.0), 2))
        coverage = 1.0 if mtype == MatchType.direct else 0.5
        status = MatchStatus.strong if strength >= 0.75 else MatchStatus.partial if strength >= 0.5 else MatchStatus.weak
        if mtype == MatchType.direct and r.category in (RequirementCategory.certification, RequirementCategory.qualification) and any(e.evidence_type in (EvidenceType.certification, EvidenceType.education) for e in evs):
            status, strength = MatchStatus.confirmed, max(strength, 0.8)  # binary credential requirement satisfied by a cited credential
        reason = f"{'Direct' if mtype == MatchType.direct else 'Transferable'} evidence for '{label(c)}' found in {len(evs)} item(s). {explanation}".strip()
        vq, months, review = None, None, mtype == MatchType.transferable
        if r.minimum_threshold and r.minimum_threshold.unit in ("years", "months"):
            months, uncertain = _duration_months(evs, today)
            need = int(r.minimum_threshold.value * (12 if r.minimum_threshold.unit == "years" else 1))
            if months is None:
                status, coverage = MatchStatus.partial, 0.5
                reason += " Duration could not be computed from dated roles."
                vq, review = f"Confirm total duration of {label(c)} experience (requirement: {r.minimum_threshold.value} {r.minimum_threshold.unit}).", True
            else:
                ok = months > need if r.minimum_threshold.comparator == ">" else months >= need
                near = abs(months - need) <= near_tolerance_months
                reason += f" Computed {months} month(s) of dated experience against a threshold of {need} month(s)."
                if ok:
                    coverage = 1.0 if mtype == MatchType.direct else 0.5
                    if mtype == MatchType.direct and strength >= 0.75 and not uncertain:
                        status = MatchStatus.confirmed
                    elif mtype == MatchType.transferable and STATUS_ORDER.index(status) < STATUS_ORDER.index(MatchStatus.partial):
                        status = MatchStatus.partial  # inferred evidence never exceeds partial
                else:
                    coverage = round(min(1.0, months / need) * (1.0 if mtype == MatchType.direct else 0.5), 2)
                    status = MatchStatus.partial
                    vq = f"Does the candidate have additional {label(c)} experience not represented in the resume? Computed {months} months vs {need} required."
                if near or uncertain:
                    review = True
                    vq = vq or f"Experience duration is close to the threshold or dates are uncertain; verify {label(c)} duration."
        if conf < review_confidence:
            review = True
        out.append(Match(**base, evidence_ids=[e.evidence_id for e in evs], match_status=status, match_type=mtype, coverage=coverage, evidence_strength=strength,
                         confidence=conf, reason=reason, verification_question=vq, human_review_required=review, computed_duration_months=months))
    return out
