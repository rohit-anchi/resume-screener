from screening_core.evidence.extractor import build_candidate
from screening_core.ingestion.service import ingest
from screening_core.matching.matcher import match_requirements
from screening_core.schemas.models import Importance, MatchStatus, MatchType
from tests.conftest import TODAY


def test_every_requirement_gets_exactly_one_status(job, candidate):
    ms = match_requirements(job.requirements, candidate.evidence, today=TODAY)
    assert [m.requirement_id for m in ms] == [r.requirement_id for r in job.requirements]
    assert all(m.match_status in MatchStatus for m in ms)


def test_duration_threshold_confirmed(job, candidate):
    ms = {m.requirement_id: m for m in match_requirements(job.requirements, candidate.evidence, today=TODAY)}
    pm = [r for r in job.requirements if r.normalised_concept == "product_management" and r.importance == Importance.required][0]
    m = ms[pm.requirement_id]
    assert m.computed_duration_months and m.computed_duration_months >= 60 and m.match_status == MatchStatus.confirmed


def test_eligibility_never_inferred_from_resume(job, candidate):
    for r, m in zip(job.requirements, match_requirements(job.requirements, candidate.evidence, today=TODAY)):
        if r.importance == Importance.eligibility:
            assert m.match_status == MatchStatus.not_assessable and m.evidence_ids == []


def test_unscorable_not_assessable_and_review(job, candidate):
    for r, m in zip(job.requirements, match_requirements(job.requirements, candidate.evidence, today=TODAY)):
        if r.importance == Importance.unscorable:
            assert m.match_status == MatchStatus.not_assessable and m.human_review_required


def test_no_evidence_is_not_absence_and_transferable_is_labelled(job):
    text = "Summary\nProject manager.\n\nExperience\nProject Manager | X | Jan 2018 - Present\n- Managed programme delivery across teams.\n"
    c = build_candidate("C", ingest("resume", "cv.txt", text.encode()), today=TODAY)
    ms = {m.requirement_id: m for m in match_requirements(job.requirements, c.evidence, today=TODAY)}
    by = {r.normalised_concept: r for r in job.requirements if r.importance == Importance.required}
    cloud = ms[by["cloud_platforms"].requirement_id]
    assert cloud.match_status == MatchStatus.no_evidence_located and "does not establish" in cloud.reason and cloud.verification_question
    pm = ms[by["product_management"].requirement_id]
    assert pm.match_type == MatchType.transferable and pm.human_review_required and "Transferable" in pm.reason and pm.coverage == 0.5


def test_below_threshold_is_partial_with_question(job):
    text = "Experience\nProduct Manager | X | Jan 2024 - Present\n- Owned product roadmap and stakeholder management.\n"
    c = build_candidate("C", ingest("resume", "cv.txt", text.encode()), today=TODAY)
    ms = {m.requirement_id: m for m in match_requirements(job.requirements, c.evidence, today=TODAY)}
    pm = [r for r in job.requirements if r.normalised_concept == "product_management" and r.importance == Importance.required][0]
    m = ms[pm.requirement_id]
    assert m.match_status == MatchStatus.partial and m.coverage < 1 and "additional" in m.verification_question


def test_explicit_absence_yields_weak_and_contradictory():
    from screening_core.requirements.extractor import extract_requirements
    jd = "Minimum qualifications\n- Experience working with cloud platforms.\n- Familiarity with SQL.\n"
    reqs = extract_requirements("D", jd)
    text = "Summary\nAnalyst with no prior experience with cloud platforms.\n\nExperience\nAnalyst | X | Jan 2020 - Present\n- Wrote SQL reports on AWS.\n"
    c = build_candidate("C", ingest("resume", "cv.txt", text.encode()), today=TODAY)
    ms = {r.normalised_concept: m for r, m in zip(reqs, match_requirements(reqs, c.evidence, today=TODAY))}
    assert ms["cloud_platforms"].match_status == MatchStatus.contradictory and ms["cloud_platforms"].human_review_required
