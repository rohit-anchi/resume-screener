"""Human review and override service. Overrides are events, never in-place mutations (ADR-009/012)."""
from __future__ import annotations

from ..schemas.models import HumanAction, MatchStatus, ReviewAction, ScreeningResult
from .store import AuditStore


class ReviewService:
    def __init__(self, store: AuditStore):
        self.store = store

    def record(self, result: ScreeningResult, action: ReviewAction) -> ScreeningResult:
        if action.screening_id != result.screening_id:
            raise ValueError("screening id mismatch")
        payload = action.model_dump()
        if action.action == "record_decision":
            if action.human_decision is None:
                raise ValueError("record_decision requires human_decision")
            if action.human_decision == HumanAction.decline_with_human_reason and len(action.reason.strip()) < 10:
                raise ValueError("a decline requires a substantive human-selected reason")
        self.store.append(f"review.{action.action}", action.actor, payload, result.screening_id)
        return self.apply(result)

    def apply(self, result: ScreeningResult) -> ScreeningResult:
        """Rebuild a view of the result with overrides applied; the original stays in the audit trail."""
        view = result.model_copy(deep=True)
        by_match = {m.requirement_id: m for m in view.matches}
        for ev in self.store.events(result.screening_id):
            p = ev.payload
            if ev.event_type == "review.change_match_status" and p.get("target_id") in by_match:
                m = by_match[p["target_id"]]
                m.match_status = MatchStatus(p["new_value"])
                m.reason = f"[HUMAN OVERRIDE by {ev.actor}: {p['reason']}] " + m.reason
                for f in view.findings:
                    if f.requirement_id == p["target_id"]:
                        f.status, f.explanation = m.match_status, m.reason
            elif ev.event_type == "review.mark_not_assessable" and p.get("target_id") in by_match:
                m = by_match[p["target_id"]]
                m.match_status = MatchStatus.not_assessable
                m.reason = f"[HUMAN: marked not assessable by {ev.actor}: {p['reason']}]"
            elif ev.event_type == "review.override_score":
                view.score.band_label = f"{view.score.band_label} (human override recorded: {p['reason']})"
            elif ev.event_type == "review.record_decision":
                view.review_triggers.append(f"HUMAN DECISION by {ev.actor}: {p['human_decision']} — {p['reason']}")
        return view
