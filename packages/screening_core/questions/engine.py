"""Recruiter and hiring-manager question generation.

Questions are derived from the job document and the evidence state. Answer *structures*
are suggested; no candidate answer content is ever fabricated.
"""
from __future__ import annotations

import re

from ..schemas.jobdoc import InterviewQuestion, JobDocument, QuestionAudience
from ..schemas.models import Candidate, EligibilityResult, EligibilityStatus, Importance, Match, MatchStatus, MatchType, Requirement
from ..text.lexicon import label

QUESTIONS_VERSION = "questions-2.1.0"
STAR = ["Situation: the context and why it mattered",
        "Task: what you were accountable for",
        "Action: the specific decisions you made",
        "Result: the measurable outcome and what you learned"]
SCOPE_STRUCTURE = ["State the scope plainly (team size, surfaces, budget, markets)",
                   "Explain your decision rights and what you escalated",
                   "Give one concrete example of a call you owned",
                   "Name the outcome and how it was measured"]
GAP_STRUCTURE = ["Acknowledge the gap directly and briefly",
                 "Give the closest adjacent evidence you do have",
                 "Explain how you closed a comparable gap before",
                 "State what you would do in the first 90 days"]
MAX_PER_AUDIENCE = 5


def generate(job: JobDocument, reqs: list[Requirement], matches: list[Match], cand: Candidate,
             elig: EligibilityResult) -> list[InterviewQuestion]:
    by_req = {r.requirement_id: r for r in reqs}
    ev = {e.evidence_id: e for e in cand.evidence}
    out: list[InterviewQuestion] = []
    n = 0

    def add(audience: QuestionAudience, question: str, why: str, trigger: str, kind: str,
            structure: list[str], follow_ups: list[str], req: Requirement | None = None) -> None:
        nonlocal n
        if sum(1 for q in out if q.audience == audience) >= MAX_PER_AUDIENCE:
            return
        n += 1
        out.append(InterviewQuestion(question_id=f"Q-{n:03d}", audience=audience, question=question, why_likely=why,
                                     requirement_id=req.requirement_id if req else None,
                                     requirement_text=req.text if req else None, trigger=trigger, trigger_kind=kind,
                                     suggested_answer_structure=structure, follow_ups=follow_ups))

    role = job.role_title or "this role"
    employer = job.employer or "the employer"

    # recruiter screen: eligibility, motivation, headline requirements
    if elig.status != EligibilityStatus.not_evaluated:
        for f in elig.findings:
            if f.status != EligibilityStatus.meets_declared_eligibility:
                add(QuestionAudience.recruiter_screen,
                    f"Can you confirm your position on: {f.explanation[:110]}",
                    "Recruiters confirm declared eligibility criteria before any technical assessment.",
                    f"eligibility finding {f.rule_id} = {f.status.value}", "eligibility",
                    ["Answer the factual question directly", "Add the supporting document or status if relevant"],
                    ["If the answer is conditional, what are the conditions and timing?"])
    for r in reqs:
        if r.importance == Importance.eligibility:
            add(QuestionAudience.recruiter_screen,
                f"The job states: '{r.text[:100]}'. How do you meet this?",
                "This is an explicit eligibility criterion in the job document and cannot be read from a resume.",
                f"{r.requirement_id} is an eligibility requirement", "eligibility",
                ["Confirm your status factually", "Note any timing or documentation"],
                ["Would you need sponsorship or relocation support?"], r)
    threshold_reqs = [by_req[m.requirement_id] for m in matches if m.computed_duration_months is not None and by_req[m.requirement_id].importance == Importance.required]
    for r in threshold_reqs[:2]:
        m = next(x for x in matches if x.requirement_id == r.requirement_id)
        add(QuestionAudience.recruiter_screen,
            f"Walk me through how your experience meets '{r.text[:80]}'.",
            "The job states a duration threshold, so a recruiter will check it early.",
            f"computed {m.computed_duration_months} months of dated evidence against the stated threshold", "evidence",
            ["State the total and the roles it spans", "Name the most relevant role first"] + STAR[2:],
            ["Which part of that time was hands-on versus oversight?"], r)

    # hiring manager: strongest matched requirements from qualification sections
    strong = [m for m in matches if m.match_status in (MatchStatus.confirmed, MatchStatus.strong)
              and by_req[m.requirement_id].importance == Importance.required and by_req[m.requirement_id].weight >= 0.6]
    for m in strong[:MAX_PER_AUDIENCE]:
        r = by_req[m.requirement_id]
        add(QuestionAudience.hiring_manager,
            f"Tell me about a time you delivered on '{r.text[:85]}'.",
            f"{employer} lists this as a required qualification and your resume shows related evidence, so expect depth probing.",
            f"{r.requirement_id} matched {m.match_status.value} with {len(m.evidence_ids)} evidence item(s)", "evidence",
            STAR, ["What would you do differently now?", "How did you know it worked?"], r)

    # evidence verification: matcher-generated questions
    for m in matches:
        if m.verification_question and by_req[m.requirement_id].importance in (Importance.required, Importance.preferred):
            r = by_req[m.requirement_id]
            excerpt = ""
            if m.evidence_ids and m.evidence_ids[0] in ev:
                excerpt = re.sub(r"\s+", " ", ev[m.evidence_ids[0]].source_location.text_span).strip()[:90]
            add(QuestionAudience.evidence_verification, m.verification_question,
                "Reviewers verify claims that are relevant but not fully evidenced in the document.",
                f"{m.match_status.value} match" + (f"; resume says '{excerpt}'" if excerpt else "; no resume evidence located"),
                "evidence" if m.evidence_ids else "gap",
                ["Point to the specific role and period", "Describe your direct contribution", "Separate what you owned from what the team owned"],
                ["Who else was involved and what was your share of the decision?"], r)

    # seniority and scope
    scope_reqs = [r for r in reqs if r.category.value in ("leadership", "stakeholder_management") or r.normalised_concept in
                  ("people_leadership", "people_management_of_managers", "exec_reporting", "product_strategy", "org_alignment", "multi_market_platform")]
    for r in scope_reqs[:MAX_PER_AUDIENCE]:
        m = next((x for x in matches if x.requirement_id == r.requirement_id), None)
        state = m.match_status.value if m else "not assessed"
        add(QuestionAudience.seniority_and_scope,
            f"What was your actual scope and decision authority in relation to '{r.text[:80]}'?",
            "Seniority claims are the most commonly probed area for leadership roles; the employer asks for this explicitly.",
            f"{r.requirement_id} ({r.category.value}) is {state}", "scope", SCOPE_STRUCTURE,
            ["How many people reported to you, directly and indirectly?", "Which decisions did you escalate and why?"], r)

    # gap focused
    for m in matches:
        r = by_req[m.requirement_id]
        if r.importance == Importance.required and m.match_status in (MatchStatus.no_evidence_located, MatchStatus.weak, MatchStatus.contradictory):
            add(QuestionAudience.gap_focused,
                f"This role requires '{r.text[:80]}'. How would you approach it?",
                "Where the document does not evidence a required qualification, interviewers test the gap directly.",
                f"{m.match_status.value}: {m.reason[:110]}", "gap" if m.match_status == MatchStatus.no_evidence_located else "ambiguity",
                GAP_STRUCTURE, ["What support would you need in the first 90 days?"], r)

    # employer and domain
    domain = [r for r in reqs if r.category.value == "domain_knowledge"]
    if job.employer:
        add(QuestionAudience.employer_and_domain,
            f"Why {employer}, and why this {role} specifically?",
            "Almost every recruiter screen tests motivation and whether you understand the employer's model.",
            f"listing is for {employer} ({job.location or 'location not stated'})", "domain",
            ["Connect a specific part of their stated mandate to your experience",
             "Name what you would want to learn or change",
             "Avoid generic praise; cite something from the job document"],
            ["What do you see as the hardest problem in this role?"])
    for r in domain[:3]:
        add(QuestionAudience.employer_and_domain,
            f"How does your background relate to '{r.text[:80]}'?",
            "Domain context in the job document signals the problem space the team is hiring for.",
            f"{r.requirement_id} is a domain requirement", "domain",
            ["State your closest domain exposure honestly", "Explain what transfers and what does not"],
            ["Which domain assumptions would you test first?"], r)
    return out
