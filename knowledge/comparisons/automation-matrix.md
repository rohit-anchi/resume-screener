# Automation-level matrix

Maximum documented level for the named mechanism; availability remains subject to the delivery qualifier. No Level 5 capability is assigned.

| Mechanism | Greenhouse | Lever | Workday Recruiting | SAP SuccessFactors Recruiting |
|---|---|---|---|---|
| Store resume/application | L0 native [GH-02] | L0 native [LV-01] | L0 native [WD-01] | L0 native [SAP-02] |
| Resume parsing | L1 native [GH-02] | L1 native [LV-01] | L1 native [WD-02] | L1 native [SAP-02] |
| Human application review | L1 native [GH-05] | L1 native [LV-04] | L1 native [WD-01] | L1 native [SAP-04] |
| Search/filter | L2 native [GH-03, GH-04] | L2 native [LV-03] | L2 configurable [WD-07] | L2 configurable [SAP-04] |
| Deterministic eligibility support | L2 configurable [GH-01] | L2 configurable [LV-06] | L2 configurable [WD-03] | L2 configurable [SAP-03] |
| Matching/prioritisation | L3 optional [GH-08] | L3 optional [LV-10, LV-12] | L3 configurable/optional [WD-05, WD-06, WD-08] | L3 optional [SAP-06] |
| Automatic workflow action | L4 optional/configured [GH-01] | L4 configured [LV-06] | L4 configured [WD-04] | L4 configured [SAP-03] |
| Final hiring decision | Not confirmed | Not confirmed | Not confirmed | Not confirmed |

## Level boundaries

- L1 parsing produces reviewable data, not suitability.
- L2 retrieval/rules aid review without recommending broad candidate quality.
- L3 outputs must disclose scope: match, prescreen grade, skills score, configured rank or third-party dossier.
- L4 applies only to explicit customer rules/workflows; it must never be described as universal platform behavior.
- L5 requires authoritative proof that the platform independently makes the relevant final hiring decision. None was found.
