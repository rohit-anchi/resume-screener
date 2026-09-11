# Workday Recruiting

## Executive summary

Workday Recruiting centers on a configurable `Job Application` business process. Review is the initiation step and Ready for Hire the completion step; intermediate subprocesses and routes vary. Native parsing populates structured fields but excludes Skills and does not imply ranking. Questionnaires and condition rules can support configured automatic advance/decline. Separate capabilities include deterministic candidate rating/ranking, optional Candidate Skills Match, and optional HiredScore AI for Recruiting. [WD-01–WD-09]

## What the platform is documented to do

- **DOCUMENTED:** Manage candidate/application records through Review, Screen, Assessment, Interview, Reference Check, Offer, Employment Agreement, Background Check and Ready for Hire subprocess types. [WD-01]
- **CONFIGURATION-DEPENDENT:** Define route/order, repeated or parallel stages, assignees, conditions and dispositions. [WD-01]
- **DOCUMENTED:** Parse resumes and allow users to review structured output. [WD-02]
- **OPTIONAL:** Match skills or use HiredScore prioritization where purchased/enabled. [WD-05, WD-08, WD-09]

## End-to-end application flow

1. Candidate submits application; Workday creates the job application and assigns Review.
2. Authorized reviewer inspects resume/cover letter and selects Move Forward or Decline.
3. Move Forward exposes eligible next subprocesses under tenant conditions.
4. Candidate may traverse any configured combination/order of Screen, Assessment, Interview, Reference, Offer, Agreement and Background Check.
5. Decline prompts an eligible disposition; candidate-facing label/notification can differ.
6. Ready for Hire completes recruiting and initiates the applicable staffing transaction. [WD-01]

## Resume parsing

- **DOCUMENTED:** Resume parsing populates fields and permits review of parsed data. [WD-02]
- **DOCUMENTED:** Parsing does not populate hidden fields or Skills; results vary with format and word order, and image-heavy resumes are discouraged. [WD-02]
- **CONFIGURATION-DEPENDENT:** External resume autofill can be hidden through application templates. [WD-02]
- **LIMITATION:** Parsing is not evidence of automatic qualification, rank, advance or decline.

## Structured application data

- **CONFIGURATION-DEPENDENT:** Job application templates determine visible, hidden and required sections/fields and may vary by requisition.
- **DOCUMENTED:** Candidate tasks can collect information at subprocesses and return it to the candidate profile. [WD-01]
- Sensitive personal-information collection exists in localized tasks but must be excluded from future screener scoring.

## Screening questions and eligibility criteria

- **DOCUMENTED/CONFIGURABLE:** Questionnaires can be placed in any subprocess, support branching and integer scoring, and expose answers/totals under security controls. [WD-03]
- **CONFIGURATION-DEPENDENT:** Ordered condition rules can automatically route, advance or decline based on application, questionnaire, assessment and other data. [WD-04]
- **LIMITATION:** This is customer-authored workflow automation, not necessarily AI and not universal.

## Search, filters, tags, and custom fields

- **DOCUMENTED:** Find Candidates offers security-controlled search/facets and actions; candidate grids and saved filters can be configured. [WD-07]
- **CONFIGURATION-DEPENDENT:** Candidate rating/ranking templates map tenant-selected fields, values, priorities and weights and can be invoked for a requisition. [WD-06]
- **UNVERIFIED:** Reviewed official evidence did not confirm general raw-resume full-text/Boolean search; do not assert it.

## Skills matching and AI capabilities

- **OPTIONAL:** Candidate Skills Match uses ML to compare Skills Cloud skills derived from application/resume with requisition skills, weights required skills more, and shows Required, Relevant and Not Found details or Unable to Score. [WD-05]
- **OPTIONAL:** HiredScore AI for Recruiting supports prioritization, rediscovery, candidate insights, text/filter search and recommendations. [WD-08]
- **OPTIONAL:** HiredScore Fit & Gap evaluates individual basic/preferred qualifications against parsed profile evidence and explains contributions to a Spotlight grade. [WD-09]
- **LIMITATION:** HiredScore is separately purchased; Workday's human-oversight assertions are first-party governance claims. [WD-08, WD-10]

## Recruiter and hiring-manager actions

Review resumes/cover letters, Move Forward, Decline, choose dispositions, compare/filter/rank candidates, inspect questionnaires/assessments, schedule interviews, review feedback and approve offers. Actor and permissions are business-process/security configured. [WD-01, WD-03, WD-06]

## Candidate pipeline

- **DOCUMENTED:** Review initiates and Ready for Hire completes. [WD-01]
- **CONFIGURATION-DEPENDENT:** Intermediate subprocesses have no universal required order; candidates can follow different paths, repeat stages or use configured parallel stages. [WD-01]
- **DOCUMENTED:** Assessment, reference, offer, agreement and background-check stages can track native workflow while external providers execute integrated services.

## Interview feedback and scorecards

- **DOCUMENTED:** Interview subprocess supports scheduling, one or more interviewers, feedback, ratings/comments and a decision-maker. [WD-01]
- **CONFIGURATION-DEPENDENT:** Interview rounds, questions, reviewers and next steps vary.
- **LIMITATION:** Interview ratings are not proven to be initial resume-screening scores.

## Native capabilities

Dynamic Job Application BP; delivered subprocess types; candidate/application records; parsing; questionnaires; dispositions; candidate search/facets; configured rating/ranking; interview/reference/offer/background tracking. [WD-01–WD-07]

## Optional licensed capabilities

Candidate Skills Match/Skills Cloud; HiredScore AI for Recruiting/Recruiting Agent; some masking, integration and advanced features subject to entitlement. [WD-05, WD-08, WD-09]

## Employer-configurable behaviours

Application templates, routes, assignees, next/parallel steps, condition rules, questionnaire scoring, ranking weights, dispositions, labels, notification timing, security and vendor integrations.

## Third-party integrations

- **THIRD-PARTY:** Assessment, calendar, e-signature and background-check vendors may participate in native workflow.
- HiredScore can itself connect with other ATS/CRM/provider services; each data flow needs separate documentation. [WD-08]

## Candidate-controlled factors

Submit readable evidence; review parsed/autofilled information where offered; answer questions accurately; complete requested tasks. Candidates cannot infer tenant BP definitions, condition rules, ranking weights, HiredScore purchase or disposition labels from a careers page.

## Unsupported or misleading claims

- “Workday uses one fixed funnel.”
- “Workday parsing fills Skills and automatically ranks applicants.”
- “Every Workday customer uses HiredScore.”
- “Move Forward always means Interview.”
- “Workday AI itself makes final hiring decisions.”
- “Standard search definitely indexes all raw resume text.” [WD-01, WD-02, WD-07, WD-08, WD-10]

## Evidence gaps

Tenant-specific workflow/rules/security; parser field/file/language benchmark; raw-resume search; rating criteria; Skills Match and HiredScore entitlement; independent AI validation/model cards; candidate notice/appeal behavior; vendor integrations.

## Sources

Primary: WD-01–WD-10. Full metadata: [../sources/source-register.md](../sources/source-register.md).
