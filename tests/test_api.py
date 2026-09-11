import base64
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from apps.api import server


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    server.STATE = server.State(tmp_path_factory.mktemp("audit") / "events.jsonl")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_full_api_flow(base, jd_bytes, resume_bytes):
    b64 = lambda b: base64.b64encode(b).decode()
    assert _call(base, "POST", "/api/v1/jobs", {"job_id": "J1", "title": "PM", "filename": "jd.txt", "content_b64": b64(jd_bytes)})[0] == 201
    code, body = _call(base, "POST", "/api/v1/candidates", {"candidate_id": "C1", "filename": "cv.txt", "content_b64": b64(resume_bytes)})
    assert code == 201 and "extracted_text" not in json.loads(body)["document"]
    code, body = _call(base, "POST", "/api/v1/screenings", {"job_id": "J1", "candidate_id": "C1", "screening_profile": "workday_informed", "mode": "recruiter_assist"})
    assert code == 201
    sid = json.loads(body)["screening_id"]
    code, rep = _call(base, "GET", f"/api/v1/screenings/{sid}/report?mode=candidate")
    assert code == 200 and "platform-informed" in rep
    code, body = _call(base, "POST", f"/api/v1/screenings/{sid}/override", {"actor": "rec", "actor_role": "recruiter", "reason": "Calibrated against panel", "new_value": 70})
    assert code == 200 and "human override recorded" in json.loads(body)["score"]["band_label"]
    code, body = _call(base, "GET", f"/api/v1/screenings/{sid}/audit")
    aud = json.loads(body)
    assert aud["chain_valid"] and any(e["event_type"] == "review.override_score" for e in aud["events"])
    assert _call(base, "GET", "/api/v1/profiles")[0] == 200 and _call(base, "GET", "/api/v1/rubrics")[0] == 200


def test_bad_ids_and_paths(base):
    assert _call(base, "GET", "/api/v1/jobs/../../etc")[0] in (400, 404)  # rejected as an invalid identifier
    assert _call(base, "POST", "/api/v1/jobs", {"job_id": "bad id!", "filename": "x.txt", "content_b64": ""})[0] == 400
    assert _call(base, "GET", "/api/v1/screenings/nope")[0] == 404
