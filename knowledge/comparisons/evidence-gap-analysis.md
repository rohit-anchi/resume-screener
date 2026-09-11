# Evidence-gap analysis

## Cross-platform gaps

| Gap | Impact | Required evidence before product assertion |
|---|---|---|
| Employer configuration is private | Cannot predict actual routing, thresholds, reviewers or integrations | Tenant screenshots/config exports, administrator attestation or scenario labeling |
| Parser performance | Cannot quantify parse accuracy or declare a layout universally safe | Versioned vendor field/format matrix plus independent benchmark |
| AI validation | Cannot validate fairness, calibration or error rates | Model card, feature list, validation cohorts, subgroup metrics and independent audit |
| Candidate notice/recourse | Cannot promise explanation, correction or appeal | Current jurisdiction/tenant candidate UX and policy |
| Third-party behavior | Cannot attribute provider scores/actions to ATS | Provider docs, contract scope, trigger/data-flow configuration and audit controls |
| Release/licensing drift | Optional features may change | Current order form, release notes and admin entitlement check |
| Human adoption | Capability does not prove actual practice | Workflow analytics or documented operating procedure |

## Platform-specific gaps

### Greenhouse

- Parsing field coverage and accuracy; exact behavior across layouts/languages.
- Real Talent pricing/contract scope and independent validation.
- Customer calibration, opt-out and disclosure settings.
- Mapping—if any—between public requirements, Talent Matching calibration and interview scorecard.

### Lever

- Talent Fit enablement/default state across current and legacy packages.
- Parser field/layout benchmark and semantic-search internals.
- Candidate AI notice/consent by jurisdiction.
- VONQ and other provider model/performance details.

### Workday Recruiting

- Baseline raw-resume full-text search is not confirmed.
- Tenant BP routes, condition rules, ranking templates and dispositions.
- Candidate Skills Match and HiredScore purchase/configuration.
- HiredScore model features, thresholds and independent adverse-impact evidence.

### SAP SuccessFactors Recruiting

- Current commercial entitlement name and regional availability for AI screening.
- AI compatibility ordering/weights, model card and data-processing specifics.
- Release-specific parser formats/languages.
- Latest versus legacy Applicant Workbench configuration and candidate-facing status labels.

## Contradictions resolved

- **“Greenhouse scorecards screen resumes” vs official scorecard docs:** official evidence limits scorecards to human feedback; optional Talent Matching is separate. [GH-07, GH-08]
- **“Lever has no matching” vs current Talent Fit:** current package may provide job-specific binary Talent Fit, but ordinary search still has no universal fit percentage. [LV-03, LV-10, LV-11]
- **“Workday stages are linear” vs dynamic BP:** each subprocess is linear; the parent process can route dynamically. [WD-01]
- **“SAP parsing ranks” vs Skill Compatibility:** classic parsing populates fields; licensed AI compatibility is separate. [SAP-02, SAP-06]

## Readiness consequence

The evidence is sufficient to design an ontology, scenario simulator and explainable readiness analysis. It is insufficient to claim algorithm replication, employer outcome prediction, universal weights/cutoffs or autonomous adverse decisions.
