# Cross-platform capability matrix

Values describe publicly documented availability, not a specific employer configuration.

| Capability | Greenhouse | Lever | Workday Recruiting | SAP SuccessFactors Recruiting |
|---|---|---|---|---|
| Resume parsing | Confirmed native | Confirmed native | Confirmed native | Confirmed native |
| Structured candidate profiles | Confirmed native | Confirmed native | Confirmed native | Confirmed native |
| Resume text search | Confirmed native | Confirmed native | Not confirmed | Configurable |
| Application questions | Configurable | Configurable | Configurable | Configurable |
| Eligibility questions | Configurable | Configurable | Configurable | Configurable |
| Knockout rules | Confirmed optional | Configurable | Configurable | Configurable |
| Candidate filtering | Confirmed native | Confirmed native | Configurable | Configurable |
| Candidate tags | Confirmed native | Confirmed native | Not confirmed | Not confirmed |
| Skills extraction | Confirmed optional | Confirmed optional | Confirmed optional | Confirmed optional |
| Skills inference | Confirmed optional | Not confirmed | Confirmed optional | Confirmed optional |
| Job-to-candidate matching | Confirmed optional | Confirmed optional | Confirmed optional | Confirmed optional |
| Candidate ranking | Confirmed optional | Third-party | Configurable | Not confirmed |
| Candidate grading | Confirmed optional | Not confirmed | Confirmed optional | Configurable |
| Recruiter recommendations | Confirmed optional | Confirmed optional | Confirmed optional | Confirmed optional |
| Automated rejection | Confirmed optional | Configurable | Configurable | Configurable |
| Pipeline management | Confirmed native | Confirmed native | Configurable | Configurable |
| Interview scorecards | Confirmed native | Confirmed native | Configurable | Configurable |
| Disposition reasons | Confirmed native | Confirmed native | Configurable | Configurable |
| AI-assisted screening | Confirmed optional | Confirmed optional | Confirmed optional | Confirmed optional |
| Third-party integrations | Confirmed native | Confirmed native | Confirmed native | Confirmed native |
| Auditability | Configurable | Configurable | Configurable | Configurable |
| Candidate-facing explanation | Confirmed optional | Not confirmed | Confirmed optional | Not confirmed |

## Evidence map

| Capability group | Greenhouse | Lever | Workday | SAP SuccessFactors |
|---|---|---|---|---|
| Parsing/profile | GH-02, GH-03, GH-11 | LV-01, LV-02, LV-07 | WD-01, WD-02 | SAP-02, SAP-07 |
| Search/filter/tags | GH-03, GH-04 | LV-03 | WD-07 | SAP-02, SAP-04 |
| Questions/rules | GH-01 | LV-05, LV-06 | WD-03, WD-04 | SAP-03 |
| Matching/rank/AI | GH-08, GH-09 | LV-10–LV-12 | WD-05, WD-06, WD-08, WD-09 | SAP-06, SAP-09 |
| Pipeline/disposition | GH-05, GH-06 | LV-07, LV-08 | WD-01 | SAP-05 |
| Interview feedback | GH-07, GH-10 | LV-09 | WD-01 | SAP-07 |

### Interpretation constraints

- `Confirmed optional` means licensed, packaged, enabled or otherwise non-universal.
- `Configurable` means native behavior depends materially on tenant setup.
- Lever candidate ranking is marked `Third-party` for VONQ screening; Talent Fit's documented output is binary, while ordinary search sorts by interaction. [LV-03, LV-10, LV-12]
- Workday resume text search remains `Not confirmed`; documented facets and HiredScore search must not be generalized to baseline raw-attachment search. [WD-07, WD-08]
- SAP prescreen grade is deterministic; Skill Compatibility is separate optional AI. [SAP-03, SAP-06]
