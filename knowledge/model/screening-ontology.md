# Screening ontology

## Core entities

- **Person/Candidate:** reusable identity and profile record.
- **Application/Opportunity:** consideration of a person for one requisition.
- **Requisition/Job:** role definition, requirements, location and workflow configuration.
- **Artifact:** resume, cover letter, answer, assessment, note, feedback or attachment.
- **Evidence item:** bounded statement from an artifact linked to a requirement.
- **Requirement:** mandatory, preferred or contextual role criterion.
- **Capability claim:** sourced assertion about a platform mechanism.
- **Stage:** configured application state in a pipeline/business process.
- **Action:** advance, route, tag, request information, archive/decline, recommend or hire.
- **Actor:** candidate, recruiter, hiring manager, interviewer, administrator, rule engine, AI service or integration.
- **Disposition:** reason/status explaining why consideration ended.

## Screening mechanisms

1. **Ingestion:** receives artifacts and structured answers.
2. **Parsing:** converts artifact text into fields; no suitability inference implied.
3. **Eligibility rule:** evaluates explicit answers against configured conditions.
4. **Search/filter:** retrieves records using text or structured facets.
5. **Matching:** compares candidate evidence with role criteria.
6. **Prioritisation:** orders or groups candidates for review.
7. **Human evaluation:** records recruiter/interviewer judgment.
8. **Workflow automation:** performs configured state/action changes.
9. **Integration:** exchanges data with an external assessment or screening service.

## Capability categories

`native-documented`, `optional-licensed`, `employer-configured`, `third-party`, `common-practice`, `unverified`.

## Automation levels

| Level | Meaning | Example |
|---|---|---|
| 0 | Record keeping only | Store resume or disposition |
| 1 | Human review support | Parsed profile or scorecard form |
| 2 | Search, filter or rule-assisted review | Boolean search or eligibility flag |
| 3 | Recommendation, matching or prioritisation | Explained skills match |
| 4 | Configured automated workflow action | Answer-triggered auto-decline |
| 5 | Fully automated decision | Not assigned in this knowledge base |

## Evidence semantics

- **Observed evidence:** directly present in resume/application.
- **Derived evidence:** transparent normalization or calculation from observed evidence.
- **Missing evidence:** not found; never equivalent to confirmed absence.
- **Contradictory evidence:** artifacts disagree; requires human resolution.
- **Unknown:** extraction or interpretation is insufficient.

## Claim identity

A claim is unique by `platform + capability + mechanism + scope + release`. Claims retain evidence IDs, precise references, confidence, limitations and verification date. Employer-specific scenarios are overlays and never overwrite platform-level facts.
