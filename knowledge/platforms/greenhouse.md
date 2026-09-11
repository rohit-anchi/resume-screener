# Greenhouse

## Executive summary

Greenhouse is documented as a structured, configurable recruiting workflow—not one universal resume-scoring algorithm. Native functions store/parse resumes, collect structured answers, support exact/Boolean retrieval, manage stages and collect interviewer scorecards. Plus/Pro application rules can automatically tag, advance or reject from configured question answers. Real Talent's optional Talent Matching provides explained, calibrated AI matching but does not itself advance or reject. [GH-01, GH-04, GH-07, GH-08]

## What the platform is documented to do

- **DOCUMENTED:** Maintain candidate profiles and job-specific applications, documents, activity and status. [GH-03, GH-05]
- **DOCUMENTED:** Search resume/note text and filter by tags, custom fields, status and rejection reason. [GH-03, GH-04]
- **CONFIGURATION-DEPENDENT:** Define job questions, interview stages, scorecard attributes, rejection reasons and access. [GH-01, GH-06, GH-07]
- **OPTIONAL:** Apply question-driven Auto-Advance/Auto-Reject and AI Talent Matching under applicable tier/add-on controls. [GH-01, GH-08]

## End-to-end application flow

1. Candidate submits configured basic fields, resume and job-post questions.
2. Greenhouse stores an application under a candidate profile and attempts resume-field extraction.
3. Application enters Application Review, unless configured application rules tag, advance or reject it.
4. Recruiter can inspect the original document, extracted/profile data and answers; advance or reject.
5. Candidate proceeds through the job's configured interview plan.
6. Interviewers submit assigned scorecards; the team reviews feedback.
7. Authorized users advance, reject with a reason, or ultimately record hire. [GH-01, GH-02, GH-05–GH-07]

## Resume parsing

- **DOCUMENTED:** Parsing scans an imported resume and auto-fills detected fields; this is extraction, not suitability scoring. [GH-02]
- **DOCUMENTED:** On parse failure, the resume remains attached and fields require manual entry; failure is not documented as rejection. [GH-02]
- **DOCUMENTED:** Candidate uploads include DOC, DOCX, PDF, RTF and TXT. [GH-11]
- **UNVERIFIED:** No public, independent accuracy rate, complete field map or layout benchmark was found.

## Structured application data

- **CONFIGURATION-DEPENDENT:** Custom job questions and linked candidate/application fields can create searchable/reportable structured data. [GH-01, GH-03]
- **DOCUMENTED:** Recruiters can see application answers and documents during Application Review. [GH-05]
- **LIMITATION:** Results on the Candidates page represent applications; one person may appear for multiple jobs. [GH-03]

## Screening questions and eligibility criteria

- **CONFIGURATION-DEPENDENT:** Rules act only when employer-defined answers satisfy configured conditions. [GH-01]
- **OPTIONAL:** Auto-Tag is broadly tiered; Auto-Advance and Auto-Reject are documented for Plus/Pro. Auto-Reject can assign a rejection reason and communication. [GH-01]
- **LIMITATION:** These deterministic rules do not establish resume keyword rejection or AI decision-making.

## Search, filters, tags, and custom fields

- **DOCUMENTED:** Talent Filtering can search exact terms in full resume/internal-note text and combine preferred (OR) and required (AND) terms. [GH-04]
- **DOCUMENTED:** Filters include location, referrals, education, status, scorecard status and configurable criteria; candidate pages include tags, custom fields and rejection reasons. [GH-03, GH-04]
- **LIMITATION:** Search visibility can affect recruiter review but does not itself reject, grade or prove candidate absence.

## Skills matching and AI capabilities

- **OPTIONAL:** Talent Matching requires the Real Talent add-on, enablement, permissions and resume parsing for full use. It compares resume/application evidence with recruiter-selected, weighted criteria and explains matched experience, industries and skills. [GH-08, GH-09]
- **DOCUMENTED:** Greenhouse states Talent Matching is assistive and cannot automatically advance or reject; humans retain decision ownership. [GH-08, GH-12]
- **OPTIONAL:** AI scorecard summaries synthesize submitted written feedback and link to source comments. They are post-interview synthesis, not initial resume ranking. [GH-10]

## Recruiter and hiring-manager actions

- Review/download documents and application answers; leave feedback; search/filter; tag; advance; transfer; reject; select reason and communication. [GH-03–GH-05]
- Hiring Manager Review may be configured as a stage; permissions determine access. [GH-06]
- Human users calibrate optional Talent Matching and remain accountable for decisions. [GH-08]

## Candidate pipeline

- **DOCUMENTED:** Application Review is automatically first in the interview plan. [GH-05]
- **CONFIGURATION-DEPENDENT:** Subsequent stages/interviews can be created, copied, renamed, reordered or removed. [GH-06]
- **CONFIGURATION-DEPENDENT:** Different jobs therefore have different workflows; stage-transition rules can trigger on movement.

## Interview feedback and scorecards

- **DOCUMENTED:** Scorecards use predetermined skills, traits, qualifications and other attributes. Interviewers submit ratings, notes and Definitely Not/No/Yes/Strong Yes recommendations. [GH-07]
- **DOCUMENTED:** Scorecards are assigned with scheduled interviews or manually and reviewed by permitted users. [GH-07]
- **LIMITATION:** A scorecard is a human interview-feedback instrument. No reviewed evidence says it automatically grades an incoming resume.

## Native capabilities

Profiles/applications; resume attachment and parsing; Application Review; text search; candidate filters/tags/custom fields; configurable interview plans; scorecards; rejection reasons; integration APIs. [GH-02–GH-07]

## Optional licensed capabilities

Plus/Pro Auto-Advance and Auto-Reject; Real Talent/Talent Matching; enabled AI scorecard summaries; other AI features subject to tier/toggle. [GH-01, GH-08–GH-10]

## Employer-configurable behaviours

Questions, required fields, rule conditions, tags, stages, scorecard criteria, reviewer permissions, rejection reasons, communications, AI calibration and opt-out/disclosure settings. [GH-01, GH-03, GH-06–GH-09]

## Third-party integrations

- **THIRD-PARTY:** Assessments, background checks and other screening services may exchange data through marketplace/API integrations. Their scores and actions belong to the named provider, not native Greenhouse.

## Candidate-controlled factors

- Submit a supported, selectable-text document; verify visible form fields; answer eligibility questions truthfully; provide clear evidence aligned to public requirements.
- Candidates cannot know private questions/rules, scorecards, calibration or integration settings.
- Simple formatting is a safe parseability practice, not a guaranteed pass technique.

## Unsupported or misleading claims

- “Every resume receives a Greenhouse ATS score.”
- “Scorecards automatically rank resumes.”
- “Missing an exact keyword causes rejection.”
- “Public requirements exactly reveal the private scorecard.”
- “Every employer enables Talent Matching.” [GH-X1; corrections GH-01, GH-07, GH-08]

## Evidence gaps

Parser accuracy/layout behavior; customer adoption/configuration; Real Talent commercial specifics by contract; independent AI validation; exact integration behavior; candidate-facing explanations by tenant.

## Sources

Primary: GH-01–GH-12. Rejected secondary: GH-X1. Full metadata: [../sources/source-register.md](../sources/source-register.md).
