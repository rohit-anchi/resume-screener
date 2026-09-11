# Multi-job assessment (optional module 1)

One resume is assessed against several LinkedIn job PDFs. Each job is screened independently against its own employer-stated requirements; nothing is averaged across employers.

## Outputs

- **Role-by-role table** — employer, role, application platform, documented alignment, band, eligibility status, required coverage, critical gap count, tailoring effort.
- **Common target-market requirements** — concepts stated in more than one role's qualification sections.
- **Recurring resume gaps** — concepts with no or weak evidence in more than one role.
- **Domain fit** — the explicit domain requirements per role.
- **Seniority fit** — leadership/scope component plus any stated duration thresholds per role.
- **Tailoring effort** — `low` / `medium` / `high`, from the share of stated required items lacking evidence and the number of critical/high recommendations.
- **Suggested application priority** — ordered by documented alignment, then fewest critical gaps.
- **Master-resume improvements** — gaps recurring across the majority of target roles.

## Required language

> Ranking reflects documented suitability against each job's stated requirements in the submitted documents. It is not a hiring probability and does not predict any employer's decision.

The caveat is a schema default and is asserted by test, so it cannot be dropped from an API response.

## Interfaces

- UI: upload two or more job PDFs, then **Multi-job review**.
- API: `POST /api/v1/multi-job-reviews {resume_id, job_document_ids[]}` → review object plus Markdown.

## Limits

Comparability depends on how completely each employer states its requirements: a role with a short advert produces fewer requirements and a coarser score. Alignment values are comparable only in the sense that each is measured against its own job document.
