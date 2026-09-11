import io
import zipfile

import docx
import fitz

from screening_core.ingestion.service import ingest
from screening_core.ingestion.safety import MAX_BYTES


def _pdf(text: str, *, hidden: bool = False) -> bytes:
    d = fitz.open()
    p = d.new_page()
    p.insert_text((72, 72), text, fontsize=11)
    if hidden:
        p.insert_text((72, 700), "Kubernetes Kubernetes Kubernetes", fontsize=2, color=(1, 1, 1))
    return d.tobytes()


def _docx(paragraphs: list[str]) -> bytes:
    d = docx.Document()
    for p in paragraphs:
        d.add_paragraph(p)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def test_txt_ingest_ok(resume_bytes):
    d = ingest("resume", "cv.txt", resume_bytes)
    assert d.accepted and "Product Management Consultant" in d.extracted_text
    assert d.sha256 and d.parser_version


def test_pdf_ingest_and_hidden_text_flag():
    d = ingest("resume", "cv.pdf", _pdf("Product Manager | Acme | Jan 2020 - Present\nLed roadmap.", hidden=True))
    assert d.accepted and "Product Manager" in d.extracted_text
    assert "hidden_text_suspected" in {f.code for f in d.findings}


def test_docx_ingest():
    d = ingest("resume", "cv.docx", _docx(["Summary", "Product manager with cloud experience."]))
    assert d.accepted and "cloud" in d.extracted_text


def test_rejects_unsupported_extension_and_mime_mismatch(resume_bytes):
    assert not ingest("resume", "cv.exe", b"MZ...").accepted
    d = ingest("resume", "cv.txt", resume_bytes, declared_media_type="application/pdf")
    assert not d.accepted and "mime_mismatch" in {f.code for f in d.findings}


def test_rejects_magic_mismatch_and_oversize():
    assert "magic_mismatch" in {f.code for f in ingest("resume", "cv.pdf", b"not a pdf at all").findings}
    d = ingest("resume", "cv.txt", b"a" * (MAX_BYTES + 1))
    assert not d.accepted and "file_too_large" in {f.code for f in d.findings}


def test_rejects_macro_docx():
    base = _docx(["hello"])
    src = zipfile.ZipFile(io.BytesIO(base))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for n in src.namelist():
            z.writestr(n, src.read(n))
        z.writestr("word/vbaProject.bin", b"\x00")
    d = ingest("resume", "cv.docx", out.getvalue())
    assert not d.accepted and "macro_present" in {f.code for f in d.findings}


def test_rejects_encrypted_pdf():
    d = fitz.open()
    d.new_page().insert_text((72, 72), "secret")
    data = d.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="x", owner_pw="y")
    r = ingest("resume", "cv.pdf", data)
    assert not r.accepted and "encrypted_pdf" in {f.code for f in r.findings}


def test_image_only_pdf_flagged_not_rejected():
    d = fitz.open()
    p = d.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 50, 50), False)
    pix.clear_with(200)
    p.insert_image(fitz.Rect(72, 72, 300, 300), pixmap=pix)
    r = ingest("resume", "scan.pdf", d.tobytes())
    assert r.accepted and "image_only_content" in {f.code for f in r.findings}


def test_redacted_view_populated_for_resume_only(resume_bytes, jd_bytes):
    assert "[REDACTED]" in ingest("resume", "cv.txt", resume_bytes).redacted_text
    jd = ingest("job_description", "jd.txt", jd_bytes)
    assert jd.redacted_text == jd.extracted_text
