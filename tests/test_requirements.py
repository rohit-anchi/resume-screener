from screening_core.schemas.models import Importance, RequirementCategory


def _by_concept(job):
    return {r.normalised_concept: r for r in job.requirements}


def test_atomic_requirements_with_spans(job):
    text = job.document.extracted_text
    assert len(job.requirements) >= 10
    for r in job.requirements:
        assert text[r.source_location.char_start:r.source_location.char_end] == r.source_location.text_span
        assert r.text.strip() in r.source_location.text_span


def test_importance_and_threshold(job):
    by = _by_concept(job)
    pm = [r for r in job.requirements if r.normalised_concept == "product_management" and r.importance == Importance.required][0]
    assert pm.minimum_threshold and pm.minimum_threshold.value == 5 and pm.minimum_threshold.unit == "years"
    assert by["sql"].importance == Importance.preferred
    assert by["saas_subscription"].importance == Importance.preferred
    assert by["cloud_platforms"].importance == Importance.required
    assert by["scrum_certification"].category == RequirementCategory.certification


def test_subjective_criteria_flagged_unscorable(job):
    uns = [r for r in job.requirements if r.importance == Importance.unscorable]
    assert uns and "culture fit" in uns[0].text.lower() and uns[0].human_review_required


def test_eligibility_requirements_classified(job):
    elig = [r for r in job.requirements if r.importance == Importance.eligibility]
    cats = {r.category for r in elig}
    assert RequirementCategory.work_authorisation in cats and RequirementCategory.travel in cats


def test_benefits_and_eeo_not_requirements(job):
    assert not any("salary" in r.text.lower() for r in job.requirements)
