"""Ingestion service: safety -> extraction -> redaction -> IngestedDocument."""
from __future__ import annotations

import hashlib
import uuid

from ..schemas.models import DocumentFinding, IngestedDocument, SourceLocation
from ..security.injection import detect_injection, keyword_stuffing, repeated_lines
from ..security.redaction import redact
from . import safety
from .extract import PARSER_VERSION, extract
from .safety import MAX_PAGES


def ingest(kind: str, filename: str, data: bytes, declared_media_type: str | None = None, *, document_id: str | None = None) -> IngestedDocument:
    doc_id = document_id or f"DOC-{uuid.uuid4().hex[:10]}"
    sha = hashlib.sha256(data).hexdigest()
    s = safety.validate(filename, data, declared_media_type)
    findings = [DocumentFinding(code=c, severity=sev, message=m) for c, sev, m in s.findings]
    text, redacted, pages = "", "", None
    if s.accepted:
        try:
            ex = extract(s.extension, data)
        except Exception as e:  # malformed content
            findings.append(DocumentFinding(code="extraction_failed", severity="critical", message=f"Extraction failed: {type(e).__name__}"))
            s.accepted = False
        else:
            text, pages = ex.text, ex.page_count
            if pages and pages > MAX_PAGES:
                findings.append(DocumentFinding(code="excessive_pages", severity="critical", message=f"{pages} pages exceeds limit {MAX_PAGES}"))
                s.accepted = False
            if ex.image_only:
                findings.append(DocumentFinding(code="image_only_content", severity="warning", message="No extractable text; OCR required and not available. Qualification scoring will be suppressed."))
            if ex.hidden_text_suspected:
                findings.append(DocumentFinding(code="hidden_text_suspected", severity="warning", message="Very small or white text detected; content retained but flagged"))
            if ex.tables_or_columns_suspected:
                findings.append(DocumentFinding(code="layout_interference", severity="info", message="Tables or columns may affect reading order"))
            for note in ex.notes:
                findings.append(DocumentFinding(code="extraction_note", severity="info", message=note))
            for phrase, a, b in detect_injection(text):
                findings.append(DocumentFinding(code="injection_suspected", severity="warning", message="Instruction-like text found in document; treated as data only",
                                                location=SourceLocation(document_id=doc_id, char_start=a, char_end=b, text_span=phrase)))
            stuffed = keyword_stuffing(text)
            if stuffed:
                findings.append(DocumentFinding(code="keyword_repetition", severity="info", message=f"Excessive repetition of: {', '.join(stuffed[:8])}"))
            dup = repeated_lines(text)
            if dup:
                findings.append(DocumentFinding(code="duplicate_content", severity="info", message=f"{dup} duplicated line(s)"))
            if kind == "resume":
                redacted = redact(text).redacted_text
            else:
                redacted = text
    return IngestedDocument(document_id=doc_id, kind=kind, filename=filename, media_type=s.media_type, sha256=sha, byte_size=len(data),
                            page_count=pages, extracted_text=text, redacted_text=redacted, accepted=s.accepted, findings=findings, parser_version=PARSER_VERSION)
