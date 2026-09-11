"""Candidate and recruiter-assist report rendering (Markdown + JSON)."""
from __future__ import annotations

from ..schemas.models import AuditEvent, Importance, MatchStatus, ScreeningResult

TITLE = "Evidence-based, platform-informed application readiness assessment"
FORBIDDEN_IN_CANDIDATE = ("reject", "hire", "decline", "move forward")


def _header(r: ScreeningResult) -> list[str]:
    return [f"# {TITLE}", "", f"Screening `{r.screening_id}` · Job: {r.job_title} · Profile: {r.profile.display_name} · Created {r.created_at}", "",
            f"> {r.profile.disclaimer}", "", "## Versions", "", *[f"- {k}: `{v}`" for k, v in r.versions.items()], ""]


def _parseability(r: ScreeningResult) -> list[str]:
    p = r.parseability
    rows = [("Text extraction", p.text_extraction_success), ("Image-only / OCR required", p.ocr_required), ("Employment history found", p.employment_history_extracted),
            ("Dates found", p.dates_extracted), ("Education found", p.education_extracted), ("Certifications found", p.certifications_extracted),
            ("Section order clear", p.section_order_clear), ("Table/column interference", p.table_or_column_interference), ("Hidden text suspected", p.hidden_text_suspected),
            ("Instruction-like text flagged", p.injection_suspected)]
    return ["## Resume parseability (document readiness, not candidate quality)", "", f"Parseability score: **{p.parseability_score}** / 100", "",
            "| Check | Result |", "|---|---|", *[f"| {k} | {'yes' if v else 'no'} |" for k, v in rows], "",
            *([f"- Chronology conflicts: {p.chronology_conflicts}"] if p.chronology_conflicts else []), *[f"- {n}" for n in p.notes], ""]


def _scores(r: ScreeningResult) -> list[str]:
    s = r.score
    out = ["## Alignment index (summary of visible components)", ""]
    if s.qualification_scoring_suppressed:
        out += [f"**Not assessable.** {s.suppression_reason}", ""]
    else:
        out += [f"**{s.alignment_index} / 100 — {s.band_label}** (confidence {s.overall_confidence})", ""]
    out += [f"_{s.band_caveat}_", "", f"Rubric `{s.rubric_id}@{s.rubric_version}` hash `{s.rubric_hash}`", "", "| Component | Weight % | Raw | Weighted | Excluded requirements |", "|---|---|---|---|---|"]
    out += [f"| {c.component} | {c.weight_percent} | {c.raw_score} | {c.weighted_points} | {', '.join(c.excluded_requirement_ids) or '—'} |" for c in s.components]
    return out + [""]


def _eligibility(r: ScreeningResult, candidate_mode: bool) -> list[str]:
    e = r.eligibility
    label = e.status.value.replace("_", " ")
    out = ["## Eligibility (separate from the alignment index)", "", f"Status: **{label}**", ""]
    for f in e.findings:
        out.append(f"- `{f.rule_id}` — {f.status.value.replace('_', ' ')}: {f.explanation}")
    if not e.findings:
        out.append("- No employer-declared eligibility rules were supplied; nothing was evaluated." if candidate_mode else "- No employer-declared eligibility rules supplied.")
    return out + [""]


def _findings(r: ScreeningResult, candidate_mode: bool) -> list[str]:
    out = ["## Requirement findings", ""]
    for imp in (Importance.eligibility, Importance.required, Importance.preferred, Importance.unscorable):
        group = [f for f in r.findings if f.importance == imp]
        if not group:
            continue
        out += [f"### {imp.value.replace('_', ' ').title()} requirements", ""]
        for f in group:
            status = f.candidate_label if candidate_mode else f.status.value.replace("_", " ")
            out += [f"**{f.requirement_id}** — {f.requirement_text}", f"- Finding: **{status}** (confidence {f.confidence})", f"- Explanation: {f.explanation}"]
            for ex, loc in zip(f.evidence_excerpts, f.locations):
                out.append(f"- Evidence: \"{ex}\" — {loc.section or 'document'} chars {loc.char_start}-{loc.char_end}")
            if f.missing_information:
                out.append(f"- Missing information: {f.missing_information}")
            if f.verification_question and not candidate_mode:
                out.append(f"- Verification question: {f.verification_question}")
            if f.score_effect and not (candidate_mode and imp == Importance.unscorable):
                out.append(f"- Score effect: {f.score_effect}")
            if f.human_review_required and not candidate_mode:
                out.append("- Human review required: yes")
            out.append("")
    return out


def _scenarios(r: ScreeningResult) -> list[str]:
    out = ["## Platform-informed scenarios", "", "Each scenario is labelled by delivery type and cites Phase 1 knowledge claims. Optional or configured capabilities may not be enabled by a given employer.", ""]
    for s in r.scenarios:
        out += [f"- **{s.title}** [{s.delivery_label}] — {s.description}"]
    return out + [""]


def _limitations(r: ScreeningResult) -> list[str]:
    return ["## Limitations", "", *[f"- {l}" for l in r.limitations], ""]


def candidate_report(r: ScreeningResult) -> str:
    imp = [f for f in r.findings if f.status == MatchStatus.no_evidence_located and f.importance in (Importance.required, Importance.preferred)]
    tips = ["## Suggested truthful improvements", ""]
    tips += [f"- If you have experience relevant to \"{f.requirement_text}\", add a concrete, dated example with scope and outcome. Do not add terms you cannot support." for f in imp] or ["- No missing-evidence items were identified for scored requirements."]
    if r.parseability.table_or_column_interference or r.parseability.hidden_text_suspected:
        tips.append("- Simplify layout (single reading order, no hidden text) so extraction is reliable.")
    tips += ["", "## Interview-readiness areas", "", *[f"- Be ready to discuss: {f.requirement_text}" for f in r.findings if f.importance == Importance.required and f.status in (MatchStatus.partial, MatchStatus.weak, MatchStatus.strong, MatchStatus.confirmed)][:8], ""]
    body = _header(r) + _parseability(r) + _eligibility(r, True) + _scores(r) + _findings(r, True) + tips + _scenarios(r) + _limitations(r)
    return "\n".join(body)


def recruiter_report(r: ScreeningResult, audit: list[AuditEvent] | None = None) -> str:
    rev = ["## Human-review recommendation", "", f"Recommended human action: **{r.recommended_human_action.value.replace('_', ' ')}** (advisory only; the recruiter records the decision)", ""]
    rev += ["Review triggers:", *[f"- {t}" for t in r.review_triggers]] if r.review_triggers else ["No review triggers."]
    rev += ["", "Available human actions: move forward · hold for review · request additional information · decline with a human-selected reason", ""]
    qs = ["## Suggested screening questions", "", *[f"- {f.verification_question}" for f in r.findings if f.verification_question][:12], ""]
    doc_lines = [f"- [{d.severity}] {d.code}: {d.message}" for d in r.document_findings] or ["- none"]
    docs = ["## Document findings", "", *doc_lines, ""]
    aud = []
    if audit:
        aud = ["## Review and override history", "", *[f"- {e.timestamp} `{e.event_type}` by {e.actor}: {e.payload.get('reason', '')}" for e in audit if e.event_type != "screening_created"], ""]
    body = _header(r) + _eligibility(r, False) + _scores(r) + _findings(r, False) + rev + qs + docs + _parseability(r) + _scenarios(r) + aud + _limitations(r)
    return "\n".join(body)
