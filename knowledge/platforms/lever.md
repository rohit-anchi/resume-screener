# Lever

## Executive summary

Lever uses a person-level candidate profile linked to one or more job-specific opportunities. Native capabilities include resume storage/parsing, application questions, full-text/Boolean search, tags, human Fast Resume Review, configurable pipeline/archive reasons, collaboration and interview feedback. Lever does not expose one universal fit percentage: ordinary search is sorted by last interaction; package-dependent Talent Fit returns a job-specific binary assessment with explanation; VONQ screening is a separate third-party-powered capability. [LV-01, LV-03, LV-04, LV-10, LV-12]

## What the platform is documented to do

- **DOCUMENTED:** Store multiple resumes and parse readable identity/contact/organization data into profiles. [LV-01, LV-02]
- **DOCUMENTED:** Search active and archived records across parseable resumes, notes and feedback. [LV-03]
- **CONFIGURATION-DEPENDENT:** Collect questions, tags, stages, archive reasons, automation and feedback forms. [LV-05–LV-09]
- **OPTIONAL/THIRD-PARTY:** Talent Fit and integrated AI screening/assessment functions vary by package/provider. [LV-10–LV-12]

## End-to-end application flow

1. Candidate submits posting-specific form and resume.
2. Lever links the application/opportunity to a person profile and parses readable fields.
3. Opportunity appears in New Applicant.
4. Recruiter can use Fast Resume Review to inspect resume, details and answers, then advance, archive or skip.
5. Configured workflows may tag, route, communicate or archive based on conditions.
6. Opportunity moves through employer-configured Applicant/Interview stages.
7. Interviewers submit structured feedback; recruiter records archive reason or Hired outcome. [LV-01, LV-04–LV-09]

## Resume parsing

- **DOCUMENTED:** Parser extracts readable information such as name, organization and contact details into profile fields. [LV-01]
- **DOCUMENTED:** Common uploads include DOC, DOCX, PDF and TXT, with a documented 10 MB limit. [LV-02]
- **DOCUMENTED:** Non-selectable scanned/image content cannot be parsed; users can manually correct profile fields. [LV-01]
- **UNVERIFIED:** No official accuracy percentage or universal table/column behavior was found.

## Structured application data

- **DOCUMENTED:** Candidate profile stores person-level data; opportunity stores job-specific consideration, resume, stage, origin and source. One person can have multiple opportunities. [LV-07]
- **CONFIGURATION-DEPENDENT:** Employers attach reusable custom question sets; internal/external questions and sensitive visibility can differ. [LV-05]
- **LIMITATION:** Tags, internal forms, application questions and offer/requisition custom fields are distinct constructs; do not call all of them “candidate custom fields.”

## Screening questions and eligibility criteria

- **CONFIGURATION-DEPENDENT:** Question answers can drive automation conditions/actions, including tags or archive, where workflows and entitlements are configured. [LV-05, LV-06]
- **DOCUMENTED:** Human Fast Resume Review remains a native initial-screen path. [LV-04]
- **LIMITATION:** No evidence supports automatic rejection simply because resume keywords fail to match.

## Search, filters, tags, and custom fields

- **DOCUMENTED:** Search spans active pipeline and archive, searches names and parseable profile content, and supports AND/OR/NOT plus field chips such as Resume. [LV-03]
- **DOCUMENTED:** Ordinary results are sorted by last interaction, not a universal fit score. [LV-03]
- **CONFIGURATION-DEPENDENT:** Posting/opportunity tags and source tags support retrieval/reporting; their meanings and use are employer-defined.

## Skills matching and AI capabilities

- **OPTIONAL:** Talent Fit compares only resume and job description at application, anonymizes the resume for comparison, and returns suitable/not-suitable plus strengths, considerations and clarification areas. Application answers are excluded. [LV-10, LV-11]
- **LIMITATION:** Talent Fit is job-specific and package/version dependent; it is not a universal 0–100 Lever score.
- **THIRD-PARTY:** VONQ AI Screening uses structured chat/voice and returns role-specific dossiers, scoring/ranking while leaving decisions to recruiters. [LV-12]
- Other integrations must be attributed to their provider, entitlement and trigger.

## Recruiter and hiring-manager actions

Review, advance, archive, skip, tag, search, add notes, mention collaborators, restrict sensitive content, schedule interviews and inspect feedback. Hiring-manager involvement and permissions are employer-configured. [LV-03, LV-04, LV-08, LV-09]

## Candidate pipeline

- **DOCUMENTED:** Unified pipeline includes Lead, Applicant and Interview sections; Archive is organized by reasons. [LV-07, LV-08]
- **CONFIGURATION-DEPENDENT:** Admins can add, rename, reorder or deactivate many stages; system stages such as New Applicant retain restrictions. [LV-07]
- **DOCUMENTED:** Changing one opportunity does not inherently change a candidate's other opportunities.

## Interview feedback and scorecards

- **DOCUMENTED:** Feedback forms support text, multiple-choice, yes/no, checkbox, code and scorecard questions; questions may be required. [LV-09]
- **DOCUMENTED:** Each feedback form includes a four-point human recommendation. [LV-09]
- **LIMITATION:** This interviewer recommendation is not a resume match score and occurs after/around interviews.

## Native capabilities

Candidate/opportunity model; resume parsing/storage; posting questions; Fast Resume Review; Boolean search; tags; pipeline/archive; collaboration; interview feedback. [LV-01–LV-09]

## Optional licensed capabilities

Automation packaging; Talent Fit/current AI platform capabilities; AI Companion and other contract-dependent functions. [LV-06, LV-10, LV-11]

## Employer-configurable behaviours

Questions, secret answers, workflow triggers/conditions/actions, tags, stages, archive reasons, feedback forms, visibility and integrations.

## Third-party integrations

- **THIRD-PARTY:** VONQ screening and provider-powered assessments/insights can send results into Lever. These are not universal native ATS behavior. [LV-12]

## Candidate-controlled factors

Use accepted selectable-text documents; check extracted contact/profile information where exposed; answer questions truthfully; present job-relevant evidence clearly. Candidates cannot control employer tags, automation, package, Talent Fit availability or reviewer practice.

## Unsupported or misleading claims

- “Lever gives every resume a fit percentage or fixed pass threshold.”
- “Search results are ordered by resume relevance.”
- “Missing keywords automatically archives an opportunity.”
- “Referrals are always moved to the top.”
- “One-column PDF or reverse chronology is technically mandatory.” [LV-X1, LV-X2; corrections LV-03, LV-06, LV-10]

## Evidence gaps

Parser accuracy and layout handling; semantic search internals; Talent Fit default enablement and jurisdictional disclosure; package availability; independent model validation; employer adoption; complete candidate-facing status/explanation behavior.

## Sources

Primary: LV-01–LV-12. Secondary/rejected: LV-X1, LV-X2. Full metadata: [../sources/source-register.md](../sources/source-register.md).
