import json
import re

import pytest

from screening_core.profiles.loader import PROHIBITED, list_profiles, load_claims, load_profile, render_scenarios
from tests.conftest import make_screening

EXPECTED = {"platform_neutral", "greenhouse_informed", "lever_informed", "workday_informed", "successfactors_informed"}


def test_all_profiles_present_and_claims_resolve():
    assert set(list_profiles()) == EXPECTED
    claims = load_claims()
    for pid in EXPECTED:
        p = load_profile(pid)
        assert p.disclaimer and p.scenarios
        for s in p.scenarios:
            assert s.claim_ids and all(c in claims for c in s.claim_ids)
            if p.platform:
                assert all(claims[c]["platform"] == p.platform for c in s.claim_ids)


def test_optional_capabilities_labelled():
    for pid in EXPECTED - {"platform_neutral"}:
        labels = {s.delivery_label for s in load_profile(pid).scenarios}
        assert "OPTIONAL" in labels and ("DOCUMENTED" in labels or "CONFIGURATION-DEPENDENT" in labels)


def test_no_prohibited_language_in_profiles_or_reports(job, candidate):
    from screening_core.reports.render import candidate_report, recruiter_report
    for pid in EXPECTED:
        s = make_screening(job, candidate, profile=pid)
        for text in (candidate_report(s), recruiter_report(s)):
            assert not PROHIBITED.search(text), pid
            assert "platform-informed" in text.lower()


def test_profile_changes_scenarios_not_scores(job, candidate):
    results = {pid: make_screening(job, candidate, profile=pid) for pid in EXPECTED}
    idx = {r.score.alignment_index for r in results.values()}
    assert len(idx) == 1
    assert len({tuple(s.scenario_id for s in r.scenarios) for r in results.values()}) == len(EXPECTED)


def test_unknown_claim_rejected(tmp_path, monkeypatch):
    from screening_core.profiles import loader
    bad = json.loads((loader.PROFILE_DIR / "lever_informed.json").read_text())
    bad["scenarios"][0]["claim_ids"] = ["LV-C99"]
    (tmp_path / "lever_informed.json").write_text(json.dumps(bad))
    monkeypatch.setattr(loader, "PROFILE_DIR", tmp_path)
    with pytest.raises(ValueError):
        loader.load_profile("lever_informed")
