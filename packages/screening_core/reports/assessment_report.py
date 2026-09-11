"""Assessment report rendering for the two-input workflow (candidate and recruiter-assist)."""
from __future__ import annotations

import re

from ..schemas.jobdoc import Assessment, BlockCategory as C, QuestionAudience
from ..schemas.models import Importance, MatchStatus, Mode, ScreeningResult

TITLE = "Evidence-based, platform-informed application readiness assessment"
CANDIDATE_LABELS = {
    MatchStatus.confirmed: "Strong evidence", MatchStatus.strong: "Strong evidence", MatchStatus.partial: "Partial evidence",
    MatchStatus.weak: "Partial evidence", MatchStatus.no_evidence_located: "No evidence located",
    MatchStatus.contradictory: "Ambiguous", MatchStatus.not_assessable: "Not assessable",
    MatchStatus.human_review_required: "Ambiguous",
}


def _flat(s: str, n: int = 220) -> str:
    t = re.sub(r"\s+", " ", s).strip()
    return t if len(t) <= n else t[: n - 1] + "\u2026"


def render(a: Assessment, s: ScreeningResult, *, mode: Mode | None = None) -> str:
    mode = mode or Mode(a.mode)
    candidate_mode = mode == Mode.candidate
    jd, L = a.job, []
    by_req = {r.requirement_id: r for r in s.requirements}
    ev = {e.evidence_id: e for e in s.evidence}

    L += [f"# {TITLE}", "",
          f"**{jd.role_title or 'Role not detected'}** at **{jd.employer or 'Employer not detected'}**", "",
          f"> {s.profile.disclaimer}", ""]

    # 1. job extraction and metadata
    L += ["## 1. Job extraction", "",
          "| Field | Value |", "|---|---|",
          f"| Employer | {jd.employer or '—'} |",
          f"| Role | {jd.role_title or '—'} |",
          f"| Location | {jd.location or '—'} |",
          f"| Employment type | {jd.employment_type or '—'} |",
          f"| Workplace type | {jd.workplace_type or '—'} |",
          f"| Compensation (as stated, not scored) | {jd.compensation_text or 'not stated'} |",
          f"| Source document | `{jd.filename}` ({jd.page_count} pages, sha256 `{jd.sha256[:12]}`) |",
          f"| Requirements extracted | {len(s.requirements)} ({sum(1 for r in s.requirements if r.importance == Importance.required)} required, "
          f"{sum(1 for r in s.requirements if r.importance == Importance.preferred)} preferred, "
          f"{sum(1 for r in s.requirements if r.importance == Importance.eligibility)} eligibility) |", ""]

    # 2. content classification / exclusion
    scored = sum(1 for b in jd.blocks if b.allowed_for_requirements)
    L += ["## 2. LinkedIn content classification", "",
          f"{len(jd.blocks)} content blocks classified; {scored} employer blocks used for requirements; "
          f"{len(jd.excluded_block_ids)} blocks excluded from scoring and retained for audit.", "",
          "| Category | Blocks | Used for requirements |", "|---|---|---|"]
    for cat, count in jd.excluded_categories.items():
        used = "yes" if C(cat) in C.requirement_bearing() else "no"
        L.append(f"| {cat} | {count} | {used} |")
    L += ["", "_LinkedIn job-match statements, applicant statistics, candidate seniority/education demographics, premium insights, "
          "similar jobs, promotions and third-party people suggestions are never used as employer requirements._", ""]
    if jd.extraction_warnings:
        L += ["**Extraction warnings**", ""] + [f"- {w}" for w in jd.extraction_warnings] + [""]

    # 3. ATS detection
    L += ["## 3. Downstream ATS detection", "",
          f"- Listing source: **{jd.listing_source}**",
          f"- Application platform: **{a.ats.application_platform.value}** (confidence {a.ats.confidence})",
          f"- Application link: {a.ats.application_url or 'not found in document'}",
          f"- Responses managed off the listing platform: {a.ats.responses_managed_off_platform}",
          f"- Approved knowledge profile available: **{a.ats.has_approved_knowledge_profile}**",
          f"- Profile applied: **{a.profile_display_name}** — {a.ats.profile_selection_reason}", ""]
    if a.ats.signals:
        L += ["<details><summary>Detection signals</summary>", ""]
        L += [f"- `{sig.signal_type}` \u2192 {sig.platform.value}: {_flat(sig.value, 120)}" for sig in a.ats.signals]
        L += ["", "</details>", ""]

    # 4. parseability
    p = s.parseability
    L += ["## 4. Resume parseability", "",
          f"Parseability score: **{p.parseability_score}/100** (document readiness only; not a measure of your suitability)", "",
          "| Check | Result |", "|---|---|"]
    for k, v in (("Text extracted", p.text_extraction_success), ("OCR required", p.ocr_required),
                 ("Employment history found", p.employment_history_extracted), ("Dates found", p.dates_extracted),
                 ("Education found", p.education_extracted), ("Certifications found", p.certifications_extracted),
                 ("Section order clear", p.section_order_clear), ("Tables/columns interfere", p.table_or_column_interference),
                 ("Hidden text suspected", p.hidden_text_suspected), ("Instruction-like text flagged", p.injection_suspected)):
        L.append(f"| {k} | {'yes' if v else 'no'} |")
    L += [""]
    if p.chronology_conflicts:
        L += [f"- Chronology conflicts detected: {p.chronology_conflicts}", ""]

    # 5. eligibility
    L += ["## 5. Eligibility findings", "", f"Status: **{a.eligibility_status.replace('_', ' ')}** (kept separate from the alignment index)", ""]
    if s.eligibility.findings:
        L += [f"- `{f.rule_id}` **{f.status.value.replace('_', ' ')}** — {f.explanation}" for f in s.eligibility.findings]
    else:
        L += ["- No employer-declared eligibility rules were supplied with this assessment."]
    elig_reqs = [r for r in s.requirements if r.importance == Importance.eligibility]
    if elig_reqs:
        L += ["", "Eligibility criteria found in the job document (each needs an explicit application answer):", ""]
        L += [f"- `{r.requirement_id}` {_flat(r.text, 180)}" for r in elig_reqs]
    L += [""]

    # 6. scores
    L += ["## 6. Documented alignment", ""]
    if s.score.qualification_scoring_suppressed:
        L += [f"**Not assessable.** {s.score.suppression_reason}", ""]
    else:
        L += [f"**{s.score.alignment_index} / 100 — {s.score.band_label}**", ""]
    L += [f"_{s.score.band_caveat}_", "",
          f"Evidence confidence: **{a.evidence_confidence}**", "",
          "| Component | Weight % | Raw | Weighted | Excluded |", "|---|---|---|---|---|"]
    for c in s.score.components:
        L.append(f"| {c.component.replace('_', ' ')} | {c.weight_percent} | {c.raw_score} | {c.weighted_points} | {len(c.excluded_requirement_ids)} |")
    L += ["", f"Rubric `{s.score.rubric_id}@{s.score.rubric_version}` hash `{s.score.rubric_hash}`", ""]

    # 7. requirement-by-requirement evidence mapping
    L += ["## 7. Requirement-by-requirement evidence mapping", ""]
    for imp in (Importance.eligibility, Importance.required, Importance.preferred, Importance.unscorable):
        group = [f for f in s.findings if f.importance == imp]
        if not group:
            continue
        L += [f"### {imp.value.replace('_', ' ').title()}", ""]
        for f in group:
            r = by_req[f.requirement_id]
            status = f.candidate_label if candidate_mode else f.status.value.replace("_", " ")
            L += [f"**`{f.requirement_id}`** {_flat(f.requirement_text, 200)}", "",
                  f"- Job source: {r.source_location.section or 'employer content'}, chars {r.source_location.char_start}\u2013{r.source_location.char_end}",
                  f"- Finding: **{status}** (confidence {f.confidence})",
                  f"- Explanation: {f.explanation}"]
            if r.minimum_threshold:
                L.append(f"- Stated threshold: {r.minimum_threshold.comparator} {r.minimum_threshold.value} {r.minimum_threshold.unit}")
            for excerpt, loc in zip(f.evidence_excerpts, f.locations):
                L.append(f"- Resume evidence: \"{_flat(excerpt, 200)}\" — {loc.section or 'document'}, chars {loc.char_start}\u2013{loc.char_end}")
            if f.missing_information:
                L.append(f"- Missing information: {f.missing_information}")
            if f.score_effect:
                L.append(f"- Score contribution: {f.score_effect}")
            if f.verification_question and not candidate_mode:
                L.append(f"- Verification required: {f.verification_question}")
            if f.human_review_required and not candidate_mode:
                L.append("- Human review required: yes")
            L.append("")

    # 8. critical gaps / missing evidence
    L += ["## 8. Critical gaps", ""]
    if a.critical_gaps:
        for g in a.critical_gaps:
            L += [f"- **`{g.requirement_id}`** ({g.status.replace('_', ' ')}) {_flat(g.requirement_text, 160)}",
                  f"  - Why it matters: {g.why_critical}", f"  - What would resolve it: {g.what_would_resolve_it}"]
    else:
        L += ["- None identified against the stated required qualifications."]
    L += ["", "## 9. Missing or ambiguous evidence", ""]
    L += [f"- {m}" for m in a.missing_or_ambiguous] or ["- None."]
    L += ["", "_\"No evidence located\" means the submitted documents did not show it. It is not a finding that you lack the qualification._", ""]

    # 10. recommendations
    L += ["## 10. Resume-tailoring recommendations", ""]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for rec in sorted(a.recommendations, key=lambda r: order[r.priority]):
        L += [f"### [{rec.priority.upper()}] {rec.title}", "", f"{rec.rationale}", ""]
        if rec.requirement_ids:
            L.append(f"- Requirements addressed: {', '.join(rec.requirement_ids)}")
        if rec.edit:
            e = rec.edit
            if e.original_text:
                L.append(f"- Original text: \"{_flat(e.original_text, 220)}\"")
            L.append(f"- Proposed text: \"{_flat(e.proposed_text, 260)}\"")
            if e.job_requirement_addressed:
                L.append(f"- Job requirement addressed: {_flat(e.job_requirement_addressed, 160)}")
            for sup in e.candidate_evidence_supporting[:3]:
                L.append(f"- Your existing evidence: \"{_flat(sup, 180)}\"")
            L.append(f"- Verification required: {e.verification_required}")
        L.append(f"- {rec.fabrication_guard}")
        L.append("")

    # 11. questions
    L += ["## 11. Recruiter and hiring-manager questions", ""]
    for aud in QuestionAudience:
        group = [q for q in a.questions if q.audience == aud]
        if not group:
            continue
        L += [f"### {aud.value.replace('_', ' ').title()}", ""]
        for q in group:
            L += [f"**{q.question}**", "", f"- Why it is likely: {q.why_likely}"]
            if q.requirement_text:
                L.append(f"- Requirement being tested: {_flat(q.requirement_text, 160)}")
            L.append(f"- Trigger ({q.trigger_kind}): {_flat(q.trigger, 180)}")
            L.append("- Suggested answer structure:")
            L += [f"  - {st}" for st in q.suggested_answer_structure]
            if q.follow_ups:
                L.append("- Likely follow-ups:")
                L += [f"  - {fu}" for fu in q.follow_ups]
            L += [f"- {q.note}", ""]

    # 12. scenarios
    L += ["## 12. Platform-informed screening scenarios", "",
          "Scenarios describe how this application may be handled, based on public platform documentation. "
          "Optional or configured capabilities may not be enabled by this employer.", ""]
    for sc in s.scenarios:
        L.append(f"- **{sc.title}** [{sc.delivery_label}] — {sc.description}")
    ai_disc = [b for b in jd.blocks if b.category == C.employer_ai_disclosure]
    if ai_disc:
        L += ["", "**Employer AI disclosure found in this listing** (employer-authored, not scored):", "",
              f"> {_flat(ai_disc[0].text, 600)}"]
    L += [""]

    # 13. limitations and audit
    L += ["## 13. Limitations", ""] + [f"- {x}" for x in a.limitations] + [""]
    L += ["## 14. Audit information", "",
          f"- Assessment `{a.assessment_id}` · screening `{a.screening_id}` · created {a.created_at}",
          f"- Mode: {a.mode}", ""]
    L += ["| Component | Version |", "|---|---|"] + [f"| {k} | `{v}` |" for k, v in a.versions.items()] + [""]
    if not candidate_mode:
        L += ["## 15. Human-review recommendation", "",
              f"Recommended human action: **{s.recommended_human_action.value.replace('_', ' ')}** (advisory only; the reviewer records the decision)", ""]
        L += ["Review triggers:", ""] + ([f"- {t}" for t in s.review_triggers] or ["- none"])
        L += ["", "Available human actions: move forward · hold for review · request additional information · decline with a human-selected reason", ""]
    return "\n".join(L)
