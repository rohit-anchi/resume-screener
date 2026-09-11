from screening_core.eligibility.engine import evaluate
from screening_core.schemas.models import ApplicationAnswer, EligibilityStatus


def test_not_evaluated_without_rules():
    assert evaluate([], []).status == EligibilityStatus.not_evaluated


def test_meets(rules, answers_yes):
    assert evaluate(rules, answers_yes).status == EligibilityStatus.meets_declared_eligibility


def test_does_not_meet_requires_human(rules):
    r = evaluate(rules, [ApplicationAnswer(question_id="Q1", question_text="q", answer="no")])
    assert r.status == EligibilityStatus.does_not_meet_declared_eligibility
    assert "Human review required" in r.findings[0].explanation


def test_missing_answer(rules):
    assert evaluate(rules, []).status == EligibilityStatus.additional_information_required


def test_conflicting_answers(rules):
    r = evaluate(rules, [ApplicationAnswer(question_id="Q1", question_text="q", answer="yes"), ApplicationAnswer(question_id="Q1", question_text="q", answer="no")])
    assert r.status == EligibilityStatus.human_review_required


def test_numeric_and_unparseable(rules):
    rules[0].operator, rules[0].expected = "gte", 3
    assert evaluate(rules, [ApplicationAnswer(question_id="Q1", question_text="q", answer="5")]).status == EligibilityStatus.meets_declared_eligibility
    assert evaluate(rules, [ApplicationAnswer(question_id="Q1", question_text="q", answer="five-ish")]).status == EligibilityStatus.human_review_required


def test_eligibility_never_in_index(job, candidate, rules):
    from tests.conftest import make_screening
    a = make_screening(job, candidate, answers=[ApplicationAnswer(question_id="Q1", question_text="q", answer="yes")], rules=rules)
    b = make_screening(job, candidate, answers=[ApplicationAnswer(question_id="Q1", question_text="q", answer="no")], rules=rules)
    assert a.score.alignment_index == b.score.alignment_index
    assert b.eligibility.status == EligibilityStatus.does_not_meet_declared_eligibility and b.recommended_human_action.value == "hold_for_review"
