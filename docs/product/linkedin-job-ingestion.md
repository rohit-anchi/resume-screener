# LinkedIn job-document ingestion

A LinkedIn job-details PDF is a saved web page. Employer-authored content is interleaved with LinkedIn's own interface, and in the validated fixtures the employer text is **split across chrome** (the Xero export resumes a sentence on page 2 after two promotional blocks). Line-based parsing is therefore unsafe; the unit of analysis is the layout block.

## Stages

1. **Block extraction** (`linkedin/blocks.py`) — every text block with page, y, x and maximum font size, in reading order, plus all link annotations.
2. **Classification** (`linkedin/classify.py`) — each block is assigned exactly one category with a reason and the rule that fired.
3. **Allow-list** — only requirement-bearing employer categories reach requirement extraction.
4. **Assembly** (`linkedin/builder.py`) — `employer_text`, sections with character offsets, retained excluded blocks, metadata, warnings.

## Categories

**Employer content (retained).** `job_header`, `employer_about`, `employer_role_overview`, `employer_team`, `employer_responsibilities`, `employer_requirements`, `employer_preferred`, `employer_work_arrangement`, `employer_eligibility`, `employer_compensation`, `employer_process`, `employer_application_instructions`, `employer_eeo`, `employer_ai_disclosure`.

**Requirement-bearing subset (scored).** `employer_role_overview`, `employer_team`, `employer_responsibilities`, `employer_requirements`, `employer_preferred`, `employer_work_arrangement`, `employer_eligibility`.

Compensation, hiring process, application instructions, EEO statements and AI-use disclosures are employer-authored and retained, but never converted into candidate requirements.

**Excluded (retained for audit, never scored).** `linkedin_nav`, `linkedin_job_match`, `linkedin_applicant_stats`, `linkedin_candidate_seniority_stats`, `linkedin_candidate_education_stats`, `linkedin_premium_insights`, `linkedin_company_insights`, `linkedin_similar_jobs`, `linkedin_advertisement`, `linkedin_resume_promotion`, `linkedin_people_suggestions`, `page_header_footer`, `garbled_fragment`, `unknown`.

`linkedin_people_suggestions` carries third-party personal data (names, degrees of connection, employers). It is excluded from scored content and from every report; a test asserts the fixture names never appear.

## Section weighting

Stated qualification sections carry full weight; narrative prose carries less and cannot create a critical gap.

| Section | Importance default | Weight |
|---|---|---|
| `employer_requirements` | required | 1.0 |
| `employer_preferred` | preferred | 1.0 |
| `employer_eligibility` / `employer_work_arrangement` (with an obligation cue) | eligibility | 1.0 |
| `employer_responsibilities` | required, review-flagged | 0.6 |
| `employer_role_overview` / `employer_team` | contextual | 0.4 |

Explicit preference wording ("is a strong plus", "nice to have", "bonus") outranks section context. Section context outranks weak cues such as "ideally" or "familiarity with".

## Soft line-wrap handling

PDF text carries hard newlines inside paragraphs. `split_items` joins a line to the previous item when it starts lowercase, starts with closing punctuation, or the previous line ends with a hyphen or conjunction. Offsets always refer to the original text, so every requirement keeps a verifiable character span.

Without this, `2+ years experience as a senior product leader managing PMs while reporting into the exec, or as a / manager-of-managers in a product function` was truncated mid-sentence and lost its second clause.

## Validated fixture behaviour

| | Amber Electric | Xero |
|---|---|---|
| Listing source | linkedin | linkedin |
| Application platform | **lever** (`jobs.lever.co/amberelectric/…`) | **ashby** (`jobs.ashbyhq.com/xero/…`) |
| Profile applied | `lever_informed` | `platform_neutral` (Ashby not yet researched) |
| Blocks / scored / excluded | 114 / 16 / 69 | 102 / 12 / 83 |
| Unattributed blocks | 0 | 0 |
| Employer / role / location / type | Amber Electric · Director of Product · Melbourne, Victoria, Australia · Full-time · Hybrid | Xero · Lead Product Manager - AI Enablement · Melbourne, Victoria, Australia · Full-time · Hybrid |
| Compensation (retained, unscored) | `$220,000 - $260,000 a year` | not stated |
| Excluded as expected | applicant statistics, job-match statements, seniority/education demographics, premium insights, company insights, similar jobs, resume promotions, people suggestions, print furniture | same |
| Requirements extracted | senior product leadership (2+ yrs, PM management / manager-of-managers), 5+ yrs commercial product experience, product strategy communicated organisation-wide, raising PM quality, multi-market/brand platform (preferred), product practices, Australia-based eligibility with visa sponsorship condition | platform product management (developer tools / infrastructure / data / AI), systems thinking, translating technical possibility into investment decisions, outcome-focused discovery and measurement, ambiguity tolerance, curiosity/pragmatism/resilience, AI-native shared capabilities, quarterly roadmaps and governance, pilot-to-adoption, stakeholder alignment |

## Extraction ambiguities found and how they are handled

These were material and are reported rather than hidden:

1. **Clipped render fragments.** Both exports contain visually truncated text (`"hi i h O i"`, `"ti I li ith l t G B ld…"`). In both cases the intact text appears elsewhere, so the fragment is classified `garbled_fragment` and discarded, and a warning advises verifying that no unique requirement existed only in a clipped block.
2. **Header metadata sits inside excluded blocks.** The listing line also carries applicant statistics, so metadata is read from raw page-1 blocks before exclusion. LinkedIn's sticky header (`Employer • Location (Workplace)`) is used authoritatively.
3. **Print furniture at the top of the page.** The browser header (timestamp, `Title | Employer | LinkedIn`, URL, page number) is split across blocks and sorts above the content; it is detected by timestamp, URL, page-number and browser-title patterns.
4. **Company names repeat legitimately.** Repeated-text chrome detection is restricted to strings of 25+ characters so that "Xero" in the job header is not treated as furniture.
5. **OR-alternatives.** "managing PMs while reporting into the exec, **or** as a manager-of-managers" and "consumer technology, marketplace, **or** platform products" are recorded with `alternative_concepts`; evidence for any alternative is a direct match.
6. **Distinct thresholds on related concepts.** Amber states 2+ years and 5+ years in adjacent bullets; de-duplication keys include the threshold so neither is dropped.
7. **Narrative prose reads like a requirement.** Role-overview sentences (for example "We're looking for a Director of Product to join Amber's executive team") are extracted at reduced weight, flagged for review, and cannot produce a critical gap.
8. **Benefit statements in a work-arrangement section.** Xero's flexible-working paragraph is classified contextual unless it contains a candidate obligation ("must be located", "willing to travel").
9. **Ashby is unresearched.** Detection is confident (0.95 from the application link) but no approved Phase 1 profile exists, so the platform-neutral profile is applied and a warning is emitted. No other ATS profile is substituted.
10. **Employer AI-use disclosure.** Amber discloses that AI tools may assist application review. This is employer-authored, retained as `employer_ai_disclosure`, surfaced in the scenarios section, and never scored.

## Failure modes and guards

- Non-PDF or malformed job documents are rejected by the shared ingestion safety checks.
- If no requirements section is identified, a warning states that coverage may be understated.
- Unattributed blocks are excluded from scoring and reported as needing human classification.
- Instruction-like text inside a job or resume document is flagged and treated as data only.
