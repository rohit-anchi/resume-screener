"""Rubric registry: versioned, hashed, file-backed (TM-06)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..schemas.models import RubricConfig

ROOT = Path(__file__).resolve().parents[3]
RUBRIC_DIR = ROOT / "config" / "rubrics"
THRESHOLDS = ROOT / "config" / "confidence-thresholds" / "default.json"


def load_rubric(rubric_id: str = "default", version: str | None = None) -> RubricConfig:
    candidates = sorted(RUBRIC_DIR.glob(f"{rubric_id}-*.json"))
    if version:
        candidates = [c for c in candidates if c.name == f"{rubric_id}-{version}.json"]
    if not candidates:
        raise FileNotFoundError(f"rubric {rubric_id} {version or ''} not found")
    path = candidates[-1]
    raw = path.read_bytes()
    cfg = RubricConfig.model_validate_json(raw)
    cfg.rubric_hash = hashlib.sha256(raw).hexdigest()[:16]
    return cfg


def load_thresholds() -> dict:
    return json.loads(THRESHOLDS.read_text(encoding="utf-8"))
