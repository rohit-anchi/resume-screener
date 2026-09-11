# ATS detection

## Principle

The **listing source** (where the job was advertised) and the **application platform** (where the application is submitted and processed) are different concepts. A job listed on LinkedIn may apply through Lever, Ashby, Greenhouse, Workday, SAP SuccessFactors, a bespoke careers site, or LinkedIn itself.

## Signals, in priority order

1. **Application link host** (weight 1.0, confidence 0.95). LinkedIn wraps outbound links in `/safety/go/?url=…` with percent-encoded dots (`jobs%2Elever%2Eco`). `_unwrap` expands the redirect, decodes nested encodings and normalises `%2E` before host matching.
2. **Off-LinkedIn application destination** that is not a known platform (weight 0.6, confidence 0.6) → `other`.
3. **Document text mention** (weight 0.3, confidence 0.35 when no link exists) — corroboration only.
4. **Listing metadata** such as "Responses managed off LinkedIn" (weight 0.1) — recorded, never decisive.

Every signal is retained in `AtsDetection.signals` for audit.

## Host patterns

| Platform | Hosts |
|---|---|
| Greenhouse | `boards.greenhouse.io`, `job-boards.greenhouse.io`, `my.greenhouse.io`, `greenhouse.io`, `grnh.se` |
| Lever | `jobs.lever.co`, `hire.lever.co`, `lever.co` |
| Ashby | `jobs.ashbyhq.com`, `ashbyhq.com` |
| Workday | `*.myworkdayjobs.com`, `*.myworkdaysite.com`, `wd*.myworkdayjobs.com`, `workday.com` |
| SAP SuccessFactors | `successfactors.com`, `successfactors.eu`, `jobs.sap.com`, `rmkcdn.successfactors.com` |

## Profile selection

```
platform ∈ {greenhouse, lever, workday, sap_successfactors}  →  that platform's Phase 1 profile
platform ∈ {ashby, other, unknown}                           →  platform_neutral
```

`PROFILE_BY_PLATFORM` is the only mapping. There is no nearest-neighbour fallback: an unapproved platform is **never** assessed with another platform's profile. A gate (`unapproved_profile_substitutions`) fails the build if that ever happens, and `has_approved_knowledge_profile` is surfaced in the UI and the report.

## Adding a platform profile

1. Research the platform to Phase 1 evidence standards and add claims to `knowledge/model/platform-capabilities.json`.
2. Add `config/platform-profiles/<platform>_informed.json`; every scenario must cite existing claim IDs for that platform (enforced by the loader and by `tests/test_profiles.py`).
3. Add the host pattern and the `PROFILE_BY_PLATFORM` entry in `ats/detect.py`.
4. Add an `evaluation/ats-detection-tests/cases.json` case.

Until step 1 is approved, the platform stays on the neutral profile. **Ashby is currently in this state**: detection is reliable, knowledge is not researched.

## Validated results

| Fixture | Listing | Platform | Confidence | Profile | Approved |
|---|---|---|---|---|---|
| Amber Electric — Director of Product | linkedin | lever | 0.95 | `lever_informed` | yes |
| Xero — Lead PM, AI Enablement | linkedin | ashby | 0.95 | `platform_neutral` | no |

Ten additional detection cases cover Greenhouse (direct and `grnh.se`), Workday tenants, SuccessFactors tenants, text-only mentions, bespoke careers sites, LinkedIn-only apply and the no-signal case.
