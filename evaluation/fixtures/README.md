# Fixtures

## `jobs/` — LinkedIn job-details PDFs (committed)

| File | Employer / role | Application platform | Profile applied |
|---|---|---|---|
| `amber-electric-director-of-product.linkedin.pdf` | Amber Electric — Director of Product | Lever | `lever_informed` |
| `xero-lead-product-manager-ai-enablement.linkedin.pdf` | Xero — Lead Product Manager, AI Enablement | Ashby | `platform_neutral` (Ashby not researched) |

Expected extraction, classification, exclusion and ATS results: `../expected-results/job-extraction/`.

## `resumes/` and `profiles/` — local personal data (do NOT commit)

`candidate-resume.local.pdf` and `candidate-linkedin-profile.local.pdf` contain real personal data and are used only to exercise the workflow on this machine. Files matching `*.local.*` are git-ignored. Tests that need them are skipped when absent:

```python
@pytest.mark.skipif(not RESUME.exists(), reason="local resume fixture not present")
```

Replace them with synthetic documents before sharing this repository.
