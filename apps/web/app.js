"use strict";
const $ = (id) => document.getElementById(id);
const state = { resume: null, jobs: [], selected: null, profile: null };

async function api(path, opts) {
  const r = await fetch(path, opts);
  const ct = r.headers.get("content-type") || "";
  const body = ct.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new Error(typeof body === "string" ? body : (body.detail || body.error || "request failed"));
  return body;
}
const b64 = (file) => new Promise((res, rej) => {
  const fr = new FileReader();
  fr.onload = () => res(String(fr.result).split(",")[1]);
  fr.onerror = rej;
  fr.readAsDataURL(file);
});
function status(msg, err) { const s = $("status"); s.hidden = false; s.className = "status" + (err ? " err" : ""); s.innerHTML = msg; }
function busy(msg) { status('<span class="spinner"></span>' + msg); }

/* ---------------------------------------------------------------- resume */
function renderResume() {
  const has = !!state.resume;
  $("resume-empty").hidden = has;
  $("resume-present").hidden = !has;
  if (!has) return;
  const r = state.resume;
  $("resume-name").textContent = r.filename;
  $("resume-meta").textContent = `${(r.byte_size / 1024).toFixed(0)} KB · sha256 ${r.sha256.slice(0, 10)}`;
  const p = r.parseability;
  const cls = p.parseability_score >= 80 ? "ok" : p.parseability_score >= 60 ? "warn" : "bad";
  $("resume-parse").innerHTML =
    `Parseability <b class="${cls}">${p.parseability_score}/100</b> · ${r.evidence_count} evidence items` +
    (p.ocr_required ? "<br><b>Image-only: OCR required, not available</b>" : "") +
    (p.hidden_text_suspected ? "<br>Hidden text flagged" : "") +
    (p.table_or_column_interference ? "<br>Tables/columns may affect reading order" : "") +
    "<br><span style='font-size:11px'>Document readiness only — not a measure of your suitability.</span>";
}
async function uploadResume(file) {
  busy("Reading resume…");
  try {
    state.resume = await api("/api/v1/resumes", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, content_b64: await b64(file) }),
    });
    renderResume(); refreshButtons();
    status(`Resume added. ${state.jobs.length ? "Select a job and screen." : "Now add a LinkedIn job PDF."}`);
  } catch (e) { status("Resume rejected: " + e.message, true); }
}

/* ---------------------------------------------------------------- jobs */
function renderJobs() {
  const ul = $("job-list"); ul.innerHTML = "";
  state.jobs.forEach((j) => {
    const li = document.createElement("li");
    if (state.selected === j.job_document_id) li.classList.add("sel");
    li.innerHTML = `<div><div>${j.role_title || j.filename}</div>
      <div class="jmeta">${j.employer || "employer not detected"} · ${j.application_platform} → ${j.profile_id.replace(/_/g, " ")}</div></div>`;
    const del = document.createElement("button");
    del.className = "danger"; del.textContent = "Remove";
    del.onclick = async (ev) => {
      ev.stopPropagation();
      await api("/api/v1/jobs/" + j.job_document_id, { method: "DELETE" });
      state.jobs = state.jobs.filter((x) => x.job_document_id !== j.job_document_id);
      if (state.selected === j.job_document_id) state.selected = state.jobs[0]?.job_document_id || null;
      renderJobs(); refreshButtons();
    };
    li.appendChild(del);
    li.onclick = () => { state.selected = j.job_document_id; renderJobs(); refreshButtons(); };
    ul.appendChild(li);
  });
}
async function uploadJobs(files) {
  for (const f of files) {
    busy(`Extracting job content from ${f.name}…`);
    try {
      const j = await api("/api/v1/jobs/linkedin", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: f.name, content_b64: await b64(f) }),
      });
      state.jobs.push(j); state.selected = j.job_document_id;
    } catch (e) { status(`Could not read ${f.name}: ${e.message}`, true); }
  }
  renderJobs(); refreshButtons();
  if (state.jobs.length) status(state.resume ? "Ready. Press “Screen resume against job”." : "Job added. Now add your resume.");
}

/* ---------------------------------------------------------------- run */
function tiles(a) {
  const t = [];
  const push = (k, v, cls, small) => t.push(`<div class="tile ${cls || ""}"><div class="k">${k}</div><div class="v${small ? " small" : ""}">${v}</div></div>`);
  const idx = a.alignment_index;
  push("Documented alignment", idx === null ? "n/a" : idx, idx === null ? "warn" : idx >= 70 ? "ok" : idx >= 55 ? "warn" : "bad");
  push("Band", a.band_label, "", true);
  push("Eligibility", a.eligibility_status.replace(/_/g, " "), a.eligibility_status === "meets_declared_eligibility" ? "ok" : "warn", true);
  push("Evidence confidence", a.evidence_confidence, a.evidence_confidence >= 0.75 ? "ok" : "warn");
  push("Application platform", a.ats.application_platform, "", true);
  push("Profile applied", a.profile_display_name, a.ats.has_approved_knowledge_profile ? "" : "warn", true);
  push("Critical gaps", a.critical_gaps.length, a.critical_gaps.length ? "bad" : "ok");
  push("Recommendations", a.recommendations.length, "");
  push("Likely questions", a.questions.length, "");
  $("summary").hidden = false;
  $("summary").innerHTML = t.join("");
}
async function run() {
  if (!state.resume || !state.selected) return;
  busy("Screening resume against the employer's stated requirements…");
  $("summary").hidden = true; $("report").innerHTML = "";
  try {
    const res = await api("/api/v1/assessments", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_document_id: state.selected, resume_id: state.resume.resume_id, mode: $("mode").value }),
    });
    tiles(res.assessment);
    $("report").innerHTML = md(res.report_markdown);
    $("versions").textContent = "assessment " + res.assessment.assessment_id + " · rubric " + (res.assessment.versions.rubric || "");
    status(`Done. Assessment ${res.assessment.assessment_id}.`);
  } catch (e) { status("Screening failed: " + e.message, true); }
}
async function runMulti() {
  if (!state.resume || state.jobs.length < 2) return;
  busy("Assessing the resume against every job…");
  try {
    const res = await api("/api/v1/multi-job-reviews", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_id: state.resume.resume_id, job_document_ids: state.jobs.map((j) => j.job_document_id) }),
    });
    $("summary").hidden = true;
    $("report").innerHTML = md(res.report_markdown);
    status("Multi-job review complete.");
  } catch (e) { status("Multi-job review failed: " + e.message, true); }
}
async function runProfile() {
  if (!state.resume || !state.profile) return;
  busy("Comparing profile with resume…");
  try {
    const res = await api("/api/v1/profile-reviews", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_id: state.resume.resume_id, filename: state.profile.name,
                             content_b64: await b64(state.profile), authorisation_confirmed: $("profile-auth").checked }),
    });
    $("summary").hidden = true;
    $("report").innerHTML = md(res.report_markdown);
    status("Profile review complete.");
  } catch (e) { status("Profile review failed: " + e.message, true); }
}

/* ---------------------------------------------------------------- tiny markdown renderer */
function md(src) {
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])_([^_]+)_/g, "$1<em>$2</em>");
  const out = []; const lines = src.split("\n");
  let inList = false, inTable = false;
  const closeList = () => { if (inList) { out.push("</ul>"); inList = false; } };
  const closeTable = () => { if (inTable) { out.push("</tbody></table>"); inTable = false; } };
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (/^\s*$/.test(l)) { closeList(); closeTable(); continue; }
    if (/^<\/?details|^<summary/.test(l.trim())) { closeList(); closeTable(); out.push(l); continue; }
    const h = l.match(/^(#{1,4})\s+(.*)$/);
    if (h) { closeList(); closeTable(); out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); continue; }
    if (/^\|/.test(l)) {
      const cells = l.split("|").slice(1, -1).map((c) => c.trim());
      if (/^\|[\s:|-]+\|?$/.test(l)) continue;
      if (!inTable) { out.push("<table><thead><tr>" + cells.map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead><tbody>"); inTable = true; }
      else out.push("<tr>" + cells.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>");
      continue;
    }
    closeTable();
    if (/^>\s?/.test(l)) { closeList(); out.push(`<blockquote>${inline(l.replace(/^>\s?/, ""))}</blockquote>`); continue; }
    const li = l.match(/^(\s*)[-*]\s+(.*)$/);
    if (li) { if (!inList) { out.push("<ul>"); inList = true; } out.push(`<li>${inline(li[2])}</li>`); continue; }
    const ol = l.match(/^\s*\d+\.\s+(.*)$/);
    if (ol) { if (!inList) { out.push("<ul>"); inList = true; } out.push(`<li>${inline(ol[1])}</li>`); continue; }
    closeList();
    out.push(`<p>${inline(l)}</p>`);
  }
  closeList(); closeTable();
  return out.join("\n");
}

/* ---------------------------------------------------------------- wiring */
function refreshButtons() {
  $("run").disabled = !(state.resume && state.selected);
  $("run-multi").disabled = !(state.resume && state.jobs.length >= 2);
  $("run-profile").disabled = !(state.resume && state.profile && $("profile-auth").checked);
}
function dropzone(label, input, handler) {
  ["dragenter", "dragover"].forEach((e) => label.addEventListener(e, (ev) => { ev.preventDefault(); label.classList.add("over"); }));
  ["dragleave", "drop"].forEach((e) => label.addEventListener(e, () => label.classList.remove("over")));
  label.addEventListener("drop", (ev) => { ev.preventDefault(); if (ev.dataTransfer.files.length) handler(ev.dataTransfer.files); });
  input.addEventListener("change", () => { if (input.files.length) handler(input.files); input.value = ""; });
}
document.addEventListener("DOMContentLoaded", () => {
  dropzone($("resume-file").closest("label"), $("resume-file"), (files) => uploadResume(files[0]));
  dropzone($("job-file").closest("label"), $("job-file"), (files) => uploadJobs([...files]));
  dropzone($("profile-file").closest("label"), $("profile-file"), (files) => {
    state.profile = files[0];
    $("profile-file").closest("label").querySelector("strong").textContent = files[0].name;
    refreshButtons();
  });
  $("resume-replace").onclick = () => $("resume-file").click();
  $("resume-delete").onclick = async () => {
    if (!state.resume) return;
    await api("/api/v1/resumes/" + state.resume.resume_id, { method: "DELETE" });
    state.resume = null; renderResume(); refreshButtons();
    $("summary").hidden = true; $("report").innerHTML = "";
    status("Resume deleted. Add a resume to begin.");
  };
  $("profile-auth").onchange = refreshButtons;
  $("run").onclick = run;
  $("run-multi").onclick = runMulti;
  $("run-profile").onclick = runProfile;
  api("/api/v1/health").then((h) => { $("versions").textContent = `core ${h.core_version} · schema ${h.schema_version} · rubric ${h.rubric}`; }).catch(() => {});
});
