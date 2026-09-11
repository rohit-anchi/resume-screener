import json
from pathlib import Path

import pytest

from screening_core.ats.detect import PROFILE_BY_PLATFORM, detect
from screening_core.profiles.loader import load_profile
from screening_core.schemas.jobdoc import AtsPlatform

CASES = json.loads((Path(__file__).resolve().parents[1] / "evaluation" / "ats-detection-tests" / "cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["name"])
def test_ats_detection(case):
    d = detect(case["links"], case["text"])
    assert d.application_platform.value == case["expected_platform"], d.signals
    assert d.selected_profile_id == case["expected_profile"]
    assert d.has_approved_knowledge_profile is case["expected_approved"]
    assert d.confidence >= case["min_confidence"]
    load_profile(d.selected_profile_id)  # selected profile must exist


def test_listing_source_differs_from_application_platform():
    d = detect(["https://www.linkedin.com/safety/go/?url=https%3A%2F%2Fjobs%2Elever%2Eco%2Facme%2F1%2Fapply"], "")
    assert d.listing_source == "linkedin" and d.application_platform == AtsPlatform.lever


def test_unapproved_platform_falls_back_to_neutral_only():
    for platform in (AtsPlatform.ashby, AtsPlatform.other, AtsPlatform.unknown):
        assert platform not in PROFILE_BY_PLATFORM
    d = detect(["https://jobs.ashbyhq.com/acme/1/application"], "")
    assert d.selected_profile_id == "platform_neutral"
    assert load_profile("platform_neutral").platform is None


def test_every_approved_platform_maps_to_a_real_profile():
    for platform, pid in PROFILE_BY_PLATFORM.items():
        prof = load_profile(pid)
        assert prof.platform, f"{pid} must name a platform"


def test_signals_are_recorded_for_audit():
    d = detect(["https://boards.greenhouse.io/acme/jobs/1"], "Apply through Greenhouse")
    kinds = {s.signal_type for s in d.signals}
    assert "application_link" in kinds and "document_text" in kinds
    assert d.application_url and d.confidence >= 0.95
