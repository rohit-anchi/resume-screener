"""Append-only, hash-chained audit store (ADR-009, TM-07)."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..schemas.models import AuditEvent

GENESIS = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(ev: dict[str, Any]) -> str:
    body = {k: v for k, v in ev.items() if k != "event_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


class AuditStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()

    def _last_hash(self) -> str:
        last = GENESIS
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = json.loads(line)["event_hash"]
        return last

    def append(self, event_type: str, actor: str, payload: dict[str, Any], screening_id: str | None = None) -> AuditEvent:
        ev = AuditEvent(event_id=f"EVT-{uuid.uuid4().hex[:12]}", event_type=event_type, timestamp=_now(), screening_id=screening_id, actor=actor, payload=payload, previous_hash=self._last_hash())
        d = ev.model_dump()
        d["event_hash"] = _hash(d)
        ev.event_hash = d["event_hash"]
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(d, default=str) + "\n")
        return ev

    def events(self, screening_id: str | None = None) -> list[AuditEvent]:
        out = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    ev = AuditEvent.model_validate_json(line)
                    if screening_id is None or ev.screening_id == screening_id:
                        out.append(ev)
        return out

    def verify_chain(self) -> tuple[bool, str]:
        prev = GENESIS
        with self.path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if not line.strip():
                    continue
                d = json.loads(line)
                if d["previous_hash"] != prev:
                    return False, f"line {i}: previous_hash mismatch"
                if _hash(d) != d["event_hash"]:
                    return False, f"line {i}: event_hash mismatch (tampered)"
                prev = d["event_hash"]
        return True, "ok"
