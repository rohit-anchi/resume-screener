"""Pre-scoring validation harness: extraction, classification, exclusion and ATS detection."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from screening_core.linkedin.builder import build_job_document
from screening_core.schemas.jobdoc import BlockCategory as C

FIX = ROOT / "evaluation" / "fixtures" / "jobs"


def report(path: Path, show_blocks: bool = False) -> None:
    jd = build_job_document(path.name, path.read_bytes())
    print("=" * 100)
    print(f"{path.name}")
    print(f"  employer={jd.employer!r} role={jd.role_title!r} location={jd.location!r} type={jd.employment_type!r} workplace={jd.workplace_type!r}")
    print(f"  comp={jd.compensation_text!r}")
    print(f"  listing_source={jd.listing_source} application_platform={jd.ats.application_platform.value} conf={jd.ats.confidence}")
    print(f"  approved_profile={jd.ats.has_approved_knowledge_profile} profile={jd.ats.selected_profile_id}")
    print(f"  app_url={jd.ats.application_url}")
    print(f"  off_platform={jd.ats.responses_managed_off_platform}")
    print(f"  blocks={len(jd.blocks)} scored={sum(b.allowed_for_requirements for b in jd.blocks)} excluded={len(jd.excluded_block_ids)}")
    print("  categories:")
    for k, v in jd.excluded_categories.items():
        print(f"    {k:42s} {v}")
    print("  sections:")
    for s in jd.sections:
        print(f"    {s.category.value:32s} {s.name:24s} {s.char_start:5d}-{s.char_end:5d} blocks={len(s.block_ids)}")
    print("  warnings:")
    for w in jd.extraction_warnings:
        print(f"    - {w}")
    unknown = [b for b in jd.blocks if b.category == C.unknown or b.review_required]
    if unknown:
        print("  NEEDS REVIEW:")
        for b in unknown:
            print(f"    [{b.block_id} p{b.page} {b.category.value}] {b.text[:110]!r}")
    print("\n  ---- EMPLOYER TEXT (scored input) ----")
    print("\n".join("    " + l for l in jd.employer_text.splitlines()))
    if show_blocks:
        print("\n  ---- ALL BLOCKS ----")
        for b in jd.blocks:
            flag = "SCORE" if b.allowed_for_requirements else ("keep " if b.category in C.allowed() else "EXCL ")
            print(f"    {flag} p{b.page} {b.category.value:38s} | {b.text[:90]!r}")


if __name__ == "__main__":
    targets = sorted(FIX.glob("*.pdf")) if len(sys.argv) < 2 else [Path(sys.argv[1])]
    for t in targets:
        report(t, show_blocks="--blocks" in sys.argv)
