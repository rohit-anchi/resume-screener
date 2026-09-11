# Phase 2 release-readiness report

Date: 2026-09-09 · Scope: vertical-slice MVP · Status: **Not ready for production; ready for internal evaluation-mode use and controlled pilot preparation.**

## 1. Features implemented

| Step | Capability | Location |
|---|---|---|
| 2 | Versioned schemas (pydantic + 16 exported JSON Schemas, `schema_version` 2.0.0) | `packages/screening_core/schemas`, `packages/schemas/` |
| 3 | Secure ingestion (PDF/DOCX/TXT; type/magic/MIME/size/page limits; encrypted, JS, embedded-file, macro, zip-bomb checks), hidden-text/column heuristics, injection detection, keyword-repetition and duplicate detection, structural redaction | `ingestion/`, `security/` |
| 4 | Job-requirement extraction: sectioning, atomic split, category, importance (section outranks cues), thresholds, OR-alternatives, unscorable/subjective flags | `requirements/extractor.py` |
| 5 | Evidence extraction: roles, YYYY-MM dates, achievements, quantification, education, certifications, explicit statements of absence, overlap/multi-current contradictions; parseability report | `evidence/extractor.py` |
| 6 | Matching: direct / equivalent-term / labelled transferable; merged-duration thresholds; 8 statuses; verification questions | `matching/matcher.py` |
| 7 | Deterministic eligibility from explicit answers + declared rules only | `eligibility/engine.py` |
| 8 | 7 component scores, hashed/versioned rubric (weights sum 100), bands with caveat, confidence, OCR suppression | `scoring/` , `config/rubrics` |
| 9 | 5 platform profiles; every scenario cites Phase 1 claim IDs and delivery label; prohibited-language lint | `config/platform-profiles`, `profiles/loader.py` |
| 10 | Candidate and recruiter-assist Markdown reports, JSON export, stdlib HTTP API (12 endpoints) | `reports/render.py`, `apps/api/server.py` |
| 11 | Review/override service, append-only hash-chained audit, human-only decisions | `audit/` |
| 12 | 67 tests (unit, integration, adversarial, API) + quality-gate runner (eligibility, citation, extraction, matching, traceability, protected attributes, override capture, adverse actions, fairness, adversarial, regression) | `tests/`, `evaluation/` |

## 2. Test and evaluation results

- `python -m pytest`: **67 passed**.
- `python -m evaluation.run_gates`: **all 10 gates passed** (see `evaluation/reports/gate-report.md`).

| Gate | Threshold | Result |
|---|---|---|
| Deterministic eligibility accuracy | ≥ 0.95 | 1.00 |
| Citation-to-source accuracy | ≥ 0.90 | 1.00 |
| Required-requirement extraction precision | ≥ 0.85 | 1.00 |
| Direct evidence-match precision | ≥ 0.85 | 1.00 |
| Protected attributes in scoring view | 0 | 0 |
| Score-contributing traceability | 100% | 100% |
| Override capture | 100% | 100% |
| Automatic adverse actions | 0 | 0 |
| Fairness max Δ index (8 variants) | 0.0 | 0.0 |
| Adversarial pass rate (6 cases) | 100% | 100% |
| Regression vs baseline | no unexplained delta | ok |

Caveat: the benchmark is synthetic and small (issue I-13). Results demonstrate mechanism correctness, not generalisation.

## 3. Quality-gate review per workstream

Each workstream was checked for: tests green; schema export valid; score→match→evidence→span traceability; protected-attribute exclusion; platform-claim resolution. All pass. Unresolved items are logged in `docs/product/phase-2-issues.md`.

## 4. Known limitations

See issues I-01 to I-13. Principal: no OCR; lexicon-bounded semantics; single-resume fairness fixture; unvalidated weights; no RBAC/persistence; local audit file.

## 5. Security and responsible-AI findings

- Injection text is detected, quoted as data, and demonstrably does not alter scores or eligibility (tests + adversarial gate).
- Structural redaction removes name, email, phone, URL, address, DOB, pronouns, honorifics, graduation year and protected-attribute lines before extraction; scores are invariant under fairness swaps.
- No Level 5 action exists; `decline` requires a human actor and a substantive reason and is recorded as an audit event.
- Remaining risks: proxy attributes (employer, school, location words inside sentences) are retained; heuristic name redaction; no independent bias audit; no legal review.

## 6. Platform-profile coverage

| Profile | Scenarios | Claims cited | Labels |
|---|---|---|---|
| platform_neutral | 2 | 8 (cross-platform) | COMMON PRACTICE, CONFIGURATION-DEPENDENT |
| greenhouse_informed | 5 | GH-C02–GH-C05 | DOCUMENTED, OPTIONAL |
| lever_informed | 4 | LV-C01–LV-C06 | DOCUMENTED, CONFIGURATION-DEPENDENT, OPTIONAL |
| workday_informed | 4 | WD-C01–WD-C06 | DOCUMENTED, CONFIGURATION-DEPENDENT, OPTIONAL |
| successfactors_informed | 4 | SAP-C01–SAP-C06 | DOCUMENTED, CONFIGURATION-DEPENDENT, OPTIONAL |

Profiles change scenario presentation only; alignment index is identical across profiles (tested).

## 7. Outstanding risks

1. Weight/credit validity and adverse-impact evidence absent (blocks any hiring-influencing pilot).
2. Lexicon coverage limits recall on unfamiliar roles; "unmapped" requirements need human classification.
3. Absence of OCR excludes scanned resumes (accessibility consideration).
4. No authentication; must not be exposed beyond localhost.
5. Candidate notice, correction and appeal UX not built.

## 8. Recommendation

- **Approve** for internal evaluation-mode use and for recruiter-assist trials on synthetic/consented data with human decision-making only.
- **Do not approve** a candidate-facing or hiring-influencing pilot until: annotated benchmark ≥100 pairs; validity and adverse-impact review; RBAC + persistent WORM audit; OCR decision; legal/privacy sign-off; candidate recourse workflow.

## 9. Rollback

Rubrics, profiles, lexicon and prompts are versioned files; every report embeds versions and rubric hash. Rollback = restore prior file versions; regression runner detects score deltas.
