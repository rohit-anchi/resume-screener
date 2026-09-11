"""Document safety validation. Uploaded files are untrusted content (TM-03)."""
from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from io import BytesIO

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 15
ALLOWED = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}
MAGIC = {".pdf": b"%PDF", ".docx": b"PK\x03\x04"}


@dataclass
class SafetyResult:
    accepted: bool
    media_type: str
    extension: str
    findings: list[tuple[str, str, str]] = field(default_factory=list)  # code, severity, message

    def add(self, code: str, severity: str, message: str) -> None:
        self.findings.append((code, severity, message))
        if severity == "critical":
            self.accepted = False


def validate(filename: str, data: bytes, declared_media_type: str | None = None) -> SafetyResult:
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    res = SafetyResult(accepted=True, media_type=ALLOWED.get(ext, "application/octet-stream"), extension=ext)
    if ext not in ALLOWED:
        res.add("unsupported_type", "critical", f"Extension {ext or '(none)'} not supported; allowed: pdf, docx, txt")
        return res
    if len(data) == 0:
        res.add("empty_file", "critical", "File is empty")
        return res
    if len(data) > MAX_BYTES:
        res.add("file_too_large", "critical", f"File exceeds {MAX_BYTES} bytes")
    if declared_media_type and declared_media_type != res.media_type:
        res.add("mime_mismatch", "critical", f"Declared media type {declared_media_type} does not match extension {ext}")
    if ext in MAGIC and not data.startswith(MAGIC[ext]):
        res.add("magic_mismatch", "critical", "File signature does not match extension")
    if ext == ".pdf":
        _check_pdf(data, res)
    elif ext == ".docx":
        _check_docx(data, res)
    elif ext == ".txt":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            res.add("invalid_encoding", "critical", "Text file is not UTF-8")
    return res


def _check_pdf(data: bytes, res: SafetyResult) -> None:
    low = data.lower()
    if b"/encrypt" in low:
        res.add("encrypted_pdf", "critical", "Password-protected or encrypted PDF is not accepted")
    if b"/javascript" in low or b"/js" in low:
        res.add("pdf_javascript", "critical", "PDF contains JavaScript actions")
    if b"/embeddedfile" in low:
        res.add("embedded_file", "critical", "PDF contains embedded files")
    if b"/launch" in low or b"/openaction" in low:
        res.add("pdf_action", "warning", "PDF contains automatic actions")
    if b"/uri" in low:
        res.add("pdf_links", "info", "PDF contains external links; links are not followed")


def _check_docx(data: bytes, res: SafetyResult) -> None:
    try:
        with zipfile.ZipFile(BytesIO(data)) as z:
            names = z.namelist()
            total = sum(i.file_size for i in z.infolist())
            if total > MAX_BYTES * 5:
                res.add("zip_bomb_suspected", "critical", "Decompressed size is excessive")
            if any(n.lower().endswith("vbaproject.bin") for n in names):
                res.add("macro_present", "critical", "Document contains macros")
            if any(n.startswith("word/embeddings/") for n in names):
                res.add("embedded_object", "critical", "Document contains embedded objects")
            if "word/document.xml" not in names:
                res.add("malformed_docx", "critical", "Missing word/document.xml")
            if any(n.startswith("word/media/") for n in names):
                res.add("images_present", "info", "Document contains images; images are not analysed")
    except zipfile.BadZipFile:
        res.add("malformed_docx", "critical", "Not a valid DOCX container")
