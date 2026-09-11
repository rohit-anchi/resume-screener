"""Demo: run the two-input assessment for every job fixture against the resume fixture."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from screening_core.assessment import job_document_from_pdf, run_assessment
from screening_core.pipeline import build_candidate_from_bytes
from screening_core.reports.assessment_report import render
from screening_core.schemas.models import Mode

RESUME = ROOT / "evaluation" / "fixtures" / "resumes" / "candidate-resume.local.pdf"
JOBS = ROOT / "evaluation" / "fixtures" / "jobs"
OUT = ROOT / "data"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    cand = build_candidate_from_bytes("CAND-1", RESUME.name, RESUME.read_bytes())
    for f in sorted(JOBS.glob("*.pdf")):
        jd = job_document_from_pdf(f.name, f.read_bytes())
        a, s, job = run_assessment(jd, cand, mode=Mode.recruiter_assist)
        print("=" * 95)
        print(f"{jd.employer} | {jd.role_title} | platform={a.ats.application_platform.value} | profile={a.profile_id}")
        print(f"  index={a.alignment_index} band={a.band_label!r} eligibility={a.eligibility_status} confidence={a.evidence_confidence}")
        for k, v in a.component_scores.items():
            print(f"    {k:34s} {v}")
        print(f"  gaps={len(a.critical_gaps)} missing={len(a.missing_or_ambiguous)} recs={len(a.recommendations)} questions={len(a.questions)}")
        for g in a.critical_gaps[:4]:
            print(f"    GAP {g.requirement_id}: {g.requirement_text[:80]}")
        for r in a.recommendations[:4]:
            print(f"    REC [{r.priority}] {r.title[:80]}")
        for q in a.questions[:3]:
            print(f"    Q [{q.audience.value}] {q.question[:80]}")
        for m, label in ((Mode.candidate, "candidate"), (Mode.recruiter_assist, "recruiter")):
            a2, s2, _ = run_assessment(jd, cand, mode=m)
            path = OUT / f"{f.stem}.{label}.md"
            path.write_text(render(a2, s2, mode=m), encoding="utf-8")
            print(f"  wrote {path.name} ({len(path.read_text(encoding='utf-8'))} chars)")


if __name__ == "__main__":
    main()
