import json

import jsonschema
import pytest
from pydantic import ValidationError

from screening_core.schemas import export, models


def test_export_and_roundtrip(tmp_path, screening):
    files = export.export(tmp_path)
    assert len(files) == len(export.EXPORTED) + len(export.ALIASES)
    for alias in export.ALIASES.values():
        assert (tmp_path / alias).exists(), alias
    schema = json.loads((tmp_path / f"ScreeningResult.{models.SCHEMA_VERSION}.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(json.loads(screening.model_dump_json()), schema)


def test_all_models_carry_schema_version(screening):
    dumped = screening.model_dump()
    assert dumped["schema_version"] == models.SCHEMA_VERSION
    assert all(m["schema_version"] == models.SCHEMA_VERSION for m in dumped["matches"])


def test_rubric_weights_must_total_100():
    with pytest.raises(ValidationError):
        models.RubricConfig(rubric_id="x", rubric_version="1", weights={"a": 50, "b": 40})


def test_eligibility_result_cannot_claim_resume_inference():
    with pytest.raises(ValidationError):
        models.EligibilityResult(status=models.EligibilityStatus.not_evaluated, findings=[], uses_resume_inference=True)


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        models.Threshold(value=1, unit="years", bogus=1)
