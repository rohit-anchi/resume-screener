from screening_core.security.redaction import assert_no_protected_markers, redact


def test_redaction_removes_identity_and_contact(resume_bytes):
    text = resume_bytes.decode()
    r = redact(text)
    assert r.candidate_name == "Priya Raman"
    assert "Priya" not in r.redacted_text and "example.com" not in r.redacted_text and "555" not in r.redacted_text
    assert "Harbour Street" not in r.redacted_text and "linkedin" not in r.redacted_text.lower()
    assert assert_no_protected_markers(r.redacted_text) == []


def test_redaction_removes_protected_lines_and_pronouns():
    text = "Alex Morgan\nGender: Female\nDate of Birth: 1990-01-01\nMarital status: married\nNationality: X\nSummary\nShe led a team and her roadmap shipped.\nGraduated 2012"
    r = redact(text)
    low = r.redacted_text.lower()
    for bad in ("female", "1990", "married", "nationality: x", " she ", " her "):
        assert bad not in low
    assert "graduated [year]" in low


def test_evidence_and_scores_never_see_identity(screening):
    joined = " ".join(e.source_location.text_span for e in screening.evidence)
    assert "Priya" not in joined and "@" not in joined and "Harbour" not in joined
    for c in screening.score.components:
        for k in c.contributions:
            assert "Priya" not in k.explanation
