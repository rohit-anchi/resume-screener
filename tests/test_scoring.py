import json

import pytest

from screening_core.schemas.models import Importance
from screening_core.scoring.rubrics import load_rubric, load_thresholds
from tests.conftest import make_screening


def test_weights_and_components(screening):
    r = load_rubric()
    assert sum(r.weights.values()) == 100 and r.rubric_hash
    comps = {c.component: c for c in screening.score.components}
    assert set(comps) == set(r.weights)
    assert screening.score.alignment_index == round(sum(c.weighted_points for c in screening.score.components), 1)
    assert screening.score.band_caveat == load_thresholds()["band_caveat"]


def test_deterministic(job, candidate):
    a, b = make_screening(job, candidate), make_screening(job, candidate)
    assert a.score.model_dump(exclude={"rubric_hash"}) == b.score.model_dump(exclude={"rubric_hash"})


def test_unscorable_excluded_from_denominator(screening):
    uns = {r.requirement_id for r in screening.requirements if r.importance in (Importance.unscorable, Importance.contextual, Importance.eligibility)}
    for c in screening.score.components:
        assert not any(k.requirement_id in uns for k in c.contributions)


def test_traceability_score_to_span(screening):
    matches = {m.match_id: m for m in screening.matches}
    ev = {e.evidence_id: e for e in screening.evidence}
    src = None
    for c in screening.score.components:
        for k in c.contributions:
            m = matches[k.match_id]
            assert m.requirement_id == k.requirement_id
            if k.points_awarded > 0:
                assert m.evidence_ids, "points awarded without evidence"
                for eid in m.evidence_ids:
                    loc = ev[eid].source_location
                    assert loc.text_span and loc.char_end > loc.char_start


def test_suppressed_when_no_text(job):
    import fitz
    from screening_core.pipeline import build_candidate_from_bytes
    d = fitz.open()
    p = d.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40), False)
    pix.clear_with(120)
    p.insert_image(fitz.Rect(72, 72, 200, 200), pixmap=pix)
    c = build_candidate_from_bytes("C", "scan.pdf", d.tobytes())
    s = make_screening(job, c)
    assert s.score.qualification_scoring_suppressed and s.score.alignment_index == 0 and "OCR" in s.score.band_label
    assert s.recommended_human_action.value == "hold_for_review"


def test_invalid_rubric_rejected(tmp_path):
    from screening_core.schemas.models import RubricConfig
    bad = {"schema_version": "2.0.0", "rubric_id": "bad", "rubric_version": "1", "weights": {"a": 60, "b": 60}}
    with pytest.raises(Exception):
        RubricConfig.model_validate(bad)
