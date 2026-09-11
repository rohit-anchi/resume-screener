# Rejected or unverified claims

| Claim | Status | Evidence-grounded correction |
|---|---|---|
| Every ATS gives every resume a universal percentage. | Rejected | Platforms expose different mechanisms; no universal cross-employer score is documented. [GH-08, LV-03, LV-10, WD-06, SAP-03] |
| Resume parsing ranks candidates. | Rejected | Parsing extracts/populates data. Matching, ranking and rules are separate capabilities. [GH-02, LV-01, WD-02, SAP-02] |
| Missing keywords automatically rejects an applicant. | Rejected | Search/filter can affect retrieval; automatic rejection requires configured rules or another documented mechanism. [GH-01, GH-04, LV-03, LV-06, WD-04, SAP-03] |
| Greenhouse scorecards screen resumes automatically. | Rejected | Scorecards capture human interview feedback; optional Talent Matching is separate. [GH-07, GH-08] |
| Lever gives every applicant the same fit score. | Rejected | Ordinary search has no match percentage; Talent Fit is job-specific and binary; VONQ is separate. [LV-03, LV-10, LV-12] |
| Workday has one mandatory sequence for all candidates. | Rejected | Review and Ready for Hire bound a configurable dynamic business process; intermediate subprocesses vary. [WD-01] |
| HiredScore is enabled for every Workday customer. | Rejected | It is an optional purchased product. [WD-08] |
| SAP classic resume parsing semantically matches applicants to jobs. | Rejected | Classic parsing populates profile fields; AI skills matching is licensed and configured separately. [SAP-02, SAP-06] |
| SAP prescreen score is an AI score. | Rejected | It is deterministic employer-authored weights, answers and thresholds. [SAP-03] |
| AI matching independently makes final hiring decisions. | Not confirmed | Reviewed vendor evidence describes decision support; configured non-AI rules can still automate workflow actions. [GH-08, WD-10, SAP-06] |
| All candidates are manually reviewed. | Unverified | Automation rules and volume practices vary; capability documentation cannot prove actual review. |
| A parser supports any layout with a known accuracy percentage. | Unverified | No independent, versioned parser benchmark was found. |
| Single-column PDF is mandatory. | Rejected as platform fact | Selectable, readable text is a safe practice; mandatory format/layout claims exceed evidence. [LV-01, WD-02] |
| Keyword stuffing improves rank. | Unsupported | Search may match terms, but no source validates density-based rank improvement; stuffing harms evidence quality. |
| Public job text exactly reveals private scorecards/rules. | Unsupported | Employer configuration is private and may diverge from the posting. |
| Candidate-facing status equals internal disposition. | Unsupported | Labels and notifications can be configured differently. [WD-01, SAP-05] |
| Tags themselves prove qualification. | Rejected | Tags are employer metadata used for organization, filtering and reporting. [GH-03, LV-03] |
