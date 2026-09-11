# Phase 2 architecture

## Current state (inspected 2026-09-09)

- Repository contained only `/knowledge` (Phase 1 foundation, 21 Markdown/JSON files). No application code, no git history, no build tooling.
- Environment: Windows, Python 3.14, pydantic 2.12, PyMuPDF 1.28, python-docx, jsonschema, pytest, uvicorn; Node 25 available but unused; **no OCR engine**; endpoint security blocks unapproved native binaries.

## Architecture decisions (ADRs)

| ADR | Decision | Rationale |
|---|---|---|
| ADR-001 | Single Python package `screening_core` under `packages/screening_core`, with one module per logical service (ingestion, requirements, evidence, matching, eligibility, scoring, profiles, reports, audit). | Vertical-slice MVP; service boundaries preserved as module boundaries so a later split into `/services` is mechanical. |
| ADR-002 | Standard-library HTTP API (`apps/api`) over an in-process pipeline. | No new dependencies; avoids blocked installs; API surface matches the Phase 2 endpoint list. |
| ADR-003 | Pydantic v2 models are the source of truth; JSON Schema is exported to `packages/schemas/` and version-stamped. | One definition, machine-validated contracts, drift test. |
| ADR-004 | Deterministic core; LLM access only through `llm/adapter.py` protocol with a deterministic `NullLLMAdapter`. LLM outputs are proposals that must pass schema validation and evidence-span verification before use. Never produce scores. | Prevents hidden decisions; keeps tests reproducible; no credentials available. |
| ADR-005 | Resume text is quarantined as data: it is never concatenated into prompt instruction slots; the adapter receives it in a `untrusted_documents` field only; injection patterns are detected and reported as document findings. | Prompt-injection constraint. |
| ADR-006 | Protected-attribute handling: a `security/redaction.py` pass produces a screening view with names, emails, phones, addresses, DOB, photos, gender/marital/religion/nationality/health/political markers removed before extraction. Scoring consumes the redacted view only; contact fields live solely in the parseability report. | Protected-attribute exclusion is structural, not policy-only. |
| ADR-007 | Eligibility is a categorical result computed from explicit application answers and employer-declared rules only; it is never blended into the alignment index. | Phase 1 scoring constraints. |
| ADR-008 | Missing evidence is `no_evidence_located` and excluded from "confirmed absent"; unscorable/subjective requirements are excluded from denominators. | Phase 1 principle 11. |
| ADR-009 | Audit store is append-only JSONL with hash chaining; overrides are new events referencing prior events. | Immutable trail. |
| ADR-010 | Platform profiles are data (`config/platform-profiles/*.json`) whose every scenario references claim IDs in `knowledge/model/platform-capabilities.json`; a test fails if a referenced claim does not exist. | Platform-claim traceability. |
| ADR-011 | OCR is an adapter seam; image-only documents are flagged `not_assessable_ocr_required` and qualification scoring is suppressed for them. | No OCR binary permitted. |
| ADR-012 | No automatic adverse action: the engine emits `recommended_human_action` only; API review endpoint records human decisions. | Level 5 prohibited. |

## Component diagram

```
apps/api (stdlib HTTP)  ──►  screening_core.pipeline.run_screening
                                  │
   ingestion.safety ─► ingestion.extract (pdf/docx/txt) ─► ingestion.parseability
                                  │ redacted screening view (security.redaction)
          requirements.extractor ─┴─ evidence.extractor
                                  │
                          matching.matcher  ──► verification questions
                         ┌────────┴────────┐
             eligibility.engine        scoring.engine (rubric registry)
                         └────────┬────────┘
                    profiles.scenarios (claims-traced) ─► reports (candidate / recruiter / json)
                                  │
                        audit.store (append-only, hash-chained) ◄── review/override
```

## Data flow contracts

Every stage emits versioned models (`schema_version`), each carrying `source_location` spans back to the extracted text and document hash. Scores reference match IDs; matches reference evidence IDs and requirement IDs.

## Deferred

Object storage, relational DB, search index, RBAC provider, UI, live LLM provider, OCR provider, multi-tenant configuration.
