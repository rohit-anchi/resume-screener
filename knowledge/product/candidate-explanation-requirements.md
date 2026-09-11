# Candidate explanation requirements

## Required result structure

1. **Assessment identity:** “Evidence-based application readiness assessment,” date, model/rubric/version.
2. **Scenario assumptions:** manual review, configured eligibility, optional matching and/or named integration.
3. **Input scope:** documents and job description used; excluded data categories.
4. **Parseability:** extracted sections, warnings and omitted/unreadable content.
5. **Eligibility:** each explicit criterion, candidate answer/evidence, status and uncertainty.
6. **Qualification alignment:** required and preferred criteria evaluated separately.
7. **Evidence strength:** quoted/paraphrased evidence with source location; no unsupported inference.
8. **Missing versus negative:** “not found” and “confirmed not met” are separate states.
9. **Confidence:** criterion-level confidence and reason for uncertainty/abstention.
10. **Actionable suggestions:** truthful clarification, formatting or evidence improvements; no keyword stuffing.
11. **Limitations:** no exact ATS/employer prediction; workflow and licensing may differ.
12. **Recourse:** correction, accommodation, human review and contest channels.

## Explanation vocabulary

Use:
- `supported`, `partially supported`, `not found`, `contradictory`, `unknown`, `not applicable`.
- “The resume states…” / “The job requires…” / “No evidence was located…”

Do not use:
- “ATS failure,” “guaranteed pass,” “culture fit,” “the platform rejected you,” or hidden-trait inferences.

## Material finding schema

```text
criterion_id
criterion_text
criterion_type: mandatory | preferred | contextual
finding_status
resume_evidence[]: artifact, page/section, exact span
job_evidence[]: source span
reasoning_summary
confidence + basis
missing_information
valid_use / invalid_use
recommended human action
```

## Candidate-facing safeguards

- Show extracted fields before consequential use and allow correction.
- Highlight uncertain parser output.
- Explain whether a result came from an explicit answer, resume evidence, configured rule or optional model.
- Provide an accessible alternative and accommodation path.
- Never reveal or imply private employer rules not supplied as input.
