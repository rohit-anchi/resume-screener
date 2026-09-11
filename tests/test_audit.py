import json

import pytest

from screening_core.audit.review import ReviewService
from screening_core.audit.store import AuditStore
from screening_core.reports.render import recruiter_report
from screening_core.schemas.models import HumanAction, MatchStatus, ReviewAction


def test_chain_and_tamper_detection(tmp_path):
    st = AuditStore(tmp_path / "a.jsonl")
    st.append("x", "u", {"a": 1})
    st.append("y", "u", {"b": 2})
    assert st.verify_chain()[0]
    lines = (tmp_path / "a.jsonl").read_text().splitlines()
    d = json.loads(lines[0]); d["payload"]["a"] = 99
    (tmp_path / "a.jsonl").write_text(json.dumps(d) + "\n" + lines[1] + "\n")
    ok, msg = st.verify_chain()
    assert not ok and "tamper" in msg


def test_override_is_event_and_visible(tmp_path, screening):
    st = AuditStore(tmp_path / "a.jsonl")
    svc = ReviewService(st)
    target = [f for f in screening.findings if f.status == MatchStatus.partial][0].requirement_id
    view = svc.record(screening, ReviewAction(screening_id=screening.screening_id, actor="rec-1", actor_role="recruiter", action="change_match_status", target_id=target, new_value="strong", reason="Verified in phone screen"))
    assert view.matches[[m.requirement_id for m in view.matches].index(target)].match_status == MatchStatus.strong
    assert screening.matches[[m.requirement_id for m in screening.matches].index(target)].match_status == MatchStatus.partial  # original untouched
    assert len(st.events(screening.screening_id)) == 1 and st.verify_chain()[0]
    assert "HUMAN OVERRIDE" in recruiter_report(view, st.events(screening.screening_id))


def test_decline_requires_human_and_reason(tmp_path, screening):
    svc = ReviewService(AuditStore(tmp_path / "a.jsonl"))
    with pytest.raises(ValueError):
        svc.record(screening, ReviewAction(screening_id=screening.screening_id, actor="r", actor_role="recruiter", action="record_decision", human_decision=HumanAction.decline_with_human_reason, reason="no"))
    view = svc.record(screening, ReviewAction(screening_id=screening.screening_id, actor="r", actor_role="recruiter", action="record_decision", human_decision=HumanAction.decline_with_human_reason, reason="Role requires on-site presence; candidate declined relocation in call"))
    assert any("HUMAN DECISION" in t for t in view.review_triggers)


def test_engine_never_emits_decline(screening):
    assert screening.recommended_human_action != HumanAction.decline_with_human_reason
