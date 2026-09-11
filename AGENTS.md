# Screener — project notes

Evidence-based, platform-informed application readiness assessment. Never describe outputs as an ATS score or as reproducing Greenhouse, Lever, Workday, SAP SuccessFactors, Ashby or any employer's private configuration.

## Primary workflow (two inputs)

LinkedIn job-details PDF + resume (PDF/DOCX) → job extraction → LinkedIn content classification/exclusion → ATS detection → requirement extraction → evidence extraction → matching → eligibility → component scoring → gaps, recommendations, questions, scenarios, audit.

## Layout

- `knowledge/` Phase 1 platform knowledge (claims in `knowledge/model/platform-capabilities.json`).
- `packages/screening_core/`
  - `linkedin/` block extraction, content classifier, job-document builder
  - `ats/` application-platform detection and profile selection
  - `ingestion/ security/ text/ requirements/ evidence/ matching/ eligibility/ scoring/ profiles/`
  - `recommendations/ questions/ reports/ audit/ modules/` (`multi_job`, `profile_review`)
  - `assessment.py` two-input orchestrator, `pipeline.py` core screening
- `packages/schemas/` exported JSON Schemas incl. `job-document.schema.json`, `assessment.schema.json`
- `config/` rubrics (`default@2.1.0`), confidence thresholds, platform profiles (hyphenated filenames map to underscore ids)
- `apps/api/server.py` stdlib HTTP API + static host · `apps/web/` vanilla SPA
- `evaluation/` fixtures, expected results, exclusion/ATS tests, `run_gates.py`
- `docs/` product, architecture (ADRs), security, acceptance, issues, readiness

## Commands (Windows PowerShell, Python 3.14)

- Tests: `python -m pytest -q` (135 tests)
- Gates: `python -m evaluation.run_gates` (14 gates; `--update-baseline` after intentional score changes)
- UI/API: `python apps/api/server.py` → http://127.0.0.1:8080/
- Job-fixture inspection: `python scripts/validate_job_fixtures.py [--blocks]`
- End-to-end demo: `python scripts/demo_assessment.py` (writes reports to `data/`)
- Schemas: `python -m screening_core.schemas.export` with `PYTHONPATH=packages`
- Set `$env:PYTHONIOENCODING="utf-8"` before scripts that print PDF text (emoji/curly quotes).

## Rules

- Deterministic core; LLM only via `llm/adapter.py` proposals with span validation. No scores from models.
- Job and resume text are untrusted data; never place them in an instruction slot.
- Only `BlockCategory.requirement_bearing()` employer content may produce requirements. LinkedIn match statements, applicant statistics, candidate demographics, premium/company insights, similar jobs, promotions and third-party people suggestions are retained for audit and never scored. Compensation, EEO, hiring process, application instructions and AI disclosures are employer-authored but not requirements.
- Listing source ≠ application platform. Unapproved platform (e.g. Ashby) → `platform_neutral` only; never substitute another ATS profile. Gate: `unapproved_profile_substitutions == 0`.
- Scoring reads the redacted view only. `no_evidence_located` ≠ absence. Eligibility never enters the weighted index.
- Narrative role prose is weight 0.6/0.4 and cannot create a critical gap; stated qualifications are weight 1.0.
- Recommendations and questions never invent experience, metrics or answers; every edit cites original text, requirement, supporting evidence and a verification note.
- Engine never emits `decline`; human decisions go through `ReviewService` and the hash-chained audit log.
- Profile review requires `authorisation_confirmed`; no private LinkedIn access.
- Change rubrics/profiles/lexicon by versioned file edits, then rerun gates.
- Environment: no OCR, no new native binaries, do not modify lockfiles. Local personal-data fixtures are `*.local.*` and git-ignored.
- The IDE `edit` tool intermittently fails to persist multi-line edits — verify on disk (`Select-String`) after editing, or patch via a script.
