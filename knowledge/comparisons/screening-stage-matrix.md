# Screening-stage matrix

| Stage | Greenhouse | Lever | Workday Recruiting | SAP SuccessFactors Recruiting |
|---|---|---|---|---|
| Intake | Profile/application; parse; configurable questions [GH-02, GH-11] | Profile/opportunity; parse; posting questions [LV-01, LV-05] | Candidate/job application; template fields; parse [WD-01, WD-02] | Candidate Profile + application; parse [SAP-02, SAP-07] |
| Initial eligibility | Optional question rules [GH-01] | Configured workflows from answers/data [LV-06] | Questionnaires + condition rules [WD-03, WD-04] | Weighted prescreen, threshold, disqualifier [SAP-03] |
| Human application review | Mandatory first stage design; recruiter advance/reject [GH-05] | Fast Resume Review: advance/archive/skip [LV-04] | Review: resume/cover letter; Move Forward/Decline [WD-01] | Applicant Workbench review/status movement [SAP-04] |
| Search/prioritization | Exact/Boolean filtering; optional Talent Matching [GH-03, GH-04, GH-08] | Boolean search; optional Talent Fit; VONQ separate [LV-03, LV-10, LV-12] | Facets; configured ranking; optional Skills Match/HiredScore [WD-05–WD-08] | Workbench filters; prescreen sort; optional Skill Compatibility [SAP-03, SAP-04, SAP-06] |
| Hiring-manager review | Configurable stage/permissions [GH-06] | Configurable users, stages and permissions [LV-07] | Assigned actor under BP configuration [WD-01] | Configured status and permissions [SAP-05, SAP-07] |
| Assessment | Typically integration/configured stage | Integration and configured stage | Native tracking/subprocess; provider may be integrated [WD-01] | Status-triggered third-party integration [SAP-08] |
| Interview | Configured interview plan [GH-06] | Configured Interview stages [LV-07] | Interview subprocess, repeatable/configurable [WD-01] | Configured statuses/workflow [SAP-05, SAP-07] |
| Feedback | Human scorecards; optional AI summary [GH-07, GH-10] | Human feedback forms/four-point recommendation [LV-09] | Ratings/comments and decision actor [WD-01] | Evaluations, ratings and notes [SAP-07] |
| Reference check | Configurable stage/integration | Configurable stage/integration | Delivered subprocess [WD-01] | Configured status/integration |
| Offer/background | Configurable stages/integrations | Configurable stages/integrations | Delivered Offer, Agreement and Background subprocesses [WD-01] | Configured statuses and vendor integrations [SAP-08] |
| Completion/disposition | Hire or reject with reason [GH-05] | Hired/archive reason [LV-08] | Ready for Hire or decline/disposition [WD-01] | Hired/withdrawn/disqualified configured status [SAP-05] |

No row defines a mandatory universal employer sequence. Only Workday documents Review as initiation and Ready for Hire as completion; its intermediate steps still vary. [WD-01]
