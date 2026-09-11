# Phase 2 plan — vertical slice

Product name in all outputs: **Evidence-based, platform-informed application readiness assessment**.

## Objective

Deliver a runnable, tested, auditable MVP slice covering all 13 mandated steps with deterministic core logic and a stubbed LLM seam. Stop before production deployment.

## Task breakdown

| ID | Task | Depends on | Acceptance criteria |
|---|---|---|---|
| T1 | Plan, architecture, threat model, acceptance criteria, evaluation plan | — | Five docs exist; ADRs recorded; task list approved implicitly by proceeding. |
| T2 | Versioned schemas (`screening_core/schemas`) + JSON Schema export | T1 | All models carry `schema_version`; export script produces files; round-trip validation test passes. |
| T3 | Secure ingestion: type/size/MIME/extension consistency, encrypted/embedded-file/macro/page-count checks, PDF/DOCX/TXT extraction, image-only detection, injection-pattern detection, redaction view | T2 | Malformed/oversized/encrypted/macro files rejected with findings; injection text preserved as data and flagged; redacted view has no contact/protected markers; spans retained. |
| T4 | Job-requirement extraction: sectioning, atomic split, category, importance, thresholds, unscorable detection, review flags | T2 | Sample JD yields atomic requirements with spans; subjective phrases flagged unscorable; thresholds parsed. |
| T5 | Candidate-evidence extraction: sections, roles, date normalisation, duration, skills, achievements/quantification, education/certifications, contradictions | T3 | Every evidence item has a span; overlapping/unknown dates flagged; no fabricated items (test asserts every span substring-exists in source). |
| T6 | Requirement→evidence matching: direct, equivalent-term (visible lexicon), transferable (labelled), duration calc, statuses, verification questions | T4, T5 | Every requirement receives exactly one status; semantic matches carry explanation; low confidence → review. |
| T7 | Deterministic eligibility engine over application answers + employer rules | T2 | Categorical result only; missing answer → `additional_information_required`; conflicts → review; no resume inference. |
| T8 | Scoring: component scores, rubric registry (weights sum 100, versioned), confidence, bands with caveat | T6, T7 | Deterministic recalculation; unscorable excluded from denominators; eligibility never in index; every contribution references match IDs. |
| T9 | Platform profiles + scenario renderer | T8, knowledge claims | 5 profiles; every scenario cites existing claim IDs; optional/configured labels; no “exact score” language (lint test). |
| T10 | Reports (candidate, recruiter-assist, JSON) + HTTP API | T9 | Candidate report never shows hire/reject; recruiter report shows human actions only; limitations block present. |
| T11 | Review/override + append-only hash-chained audit | T10 | Override creates new event; chain verifies; report regenerates with override visible. |
| T12 | Test suites: unit, integration, regression, fairness, adversarial; quality-gate runner | T3–T11 | Thresholds in evaluation plan evaluated; gate report generated; critical failures block. |
| T13 | Release-readiness report | T12 | Documents results, limitations, risks, pilot recommendation. |

## Quality gates after each workstream

1. `pytest` green.
2. Schema export validated against samples.
3. Traceability test: score → match → evidence → span.
4. Protected-attribute exclusion test on redacted view.
5. Platform-claim resolution test.
6. Unresolved issues appended to `docs/product/phase-2-issues.md`.

## Explicit non-goals

See Phase 2 scope §2.2 of the brief; additionally no UI, no persistence beyond local files, no live LLM, no OCR.
