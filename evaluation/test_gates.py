"""Pytest wrapper so quality gates run with the suite."""
from evaluation.run_gates import THRESHOLDS, run


def test_quality_gates():
    rep = run()
    failed = [k for k, v in rep["gates"].items() if not v]
    assert not failed, f"gates failed: {failed}; results={rep['results']}; notes={rep['notes']}"
    assert set(rep["gates"]) == set(THRESHOLDS)
