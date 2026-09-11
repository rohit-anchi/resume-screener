import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT))

from screening_core.pipeline import build_candidate_from_bytes, build_job, run_screening  # noqa: E402
from screening_core.schemas.models import ApplicationAnswer, EligibilityRule, Mode, ScreeningRequest  # noqa: E402

DATA = ROOT / "evaluation" / "datasets"
TODAY = date(2026, 9, 9)


@pytest.fixture(scope="session")
def jd_bytes():
    return (DATA / "jd-001-senior-pm-telemetry.txt").read_bytes()


@pytest.fixture(scope="session")
def resume_bytes():
    return (DATA / "resume-001-baseline.txt").read_bytes()


@pytest.fixture(scope="session")
def job(jd_bytes):
    return build_job("JOB-001", "Senior Product Manager", "jd.txt", jd_bytes)


@pytest.fixture(scope="session")
def candidate(resume_bytes):
    return build_candidate_from_bytes("CAND-001", "resume.txt", resume_bytes, today=TODAY)


@pytest.fixture
def rules():
    return [EligibilityRule(rule_id="R1", question_id="Q1", description="Authorised to work without sponsorship", operator="truthy", expected=True, legal_basis="Declared lawful work-authorisation requirement for the role")]


@pytest.fixture
def answers_yes():
    return [ApplicationAnswer(question_id="Q1", question_text="Are you authorised to work without sponsorship?", answer="yes")]


@pytest.fixture
def screening(job, candidate, rules, answers_yes):
    req = ScreeningRequest(job_id="JOB-001", candidate_id="CAND-001", screening_profile="greenhouse_informed", mode=Mode.recruiter_assist, application_answers=answers_yes, employer_rules=rules)
    return run_screening(job, candidate, req, today=TODAY)


def make_screening(job, candidate, profile="platform_neutral", mode=Mode.candidate, answers=None, rules=None):
    req = ScreeningRequest(job_id=job.job_id, candidate_id=candidate.candidate_id, screening_profile=profile, mode=mode, application_answers=answers or [], employer_rules=rules or [])
    return run_screening(job, candidate, req, today=TODAY)
