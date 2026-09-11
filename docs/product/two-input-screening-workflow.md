# Two-input screening workflow

Product name in every output: **Evidence-based, platform-informed application readiness assessment**.

## Inputs

1. A LinkedIn job-details PDF (the employer's advertised role, saved from the LinkedIn job page).
2. A resume in PDF or DOCX.

Optional: answers to the employer's stated eligibility criteria; a LinkedIn profile PDF; additional job PDFs for multi-job review.

## Pipeline

```
LinkedIn job PDF ─► block extraction ─► content classification ─► allow-list ─► employer_text + sections
                                                   │                              │
                                                   └─► excluded blocks (audit)    ├─► requirement extraction
                        application links ─► ATS detection ─► profile selection   │
resume (PDF/DOCX) ─► safety ─► extraction ─► redaction ─► evidence extraction ────┤
                                          └─► parseability report                 ▼
                                                            requirement ⇄ evidence matching
                                                    ┌───────────────┴───────────────┐
                                       eligibility engine (answers only)     component scoring
                                                    └───────────────┬───────────────┘
                              critical gaps · recommendations · questions · scenarios · audit
```

## Output sections (report order)

1. Job extraction — employer, role, location, employment type, workplace type, compensation as stated
2. LinkedIn content classification — per-category block counts and what was used for requirements
3. Downstream ATS detection — listing source, application platform, profile applied, signals
4. Resume parseability
5. Eligibility findings
6. Documented alignment (component scores, band, evidence confidence)
7. Requirement-by-requirement evidence mapping
8. Critical gaps
9. Missing or ambiguous evidence
10. Resume-tailoring recommendations
11. Recruiter and hiring-manager questions
12. Platform-informed screening scenarios
13. Limitations
14. Audit information
15. Human-review recommendation (recruiter-assist mode only)

## Score components

| Component | Weight (rubric `default@2.1.0`) |
|---|---|
| Required qualification coverage | 35 |
| Relevant experience alignment | 18 |
| Demonstrated skill evidence | 14 |
| Leadership and operating scope | 12 |
| Achievement and impact evidence | 9 |
| Preferred qualification coverage | 5 |
| Application completeness | 4 |
| Resume parseability | 3 |

**Eligibility status** and **evidence confidence** are reported separately and are never folded into the weighted index. Changing an eligibility answer changes the categorical eligibility result and the recommended human action, never the alignment index (asserted by test).

## Every score-contributing finding carries

job requirement · requirement source location (section + character span) · resume evidence excerpt · resume source location · match status · confidence · explanation · score contribution · verification requirement.

`no_evidence_located` means the submitted documents did not show it. It is never rendered as "the candidate does not possess the qualification"; only an explicit statement of absence in the resume produces a confirmed-absent style finding, and that is flagged for human review.

## Modes

- **Candidate** — outcome labels only (Strong evidence / Partial evidence / No evidence located / Ambiguous / Not assessable / Candidate input required). No hire, reject, advance or decline language.
- **Recruiter assist** — adds match statuses, verification questions, review triggers and an advisory human action. The engine never executes an adverse decision; a decline requires a human actor and a substantive reason recorded in the audit chain.
- **Evaluation** — fixtures, expected results and gates (`python -m evaluation.run_gates`).

## Interfaces

- Web UI at `http://127.0.0.1:8080/` (`python apps/api/server.py`): resume uploader with replace/delete, job screener with multi-file upload, large results pane, multi-job review, profile review.
- JSON API documented in `apps/api/server.py`; machine-readable contracts in `packages/schemas/` (`job-document.schema.json`, `assessment.schema.json`).
