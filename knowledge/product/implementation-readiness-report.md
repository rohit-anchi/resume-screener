# Implementation-readiness report

## Decision

**Ready for Phase 2 discovery/prototyping; not ready for a production scoring engine or autonomous screening.**

The foundation supports a source-grounded capability ontology, scenario-based simulation, parser/evidence prototype and explanation UX. It does not support universal ATS weights, employer outcome prediction, exact scores or automatic adverse action.

## What is ready

- Four platform capability models with native/optional/configured/third-party distinctions.
- Source register, rejected myths and claim-level machine-readable dataset.
- Cross-platform capability, stage and automation matrices.
- Defensible candidate dimensions without formula/weights.
- Responsible-AI, audit and explanation requirements.

## Blocking evidence gaps for production

1. Representative resume parser benchmark by format, language, accessibility and layout.
2. Validity study linking proposed criteria to job performance for defined role families.
3. Independent fairness/adverse-impact evaluation and proxy analysis.
4. Legal review by deployment jurisdiction and employer use case.
5. Candidate notice, correction, accommodation, appeal and deletion design.
6. Model cards/data-processing terms for any selected AI or third-party provider.
7. Tenant-level configuration input model; no employer behavior may be assumed.
8. Security, privacy, retention, audit and incident controls.
9. Human-factors evidence that explanations reduce automation bias.
10. Current platform entitlement/release revalidation before platform-specific claims ship.

## Recommended Phase 2 scope

Build a non-production **evidence extraction and scenario prototype** that:

- ingests a job description and resume;
- redacts/excludes protected attributes before evaluation;
- extracts criterion/evidence pairs with source spans and confidence;
- keeps eligibility, alignment, evidence strength and parseability separate;
- supports manual, configured-rule, optional-match and third-party scenarios;
- produces explanations and abstains on ambiguity;
- records a complete audit event;
- never outputs a universal ATS score or automated final decision.

## Phase 2 acceptance criteria

1. Every requirement is classified mandatory/preferred/contextual and traceable to the job input.
2. Every material candidate finding cites exact resume evidence or returns `not found`/`unknown`.
3. Protected attributes and defined proxies are excluded and verified by tests.
4. Missing evidence is distinct from confirmed non-qualification in schema and UX.
5. Parseability warnings cannot reduce qualification alignment.
6. Scenario and employer-configuration assumptions are explicit and user-selectable.
7. No UI/API uses prohibited claims such as “exact ATS score” or guaranteed pass.
8. No Level 5 decision; Level 4 actions are simulated only and require human confirmation.
9. Model, prompt, rubric, source, evidence and reviewer actions are audit logged.
10. Candidate can inspect/correct extraction and request human review/accommodation.
11. Benchmark reports extraction accuracy, attribution accuracy, false-negative rate and subgroup/accessibility results.
12. Security/privacy threat model and retention/deletion tests pass.
13. JSON claims validate against the schema; source IDs resolve to the register.
14. Responsible-AI/legal owners approve a documented go/no-go before pilot.

## Go/no-go for later production pilot

Proceed only after all blockers have named owners, evidence artifacts and approved thresholds. Pilot should remain advisory (Automation Levels 1–3), monitored, reversible and human-controlled.
