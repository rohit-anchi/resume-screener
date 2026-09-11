# SAP SuccessFactors Recruiting

## Executive summary

SAP SuccessFactors Recruiting separates a reusable Candidate Profile from a requisition-specific application. Classic Recruiting supports resume parsing, structured templates, searchable profile data, configurable applicant statuses and deterministic prescreen questions that may score, grade or auto-disqualify. Newer AI-assisted applicant screening/Skill Compatibility requires entitlement, feature switches, latest Applicant Workbench and requisition eligibility configuration. It is decision support, not evidence of universal autonomous rejection. [SAP-01–SAP-07]

## What the platform is documented to do

- **DOCUMENTED:** Configure requisitions, candidate profiles, job applications, status pipelines and recruiter workbench. [SAP-01, SAP-02, SAP-04, SAP-05]
- **CONFIGURATION-DEPENDENT:** Define fields, permissions, questions, scoring/thresholds, disqualifiers, statuses and labels. [SAP-03, SAP-05]
- **OPTIONAL:** Extract/validate skills and compare applicant-to-job skills under AI entitlement and controls. [SAP-06]
- **THIRD-PARTY:** Trigger assessments/background checks through configured vendor integrations. [SAP-08]

## End-to-end application flow

1. Approved requisition is posted through configured channels.
2. Candidate creates/uses a profile and submits a requisition-specific application, resume and prescreen answers.
3. Resume parsing may populate standard profile fields.
4. Prescreen answers may produce a weighted score/grade or configured auto-disqualification.
5. Recruiter reviews the application in the Applicant Workbench and moves it among configured statuses.
6. Hiring-manager review, assessments, interviews, offers and background checks appear as configured statuses/integrations.
7. Final status records hire, withdrawal or disposition. [SAP-02–SAP-08]

## Resume parsing

- **DOCUMENTED:** Parsing accelerates profile creation; recruiter mass upload can parse resumes and create Candidate Profiles. [SAP-02, SAP-07]
- **DOCUMENTED:** SAP support states standard Candidate Profile fields—not arbitrary custom fields—are populated; accuracy/date/language limits exist.
- **LIMITATION:** Classic parsing is data extraction, not semantic matching, AI scoring or automatic ranking.

## Structured application data

- **DOCUMENTED:** Profile stores reusable basic information and is searchable; application stores requisition-specific screening/reporting data. [SAP-02]
- **CONFIGURATION-DEPENDENT:** Profile/application templates define fields, internal/external/country context, permissions and requiredness. [SAP-01]
- **LIMITATION:** Candidate Search targets profile data, not all application or prescreen responses; Applicant Workbench is the application context.

## Screening questions and eligibility criteria

- **DOCUMENTED/CONFIGURABLE:** Prescreen questions can be role-specific, weighted and scored, define a required threshold, or act as disqualifiers. Wrong answers/below-threshold scores can move applicants to auto-disqualified status. [SAP-02, SAP-03]
- **DOCUMENTED:** Prescreen ratings can be displayed and sorted. [SAP-03]
- **LIMITATION:** Ordinary application questions are not equivalent to prescreen disqualifiers; prescreen score is deterministic, not AI.

## Search, filters, tags, and custom fields

- **DOCUMENTED:** Candidate Search operates on profile data; Applicant Workbench supports keyword search, configurable columns, quick actions and configured standard/custom/picklist filters. [SAP-02, SAP-04]
- **DOCUMENTED:** Current SAP Learning says combined latest-workbench filters use OR logic. [SAP-04]
- **NOT CONFIRMED:** A Greenhouse/Lever-like universal candidate tag construct was not established; customer fields/statuses should not be mislabeled as tags.

## Skills matching and AI capabilities

- **OPTIONAL:** AI-assisted applicant screening extracts job skills, lets recruiters validate/classify primary/secondary skills, uses resume or candidate-added skills, and groups them as matching job, relevant or unmatched. [SAP-06]
- **OPTIONAL:** Eligible requisitions can show Skill Compatibility; product material describes direct, related and potentially acquirable skills. [SAP-06, SAP-09]
- **CONFIGURATION-DEPENDENT:** SAP AI Units/commercial entitlement, AI-Assisted HXM Skills, latest Applicant Workbench, feature settings, AI Services Administration, billing object and eligibility business rule are documented prerequisites. [SAP-06]
- **LIMITATION:** This embedded use case is not automatically the Joule conversational UI and does not prove autonomous disposition.

## Recruiter and hiring-manager actions

Recruiters inspect resume, profile/application fields, prescreen answers/ratings, documents, comments, history and audit; compare/filter candidates and change statuses. Hiring-manager review is a configured status/process rather than a universal sequence. [SAP-04, SAP-07]

## Candidate pipeline

- **DOCUMENTED:** Applicant statuses represent in-progress, disqualified/disposition, hired, withdrawn and system states. [SAP-05]
- **CONFIGURATION-DEPENDENT:** Instance base set, requisition-template status subsets, transitions, internal labels and candidate-facing labels vary. [SAP-05]
- **THIRD-PARTY:** Assessment/background-check actions may trigger on entry to configured statuses. [SAP-08]

## Interview feedback and scorecards

- **DOCUMENTED:** Official process material supports interview evaluations, ratings and notes. [SAP-07]
- **CONFIGURATION-DEPENDENT:** Interview status, forms, permissions and manager actions depend on template/workflow design.
- **LIMITATION:** No reviewed source supports treating interview evaluation as the initial resume AI score.

## Native capabilities

Requisition/profile/application templates; classic resume parsing; prescreen weights/thresholds/disqualifiers; Candidate Search; Applicant Workbench; status pipeline; recruiter review and disposition. [SAP-01–SAP-07]

## Optional licensed capabilities

AI-assisted applicant screening, Skill Compatibility and related skills capabilities under AI Units/current commercial packaging and technical configuration. [SAP-06, SAP-09]

## Employer-configurable behaviours

Templates/fields/permissions, questions/weights/thresholds, status sets/transitions/labels, workbench filters, AI eligibility rules, recruiter validation and integrated service triggers.

## Third-party integrations

- **THIRD-PARTY:** Assessment/background-check/e-signature vendors require contracts, permissions and integration configuration. Native Recruiting orchestrates workflow; providers generate external results. [SAP-08]

## Candidate-controlled factors

Maintain accurate reusable profile data; review parsed fields where possible; complete application/prescreen questions truthfully; provide explicit job-relevant skill evidence; add skills when enabled. Candidates cannot know private score thresholds, status logic, AI entitlement or eligibility rules.

## Unsupported or misleading claims

- “Classic SuccessFactors parsing ranks every resume.”
- “Prescreening score is AI.”
- “AI Skill Compatibility automatically rejects applicants.”
- “Candidate Search includes every application answer.”
- “Joule chat must be deployed for embedded screening.”
- “Every tenant has identical statuses or filter logic.” [SAP-02–SAP-06]

## Evidence gaps

Current entitlement naming; model/weights/validation and independent bias evidence; automatic ordering behavior; AI data processing/retention/subprocessors; release-specific parser formats/languages; candidate explanations/appeals; exact tenant status/integration configuration.

## Sources

Primary: SAP-01–SAP-09. Full metadata: [../sources/source-register.md](../sources/source-register.md).
