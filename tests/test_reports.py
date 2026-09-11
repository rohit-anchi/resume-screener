import re

from screening_core.reports.render import FORBIDDEN_IN_CANDIDATE, candidate_report, recruiter_report
from screening_core.schemas.models import Mode
from tests.conftest import make_screening


def test_candidate_report_has_no_hiring_labels(job, candidate):
    s = make_screening(job, candidate, mode=Mode.candidate)
    full = candidate_report(s).lower()
    text = full.split("## platform-informed scenarios")[0]  # findings/scores/tips only; scenario text describes platforms
    for w in FORBIDDEN_IN_CANDIDATE:
        assert not re.search(rf"\b{w}\b", text), w
    text = full
    assert "no evidence located" in text or "strong evidence" in text
    assert "## limitations" in text and "does not reproduce" in text


def test_recruiter_report_offers_human_actions_only(screening):
    text = recruiter_report(screening)
    assert "Recommended human action" in text and "advisory only" in text
    assert "decline with a human-selected reason" in text
    assert "Verification question" in text and "## Limitations" in text


def test_missing_evidence_distinct_from_failure(job):
    from screening_core.pipeline import build_candidate_from_bytes
    c = build_candidate_from_bytes("C", "cv.txt", b"Experience\nAnalyst | X | Jan 2020 - Present\n- Wrote SQL reports.\n")
    s = make_screening(job, c, mode=Mode.candidate)
    text = candidate_report(s)
    assert "No evidence located" in text and "does not establish that the candidate lacks" in text
    assert "Candidate input required" in text


def test_json_export_roundtrip(screening):
    from screening_core.schemas.models import ScreeningResult
    assert ScreeningResult.model_validate_json(screening.model_dump_json()).screening_id == screening.screening_id
