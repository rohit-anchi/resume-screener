# Responsible-AI requirements

## Prohibited inputs and inferences

- Protected/sensitive attributes and direct identifiers must be removed from model scoring context.
- Prohibit proxy features, including location/school/employer prestige unless a documented job-related purpose and fairness review exists.
- Prohibit inferred personality, emotion, health, family/demographic status and culture fit.
- Do not train on historical hiring outcomes without explicit bias, validity, consent, provenance and legal review.

## Governance controls

| Control | Requirement |
|---|---|
| Purpose | Define role-related use, affected population, owner and prohibited uses. |
| Data | Record provenance, lawful basis, minimization, retention, residency and subprocessors. |
| Rubric | Version mandatory/preferred criteria; require job analysis and approval. |
| Model | Version model/prompt/configuration; document limits, confidence and fallback. |
| Explainability | Link every material finding to source text and criterion; disclose derivation. |
| Human oversight | Reviewer can inspect evidence, override, record reason and escalate uncertainty. |
| Candidate rights | Notice, correction, accommodation, alternative review, contest/appeal and contact channel. |
| Fairness | Predeployment and recurring subgroup performance/adverse-impact analysis; intersectional where lawful. |
| Quality | Measure extraction, evidence attribution, false negative/positive, calibration and abstention. |
| Security | Least privilege, encryption, tenant isolation, prompt-injection defenses and audit logging. |
| Monitoring | Drift, override, complaint, failure and disparate-outcome alerts with rollback criteria. |
| Vendors | Model/data-flow due diligence, contractual restrictions, incident reporting and deletion guarantees. |

## Decision policy

- Automation Levels 0–3 may support review when evidence and explanations are visible.
- Level 4 requires explicit customer configuration, validated job-related rules, pre-adverse human review where required, and reversible actions.
- Level 5 is prohibited for the future product under this foundation.
- Unknown, conflicting or low-confidence evidence must abstain rather than become a negative score.

## Audit event minimum

`event_id`, tenant, role/requisition, candidate pseudonymous ID, timestamp, actor, model/rubric/version, scenario, input hashes, criteria, evidence spans, transformations, outputs/confidence, protected-data exclusion result, human action/override/reason and notices delivered.

## Validation gates

1. Legal and employment-selection validity review.
2. Independent responsible-AI/security review.
3. Representative parser/evidence benchmark.
4. Accessibility and accommodation testing.
5. Adverse-impact analysis with approved thresholds/remediation.
6. Human-factors test showing explanations enable—not anchor—reviewers.
7. Incident, appeal, rollback and deletion runbooks.
