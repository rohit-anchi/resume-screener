# Phase 2 unresolved issues log

| ID | Workstream | Issue | Severity | Disposition |
|---|---|---|---|---|
| I-01 | Ingestion | No OCR engine; image-only PDFs are flagged `not assessable` and scoring is suppressed. | High for scanned resumes | Adapter seam exists; requires approved OCR provider. |
| I-02 | Extraction | Lexicon-based concept matching (≈30 concepts). Requirements outside the lexicon become `unmapped_*` and require human classification. | High for general use | Extend lexicon via config; Phase 3 LLM proposals must pass span validation. |
| I-03 | Extraction | Compound requirements joined by "and" (e.g. "SQL and analytics tooling") are matched on the longest concept only; not split atomically. | Medium | Add conjunction splitting with per-part concepts. |
| I-04 | Extraction | Role header parsing assumes `Title | Employer | Dates` or `Title, Employer, Dates` patterns; unusual layouts may misattribute employer/title. | Medium | Extend patterns; benchmark on real layouts. |
| I-05 | Evidence | "Career break" lines with dates are parsed as roles (no concepts, no score effect). | Low | Add explicit break detection; ensure it is never scored negatively. |
| I-06 | Scoring | Component weights and status credits (1.0/0.85/0.5/0.2) are initial engineering defaults, not validated against job performance. | High before pilot | Validity study required (see readiness report). |
| I-07 | Fairness | Fairness suite covers 8 synthetic variants on one resume; no real-population subgroup analysis. | High before pilot | Expand dataset; independent review. |
| I-08 | Security | API has no authentication/RBAC; localhost only. | Blocker for any shared deployment | Implement RBAC roles defined in brief §16.3. |
| I-09 | Audit | Audit store is a local JSONL file; not WORM. | Medium | Move to append-only service before pilot. |
| I-10 | Persistence | Jobs/candidates/screenings held in memory; lost on restart. | Medium | Add relational/object storage. |
| I-11 | Redaction | Name heuristic uses title-case first lines; unusual names or headers may not redact; proxies such as employer names and schools are retained by design. | Medium | Add NER-based redaction with span validation; governance decision on proxy handling. |
| I-12 | Tooling | The IDE `edit` tool intermittently failed to persist multi-line edits; changes were applied via scripted patches and verified on disk. | Process | Verify on-disk state after edits. |
| I-13 | Evaluation | Dataset is synthetic and small (2 JDs, 3 resumes, 8 fairness variants, 6 adversarial cases) plus 2 real LinkedIn job PDFs. Metrics at 100% reflect fixture fit, not generalisation. | High | Build annotated benchmark ≥100 pairs before pilot claims. |

## Two-input workflow additions (this iteration)

| ID | Area | Issue | Severity | Disposition |
|---|---|---|---|---|
| I-14 | LinkedIn ingestion | Classifier is rule-based and validated on 2 exports from one locale/date. LinkedIn changes its layout frequently; new chrome may land in `unknown` (excluded, flagged) or, worse, be inherited into an excluded region. | High | Gate `linkedin_exclusion_accuracy` plus `unknown`-block warnings; expand fixtures across locales, Easy Apply, and promoted/basic listings. |
| I-15 | LinkedIn ingestion | Clipped render fragments are discarded. In both fixtures the intact text existed elsewhere, but a requirement present *only* in a clipped block would be silently lost; a warning is emitted but cannot detect the case. | Medium | Compare discarded fragment tokens against retained text and escalate when unmatched. |
| I-16 | Ashby | Detection is reliable but no approved knowledge profile exists, so Ashby applications are assessed platform-neutrally. | Medium | Research Ashby to Phase 1 evidence standards, then add the profile per `docs/architecture/ats-detection.md`. |
| I-17 | Requirement extraction | Cross-block sentence continuations (page breaks) are not unwrapped; only within-block soft wraps are. Affects narrative sections at weight 0.4–0.6. | Low | Extend unwrapping across adjacent same-section blocks. |
| I-18 | Concept coverage | Lexicon is 44 concepts. Requirements outside it become `unmapped_*`, flagged for human classification and excluded from concept matching. | High for other domains | Extend lexicon per target market; Phase 3 LLM proposals must pass span validation. |
| I-19 | Scoring | Rubric `default@2.1.0` weights (incl. the new 12% leadership/scope component) remain unvalidated engineering defaults. | High before pilot | Validity study; see readiness report. |
| I-20 | Profile review | Section detection relies on LinkedIn export headings ("Summary", "Experience", "Top Skills", "Certifications"); other export variants may parse partially, and row statuses are indicative. | Medium | Broaden patterns; add export-variant fixtures. |
| I-21 | Multi-job | Comparability depends on advert completeness: a terse advert yields fewer requirements and a coarser score. | Medium | Surface requirement counts alongside alignment in the UI. |
| I-22 | Personal data | Real resume/profile fixtures live locally under `evaluation/fixtures/{resumes,profiles}/` and are git-ignored. Tests skip when absent. | Medium | Replace with synthetic equivalents before sharing the repository. |
| I-23 | API/UI | Single active resume per server instance, in-memory state, no auth. | Blocker for shared deployment | Add RBAC and persistence (see I-08, I-10). |
