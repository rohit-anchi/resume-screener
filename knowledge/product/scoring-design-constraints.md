# Scoring design constraints

No final formula, weights or cutoffs are approved. Dimensions must remain separate, explained and role-specific. A composite score may not be designed until validity, fairness and user-research evidence exists.

## Dimension assessment

| Dimension | Definition / input | Defensible measurement | Valid use | Invalid use | Bias risk | Required explanation/evidence | Human review |
|---|---|---|---|---|---|---|---|
| Mandatory eligibility | Explicit lawful must-have; JD/form answers | Met / not met / unknown per criterion | Route explicit constraints | Infer from identity/location proxies | Citizenship, disability, geography proxies | Criterion, source, answer/evidence, legal basis | Required before adverse action |
| Required qualification coverage | Coverage of stated required criteria | Criterion-level supported/partial/not found | Identify evidence gaps | Treat not found as absence | Credential inflation; nontraditional paths | JD span + resume span per item | Required for negatives |
| Preferred qualification coverage | Coverage of stated preferences | Separate non-gating coverage | Development/readiness context | Convert preferences into knockouts | Prestige and opportunity bias | Mark preferred; show item evidence | Review aggregate effect |
| Relevant experience | Role-related tasks/outcomes | Evidence-linked duration/scope bands | Compare job-related exposure | Count total tenure as quality | Career breaks, sector access | Roles, dates, task/outcome spans | Resolve ambiguous equivalence |
| Recency of applicable experience | Time since evidenced use | Transparent date range; unknown allowed | Identify currency where justified | Penalize age or older workers | Age proxy | Why recency is job-relevant; dates used | Approve recency requirement |
| Demonstrated skill evidence | Observable use of required skill | Mention < context < applied outcome evidence | Distinguish claim from demonstration | Keyword count | Writing style, access to projects | Exact evidence and strength level | Review inferred equivalence |
| Scope and seniority alignment | Scale, autonomy, complexity and accountability | Role-specific behavioral anchors | Assess level evidence | Infer from title/age/pay | Title and organization bias | Observable scope facts, not title alone | Required |
| Domain alignment | Relevant domain constraints/knowledge | Explicit experience/evidence categories | Identify ramp-up needs | Prefer prestige or identical employers | Industry access bias | Explain transferable and direct evidence | Review transferability |
| Achievement evidence | Outcomes attributable to candidate | Presence, specificity, attribution | Assess evidence quality | Reward embellished prose | Communication and role-type bias | Quote outcome and attribution limits | Review ambiguous attribution |
| Quantified impact | Verifiable scale/metric context | Presence and contextual quality, not raw magnitude | Strengthen outcome evidence | Penalize roles lacking metrics | Function/sector inequity | Metric, baseline, period and role | Verify plausibility |
| Leadership/collaboration | Observable role-related behaviors | Anchored examples: influence, coordination, decisions | Assess required competency | Personality/culture-fit inference | Style, language, management-title bias | Behavior, context and outcome evidence | Required |
| Career chronology clarity | Understandable role/date sequence | Complete / ambiguous / conflict / unknown | Request clarification | Penalize gaps or nonlinearity | Caregiving, disability, unemployment | State ambiguity only; never infer reason | Required before negative use |
| Resume parseability | Machine-readable extraction quality | Field/text extraction success and warnings | Improve data quality/readability | Treat formatting as qualification | Accessibility/design/language | Identify unreadable spans and workaround | No adverse action from parseability |
| Application completeness | Completion of required fields/artifacts | Complete / missing / inaccessible | Request missing information | Score optional disclosure | Disability/privacy risk | Identify required field and status | Required before decline |
| Evidence confidence | Reliability of each extracted finding | High/medium/low/unknown from source quality and ambiguity | Drive abstention/review | Convert confidence into candidate quality | Sparse-resume bias | Basis: direct quote, derivation, conflict | Low confidence requires review |

## Global constraints

- Do not score protected data, proxies, formatting aesthetics, school/employer prestige, unexplained gaps or optional demographic disclosures.
- Do not reward keyword frequency; normalize synonyms only with visible mappings and human-correctable evidence.
- Mandatory criteria require explicit source, job-relatedness and lawful use.
- Missing evidence cannot produce the same state as confirmed non-qualification.
- Parseability and completeness are service-quality signals, not candidate merit.
- Every output must retain criterion, source spans, derivation, confidence, limitation and human-review requirement.
