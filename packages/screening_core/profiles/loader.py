"""Platform-profile loader with Phase 1 claim traceability (ADR-010)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..schemas.models import PlatformProfile, Scenario

ROOT = Path(__file__).resolve().parents[3]
PROFILE_DIR = ROOT / "config" / "platform-profiles"
CLAIMS = ROOT / "knowledge" / "model" / "platform-capabilities.json"
PROHIBITED = re.compile(r"exact ats score|guaranteed? (?:ats )?pass|this is how \w+ ranks|will reject this resume|gives this candidate \d+%|automatically fails", re.I)


def load_claims() -> dict[str, dict]:
    data = json.loads(CLAIMS.read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["claims"]}


def _profile_id(stem: str) -> str:
    return stem.replace("-", "_")


def list_profiles() -> list[str]:
    return sorted(_profile_id(p.stem) for p in PROFILE_DIR.glob("*.json"))


def load_profile(profile_id: str) -> PlatformProfile:
    canonical = _profile_id(profile_id)
    path = next((p for p in PROFILE_DIR.glob("*.json") if _profile_id(p.stem) == canonical), None)
    if path is None:
        raise FileNotFoundError(f"unknown profile {profile_id}")
    prof = PlatformProfile.model_validate_json(path.read_text(encoding="utf-8"))
    claims = load_claims()
    for s in prof.scenarios:
        missing = [c for c in s.claim_ids if c not in claims]
        if missing:
            raise ValueError(f"profile {profile_id} scenario {s.scenario_id} references unknown claims {missing}")
        if prof.platform and any(claims[c]["platform"] != prof.platform for c in s.claim_ids):
            raise ValueError(f"profile {profile_id} scenario {s.scenario_id} cites claims from another platform")
        if PROHIBITED.search(s.description) or PROHIBITED.search(prof.disclaimer):
            raise ValueError(f"profile {profile_id} contains prohibited language")
    return prof


def render_scenarios(prof: PlatformProfile) -> list[Scenario]:
    claims = load_claims()
    out = []
    for s in prof.scenarios:
        cites = "; ".join(f"{c} ({claims[c]['label']}, automation L{claims[c]['automationLevel']})" for c in s.claim_ids)
        out.append(Scenario(scenario_id=s.scenario_id, title=s.title, description=f"{s.description} Evidence: {cites}.", delivery_label=s.delivery_label, claim_ids=s.claim_ids, emphasis=s.emphasis))
    return out
