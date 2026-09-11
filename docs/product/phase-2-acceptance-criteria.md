# Phase 2 acceptance criteria

| # | Criterion | Verification |
|---|---|---|
| AC1 | PDF, DOCX and TXT resumes and TXT/JSON job descriptions ingest safely; unsafe files rejected with visible findings. | `tests/test_ingestion.py` |
| AC2 | Text inside documents never alters system behaviour; injection phrases are flagged and quoted as data. | `tests/test_adversarial.py` |
| AC3 | Requirements are atomic, categorised, importance-classified, threshold-parsed, span-cited; subjective criteria are `unscorable` and never enter denominators. | `tests/test_requirements.py`, `tests/test_scoring.py` |
| AC4 | Every evidence item cites an exact span present in the extracted text. | `tests/test_evidence.py::test_no_fabricated_spans` |
| AC5 | Every requirement receives exactly one match status; `no_evidence_located` ≠ `confirmed_absent`. | `tests/test_matching.py` |
| AC6 | Eligibility is categorical, separate from the index, and uses only explicit answers/declared rules. | `tests/test_eligibility.py` |
| AC7 | Component scores are deterministic, weights sum to 100, every contribution references match IDs, band caveat present. | `tests/test_scoring.py`, `tests/test_traceability.py` |
| AC8 | Redacted screening view contains no name/email/phone/address/DOB/protected markers; scoring identical across name/pronoun/address swaps. | `tests/test_redaction.py`, `evaluation/fairness` |
| AC9 | All five profiles load; each scenario cites resolvable Phase 1 claim IDs; optional/configured labels present; prohibited phrases absent. | `tests/test_profiles.py` |
| AC10 | Candidate report has no hire/reject labels; recruiter report offers human actions only; both include limitations. | `tests/test_reports.py` |
| AC11 | Overrides are append-only, hash-chained, and visible in regenerated reports. | `tests/test_audit.py` |
| AC12 | Quality-gate runner reports thresholds (eligibility ≥95%, citation ≥90%, requirement precision ≥85%, direct-match precision ≥85%, 0 protected attributes, 100% traceability, 100% override capture, 0 automatic adverse actions). | `evaluation/run_gates.py` |
| AC13 | Release-readiness report enumerates results, limitations, risks and recommendation. | `docs/product/phase-2-release-readiness.md` |
