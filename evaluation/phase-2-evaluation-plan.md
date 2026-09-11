# Phase 2 evaluation plan

## Datasets

- `evaluation/datasets/`: synthetic job descriptions and resumes (no real personal data).
- `evaluation/expected-results/`: annotated requirement lists, expected match statuses, eligibility outcomes.
- `evaluation/fairness/`: paired variants (name, pronoun, address, graduation-year, terminology, verbosity, career break).
- `evaluation/adversarial/`: injection, hidden text, keyword stuffing, conflicting dates, protected info, rule-bypass instructions.

## Metrics and thresholds

| Metric | Threshold | Computation |
|---|---|---|
| Deterministic eligibility accuracy | ≥ 95% | expected vs actual eligibility status over cases |
| Citation-to-source accuracy | ≥ 90% | evidence spans present verbatim in extracted text |
| Required-requirement extraction precision | ≥ 85% | extracted required concepts ∩ annotated / extracted |
| Direct evidence-match precision | ≥ 85% | direct matches judged correct in annotations |
| Protected attributes in scoring | 0 | redaction invariance + view inspection |
| Score-contributing traceability | 100% | every contribution → match → evidence → span |
| Override capture | 100% | every override → audit event |
| Automatic adverse actions | 0 | no decline without human event |
| Score invariance under fairness swaps | Δ index = 0 | paired runs |

## Regression

`evaluation/regression/baseline.json` stores component scores per case; runner fails on unexplained deltas.

## Reporting

`python -m evaluation.run_gates` writes `evaluation/reports/gate-report.json` and Markdown summary; any critical gate failure exits non-zero.
