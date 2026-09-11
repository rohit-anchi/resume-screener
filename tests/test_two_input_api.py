import base64
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from apps.api import server

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "evaluation" / "fixtures" / "jobs"
RESUME = ROOT / "evaluation" / "fixtures" / "resumes" / "candidate-resume.local.pdf"
AMBER = JOBS / "amber-electric-director-of-product.linkedin.pdf"
XERO = JOBS / "xero-lead-product-manager-ai-enablement.linkedin.pdf"
b64 = lambda b: base64.b64encode(b).decode()


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    server.STATE = server.State(tmp_path_factory.mktemp("audit") / "events.jsonl")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


@pytest.mark.skipif(not RESUME.exists(), reason="local resume fixture not present")
def test_two_input_workflow(base):
    code, body = call(base, "GET", "/api/v1/health")
    assert code == 200 and json.loads(body)["status"] == "ok"

    # resume add
    code, body = call(base, "POST", "/api/v1/resumes", {"filename": RESUME.name, "content_b64": b64(RESUME.read_bytes())})
    assert code == 201
    resume = json.loads(body)
    assert resume["resume_id"].startswith("RES-") and resume["parseability"]["parseability_score"] >= 0

    # job add (LinkedIn PDF)
    code, body = call(base, "POST", "/api/v1/jobs/linkedin", {"filename": AMBER.name, "content_b64": b64(AMBER.read_bytes())})
    assert code == 201
    job = json.loads(body)
    assert job["employer"] == "Amber Electric" and job["application_platform"] == "lever" and job["profile_id"] == "lever_informed"
    assert job["excluded_blocks"] > 0 and job["scored_blocks"] > 0

    # assessment
    code, body = call(base, "POST", "/api/v1/assessments",
                      {"job_document_id": job["job_document_id"], "resume_id": resume["resume_id"], "mode": "candidate"})
    assert code == 201
    payload = json.loads(body)
    a, report = payload["assessment"], payload["report_markdown"]
    assert a["ats"]["application_platform"] == "lever"
    assert a["component_scores"] and a["evidence_confidence"] >= 0
    for section in ("1. Job extraction", "2. LinkedIn content classification", "3. Downstream ATS detection",
                    "4. Resume parseability", "5. Eligibility findings", "6. Documented alignment",
                    "7. Requirement-by-requirement evidence mapping", "8. Critical gaps", "9. Missing or ambiguous evidence",
                    "10. Resume-tailoring recommendations", "11. Recruiter and hiring-manager questions",
                    "12. Platform-informed screening scenarios", "13. Limitations", "14. Audit information"):
        assert section in report, section
    assert payload["eligibility_questions"], "Amber states eligibility criteria"

    # eligibility answers change the categorical result but never the weighted index
    qid = payload["eligibility_questions"][0]["requirement_id"]
    code, body2 = call(base, "POST", "/api/v1/assessments",
                       {"job_document_id": job["job_document_id"], "resume_id": resume["resume_id"], "mode": "candidate",
                        "answers": [{"question_id": qid, "answer": "no"}]})
    assert code == 201
    a2 = json.loads(body2)["assessment"]
    assert a2["eligibility_status"] == "does_not_meet_declared_eligibility"
    assert a2["alignment_index"] == a["alignment_index"]

    # report endpoint + audit chain
    code, rep = call(base, "GET", f"/api/v1/assessments/{a['assessment_id']}/report?mode=recruiter_assist")
    assert code == 200 and "15. Human-review recommendation" in rep
    code, aud = call(base, "GET", f"/api/v1/assessments/{a['assessment_id']}/audit")
    assert code == 200 and json.loads(aud)["chain_valid"]

    # second job -> multi-job review
    code, body = call(base, "POST", "/api/v1/jobs/linkedin", {"filename": XERO.name, "content_b64": b64(XERO.read_bytes())})
    assert code == 201
    xero = json.loads(body)
    assert xero["application_platform"] == "ashby" and xero["profile_id"] == "platform_neutral"
    code, body = call(base, "POST", "/api/v1/multi-job-reviews",
                      {"resume_id": resume["resume_id"], "job_document_ids": [job["job_document_id"], xero["job_document_id"]]})
    assert code == 201
    mj = json.loads(body)
    assert len(mj["review"]["entries"]) == 2 and "documented suitability" in mj["review"]["caveat"]
    assert "not a hiring probability" in mj["review"]["caveat"]

    # profile review requires authorisation
    prof = ROOT / "evaluation" / "fixtures" / "profiles" / "candidate-linkedin-profile.local.pdf"
    if prof.exists():
        code, _ = call(base, "POST", "/api/v1/profile-reviews",
                       {"resume_id": resume["resume_id"], "filename": prof.name, "content_b64": b64(prof.read_bytes()),
                        "authorisation_confirmed": False})
        assert code == 403
        code, body = call(base, "POST", "/api/v1/profile-reviews",
                          {"resume_id": resume["resume_id"], "filename": prof.name, "content_b64": b64(prof.read_bytes()),
                           "authorisation_confirmed": True})
        assert code == 201 and json.loads(body)["review"]["authorisation_confirmed"] is True

    # replace and delete
    code, body = call(base, "POST", "/api/v1/resumes", {"filename": RESUME.name, "content_b64": b64(RESUME.read_bytes())})
    assert code == 201
    rid = json.loads(body)["resume_id"]
    assert call(base, "DELETE", f"/api/v1/resumes/{rid}")[0] == 200
    assert call(base, "GET", f"/api/v1/resumes/{rid}")[0] == 404
    assert call(base, "DELETE", f"/api/v1/jobs/{xero['job_document_id']}")[0] == 200


def test_ui_served(base):
    code, body = call(base, "GET", "/")
    assert code == 200 and "application readiness assessment" in body.lower()
    assert call(base, "GET", "/app.js")[0] == 200 and call(base, "GET", "/app.css")[0] == 200


def test_rejects_non_pdf_job_and_bad_ids(base):
    code, _ = call(base, "POST", "/api/v1/jobs/linkedin", {"filename": "job.txt", "content_b64": b64(b"hello")})
    assert code in (400, 500)
    assert call(base, "GET", "/api/v1/resumes/../../etc")[0] in (400, 404)
    assert call(base, "POST", "/api/v1/assessments", {"job_document_id": "nope", "resume_id": "nope"})[0] == 404
