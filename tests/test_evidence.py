from screening_core.evidence.extractor import build_candidate
from screening_core.ingestion.service import ingest
from screening_core.schemas.models import EvidenceType
from screening_core.text import dates
from tests.conftest import TODAY


def test_no_fabricated_spans(candidate):
    src = candidate.document.redacted_text
    for e in candidate.evidence:
        assert src[e.source_location.char_start:e.source_location.char_end] == e.source_location.text_span
        assert e.source_location.text_span in src


def test_roles_dates_and_quantification(candidate):
    roles = [e for e in candidate.evidence if e.evidence_type == EvidenceType.employment_role]
    assert len(roles) == 3
    assert roles[0].employment_period.start == "2022-07" and roles[0].employment_period.end == "present"
    assert any(e.quantified for e in candidate.evidence if e.evidence_type == EvidenceType.employment_achievement)
    assert any(e.evidence_type == EvidenceType.certification for e in candidate.evidence)
    assert any(e.evidence_type == EvidenceType.education for e in candidate.evidence)


def test_duration_math_merges_overlaps():
    a = (dates.YM(2019, 3), dates.YM(2022, 6))
    b = (dates.YM(2022, 1), dates.YM(2023, 1))
    assert dates.merged_months([a, b]) == 47  # 2019-03..2023-01 inclusive
    assert dates.overlaps([a, b]) == 1


def test_contradiction_detection_overlapping_roles():
    text = ("Summary\nProduct manager.\n\nExperience\nProduct Manager | A Corp | Jan 2020 - Present\n- Owned roadmap.\n"
            "Senior Product Manager | B Corp | Jan 2021 - Present\n- Led stakeholder reviews.\n")
    doc = ingest("resume", "cv.txt", text.encode())
    c = build_candidate("C", doc, today=TODAY)
    assert any("overlapping" in x for x in c.contradictions) and any("current" in x for x in c.contradictions)
    assert c.parseability.chronology_conflicts == 2


def test_explicit_absence_is_captured_separately():
    text = "Summary\nAnalyst with no prior experience with cloud platforms.\n\nExperience\nAnalyst | X | Jan 2020 - Present\n- Wrote SQL reports.\n"
    c = build_candidate("C", ingest("resume", "cv.txt", text.encode()), today=TODAY)
    ab = [e for e in c.evidence if e.evidence_type == EvidenceType.explicit_statement_of_absence]
    assert ab and "cloud_platforms" in ab[0].normalised_concepts
