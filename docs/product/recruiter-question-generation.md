# Recruiter question generation

Questions are derived from the employer's stated requirements and the evidence state of the resume. **No candidate answer content is ever generated** — only a structure to prepare within.

## Audiences

| Audience | Derived from |
|---|---|
`recruiter_screen` | eligibility findings, eligibility requirements in the job document, stated duration thresholds |
`hiring_manager` | required qualifications with confirmed or strong evidence (depth probing) |
`evidence_verification` | matcher-generated verification questions (partial, transferable, threshold-adjacent, low-confidence) |
`seniority_and_scope` | leadership, stakeholder, strategy, org-alignment and multi-market requirements |
`gap_focused` | required qualifications with no evidence located, weak or contradictory evidence |
`employer_and_domain` | employer identity plus domain-knowledge requirements |

## Each question carries

- `question` — what is likely to be asked
- `why_likely` — the reason a reviewer would ask it
- `requirement_id` / `requirement_text` — the job requirement being tested
- `trigger` + `trigger_kind` (`evidence`, `gap`, `ambiguity`, `scope`, `domain`, `eligibility`) — the resume evidence or gap that produced it
- `suggested_answer_structure` — a scaffold (STAR for behavioural, a scope scaffold for seniority, an acknowledge/adjacent/close scaffold for gaps)
- `follow_ups` — likely second questions
- `note` — an explicit statement that the candidate must supply the content

## Anti-fabrication

The engine emits structures and quotes only the candidate's own resume spans as triggers. It never drafts an achievement, a metric or a claim of experience. Gap questions are framed as "how would you approach it", never as an assertion that the candidate lacks the capability.

Volume is capped at five questions per audience so the output stays usable.
