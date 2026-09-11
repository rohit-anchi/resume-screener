import json
import re
from pathlib import Path

import pytest

from screening_core.linkedin.blocks import canon, is_garbled, is_page_furniture
from screening_core.linkedin.builder import build_job_document, requirement_sections
from screening_core.linkedin.classify import classify
from screening_core.requirements.extractor import extract_requirements
from screening_core.schemas.jobdoc import BlockCategory as C

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "evaluation" / "fixtures" / "jobs"
EXPECTED = ROOT / "evaluation" / "expected-results" / "job-extraction"
EXCLUSION = json.loads((ROOT / "evaluation" / "linkedin-content-exclusion-tests" / "cases.json").read_text(encoding="utf-8"))

CASES = sorted(EXPECTED.glob("*.json"))


@pytest.fixture(scope="module")
def docs():
    return {p.stem: build_job_document(p.name, p.read_bytes()) for p in FIX.glob("*.pdf")}


def _expected(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case_path", CASES, ids=lambda p: p.stem)
def test_job_metadata(case_path, docs):
    exp = _expected(case_path)
    jd = docs[Path(exp["fixture"]).stem]
    assert jd.listing_source == exp["listing_source"]
    assert jd.employer == exp["employer"]
    assert jd.role_title == exp["role_title"]
    assert jd.location == exp["location"]
    assert jd.employment_type == exp["employment_type"]
    assert jd.workplace_type == exp["workplace_type"]
    if exp["compensation_text_contains"]:
        assert exp["compensation_text_contains"] in (jd.compensation_text or "")


@pytest.mark.parametrize("case_path", CASES, ids=lambda p: p.stem)
def test_ats_detection_and_profile_selection(case_path, docs):
    exp = _expected(case_path)
    jd = docs[Path(exp["fixture"]).stem]
    assert jd.ats.application_platform.value == exp["application_platform"]
    assert jd.ats.has_approved_knowledge_profile is exp["has_approved_knowledge_profile"]
    assert jd.ats.selected_profile_id == exp["selected_profile_id"]
    assert exp["application_url_contains"] in (jd.ats.application_url or "")
    assert jd.ats.responses_managed_off_platform is exp["responses_managed_off_platform"]
    # listing source and application platform are distinct concepts
    assert jd.listing_source == "linkedin" and jd.ats.application_platform.value != "linkedin"


@pytest.mark.parametrize("case_path", CASES, ids=lambda p: p.stem)
def test_employer_content_included(case_path, docs):
    exp = _expected(case_path)
    jd = docs[Path(exp["fixture"]).stem]
    flat = re.sub(r"\s+", " ", jd.employer_text)
    for phrase in exp["employer_text_must_contain"]:
        assert re.sub(r"\s+", " ", phrase) in flat, phrase


@pytest.mark.parametrize("case_path", CASES, ids=lambda p: p.stem)
def test_linkedin_content_excluded_from_scored_text(case_path, docs):
    exp = _expected(case_path)
    jd = docs[Path(exp["fixture"]).stem]
    flat = re.sub(r"\s+", " ", canon(jd.employer_text)).lower()
    for phrase in exp["employer_text_must_not_contain"]:
        assert re.sub(r"\s+", " ", canon(phrase)).lower() not in flat, phrase


@pytest.mark.parametrize("case_path", CASES, ids=lambda p: p.stem)
def test_excluded_content_retained_for_audit(case_path, docs):
    exp = _expected(case_path)
    jd = docs[Path(exp["fixture"]).stem]
    # every block keeps a category and a reason, and nothing is silently dropped
    assert len(jd.blocks) >= 80
    assert all(b.classification_reason for b in jd.blocks)
    excluded = [b for b in jd.blocks if b.block_id in jd.excluded_block_ids]
    assert excluded and all(b.category not in C.allowed() for b in excluded)
    for cat in exp["retained_but_unscored_categories"]:
        matching = [b for b in jd.blocks if b.category.value == cat]
        assert matching, f"expected retained category {cat}"
        assert all(not b.allowed_for_requirements for b in matching), cat


@pytest.mark.parametrize("case_path", CASES, ids=lambda p: p.stem)
def test_no_unattributed_blocks(case_path, docs):
    exp = _expected(case_path)
    jd = docs[Path(exp["fixture"]).stem]
    unknown = [b for b in jd.blocks if b.category == C.unknown]
    assert not unknown, [b.text[:60] for b in unknown]


@pytest.mark.parametrize("case_path", CASES, ids=lambda p: p.stem)
def test_requirement_extraction_from_classified_sections(case_path, docs):
    exp = _expected(case_path)
    jd = docs[Path(exp["fixture"]).stem]
    reqs = extract_requirements(jd.job_document_id, jd.employer_text, requirement_sections(jd))
    concepts_required = {r.normalised_concept for r in reqs if r.importance.value == "required"}
    concepts_preferred = {r.normalised_concept for r in reqs if r.importance.value == "preferred"}
    for c in exp["expected_requirement_concepts_required"]:
        assert c in concepts_required, f"missing required concept {c}"
    for c in exp["expected_requirement_concepts_preferred"]:
        assert c in concepts_preferred, f"missing preferred concept {c}"
    anywhere = {r.normalised_concept for r in reqs} | {a for r in reqs for a in r.alternative_concepts}
    for c in exp.get("expected_concepts_anywhere", []):
        assert c in anywhere, f"missing concept anywhere {c}"
    has_elig = any(r.importance.value == "eligibility" for r in reqs)
    assert has_elig is exp["expected_eligibility_requirement_present"]
    # spans must resolve into the employer text
    for r in reqs:
        assert jd.employer_text[r.source_location.char_start:r.source_location.char_end] == r.source_location.text_span


def test_amber_thresholds_are_not_conflated(docs):
    jd = docs["amber-electric-director-of-product.linkedin"]
    reqs = extract_requirements(jd.job_document_id, jd.employer_text, requirement_sections(jd))
    thresholds = sorted({(r.minimum_threshold.value, r.minimum_threshold.unit) for r in reqs if r.minimum_threshold})
    assert (2.0, "years") in thresholds and (5.0, "years") in thresholds


def test_strong_plus_is_preferred_not_required(docs):
    jd = docs["amber-electric-director-of-product.linkedin"]
    reqs = extract_requirements(jd.job_document_id, jd.employer_text, requirement_sections(jd))
    plus = [r for r in reqs if "strong plus" in r.text]
    assert plus and all(r.importance.value == "preferred" for r in plus)


def test_third_party_personal_data_never_scored(docs):
    for jd in docs.values():
        low = jd.employer_text.lower()
        for phrase in EXCLUSION["third_party_personal_data"]["phrases"]:
            assert phrase.lower() not in low, phrase


@pytest.mark.parametrize("case", EXCLUSION["phrase_cases"], ids=lambda c: c["expected_category"] + ":" + c["phrase"][:24])
def test_exclusion_phrase_classification(case):
    from screening_core.linkedin.blocks import RawBlock

    block = RawBlock(page=1, order=1, y=300.0, x=10.0, max_font_size=10.0, text=case["phrase"])
    result = classify([block], page_count=1)[0]
    assert result.category.value == case["expected_category"], (case["phrase"], result.category.value, result.reason)
    assert result.category not in C.requirement_bearing()


def test_garbled_and_furniture_helpers():
    assert is_garbled("ti I li ith l t G B ld 'll t l th t t t h th t d h l thi k d t")
    assert is_garbled("hi i h O i")
    assert not is_garbled("You think in systems, comfortably joining the dots across various phases and teams.")
    assert is_page_furniture("9/9/26, 4:43 PM")
    assert is_page_furniture("https://www.linkedin.com/jobs/view/4440679590/")
    assert not is_page_furniture("Skills & Qualifications")


def test_ashby_never_substitutes_a_known_profile(docs):
    jd = docs["xero-lead-product-manager-ai-enablement.linkedin"]
    assert jd.ats.application_platform.value == "ashby"
    assert jd.ats.selected_profile_id == "platform_neutral"
    assert "no approved Phase 1 knowledge profile" in jd.ats.profile_selection_reason
    assert any("platform-neutral" in w for w in jd.extraction_warnings)
