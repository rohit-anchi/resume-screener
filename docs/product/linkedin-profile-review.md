# LinkedIn profile review (optional module 2)

Compares a **user-supplied** LinkedIn profile PDF with the resume already uploaded.

## Authorisation

- A profile document must be supplied by the user; no LinkedIn account, session or private endpoint is accessed.
- `authorisation_confirmed` must be `true`. The API returns **403** and the service raises `PermissionError` otherwise.
- The UI requires an explicit checkbox before the action is enabled.
- The profile document is redacted on the same path as the resume before comparison.

## Dimensions compared

Headline · About/Summary · Experience · Skills · Certifications · Featured content · Employment dates · Current title · Product leadership scope · AI and platform experience.

## Row statuses

`aligned` · `missing_in_profile` · `missing_in_resume` · `potential_contradiction` · `not_assessable`

## Outputs

- Comparison table with the evidence found on each side
- Missing profile evidence (in the resume, absent from the profile)
- Missing resume evidence (in the profile, absent from the resume)
- Potential contradictions (for example a large difference in dated history)
- Target-market improvement recommendations

## Limitations (printed in the report)

- Only the supplied PDF is read; no private LinkedIn data is accessed.
- Profile exports vary in layout, so section and role detection is indicative rather than exact.
- Differences are prompts for the user's review, not findings of inaccuracy.
- The module never rewrites the profile or the resume; it proposes changes for the user to make.
