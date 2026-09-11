"""Optional module 1: one resume assessed against multiple LinkedIn job PDFs.

Rankings describe documented suitability against each employer's stated requirements in the
supplied documents. They are not hiring probabilities.
"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timezone

from ..schemas.jobdoc import Assessment, MultiJobEntry, MultiJobReview
from ..schemas.models import Importance, Job, MatchStatus, ScreeningResult
from ..text.lexicon import label

MULTIJOB_VERSION = "multi-job-2.1.0"


def _tailoring_effort(a: Assessment, s: ScreeningResult) -> tuple[str, str]:
    required = [r for r in s.requirements if r.importance == Importance.required and r.weight >= 1.0]
    by = {m.requirement_id: m for m in s.matches}
    unmet = [r for r in required if by[r.requirement_id].match_status in (MatchStatus.no_evidence_located, MatchStatus.weak, MatchStatus.contradictory)]
    ratio = (len(unmet) / len(required)) if required else 0.0
    edits = len([r for r in a.recommendations if r.priority in ("critical", "high")])
    if ratio <= 0.2 and edits <= 4:
        return "low", f"{len(unmet)} of {len(required)} stated required items lack evidence; {edits} high-priority edits suggested."
    if ratio <= 0.5:
        return "medium", f"{len(unmet)} of {len(required)} stated required items lack evidence; {edits} high-priority edits suggested."
    return "high", f"{len(unmet)} of {len(required)} stated required items lack evidence; {edits} high-priority edits suggested."


def review(candidate_id: str, items: list[tuple[Assessment, ScreeningResult, Job]]) -> MultiJobReview:
    entries: list[MultiJobEntry] = []
    concept_counter: Counter[str] = Counter()
    gap_counter: Counter[str] = Counter()
    domain: dict[str, str] = {}
    seniority: dict[str, str] = {}

    for a, s, job in items:
        req_cov = next((c.raw_score for c in s.score.components if c.component == "required_qualification_coverage"), 0.0)
        effort, reason = _tailoring_effort(a, s)
        entries.append(MultiJobEntry(job_document_id=a.job.job_document_id, employer=a.job.employer, role_title=a.job.role_title,
                                     application_platform=a.ats.application_platform.value, alignment_index=a.alignment_index,
                                     band_label=a.band_label, eligibility_status=a.eligibility_status, required_coverage=req_cov,
                                     critical_gap_count=len(a.critical_gaps), tailoring_effort=effort, tailoring_reason=reason))
        stated = [r for r in s.requirements if r.importance in (Importance.required, Importance.preferred) and r.weight >= 1.0]
        for r in stated:
            concept_counter[r.normalised_concept] += 1
        by = {m.requirement_id: m for m in s.matches}
        for r in stated:
            if by[r.requirement_id].match_status in (MatchStatus.no_evidence_located, MatchStatus.weak):
                gap_counter[r.normalised_concept] += 1
        key = f"{a.job.employer or '?'} — {a.job.role_title or '?'}"
        dom = [r.normalised_concept for r in s.requirements if r.category.value == "domain_knowledge"]
        domain[key] = ", ".join(sorted({label(d) for d in dom})) or "no explicit domain requirement stated"
        lead = next((c.raw_score for c in s.score.components if c.component == "leadership_and_operating_scope"), None)
        seniority[key] = ("leadership/scope evidence " + (f"{lead}/100" if lead is not None else "not scored") +
                          (f"; stated thresholds: {', '.join(sorted({f'{int(r.minimum_threshold.value)} {r.minimum_threshold.unit}' for r in s.requirements if r.minimum_threshold}))}"
                           if any(r.minimum_threshold for r in s.requirements) else "; no duration threshold stated"))

    n = len(items)
    common = [f"{label(c)} (in {k} of {n} roles)" for c, k in concept_counter.most_common() if k > 1 and n > 1]
    recurring = [f"{label(c)} — no or weak evidence in {k} of {n} roles" for c, k in gap_counter.most_common() if k > 1 and n > 1]
    priority = [e.job_document_id for e in sorted(entries, key=lambda e: (-(e.alignment_index or -1), e.critical_gap_count))]
    master: list[str] = []
    for c, k in gap_counter.most_common(6):
        if k >= max(2, n // 2):
            master.append(f"Add explicit, dated evidence for {label(c)} to the master resume: it is a stated requirement in {k} of {n} target roles.")
    if not master:
        master.append("No requirement gap recurs across the majority of target roles; keep tailoring per application.")
    if any(e.eligibility_status != "meets_declared_eligibility" for e in entries):
        master.append("Prepare standard, truthful answers for eligibility questions (work authorisation, location, travel) — these are evaluated literally from application answers.")
    return MultiJobReview(review_id=f"MJR-{uuid.uuid4().hex[:10]}", created_at=datetime.now(timezone.utc).isoformat(),
                          candidate_id=candidate_id, entries=entries, common_requirements=common, recurring_gaps=recurring,
                          domain_fit=domain, seniority_fit=seniority, suggested_priority=priority, master_resume_improvements=master)


def render(r: MultiJobReview) -> str:
    L = ["# Multi-job review", "", f"Review `{r.review_id}` · {len(r.entries)} role(s) · created {r.created_at}", "",
         f"> {r.caveat}", "", "## Role-by-role", "",
         "| Employer | Role | Platform | Alignment | Band | Eligibility | Required coverage | Critical gaps | Tailoring |",
         "|---|---|---|---|---|---|---|---|---|"]
    for e in r.entries:
        L.append(f"| {e.employer or '—'} | {e.role_title or '—'} | {e.application_platform} | "
                 f"{'n/a' if e.alignment_index is None else e.alignment_index} | {e.band_label} | {e.eligibility_status.replace('_', ' ')} | "
                 f"{e.required_coverage} | {e.critical_gap_count} | {e.tailoring_effort} |")
    L += ["", "## Common target-market requirements", ""] + ([f"- {c}" for c in r.common_requirements] or ["- No requirement recurs across these roles."])
    L += ["", "## Recurring resume gaps", ""] + ([f"- {g}" for g in r.recurring_gaps] or ["- No gap recurs across these roles."])
    L += ["", "## Domain fit", ""] + [f"- **{k}**: {v}" for k, v in r.domain_fit.items()]
    L += ["", "## Seniority fit", ""] + [f"- **{k}**: {v}" for k, v in r.seniority_fit.items()]
    L += ["", "## Suggested application priority", ""]
    order = {e.job_document_id: e for e in r.entries}
    for i, jid in enumerate(r.suggested_priority, 1):
        e = order[jid]
        L.append(f"{i}. {e.employer or '—'} — {e.role_title or '—'} (documented alignment {'n/a' if e.alignment_index is None else e.alignment_index}, "
                 f"{e.critical_gap_count} critical gap(s), {e.tailoring_effort} tailoring effort)")
    L += ["", "## Master-resume improvements", ""] + [f"- {m}" for m in r.master_resume_improvements]
    L += ["", "_Priority reflects documented suitability and tailoring effort only. It does not predict any employer's decision._", ""]
    return "\n".join(L)
