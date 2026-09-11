"""Quality-gate runner. Exit code 1 if any critical gate fails.

Usage: python -m evaluation.run_gates [--update-baseline]
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from screening_core.ats.detect import detect as ats_detect  # noqa: E402
from screening_core.audit.review import ReviewService  # noqa: E402
from screening_core.linkedin.blocks import RawBlock, canon  # noqa: E402
from screening_core.linkedin.builder import build_job_document  # noqa: E402
from screening_core.linkedin.classify import classify as classify_blocks  # noqa: E402
from screening_core.schemas.jobdoc import BlockCategory  # noqa: E402
from screening_core.audit.store import AuditStore  # noqa: E402
from screening_core.pipeline import build_candidate_from_bytes, build_job, run_screening  # noqa: E402
from screening_core.schemas.models import ApplicationAnswer, EligibilityRule, HumanAction, Importance, MatchStatus, MatchType, Mode, ReviewAction, ScreeningRequest  # noqa: E402
from screening_core.security.redaction import assert_no_protected_markers  # noqa: E402

EV = ROOT / "evaluation"
DATA = EV / "datasets"
TODAY = date(2026, 9, 9)
THRESHOLDS = {"eligibility_accuracy": 0.95, "citation_accuracy": 0.90, "required_extraction_precision": 0.85, "direct_match_precision": 0.85,
              "protected_attribute_hits": 0, "traceability": 1.0, "override_capture": 1.0, "automatic_adverse_actions": 0,
              "fairness_max_delta": 0.0, "adversarial_pass_rate": 1.0, "job_extraction_accuracy": 1.0,
              "linkedin_exclusion_accuracy": 1.0, "ats_detection_accuracy": 1.0, "unapproved_profile_substitutions": 0}


def _screen(job_file: str, resume_bytes: bytes, answers, rule, cid="C", profile="platform_neutral"):
    job = build_job("J", "job", job_file, (DATA / job_file).read_bytes())
    cand = build_candidate_from_bytes(cid, "cv.txt", resume_bytes, today=TODAY)
    req = ScreeningRequest(job_id="J", candidate_id=cid, screening_profile=profile, mode=Mode.recruiter_assist,
                           application_answers=[ApplicationAnswer(question_id=a["question_id"], question_text="q", answer=a["answer"]) for a in answers], employer_rules=[rule] if rule else [])
    return job, cand, run_screening(job, cand, req, today=TODAY)


def _apply(text: bytes, spec: dict) -> bytes:
    s = text.decode()
    for a, b in spec.get("replace", []):
        assert a in s, f"fixture replace target missing: {a}"
        s = s.replace(a, b)
    if spec.get("append"):
        s += spec["append"] * spec.get("repeat", 1)
    return s.encode()


def run(update_baseline: bool = False) -> dict:
    spec = json.loads((EV / "expected-results" / "cases.json").read_text())
    rule = EligibilityRule(**spec["rule"])
    metrics = {k: {"num": 0, "den": 0} for k in ("eligibility", "citation", "required_extraction", "direct_match", "traceability")}
    protected_hits, adverse, notes, scores = 0, 0, [], {}
    for c in spec["cases"]:
        job, cand, res = _screen(c["job"], (DATA / c["resume"]).read_bytes(), c["answers"], rule, cid=c["case_id"])
        scores[c["case_id"]] = {"index": res.score.alignment_index, "components": {k.component: k.raw_score for k in res.score.components}}
        m = metrics["eligibility"]; m["den"] += 1; m["num"] += res.eligibility.status.value == c["expected_eligibility"]
        # citation: every evidence span verbatim in redacted source
        src = cand.document.redacted_text
        for e in res.evidence:
            metrics["citation"]["den"] += 1
            metrics["citation"]["num"] += src[e.source_location.char_start:e.source_location.char_end] == e.source_location.text_span
        # required extraction precision: extracted required concepts that are annotated as expected
        req_concepts = [r.normalised_concept for r in res.requirements if r.importance == Importance.required]
        for rc in req_concepts:
            metrics["required_extraction"]["den"] += 1
            metrics["required_extraction"]["num"] += rc in c["expected_required_concepts"]
        if c["expected_unscorable_present"] != any(r.importance == Importance.unscorable for r in res.requirements):
            notes.append(f"{c['case_id']}: unscorable detection mismatch")
        # direct-match precision
        by = {r.requirement_id: r.normalised_concept for r in res.requirements}
        scorable = {r.requirement_id for r in res.requirements if r.importance in (Importance.required, Importance.preferred)}
        for mt in res.matches:
            if mt.requirement_id not in scorable:
                continue
            if mt.match_type == MatchType.direct and mt.match_status in (MatchStatus.confirmed, MatchStatus.strong, MatchStatus.partial):
                metrics["direct_match"]["den"] += 1
                metrics["direct_match"]["num"] += by[mt.requirement_id] in c["expected_direct_matches_correct"]
            exp = c["expected_statuses"].get(by[mt.requirement_id])
            if exp and mt.match_status.value not in exp:
                notes.append(f"{c['case_id']}: {by[mt.requirement_id]} status {mt.match_status.value} not in {exp}")
        # traceability
        mmap = {x.match_id: x for x in res.matches}
        for comp in res.score.components:
            for k in comp.contributions:
                metrics["traceability"]["den"] += 1
                metrics["traceability"]["num"] += (k.points_awarded == 0) or bool(mmap[k.match_id].evidence_ids)
        protected_hits += len(assert_no_protected_markers(cand.document.redacted_text))
        adverse += res.recommended_human_action == HumanAction.decline_with_human_reason
    # override capture
    store = AuditStore(EV / "reports" / "_gate_audit.jsonl")
    store.path.write_text("")
    _, _, res = _screen(spec["cases"][0]["job"], (DATA / spec["cases"][0]["resume"]).read_bytes(), spec["cases"][0]["answers"], rule)
    svc = ReviewService(store)
    for i, r in enumerate(res.requirements[:3]):
        svc.record(res, ReviewAction(screening_id=res.screening_id, actor="gate", actor_role="recruiter", action="change_match_status", target_id=r.requirement_id, new_value="partial", reason="gate check"))
    override_capture = len(store.events(res.screening_id)) / 3
    # fairness
    fz = json.loads((EV / "fairness" / "pairs.json").read_text())
    base_bytes = (DATA / fz["base"]).read_bytes()
    _, _, base = _screen(fz["job"], base_bytes, [], None)
    fairness = {}
    for v in fz["variants"]:
        _, _, r = _screen(fz["job"], _apply(base_bytes, v), [], None)
        fairness[v["name"]] = round(r.score.alignment_index - base.score.alignment_index, 2)
    # adversarial
    ad = json.loads((EV / "adversarial" / "cases.json").read_text())
    ad_base_bytes = (DATA / ad["base"]).read_bytes()
    _, _, ad_base = _screen(ad["job"], ad_base_bytes, [], None)
    adv_results = {}
    for c in ad["cases"]:
        _, cand, r = _screen(ad["job"], _apply(ad_base_bytes, c), [], None)
        ok = True
        if c.get("expect_flag"):
            ok &= c["expect_flag"] in {f.code for f in r.document_findings}
            ok &= r.score.alignment_index <= ad_base.score.alignment_index + 0.5
        if c.get("expect_contradiction"):
            ok &= bool(cand.contradictions) and any(t.startswith("resume:") for t in r.review_triggers)
        if c.get("expect_score_unchanged"):
            ok &= r.score.alignment_index == ad_base.score.alignment_index
        adv_results[c["name"]] = ok
    # regression
    baseline_path = EV / "regression" / "baseline.json"
    regression = {"status": "no_baseline"}
    if baseline_path.exists() and not update_baseline:
        base_scores = json.loads(baseline_path.read_text())
        deltas = {k: round(v["index"] - base_scores.get(k, {}).get("index", v["index"]), 2) for k, v in scores.items()}
        regression = {"status": "ok" if all(d == 0 for d in deltas.values()) else "changed", "deltas": deltas}
    if update_baseline or not baseline_path.exists():
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(scores, indent=2))
        regression = {"status": "baseline_written"}

    # ---- two-input workflow gates: LinkedIn job extraction, content exclusion, ATS detection ----
    job_checks = job_hits = excl_checks = excl_hits = ats_checks = ats_hits = 0
    substitutions = 0
    jobdir = ROOT / "evaluation" / "fixtures" / "jobs"
    for exp_path in sorted((EV / "expected-results" / "job-extraction").glob("*.json")):
        exp = json.loads(exp_path.read_text(encoding="utf-8"))
        pdf = jobdir / exp["fixture"]
        if not pdf.exists():
            notes.append(f"missing job fixture {exp['fixture']}")
            continue
        jd = build_job_document(pdf.name, pdf.read_bytes())
        flat = re.sub(r"\s+", " ", canon(jd.employer_text)).lower()
        for field, actual in (("employer", jd.employer), ("role_title", jd.role_title), ("location", jd.location),
                              ("employment_type", jd.employment_type), ("workplace_type", jd.workplace_type),
                              ("listing_source", jd.listing_source)):
            job_checks += 1
            ok = actual == exp[field]
            job_hits += ok
            if not ok:
                notes.append(f"{exp['fixture']}: {field} expected {exp[field]!r} got {actual!r}")
        for phrase in exp["employer_text_must_contain"]:
            job_checks += 1
            ok = re.sub(r"\s+", " ", canon(phrase)).lower() in flat
            job_hits += ok
            if not ok:
                notes.append(f"{exp['fixture']}: missing employer phrase {phrase[:50]!r}")
        for phrase in exp["employer_text_must_not_contain"]:
            excl_checks += 1
            ok = re.sub(r"\s+", " ", canon(phrase)).lower() not in flat
            excl_hits += ok
            if not ok:
                notes.append(f"{exp['fixture']}: LinkedIn content leaked into scored text: {phrase[:50]!r}")
        unattributed = [b for b in jd.blocks if b.category == BlockCategory.unknown]
        excl_checks += 1
        excl_hits += not unattributed
        if unattributed:
            notes.append(f"{exp['fixture']}: {len(unattributed)} unattributed block(s)")
        for field, actual in (("application_platform", jd.ats.application_platform.value),
                              ("selected_profile_id", jd.ats.selected_profile_id),
                              ("has_approved_knowledge_profile", jd.ats.has_approved_knowledge_profile)):
            ats_checks += 1
            ok = actual == exp[field]
            ats_hits += ok
            if not ok:
                notes.append(f"{exp['fixture']}: {field} expected {exp[field]!r} got {actual!r}")
        if not jd.ats.has_approved_knowledge_profile and jd.ats.selected_profile_id != "platform_neutral":
            substitutions += 1
            notes.append(f"{exp['fixture']}: unapproved platform was given profile {jd.ats.selected_profile_id}")

    for case in json.loads((EV / "ats-detection-tests" / "cases.json").read_text(encoding="utf-8"))["cases"]:
        d = ats_detect(case["links"], case["text"])
        for field, actual in (("expected_platform", d.application_platform.value), ("expected_profile", d.selected_profile_id),
                              ("expected_approved", d.has_approved_knowledge_profile)):
            ats_checks += 1
            ok = actual == case[field]
            ats_hits += ok
            if not ok:
                notes.append(f"ats case {case['name']}: {field} expected {case[field]!r} got {actual!r}")
        if not d.has_approved_knowledge_profile and d.selected_profile_id != "platform_neutral":
            substitutions += 1

    for case in json.loads((EV / "linkedin-content-exclusion-tests" / "cases.json").read_text(encoding="utf-8"))["phrase_cases"]:
        block = RawBlock(page=1, order=1, y=300.0, x=10.0, max_font_size=10.0, text=case["phrase"])
        got = classify_blocks([block], page_count=1)[0]
        excl_checks += 1
        ok = got.category.value == case["expected_category"] and got.category not in BlockCategory.requirement_bearing()
        excl_hits += ok
        if not ok:
            notes.append(f"exclusion case {case['phrase'][:40]!r}: expected {case['expected_category']} got {got.category.value}")

    def ratio(k):
        m = metrics[k]
        return round(m["num"] / m["den"], 3) if m["den"] else None

    results = {
        "eligibility_accuracy": ratio("eligibility"), "citation_accuracy": ratio("citation"), "required_extraction_precision": ratio("required_extraction"),
        "direct_match_precision": ratio("direct_match"), "traceability": ratio("traceability"), "protected_attribute_hits": protected_hits,
        "override_capture": override_capture, "automatic_adverse_actions": adverse, "fairness_max_delta": max(abs(d) for d in fairness.values()),
        "adversarial_pass_rate": round(sum(adv_results.values()) / len(adv_results), 3),
        "job_extraction_accuracy": round(job_hits / job_checks, 3) if job_checks else None,
        "linkedin_exclusion_accuracy": round(excl_hits / excl_checks, 3) if excl_checks else None,
        "ats_detection_accuracy": round(ats_hits / ats_checks, 3) if ats_checks else None,
        "unapproved_profile_substitutions": substitutions,
    }
    gates = {}
    for k, th in THRESHOLDS.items():
        v = results[k]
        gates[k] = (v <= th) if k in ("protected_attribute_hits", "automatic_adverse_actions", "fairness_max_delta",
                                      "unapproved_profile_substitutions") else (v is not None and v >= th)
    report = {"generated": TODAY.isoformat(), "thresholds": THRESHOLDS, "results": results, "gates": gates, "all_passed": all(gates.values()),
              "fairness_deltas": fairness, "adversarial": adv_results, "regression": regression, "scores": scores, "notes": notes}
    out = EV / "reports"
    out.mkdir(exist_ok=True)
    (out / "gate-report.json").write_text(json.dumps(report, indent=2))
    md = ["# Phase 2 quality-gate report", "", f"Generated {report['generated']} · All gates passed: **{report['all_passed']}**", "", "| Gate | Threshold | Result | Pass |", "|---|---|---|---|"]
    md += [f"| {k} | {THRESHOLDS[k]} | {results[k]} | {'yes' if gates[k] else 'NO'} |" for k in THRESHOLDS]
    md += ["", "## Fairness deltas (alignment index vs base)", "", *[f"- {k}: {v}" for k, v in fairness.items()], "", "## Adversarial", "", *[f"- {k}: {'pass' if v else 'FAIL'}" for k, v in adv_results.items()],
           "", f"## Regression: {regression}", "", "## Notes", "", *([f"- {n}" for n in notes] or ["- none"])]
    (out / "gate-report.md").write_text("\n".join(md))
    (EV / "reports" / "_gate_audit.jsonl").unlink(missing_ok=True)
    return report


if __name__ == "__main__":
    rep = run(update_baseline="--update-baseline" in sys.argv)
    print(json.dumps({"all_passed": rep["all_passed"], "results": rep["results"], "notes": rep["notes"]}, indent=2))
    sys.exit(0 if rep["all_passed"] else 1)
