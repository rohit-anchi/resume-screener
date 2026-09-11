"""Standard-library HTTP API and static host for the candidate two-input workflow (ADR-002).

Localhost only; RBAC deferred (TM-05). Documents are sent as base64 in JSON bodies.

Endpoints
  GET    /                                  static single-page app
  GET    /api/v1/health
  POST   /api/v1/resumes                    {filename, content_b64}        add / replace
  GET    /api/v1/resumes/{id}
  DELETE /api/v1/resumes/{id}
  POST   /api/v1/jobs/linkedin              {filename, content_b64}        LinkedIn job PDF
  GET    /api/v1/jobs/{id}                  full job document (blocks + classification)
  DELETE /api/v1/jobs/{id}
  POST   /api/v1/assessments                {job_document_id, resume_id, mode, answers?}
  GET    /api/v1/assessments/{id}
  GET    /api/v1/assessments/{id}/report?mode=
  GET    /api/v1/assessments/{id}/audit
  POST   /api/v1/assessments/{id}/review    ReviewAction
  POST   /api/v1/multi-job-reviews          {resume_id, job_document_ids[]}
  POST   /api/v1/profile-reviews            {resume_id, filename, content_b64, authorisation_confirmed}
  GET    /api/v1/profiles | /api/v1/rubrics
  Phase 2 endpoints for plain-text jobs/candidates/screenings remain available.
"""
from __future__ import annotations

import base64
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages"))

from screening_core import __version__ as CORE_VERSION  # noqa: E402
from screening_core.assessment import eligibility_rules_from_job, job_document_from_pdf, run_assessment  # noqa: E402
from screening_core.audit.review import ReviewService  # noqa: E402
from screening_core.audit.store import AuditStore  # noqa: E402
from screening_core.ingestion.service import ingest  # noqa: E402
from screening_core.modules import multi_job, profile_review  # noqa: E402
from screening_core.pipeline import build_candidate_from_bytes, build_job, run_screening  # noqa: E402
from screening_core.profiles.loader import list_profiles, load_profile  # noqa: E402
from screening_core.reports.assessment_report import render as render_assessment  # noqa: E402
from screening_core.reports.render import candidate_report, recruiter_report  # noqa: E402
from screening_core.schemas.models import SCHEMA_VERSION, ApplicationAnswer, Mode, ReviewAction, ScreeningRequest  # noqa: E402
from screening_core.scoring.rubrics import load_rubric  # noqa: E402

ID_RX = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_BODY = 24 * 1024 * 1024
WEB = ROOT / "apps" / "web"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/app.css": ("app.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8")}


class State:
    def __init__(self, audit_path: Path):
        self.resumes: dict[str, dict] = {}      # resume_id -> {candidate, filename}
        self.job_docs: dict[str, object] = {}   # job_document_id -> JobDocument
        self.assessments: dict[str, dict] = {}  # assessment_id -> {assessment, screening, job}
        self.jobs, self.candidates, self.screenings = {}, {}, {}
        self.audit = AuditStore(audit_path)
        self.review = ReviewService(self.audit)


STATE = State(ROOT / "data" / "audit" / "events.jsonl")


def _resume_summary(resume_id: str, entry: dict) -> dict:
    cand = entry["candidate"]
    return {"resume_id": resume_id, "candidate_id": cand.candidate_id, "filename": cand.document.filename,
            "byte_size": cand.document.byte_size, "sha256": cand.document.sha256,
            "page_count": cand.document.page_count, "accepted": cand.document.accepted,
            "evidence_count": len(cand.evidence), "contradictions": cand.contradictions,
            "document_findings": [f.model_dump() for f in cand.document.findings],
            "parseability": cand.parseability.model_dump()}


def _job_summary(jd) -> dict:
    return {"job_document_id": jd.job_document_id, "filename": jd.filename, "employer": jd.employer,
            "role_title": jd.role_title, "location": jd.location, "employment_type": jd.employment_type,
            "workplace_type": jd.workplace_type, "compensation_text": jd.compensation_text,
            "listing_source": jd.listing_source, "application_platform": jd.ats.application_platform.value,
            "application_url": jd.ats.application_url, "has_approved_knowledge_profile": jd.ats.has_approved_knowledge_profile,
            "profile_id": jd.ats.selected_profile_id, "profile_reason": jd.ats.profile_selection_reason,
            "block_count": len(jd.blocks), "scored_blocks": sum(b.allowed_for_requirements for b in jd.blocks),
            "excluded_blocks": len(jd.excluded_block_ids), "excluded_categories": jd.excluded_categories,
            "extraction_warnings": jd.extraction_warnings}


class Handler(BaseHTTPRequestHandler):
    server_version = "Screener/2.1"

    # ---------------------------------------------------------------- helpers
    def _send(self, code: int, body, content_type="application/json"):
        data = body.encode() if isinstance(body, str) else json.dumps(body, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", "0"))
        if n > MAX_BODY:
            raise ValueError("body too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def _parts(self, path: str) -> list[str]:
        return [p for p in path.split("/") if p]

    def _require_id(self, value: str) -> str:
        if not ID_RX.match(value):
            raise ValueError("invalid identifier")
        return value

    # ---------------------------------------------------------------- GET
    def do_GET(self):
        u = urlparse(self.path)
        if u.path in STATIC:
            name, ctype = STATIC[u.path]
            f = WEB / name
            if not f.exists():
                return self._send(404, {"error": "ui not found"})
            return self._send(200, f.read_text(encoding="utf-8"), ctype)
        p = self._parts(u.path)
        if p[:2] != ["api", "v1"]:
            return self._send(404, {"error": "not found"})
        try:
            res = p[2] if len(p) > 2 else ""
            rid = self._require_id(p[3]) if len(p) > 3 else None
            sub = p[4] if len(p) > 4 else None
            q = parse_qs(u.query)
            if res == "health":
                r = load_rubric()
                return self._send(200, {"status": "ok", "core_version": CORE_VERSION, "schema_version": SCHEMA_VERSION,
                                        "rubric": f"{r.rubric_id}@{r.rubric_version}", "profiles": list_profiles(),
                                        "resumes": len(STATE.resumes), "job_documents": len(STATE.job_docs),
                                        "assessments": len(STATE.assessments)})
            if res == "profiles":
                return self._send(200, {"profiles": [load_profile(x).model_dump() for x in list_profiles()]})
            if res == "rubrics":
                return self._send(200, {"rubrics": [load_rubric().model_dump()]})
            if res == "resumes" and rid:
                if rid not in STATE.resumes:
                    return self._send(404, {"error": "resume not found"})
                return self._send(200, _resume_summary(rid, STATE.resumes[rid]))
            if res == "jobs" and rid:
                if rid in STATE.job_docs:
                    return self._send(200, STATE.job_docs[rid].model_dump())
                if rid in STATE.jobs:
                    return self._send(200, STATE.jobs[rid].model_dump())
                return self._send(404, {"error": "job not found"})
            if res == "assessments" and rid:
                if rid not in STATE.assessments:
                    return self._send(404, {"error": "assessment not found"})
                entry = STATE.assessments[rid]
                if sub == "report":
                    mode = Mode(q.get("mode", [entry["assessment"].mode])[0])
                    view = STATE.review.apply(entry["screening"])
                    return self._send(200, render_assessment(entry["assessment"], view, mode=mode), "text/markdown; charset=utf-8")
                if sub == "audit":
                    ok, msg = STATE.audit.verify_chain()
                    return self._send(200, {"chain_valid": ok, "detail": msg,
                                            "events": [e.model_dump() for e in STATE.audit.events(entry["screening"].screening_id)]})
                return self._send(200, {"assessment": entry["assessment"].model_dump()})
            if res == "screenings" and rid:
                if rid not in STATE.screenings:
                    return self._send(404, {"error": "screening not found"})
                obj = STATE.screenings[rid]
                if sub == "report":
                    mode = q.get("mode", ["candidate"])[0]
                    view = STATE.review.apply(obj)
                    text = recruiter_report(view, STATE.audit.events(rid)) if mode == "recruiter" else candidate_report(view)
                    return self._send(200, text, "text/markdown; charset=utf-8")
                if sub == "audit":
                    ok, msg = STATE.audit.verify_chain()
                    return self._send(200, {"chain_valid": ok, "detail": msg, "events": [e.model_dump() for e in STATE.audit.events(rid)]})
                return self._send(200, STATE.review.apply(obj).model_dump())
            if res in ("jobs", "candidates") and not rid:
                store = STATE.job_docs if res == "jobs" else STATE.resumes
                return self._send(200, {"count": len(store), "ids": sorted(store)})
            return self._send(404, {"error": "not found"})
        except ValueError as e:
            return self._send(400, {"error": "bad_request", "detail": str(e)})
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": type(e).__name__, "detail": str(e)})

    # ---------------------------------------------------------------- POST
    def do_POST(self):
        u = urlparse(self.path)
        p = self._parts(u.path)
        if p[:2] != ["api", "v1"]:
            return self._send(404, {"error": "not found"})
        try:
            res = p[2] if len(p) > 2 else ""
            rid = self._require_id(p[3]) if len(p) > 3 else None
            sub = p[4] if len(p) > 4 else None
            body = self._body()

            if res == "resumes" and not rid:
                data = base64.b64decode(body["content_b64"])
                cand = build_candidate_from_bytes(f"CAND-{len(STATE.resumes) + 1}", body["filename"], data)
                if not cand.document.accepted:
                    return self._send(400, {"error": "resume_rejected",
                                            "detail": "; ".join(f.message for f in cand.document.findings if f.severity == "critical"),
                                            "findings": [f.model_dump() for f in cand.document.findings]})
                resume_id = f"RES-{cand.document.sha256[:10]}"
                STATE.resumes = {resume_id: {"candidate": cand, "filename": body["filename"]}}  # single active resume
                STATE.candidates[cand.candidate_id] = cand
                STATE.audit.append("resume_added", body.get("actor", "web"), {"resume_id": resume_id, "sha256": cand.document.sha256,
                                                                             "filename": body["filename"], "replaced_previous": True})
                return self._send(201, _resume_summary(resume_id, STATE.resumes[resume_id]))

            if res == "jobs" and rid == "linkedin":
                data = base64.b64decode(body["content_b64"])
                jd = job_document_from_pdf(body["filename"], data)
                STATE.job_docs[jd.job_document_id] = jd
                STATE.audit.append("job_document_added", body.get("actor", "web"),
                                   {"job_document_id": jd.job_document_id, "sha256": jd.sha256, "employer": jd.employer,
                                    "role_title": jd.role_title, "application_platform": jd.ats.application_platform.value,
                                    "profile_id": jd.ats.selected_profile_id, "excluded_blocks": len(jd.excluded_block_ids)})
                return self._send(201, _job_summary(jd))

            if res == "assessments" and not rid:
                jd = STATE.job_docs.get(body["job_document_id"])
                entry = STATE.resumes.get(body["resume_id"])
                if jd is None or entry is None:
                    return self._send(404, {"error": "job document or resume not found"})
                mode = Mode(body.get("mode", "candidate"))
                answers = [ApplicationAnswer(question_id=a["question_id"], question_text=a.get("question_text", ""), answer=a["answer"])
                           for a in body.get("answers", [])]
                # first pass establishes the employer's stated eligibility criteria
                a, s, job = run_assessment(jd, entry["candidate"], mode=mode, answers=answers)
                if answers:
                    # re-evaluate with rules derived from the employer's own job document
                    a, s, job = run_assessment(jd, entry["candidate"], mode=mode, answers=answers,
                                               employer_rules=eligibility_rules_from_job(job))
                STATE.assessments[a.assessment_id] = {"assessment": a, "screening": s, "job": job}
                STATE.screenings[s.screening_id] = s
                STATE.audit.append("assessment_created", body.get("actor", "web"),
                                   {"assessment_id": a.assessment_id, "screening_id": s.screening_id, "mode": a.mode,
                                    "job_document_id": jd.job_document_id, "resume_id": body["resume_id"],
                                    "alignment_index": a.alignment_index, "eligibility": a.eligibility_status,
                                    "platform": a.ats.application_platform.value, "profile": a.profile_id,
                                    "versions": a.versions}, s.screening_id)
                return self._send(201, {"assessment": a.model_dump(),
                                        "report_markdown": render_assessment(a, s, mode=mode),
                                        "eligibility_questions": [{"requirement_id": r.requirement_id, "text": r.text}
                                                                  for r in job.requirements if r.importance.value == "eligibility"]})

            if res == "assessments" and rid and sub in ("review", "override"):
                entry = STATE.assessments.get(rid)
                if entry is None:
                    return self._send(404, {"error": "assessment not found"})
                body.setdefault("screening_id", entry["screening"].screening_id)
                if sub == "override":
                    body["action"] = "override_score"
                action = ReviewAction.model_validate(body)
                view = STATE.review.record(entry["screening"], action)
                return self._send(200, {"assessment": entry["assessment"].model_dump(),
                                        "report_markdown": render_assessment(entry["assessment"], view, mode=Mode(entry["assessment"].mode))})

            if res == "multi-job-reviews" and not rid:
                entry = STATE.resumes.get(body["resume_id"])
                if entry is None:
                    return self._send(404, {"error": "resume not found"})
                ids = [self._require_id(x) for x in body["job_document_ids"]]
                missing = [x for x in ids if x not in STATE.job_docs]
                if missing:
                    return self._send(404, {"error": "job documents not found", "detail": missing})
                items = [run_assessment(STATE.job_docs[x], entry["candidate"], mode=Mode.candidate) for x in ids]
                r = multi_job.review(entry["candidate"].candidate_id, items)
                for a, s, _ in items:
                    STATE.assessments[a.assessment_id] = {"assessment": a, "screening": s, "job": _}
                STATE.audit.append("multi_job_review", body.get("actor", "web"),
                                   {"review_id": r.review_id, "job_document_ids": ids,
                                    "priority": r.suggested_priority}, None)
                return self._send(201, {"review": r.model_dump(), "report_markdown": multi_job.render(r)})

            if res == "profile-reviews" and not rid:
                entry = STATE.resumes.get(body["resume_id"])
                if entry is None:
                    return self._send(404, {"error": "resume not found"})
                if not body.get("authorisation_confirmed"):
                    return self._send(403, {"error": "authorisation_required",
                                            "detail": "Profile comparison requires explicit authorisation for the supplied document."})
                doc = ingest("resume", body["filename"], base64.b64decode(body["content_b64"]))
                if not doc.accepted:
                    return self._send(400, {"error": "profile_rejected",
                                            "detail": "; ".join(f.message for f in doc.findings if f.severity == "critical")})
                r = profile_review.review(entry["candidate"].candidate_id, doc, entry["candidate"], authorisation_confirmed=True)
                STATE.audit.append("profile_review", body.get("actor", "web"),
                                   {"review_id": r.review_id, "profile_sha256": doc.sha256, "authorised": True}, None)
                return self._send(201, {"review": r.model_dump(), "report_markdown": profile_review.render(r)})

            # ---- Phase 2 plain-text endpoints ----
            if res == "jobs" and not rid:
                self._require_id(body["job_id"])
                job = build_job(body["job_id"], body.get("title", body["job_id"]), body["filename"],
                                base64.b64decode(body["content_b64"]), body.get("media_type"))
                STATE.jobs[job.job_id] = job
                STATE.audit.append("job_created", body.get("actor", "api"), {"job_id": job.job_id, "sha256": job.document.sha256})
                return self._send(201, job.model_dump())
            if res == "candidates" and not rid:
                self._require_id(body["candidate_id"])
                cand = build_candidate_from_bytes(body["candidate_id"], body["filename"],
                                                  base64.b64decode(body["content_b64"]), body.get("media_type"))
                STATE.candidates[cand.candidate_id] = cand
                STATE.audit.append("candidate_created", body.get("actor", "api"), {"candidate_id": cand.candidate_id, "sha256": cand.document.sha256})
                return self._send(201, cand.model_dump(exclude={"document": {"extracted_text"}}))
            if res == "screenings" and not rid:
                req = ScreeningRequest.model_validate(body)
                if req.job_id not in STATE.jobs or req.candidate_id not in STATE.candidates:
                    return self._send(404, {"error": "job or candidate not found"})
                result = run_screening(STATE.jobs[req.job_id], STATE.candidates[req.candidate_id], req)
                STATE.screenings[result.screening_id] = result
                STATE.audit.append("screening_created", req.initiated_by,
                                   {"versions": result.versions, "alignment_index": result.score.alignment_index,
                                    "eligibility": result.eligibility.status.value,
                                    "recommended_human_action": result.recommended_human_action.value}, result.screening_id)
                return self._send(201, result.model_dump())
            if res == "screenings" and rid and sub in ("review", "override"):
                if rid not in STATE.screenings:
                    return self._send(404, {"error": "screening not found"})
                body.setdefault("screening_id", rid)
                if sub == "override":
                    body["action"] = "override_score"
                view = STATE.review.record(STATE.screenings[rid], ReviewAction.model_validate(body))
                return self._send(200, view.model_dump())
            return self._send(405, {"error": "method not allowed"})
        except KeyError as e:
            return self._send(400, {"error": "missing_field", "detail": str(e)})
        except (ValueError, PermissionError) as e:
            return self._send(400, {"error": type(e).__name__, "detail": str(e)})
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": type(e).__name__, "detail": str(e)})

    # ---------------------------------------------------------------- DELETE
    def do_DELETE(self):
        p = self._parts(urlparse(self.path).path)
        if p[:2] != ["api", "v1"] or len(p) < 4:
            return self._send(404, {"error": "not found"})
        try:
            res, rid = p[2], self._require_id(p[3])
            if res == "resumes":
                if rid not in STATE.resumes:
                    return self._send(404, {"error": "resume not found"})
                sha = STATE.resumes[rid]["candidate"].document.sha256
                del STATE.resumes[rid]
                STATE.audit.append("resume_deleted", "web", {"resume_id": rid, "sha256": sha})
                return self._send(200, {"deleted": rid})
            if res == "jobs":
                if rid not in STATE.job_docs:
                    return self._send(404, {"error": "job document not found"})
                del STATE.job_docs[rid]
                STATE.audit.append("job_document_deleted", "web", {"job_document_id": rid})
                return self._send(200, {"deleted": rid})
            return self._send(404, {"error": "not found"})
        except ValueError as e:
            return self._send(400, {"error": "bad_request", "detail": str(e)})

    def log_message(self, fmt, *args):
        return


def serve(host="127.0.0.1", port=8080):
    print(f"Screener UI: http://{host}:{port}/")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve(port=int(sys.argv[1]) if len(sys.argv) > 1 else 8080)
