"""Export pydantic models to versioned JSON Schema files under packages/schemas."""
from __future__ import annotations

import json
from pathlib import Path

from . import jobdoc, models

EXPORTED = [
    models.IngestedDocument, models.ParseabilityReport, models.Requirement, models.Job,
    models.Evidence, models.Candidate, models.Match, models.EligibilityRule, models.EligibilityResult,
    models.ScoreResult, models.RubricConfig, models.PlatformProfile, models.ScreeningRequest,
    models.ScreeningResult, models.AuditEvent, models.ReviewAction,
    jobdoc.ContentBlock, jobdoc.JobSection, jobdoc.AtsDetection, jobdoc.JobDocument, jobdoc.Assessment,
    jobdoc.Recommendation, jobdoc.InterviewQuestion, jobdoc.CriticalGap, jobdoc.MultiJobReview, jobdoc.ProfileReview,
]
# stable filenames required as Phase 2 deliverables
ALIASES = {"JobDocument": "job-document.schema.json", "Assessment": "assessment.schema.json"}


def export(target: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for m in EXPORTED:
        schema = m.model_json_schema()
        schema["$id"] = f"urn:screener:{m.__name__}:{models.SCHEMA_VERSION}"
        path = target / f"{m.__name__}.{models.SCHEMA_VERSION}.schema.json"
        path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        written.append(path)
        alias = ALIASES.get(m.__name__)
        if alias:
            alias_path = target / alias
            alias_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
            written.append(alias_path)
    return written


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3] / "packages" / "schemas"
    for p in export(root):
        print(p)
